from datetime import timedelta

from django.db import transaction
from django.db.models import Count, Q
from django.utils.cache import patch_vary_headers
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, BasePermission
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import AccessToken

from accounts.serializers import FlexibleTokenObtainPairSerializer
from .models import PartnerApplication, PartnerApplicationEvent
from .recruitment import origin_allowed


class PortalLoginThrottle(AnonRateThrottle):
    rate = '10/hour'
    scope = 'partner_portal_login'


class TrustedPortalOrigin(BasePermission):
    def has_permission(self, request, view):
        return origin_allowed(request)


class CanScreenApplications(BasePermission):
    message = 'Your staff account does not have permission to view partner applications.'

    def has_permission(self, request, view):
        user = request.user
        return bool(user.is_authenticated and user.is_active and user.is_staff and user.has_perm('partners.view_partnerapplication'))


class PortalView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [TrustedPortalOrigin, CanScreenApplications]

    def initial(self, request, *args, **kwargs):
        if not origin_allowed(request):
            raise PermissionDenied("Origin not allowed.")
        return super().initial(request, *args, **kwargs)

    def get_permissions(self):
        if self.request.method == 'OPTIONS':
            return [TrustedPortalOrigin()]
        return super().get_permissions()

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        origin = request.headers.get('Origin', '')
        if origin and origin_allowed(request):
            response['Access-Control-Allow-Origin'] = origin
            response['Access-Control-Allow-Methods'] = 'GET, POST, PATCH, OPTIONS'
            response['Access-Control-Allow-Headers'] = 'Authorization, Content-Type'
        response['Cache-Control'] = 'no-store'
        patch_vary_headers(response, ('Origin',))
        return response

    def options(self, request, *args, **kwargs):
        return Response(status=204)


def staff_identity(user):
    return {
        'name': user.full_name or user.get_full_name() or user.username,
        'can_change': user.has_perm('partners.change_partnerapplication'),
    }


class PortalLoginView(PortalView):
    authentication_classes = []
    permission_classes = [TrustedPortalOrigin, AllowAny]
    throttle_classes = [PortalLoginThrottle]

    def post(self, request):
        serializer = FlexibleTokenObtainPairSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.user
        if not (user.is_staff and user.has_perm('partners.view_partnerapplication')):
            raise PermissionDenied('Your account does not have access to the staff onboarding portal.')
        access = AccessToken(serializer.validated_data['access'])
        access.set_exp(lifetime=timedelta(minutes=20))
        return Response({'access': str(access), 'expires_in': 1200, 'staff': staff_identity(user)})


class PortalMeView(PortalView):
    def get(self, request):
        return Response(staff_identity(request.user))


class StaffApplicationSerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source='get_status_display', read_only=True)
    partner_type_label = serializers.CharField(source='get_partner_type_display', read_only=True)
    experience_label = serializers.CharField(source='get_experience_display', read_only=True)
    availability_label = serializers.CharField(source='get_training_availability_display', read_only=True)

    class Meta:
        model = PartnerApplication
        fields = ('id', 'reference', 'full_name', 'phone_number', 'email', 'county', 'operating_area', 'partner_type', 'partner_type_label', 'experience_label', 'availability_label', 'status', 'status_label', 'office_appointment', 'created_at', 'updated_at')
        read_only_fields = fields


class StaffApplicationListView(PortalView):
    def get(self, request):
        queryset = PartnerApplication.objects.all()
        search = request.query_params.get('search', '').strip()[:150]
        if search:
            queryset = queryset.filter(Q(full_name__icontains=search) | Q(reference__icontains=search) | Q(phone_number__icontains=search) | Q(operating_area__icontains=search) | Q(county__icontains=search))
        counts = dict(queryset.values_list('status').annotate(total=Count('id')))
        state = request.query_params.get('status', '')
        if state:
            if state not in PartnerApplication.Status.values:
                raise serializers.ValidationError({'status': 'Choose a valid application status.'})
            queryset = queryset.filter(status=state)
        paginator = PageNumberPagination()
        paginator.page_size = 20
        page = paginator.paginate_queryset(queryset, request)
        response = paginator.get_paginated_response(StaffApplicationSerializer(page, many=True).data)
        response.data['counts'] = counts
        response.data['statuses'] = [{'value': key, 'label': label} for key, label in PartnerApplication.Status.choices]
        return response


class ScreeningUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=PartnerApplication.Status.choices)
    office_appointment = serializers.DateTimeField(allow_null=True)
    expected_updated_at = serializers.DateTimeField()
    action = serializers.ChoiceField(choices=PartnerApplicationEvent._meta.get_field('action').choices)

    def validate(self, attrs):
        if attrs['status'] == PartnerApplication.Status.INVITED and attrs['office_appointment'] is None:
            raise serializers.ValidationError({'office_appointment': 'An office invitation requires an appointment date and time.'})
        return attrs


def application_detail(application):
    result = StaffApplicationSerializer(application).data
    enrollment = getattr(application, 'training_enrollment', None)
    result['training'] = ({'id':enrollment.pk, 'class_name':enrollment.cohort.name, 'location':enrollment.cohort.location, 'state':enrollment.state} if enrollment else None)
    result['history'] = [{
        'action': event.get_action_display(),
        'actor': event.actor.full_name or event.actor.username,
        'previous_status': event.previous_status,
        'new_status': event.new_status,
        'previous_appointment': event.previous_appointment,
        'new_appointment': event.new_appointment,
        'created_at': event.created_at,
    } for event in application.screening_events.select_related('actor').all()[:50]]
    return result


class StaffApplicationDetailView(PortalView):
    def get(self, request, pk):
        from django.shortcuts import get_object_or_404
        return Response(application_detail(get_object_or_404(PartnerApplication, pk=pk)))

    def patch(self, request, pk):
        if not request.user.has_perm('partners.change_partnerapplication'):
            raise PermissionDenied('Your account has read-only access to applications.')
        serializer = ScreeningUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        from django.shortcuts import get_object_or_404
        with transaction.atomic():
            application = get_object_or_404(PartnerApplication.objects.select_for_update(), pk=pk)
            if application.updated_at != data['expected_updated_at']:
                return Response({'detail': 'Another staff member updated this application. Reload it before saving.'}, status=409)
            enrollment = getattr(application, 'training_enrollment', None)
            if enrollment and hasattr(enrollment, 'activation') and data['status'] in ('declined','withdrawn'):
                raise serializers.ValidationError('This partner is activated. Use partner management for suspension or termination.')
            if enrollment and enrollment.cohort.scheduled_date and data['office_appointment'] != application.office_appointment:
                raise serializers.ValidationError({'office_appointment':'This appointment belongs to the assigned training class and cannot be changed independently.'})
            old_status = application.status
            old_appointment = application.office_appointment
            application.status = data['status']
            application.office_appointment = data['office_appointment']
            application.save(update_fields=['status', 'office_appointment', 'updated_at'])
            PartnerApplicationEvent.objects.create(
                application=application, actor=request.user, action=data['action'],
                previous_status=old_status, new_status=application.status,
                previous_appointment=old_appointment, new_appointment=application.office_appointment,
            )
        return Response(application_detail(application))
