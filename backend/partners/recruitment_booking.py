"""Public availability and atomic application-plus-training reservation."""
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import serializers
from rest_framework.decorators import api_view, authentication_classes, permission_classes, throttle_classes
from rest_framework.exceptions import APIException
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import (PartnerApplication, TrainingCohort, TrainingEnrollment,
                     TrainingAttendance, TrainingAssessment)
from .recruitment import (ApplicationSerializer, RecruitmentThrottle, recruitment_cors,
                          origin_allowed)
from .training_models import MODULES
from .training_portal import audit
from .training_schedule import starts_at, KENYA


class AvailabilityThrottle(RecruitmentThrottle):
    rate = '120/hour'
    scope = 'partner_training_availability'


class BookingInput(ApplicationSerializer):
    training_session = serializers.IntegerField(min_value=1, write_only=True)
    training_availability = serializers.ChoiceField(choices=('weekdays','weekends','flexible'), default='flexible')

    class Meta(ApplicationSerializer.Meta):
        fields = (*ApplicationSerializer.Meta.fields, 'training_session')


class BookingConflict(APIException):
    status_code = 409
    default_code = 'training_booking_conflict'


def booking_details(enrollment):
    cohort = enrollment.cohort
    return {'date':cohort.scheduled_date, 'time':cohort.get_slot_display(),
            'location':cohort.location, 'timezone':'Africa/Nairobi'}


@recruitment_cors
@api_view(['GET', 'OPTIONS'])
@authentication_classes([])
@permission_classes([AllowAny])
@throttle_classes([AvailabilityThrottle])
def available_sessions(request):
    if not origin_allowed(request):
        return Response({'detail':'Origin not allowed.'}, status=403)
    if request.method == 'OPTIONS':
        return Response(status=204)
    sessions = []
    for cohort in TrainingCohort.objects.filter(scheduled_date__gte=timezone.localdate(timezone=KENYA), slot__in=('am','pm')).annotate(active_count=Count('enrollments',filter=~Q(enrollments__state='withdrawn'))).order_by('scheduled_date','slot'):
        remaining = 12-cohort.active_count
        if remaining > 0 and starts_at(cohort) > timezone.now():
            sessions.append({'id':cohort.pk,'date':cohort.scheduled_date,'time':cohort.get_slot_display(),
                             'location':cohort.location,'remaining':remaining,'timezone':'Africa/Nairobi'})
    return Response({'sessions':sessions})


@recruitment_cors
@api_view(['POST', 'OPTIONS'])
@authentication_classes([])
@permission_classes([AllowAny])
@throttle_classes([RecruitmentThrottle])
def reserve_training(request):
    if not origin_allowed(request):
        return Response({'detail':'Origin not allowed.'}, status=403)
    if request.method == 'OPTIONS':
        return Response(status=204)
    serializer = BookingInput(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = dict(serializer.validated_data)
    session_id = data.pop('training_session')
    with transaction.atomic():
        # Same row lock used by staff scheduling and reopening: capacity is checked
        # again at submission, not trusted from the public availability snapshot.
        cohort = TrainingCohort.objects.select_for_update().filter(pk=session_id,scheduled_date__isnull=False,slot__in=('am','pm')).first()
        if cohort is None:
            raise BookingConflict('That class is unavailable. Refresh the sessions and choose another time.')
        data['training_availability'] = 'weekends' if cohort.scheduled_date.weekday() >= 5 else 'weekdays'
        application, created = PartnerApplication.objects.get_or_create(submission_key=data['submission_key'],defaults=data)
        if any(getattr(application,key) != value for key,value in data.items()):
            raise BookingConflict('An application was already submitted with this request. Check its progress or start another application before changing details.')
        if not created:
            enrollment = TrainingEnrollment.objects.filter(application=application).select_related('cohort').first()
            if enrollment is None or enrollment.cohort_id != cohort.pk:
                raise BookingConflict('This application already exists. Check its progress; no new training place has been reserved.')
            # Idempotent retries still work after this session fills or starts.
            return Response({'reference':application.reference,'status':application.get_status_display(),
                             'training':booking_details(enrollment),'message':'Your existing training reservation is confirmed.'})
        if starts_at(cohort) <= timezone.now() or cohort.enrollments.exclude(state='withdrawn').count() >= 12:
            raise BookingConflict('That class has filled or started. Refresh the sessions and choose another time. Your application has not been submitted.')
        enrollment = TrainingEnrollment.objects.create(application=application,cohort=cohort)
        TrainingAttendance.objects.bulk_create([TrainingAttendance(enrollment=enrollment,session=session) for session in cohort.sessions.all()])
        TrainingAssessment.objects.bulk_create([TrainingAssessment(enrollment=enrollment,module=code) for code,_ in MODULES])
        application.office_appointment = starts_at(cohort)
        application.save(update_fields=['office_appointment','updated_at'])
        audit(cohort,None,'Applicant reserved training',enrollment=enrollment,
              record={'source':'applicant','slot':cohort.slot,'date':cohort.scheduled_date.isoformat()})
    return Response({'reference':application.reference,'status':application.get_status_display(),
                     'training':booking_details(enrollment),
                     'message':'Your training place is reserved. Attend your selected session; our team will approve and activate your account when ready.'},status=201)
