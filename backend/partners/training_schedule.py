"""Date-first allocation. Capacity decisions share the cohort row lock."""
from datetime import datetime, time
from zoneinfo import ZoneInfo
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers
from rest_framework.response import Response
from .models import (PartnerApplication, PartnerApplicationEvent, TrainingCohort,
                     TrainingSession, TrainingEnrollment, TrainingAttendance, TrainingAssessment)
from .staff_portal import PortalView
from .training_models import MODULES
from .training_portal import require_training_editor, cohort_data, enrollment_data, audit

KENYA = ZoneInfo('Africa/Nairobi')
SLOTS = [('am', time(9)), ('pm', time(14))]


def starts_at(cohort):
    return datetime.combine(cohort.scheduled_date, dict(SLOTS)[cohort.slot], tzinfo=KENYA)


class OpenDateInput(serializers.Serializer):
    date = serializers.DateField()
    trainer_name = serializers.CharField(max_length=100, required=False)
    location = serializers.CharField(max_length=150, required=False)

    def validate_date(self, value):
        if value < timezone.localdate(timezone=KENYA):
            raise serializers.ValidationError('Choose today or a future training date.')
        return value


class TrainingDatesView(PortalView):
    def get(self, request):
        cohorts = TrainingCohort.objects.filter(scheduled_date__gte=timezone.localdate(timezone=KENYA)).order_by('scheduled_date', 'slot')
        days = {}
        for cohort in cohorts:
            if cohort.slot not in dict(SLOTS) or starts_at(cohort) <= timezone.now():
                continue
            day = days.setdefault(cohort.scheduled_date.isoformat(), {'date':cohort.scheduled_date, 'remaining':0, 'classes':[]})
            data = cohort_data(cohort)
            data['remaining'] = max(0, 12-data['enrolled'])
            day['remaining'] += data['remaining']
            day['classes'].append(data)
        previous = TrainingCohort.objects.exclude(slot='').order_by('-created_at').first()
        return Response({'dates':list(days.values()), 'defaults':{
            'trainer_name':previous.trainer_name if previous else (request.user.full_name or request.user.username),
            'location':previous.location if previous else '',
        }})

    def post(self, request):
        require_training_editor(request.user)
        serializer = OpenDateInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        previous = TrainingCohort.objects.exclude(slot='').order_by('-created_at').first()
        trainer = values.get('trainer_name') or (previous.trainer_name if previous else (request.user.full_name or request.user.username))
        location = values.get('location') or (previous.location if previous else '')
        if not trainer or not location:
            raise serializers.ValidationError('Set the trainer and office location for the first training date. These will be reused.')
        try:
            with transaction.atomic():
                for slot, _ in SLOTS:
                    cohort = TrainingCohort.objects.create(
                        scheduled_date=values['date'], slot=slot,
                        name=f"{values['date'].isoformat()} · {'Morning' if slot=='am' else 'Afternoon'}",
                        trainer_name=trainer, location=location, created_by=request.user)
                    TrainingSession.objects.create(cohort=cohort, date=values['date'])
                    audit(cohort, request.user, 'Training date opened')
        except IntegrityError:
            return Response({'detail':'This training date is already open. Its existing classes have been kept.'}, status=409)
        return Response({'detail':'Training date opened: two classes, 12 places each.'}, status=201)


class AllocateInput(serializers.Serializer):
    date = serializers.DateField()
    expected_updated_at = serializers.DateTimeField()


class ScheduleApplicantView(PortalView):
    def post(self, request, pk):
        require_training_editor(request.user)
        serializer = AllocateInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        if values['date'] < timezone.localdate(timezone=KENYA):
            raise serializers.ValidationError('Choose today or a future training date.')
        with transaction.atomic():
            # A chronological lock order serializes concurrent claims on place 12.
            cohorts = list(TrainingCohort.objects.select_for_update().filter(
                scheduled_date__gte=values['date'], slot__in=('am','pm')).order_by('scheduled_date','slot'))
            if not any(c.scheduled_date == values['date'] for c in cohorts):
                raise serializers.ValidationError('Open the selected training date first.')
            application = get_object_or_404(PartnerApplication.objects.select_for_update(), pk=pk)
            if application.updated_at != values['expected_updated_at']:
                return Response({'detail':'This application changed. Reload it before scheduling.'}, status=409)
            existing = TrainingEnrollment.objects.filter(application=application).first()
            if existing:
                return Response({'detail':'This applicant already has a training record. Open Training to view it; no second enrollment was made.', 'enrollment_id':existing.pk}, status=409)
            if application.status in ('declined','withdrawn'):
                raise serializers.ValidationError('Closed applications cannot be scheduled.')
            cohort = next((c for c in cohorts if starts_at(c)>timezone.now() and c.enrollments.exclude(state='withdrawn').count()<12), None)
            if cohort is None:
                return Response({'detail':'All available classes are full or have started. Open another training date; the application has not been changed.'}, status=409)
            enrollment = TrainingEnrollment.objects.create(application=application, cohort=cohort)
            TrainingAttendance.objects.bulk_create([TrainingAttendance(enrollment=enrollment, session=s) for s in cohort.sessions.all()])
            TrainingAssessment.objects.bulk_create([TrainingAssessment(enrollment=enrollment, module=code) for code,_ in MODULES])
            old_status, old_appointment = application.status, application.office_appointment
            application.status = 'invited'
            application.office_appointment = starts_at(cohort)
            application.save(update_fields=['status','office_appointment','updated_at'])
            PartnerApplicationEvent.objects.create(application=application, actor=request.user, action='appointment',
                previous_status=old_status,new_status='invited',previous_appointment=old_appointment,new_appointment=application.office_appointment)
            audit(cohort, request.user, 'Automatically scheduled', enrollment=enrollment,
                  record={'selected_date':values['date'].isoformat(), 'assigned_date':cohort.scheduled_date.isoformat(), 'slot':cohort.slot})
        return Response({'enrollment':enrollment_data(enrollment), 'class':cohort_data(cohort),
                         'overflow':cohort.scheduled_date != values['date'],
                         'detail':'Training scheduled. Contact the applicant to confirm; no message was sent.'}, status=201)
