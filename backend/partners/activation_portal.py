"""Deliberate staff admission of a certified applicant into an existing app account."""
import uuid
from django.db import transaction
from django.db.models import Value
from django.db.models.functions import Replace
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from accounts.models import User
from .models import Partner, PartnerActivation, TrainingEnrollment, PartnerApplication
from .staff_portal import PortalView
from .training_portal import readiness, audit, require_supervisor


def require_activator(user):
    if not user.has_perm('partners.activate_trained_partner'):
        raise PermissionDenied('Only staff authorized to activate certified partners may use this action.')


def matching_accounts(application):
    phone = 'phone_number'
    for character in (' ', '-', '+', '(', ')'):
        phone = Replace(phone, Value(character), Value(''))
    return User.objects.annotate(normalized_phone=phone).filter(
        normalized_phone__in=(application.phone_number, '0'+application.phone_number[3:]),
        is_active=True, is_staff=False, is_superuser=False)


def activation_data(activation):
    return {'partner_id':activation.partner_id, 'partner_code':activation.partner.partner_code,
            'username':activation.partner.user.username, 'activated_at':activation.activated_at,
            'activated_by':activation.activated_by.full_name or activation.activated_by.username,
            'is_active':activation.partner.is_active,
            'verification_status':activation.partner.verification_status}


def preparation(enrollment):
    activation = getattr(enrollment, 'activation', None)
    if activation:
        return {'activation':activation_data(activation), 'account':None, 'issues':[]}
    issues = []
    if enrollment.application.status in ('declined', 'withdrawn') or enrollment.state == 'withdrawn':
        issues.append('This application or training enrollment is closed.')
    candidates = list(matching_accounts(enrollment.application)[:2])
    account = None
    if not candidates:
        issues.append('No active personal app account matches this phone number. Ask the applicant to register in the app using the same number, then reload.')
    elif len(candidates) != 1:
        issues.append('More than one account matches this phone number. Resolve the duplicate accounts before activation.')
    else:
        user = candidates[0]
        if user.role != User.ROLE_CUSTOMER or Partner.objects.filter(user=user).exists():
            issues.append('This account already has a partner role or profile. Review it through partner management; this action will not overwrite it.')
        else:
            account = {'id':user.pk,'username':user.username,'full_name':user.full_name,'phone_number':user.phone_number}
    return {'activation':None, 'account':account, 'issues':issues}


class ActivationInput(serializers.Serializer):
    expected_updated_at = serializers.DateTimeField()
    user_id = serializers.IntegerField(min_value=1)
    account_confirmed = serializers.BooleanField()
    no_cash_confirmed = serializers.BooleanField()

    approve_training = serializers.BooleanField(default=False)
    identity_checked = serializers.BooleanField(required=False)
    agreement_signed = serializers.BooleanField(required=False)
    training_confirmed = serializers.BooleanField(required=False)

    def validate(self, attrs):
        if not attrs['account_confirmed'] or not attrs['no_cash_confirmed']:
            raise serializers.ValidationError('Confirm account ownership and the no-cash policy at the office before activation.')
        if attrs['approve_training'] and not all(attrs.get(key) for key in (
            'identity_checked', 'agreement_signed', 'training_confirmed'
        )):
            raise serializers.ValidationError('Confirm identity, the signed agreement and satisfactory training before approval.')
        return attrs


class PartnerActivationView(PortalView):
    def get(self, request, pk):
        require_activator(request.user)
        enrollment = get_object_or_404(TrainingEnrollment, pk=pk)
        return Response(preparation(enrollment))

    def post(self, request, pk):
        require_activator(request.user)
        serializer = ActivationInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        if values['approve_training']:
            require_supervisor(request.user)
        with transaction.atomic():
            enrollment = get_object_or_404(TrainingEnrollment.objects.select_for_update(), pk=pk)
            # Serialize against staff screening/closure while checking readiness.
            application = PartnerApplication.objects.select_for_update().get(pk=enrollment.application_id)
            enrollment.application = application
            existing = PartnerActivation.objects.filter(enrollment=enrollment).first()
            if existing:
                return Response({'activation':activation_data(existing), 'detail':'This partner was already activated. No access settings were changed.'})
            if enrollment.updated_at != values['expected_updated_at']:
                return Response({'detail':'This training record changed. Reload it before activation.'}, status=409)
            if values['approve_training']:
                if enrollment.state not in ('enrolled', 'certified') or application.status in ('declined', 'withdrawn'):
                    raise serializers.ValidationError('Closed or withdrawn applicants cannot be approved here.')
                enrollment.identity_checked = True
                enrollment.agreement_signed = True
                enrollment.state = 'certified'
                enrollment.certified_by = request.user
                enrollment.certified_at = timezone.now()
                enrollment.save(update_fields=['identity_checked', 'agreement_signed', 'state', 'certified_by', 'certified_at', 'updated_at'])
                audit(enrollment.cohort, request.user, 'Training approved by supervisor', enrollment=enrollment,
                      record={'training_confirmed': True, 'identity_checked': True, 'agreement_signed': True,
                              'attendance_and_assessments': 'advisory'})
            if enrollment.state != 'certified' or not enrollment.certified_at or not enrollment.certified_by_id:
                raise serializers.ValidationError('Supervisor certification is required before partner activation.')
            issues = readiness(enrollment)
            if issues:
                raise serializers.ValidationError({'readiness':issues})
            # Do not elevate admin accounts, revive inactive profiles or override bans.
            users = list(matching_accounts(application).select_for_update().order_by('pk')[:2])
            if len(users) != 1 or users[0].pk != values['user_id']:
                raise serializers.ValidationError('There must be exactly one active personal app account matching the applicant phone number. Reload after resolving the account match.')
            user = users[0]
            if user.role != User.ROLE_CUSTOMER or Partner.objects.filter(user=user).exists():
                raise serializers.ValidationError('This account already has a partner role or profile. Existing restrictions and partner settings cannot be overwritten here.')
            now = timezone.now()
            partner = Partner.objects.create(user=user, business_name=application.full_name,
                display_name=application.full_name,
                partner_type=application.partner_type if application.partner_type in ('agent','agency','owner','developer') else 'agent',
                partner_code='PHA-'+uuid.uuid4().hex[:12].upper(), county=application.county,
                service_area=application.operating_area, phone_number=application.phone_number,
                verification_status=Partner.STATUS_APPROVED, is_active=True,
                verified_by=request.user, verified_at=now)
            user.role = User.ROLE_PARTNER
            user.save(update_fields=['role'])
            activation = PartnerActivation.objects.create(enrollment=enrollment, partner=partner, activated_by=request.user)
            enrollment.save(update_fields=['updated_at'])
            audit(enrollment.cohort,request.user,'Partner activated',enrollment=enrollment,
                  record={'partner_id':partner.pk,'user_id':user.pk,'account_confirmed':True,
                          'no_cash_confirmed':True,'policy_version':activation.policy_version})
        return Response({'activation':activation_data(activation),
                         'detail':'Partner approved and activated. Ask them to sign out and sign in again in the app. Property submissions still require the existing approval process.'},status=201)

