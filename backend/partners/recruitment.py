import re
from functools import wraps

from django.conf import settings
from django.db import transaction
from django.utils.cache import patch_vary_headers
from rest_framework import serializers
from rest_framework.decorators import api_view, authentication_classes, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle

from .models import PartnerApplication


class RecruitmentThrottle(AnonRateThrottle):
    rate = '20/hour'
    scope = 'partner_recruitment'


def normalize_phone(value):
    value = re.sub(r'[\s()+-]', '', value)
    if value.startswith('0') and len(value) == 10:
        value = '254' + value[1:]
    if not re.fullmatch(r'254[17]\d{8}', value):
        raise serializers.ValidationError('Enter a Kenyan mobile number, for example 07XXXXXXXX or 2547XXXXXXXX.')
    return value


class ApplicationSerializer(serializers.ModelSerializer):
    consent = serializers.BooleanField(write_only=True)
    office_training = serializers.BooleanField(write_only=True)
    website = serializers.CharField(required=False, allow_blank=True, write_only=True)
    phone_number = serializers.CharField(max_length=30)

    class Meta:
        model = PartnerApplication
        fields = ('submission_key', 'full_name', 'phone_number', 'email', 'county', 'operating_area', 'partner_type', 'experience', 'training_availability', 'consent', 'office_training', 'website')
        extra_kwargs = {'submission_key': {'read_only': False, 'validators': []}}

    def validate_phone_number(self, value):
        return normalize_phone(value)

    def validate(self, attrs):
        if not attrs.pop('consent') or not attrs.pop('office_training'):
            raise serializers.ValidationError('Please accept the recruitment notice and mandatory in-person training.')
        if attrs.pop('website', ''):
            raise serializers.ValidationError('Unable to accept this application.')
        return attrs


def cors_response(request, response):
    origin = request.headers.get('Origin', '')
    allowed = getattr(settings, 'PARTNER_APPLICATION_ORIGINS', ('https://patahao.app', 'https://www.patahao.app'))
    if origin in allowed:
        response['Access-Control-Allow-Origin'] = origin
        response['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type'
    response['Cache-Control'] = 'no-store'
    patch_vary_headers(response, ('Origin',))
    return response


def recruitment_cors(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        return cors_response(request, view(request, *args, **kwargs))
    return wrapped


def origin_allowed(request):
    origin = request.headers.get('Origin')
    return not origin or origin in getattr(settings, 'PARTNER_APPLICATION_ORIGINS', ('https://patahao.app', 'https://www.patahao.app'))


@recruitment_cors
@api_view(['POST', 'OPTIONS'])
@authentication_classes([])
@permission_classes([AllowAny])
@throttle_classes([RecruitmentThrottle])
def apply(request):
    if not origin_allowed(request):
        return Response({'detail': 'Origin not allowed.'}, status=403)
    if request.method == 'OPTIONS':
        return cors_response(request, Response(status=204))
    serializer = ApplicationSerializer(data=request.data)
    if not serializer.is_valid():
        return cors_response(request, Response(serializer.errors, status=400))
    data = serializer.validated_data
    with transaction.atomic():
        application, created = PartnerApplication.objects.get_or_create(
            submission_key=data['submission_key'], defaults=data,
        )
    if not created and any(getattr(application, k) != v for k, v in data.items()):
        return cors_response(request, Response({'detail': 'Start a new application before changing submitted details.'}, status=409))
    return cors_response(request, Response({
        'reference': application.reference,
        'status': application.get_status_display(),
        'message': 'Application received. Our team will contact you to discuss screening and an office visit. Applying does not create a partner account or grant field access.',
    }, status=201 if created else 200))


class StatusSerializer(serializers.Serializer):
    reference = serializers.CharField(max_length=40)
    phone_number = serializers.CharField(max_length=30)

    def validate_phone_number(self, value):
        return normalize_phone(value)


@recruitment_cors
@api_view(['POST', 'OPTIONS'])
@authentication_classes([])
@permission_classes([AllowAny])
@throttle_classes([RecruitmentThrottle])
def application_status(request):
    if not origin_allowed(request):
        return Response({'detail': 'Origin not allowed.'}, status=403)
    if request.method == 'OPTIONS':
        return cors_response(request, Response(status=204))
    serializer = StatusSerializer(data=request.data)
    if not serializer.is_valid():
        return cors_response(request, Response(serializer.errors, status=400))
    a = PartnerApplication.objects.filter(**serializer.validated_data).first()
    if a is None:
        return cors_response(request, Response({'detail': 'No application matches those details.'}, status=404))
    payload = {'reference': a.reference, 'status': a.get_status_display(), 'office_appointment': a.office_appointment, 'message': 'Our team will confirm office arrangements directly. No partner field access is granted by an application.'}
    enrollment = getattr(a, 'training_enrollment', None)
    if enrollment:
        if a.status not in ('declined', 'withdrawn'):
            payload['status'] = enrollment.get_state_display()
        payload['training'] = {
            'cohort': enrollment.cohort.name,
            'dates': list(enrollment.cohort.sessions.values_list('date', flat=True)),
            'attendance_completed': enrollment.attendance.filter(result__in=('present', 'makeup')).count(),
            'sessions_required': enrollment.cohort.sessions.count(),
            'competent_modules': enrollment.assessments.filter(result='pass').count(),
            'modules_required': 8,
        }
        payload['message'] = 'Training certification requires attendance, practical assessment and supervisor approval. Account activation and field access are separate steps.'
    return cors_response(request, Response(payload))
