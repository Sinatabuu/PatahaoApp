"""Recruitment snapshots and office schedules, using Kenya calendar dates."""
import csv
import io
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.http import HttpResponse
from django.db.models import Count
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from .models import PartnerApplication
from .staff_portal import PortalView

KENYA = ZoneInfo('Africa/Nairobi')


class ReportFilters(serializers.Serializer):
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)
    county = serializers.CharField(required=False, allow_blank=True, max_length=100)
    appointment_scope = serializers.ChoiceField(choices=('upcoming', 'past', 'all'), default='upcoming')

    def validate(self, data):
        for key in ('date_from', 'date_to'):
            if key in data and not 2000 <= data[key].year <= 2100:
                raise serializers.ValidationError({key: 'Choose a date between 2000 and 2100.'})
        if data.get('date_from') and data.get('date_to') and data['date_from'] > data['date_to']:
            raise serializers.ValidationError('The start date must be on or before the end date.')
        return data


def filtered_records(request):
    raw = {key: value for key, value in request.query_params.items() if value != ''}
    serializer = ReportFilters(data=raw)
    serializer.is_valid(raise_exception=True)
    filters = serializer.validated_data
    applications = PartnerApplication.objects.all()
    if filters.get('county'):
        applications = applications.filter(county__iexact=filters['county'])
    # Appointment dates and application dates are different report dimensions.
    appointments = applications.exclude(status__in=('declined', 'withdrawn')).filter(office_appointment__isnull=False)
    for field, direction, key in [('created_at', 'gte', 'date_from'), ('created_at', 'lt', 'date_to')]:
        if key in filters:
            day = filters[key] + (timedelta(days=1) if key == 'date_to' else timedelta())
            boundary = datetime.combine(day, time.min, tzinfo=KENYA)
            applications = applications.filter(**{f'{field}__{direction}': boundary})
            appointments = appointments.filter(**{f'office_appointment__{direction}': boundary})
    return filters, applications, appointments


def scope_appointments(queryset, scope, now):
    if scope == 'upcoming':
        return queryset.filter(office_appointment__gte=now)
    if scope == 'past':
        return queryset.filter(office_appointment__lt=now)
    return queryset


def appointment_row(application):
    return {
        'id': application.pk, 'reference': application.reference,
        'full_name': application.full_name, 'county': application.county,
        'operating_area': application.operating_area,
        'status': application.status, 'status_label': application.get_status_display(),
        'office_appointment': application.office_appointment.isoformat(),
    }


class StaffRecruitmentReportsView(PortalView):
    def get(self, request):
        filters, applications, appointments = filtered_records(request)
        now = timezone.now()
        counts = dict(applications.order_by().values_list('status').annotate(total=Count('id')))
        pipeline = [{'status': key, 'label': label, 'count': counts.get(key, 0)} for key, label in PartnerApplication.Status.choices]
        counties = list(applications.order_by().values('county').annotate(count=Count('id')).order_by('-count', 'county')[:50])
        schedule = scope_appointments(appointments, filters['appointment_scope'], now).order_by('office_appointment', 'pk')
        paginator = PageNumberPagination()
        paginator.page_size = 20
        page = paginator.paginate_queryset(schedule, request)
        return Response({
            'generated_at': now, 'timezone': 'Africa/Nairobi',
            'filters': filters,
            'pipeline': {'total': sum(counts.values()), 'statuses': pipeline, 'counties': counties},
            'appointments': {
                'upcoming_count': appointments.filter(office_appointment__gte=now).count(),
                'past_count': appointments.filter(office_appointment__lt=now).count(),
                'count': paginator.page.paginator.count,
                'next': paginator.get_next_link(), 'previous': paginator.get_previous_link(),
                'results': [appointment_row(a) for a in page],
            },
            'can_export': request.user.has_perm('partners.change_partnerapplication'),
        })


def safe_cell(value):
    text = str(value if value is not None else '')
    # Spreadsheet software must not interpret applicant-entered values as formulas.
    if text.lstrip().startswith(('=', '+', '-', '@')) or text.startswith(('\t', '\r', '\n')):
        return "'" + text
    return text


class StaffRecruitmentReportExportView(PortalView):
    def get(self, request):
        if not request.user.has_perm('partners.change_partnerapplication'):
            raise PermissionDenied('Report downloads require screening update permission.')
        filters, applications, appointments = filtered_records(request)
        report = request.query_params.get('report', 'pipeline')
        output = io.StringIO(newline='')
        writer = csv.writer(output)
        if report == 'pipeline':
            counts = dict(applications.order_by().values_list('status').annotate(total=Count('id')))
            writer.writerow(['Current application status', 'Applications received in selected Kenya date range'])
            for value, label in PartnerApplication.Status.choices:
                writer.writerow([label, counts.get(value, 0)])
            writer.writerow(['Total', sum(counts.values())])
        elif report == 'appointments':
            appointments = scope_appointments(appointments, filters['appointment_scope'], timezone.now()).order_by('office_appointment', 'pk')
            if appointments.count() > 10000:
                raise serializers.ValidationError('This export exceeds 10,000 appointments. Narrow the date range or county.')
            writer.writerow(['Application reference', 'Applicant', 'County', 'Operating area', 'Current status', 'Office appointment (Kenya UTC+03:00)'])
            for a in appointments.iterator(chunk_size=500):
                writer.writerow([safe_cell(value) for value in (a.reference, a.full_name, a.county, a.operating_area, a.get_status_display(), a.office_appointment.astimezone(KENYA).strftime('%Y-%m-%d %H:%M'))])
        else:
            raise serializers.ValidationError('Choose pipeline or appointments for the report.')
        writer.writerow([])
        writer.writerow(['Generated (Kenya)', timezone.now().astimezone(KENYA).strftime('%Y-%m-%d %H:%M')])
        writer.writerow(['From date (Kenya)', filters.get('date_from', 'All dates')])
        writer.writerow(['To date (Kenya)', filters.get('date_to', 'All dates')])
        writer.writerow(['County filter', safe_cell(filters.get('county') or 'All counties')])
        writer.writerow(['Date basis', 'Application submission date; current status' if report == 'pipeline' else 'Office appointment date'])
        if report == 'appointments':
            writer.writerow(['Appointment scope', filters['appointment_scope']])
            writer.writerow(['Note', 'Past appointments do not confirm attendance. Declined and withdrawn applications excluded.'])
        response = HttpResponse('\ufeff' + output.getvalue(), content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="patahao-{report}.csv"'
        response['Access-Control-Expose-Headers'] = 'Content-Disposition'
        return response
