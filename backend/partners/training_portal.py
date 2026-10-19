from zoneinfo import ZoneInfo
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from .models import (PartnerApplication, TrainingCohort, TrainingSession, TrainingEnrollment, TrainingAttendance, TrainingAssessment, TrainingEvent)
from .training_models import MODULES
from .staff_portal import PortalView


def require_training_editor(user):
    if not user.has_perm('partners.change_partnerapplication'):
        raise PermissionDenied('Training changes require screening-edit permission.')


def require_supervisor(user):
    if not user.has_perm('partners.certify_partner_training'):
        raise PermissionDenied('Only an authorized training supervisor may certify, reopen or withdraw training.')


def readiness(enrollment):
    attendance = {a.session_id:a.result for a in enrollment.attendance.all()}
    results = {a.module:a.result for a in enrollment.assessments.all()}
    sessions = list(enrollment.cohort.sessions.all())
    missing = []
    if any(s.date > timezone.localdate(timezone.now(), ZoneInfo('Africa/Nairobi')) for s in sessions): missing.append('All training dates must have taken place before certification.')
    if not enrollment.identity_checked: missing.append('Original identity documents must be checked at the office.')
    if not enrollment.agreement_signed: missing.append('The signed agreement must be confirmed in the physical file.')
    if not sessions or any(attendance.get(s.pk) not in ('present', 'makeup') for s in sessions): missing.append('Every training session needs attendance or completed make-up training.')
    if any(results.get(code) != 'pass' for code, _ in MODULES): missing.append('All eight practical modules must be assessed as competent.')
    if enrollment.application.status in ('declined', 'withdrawn'): missing.append('The application is closed.')
    return missing


def cohort_data(cohort):
    active = cohort.enrollments.exclude(state='withdrawn')
    return {'id':cohort.pk, 'reference':cohort.reference, 'name':cohort.name, 'location':cohort.location, 'trainer_name':cohort.trainer_name, 'capacity':12, 'enrolled':active.count(), 'certified':active.filter(state='certified').count(), 'sessions':[{'id':s.pk,'date':s.date} for s in cohort.sessions.all()]}


def enrollment_data(e):
    return {'id':e.pk,'application_reference':e.application.reference,'full_name':e.application.full_name,'cohort_id':e.cohort_id,'state':e.state,'state_label':e.get_state_display(),'identity_checked':e.identity_checked,'agreement_signed':e.agreement_signed,'updated_at':e.updated_at,'certified_at':e.certified_at,'certified_by':(e.certified_by.full_name or e.certified_by.username) if e.certified_by else None,
        'attendance':[{'session_id':a.session_id,'date':a.session.date,'result':a.result} for a in e.attendance.select_related('session').all()],
        'assessments':[{'module':a.module,'label':dict(MODULES)[a.module],'result':a.result} for a in e.assessments.all()],
        'readiness_issues':readiness(e),
        'history':[{'action':x.action,'actor':x.actor.full_name or x.actor.username,'created_at':x.created_at} for x in e.events.select_related('actor').all()[:50]]}


def audit(cohort, actor, action, enrollment=None, record=None):
    TrainingEvent.objects.create(cohort=cohort, enrollment=enrollment, actor=actor, action=action, record=record or {})


class CohortInput(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    location = serializers.CharField(max_length=150)
    trainer_name = serializers.CharField(max_length=100)
    dates = serializers.ListField(child=serializers.DateField(), min_length=1, max_length=10)

    def validate_dates(self, dates):
        if len(set(dates)) != len(dates):
            raise serializers.ValidationError('Training dates must be unique.')
        return sorted(dates)


class TrainingCohortListView(PortalView):
    def get(self, request):
        paginator=PageNumberPagination();paginator.page_size=20
        page=paginator.paginate_queryset(TrainingCohort.objects.prefetch_related('sessions').all(),request)
        response=paginator.get_paginated_response([cohort_data(c) for c in page])
        response.data['can_manage']=request.user.has_perm('partners.change_partnerapplication')
        response.data['can_certify']=request.user.has_perm('partners.certify_partner_training')
        return response

    def post(self, request):
        require_training_editor(request.user)
        data=CohortInput(data=request.data);data.is_valid(raise_exception=True)
        values=data.validated_data
        with transaction.atomic():
            cohort=TrainingCohort.objects.create(name=values['name'],location=values['location'],trainer_name=values['trainer_name'],created_by=request.user)
            TrainingSession.objects.bulk_create([TrainingSession(cohort=cohort,date=d) for d in values['dates']])
            audit(cohort,request.user,'Cohort created',record={'dates':[d.isoformat() for d in values['dates']]})
        return Response(cohort_data(cohort),status=201)


class EnrollmentInput(serializers.Serializer):
    application_reference=serializers.CharField(max_length=40)


class TrainingCohortDetailView(PortalView):
    def get(self,request,pk):
        cohort=get_object_or_404(TrainingCohort,pk=pk)
        data=cohort_data(cohort)
        data['enrollments']=[{'id':e.pk,'full_name':e.application.full_name,'reference':e.application.reference,'state':e.state,'state_label':e.get_state_display()} for e in cohort.enrollments.select_related('application').all()]
        return Response(data)

    def post(self,request,pk):
        require_training_editor(request.user)
        data=EnrollmentInput(data=request.data);data.is_valid(raise_exception=True)
        with transaction.atomic():
            cohort=get_object_or_404(TrainingCohort.objects.select_for_update(),pk=pk)
            application=get_object_or_404(PartnerApplication.objects.select_for_update(),reference=data.validated_data['application_reference'].strip().upper())
            if application.status not in ('screening','invited'):
                raise serializers.ValidationError('Screen the applicant before assigning training. Closed applications cannot be enrolled.')
            if TrainingEnrollment.objects.filter(application=application).exists():
                raise serializers.ValidationError('This application already has a training record. Open that record instead.')
            if cohort.enrollments.exclude(state='withdrawn').count()>=12:
                raise serializers.ValidationError('This cohort already has 12 active trainees. Create another cohort.')
            e=TrainingEnrollment.objects.create(cohort=cohort,application=application)
            TrainingAttendance.objects.bulk_create([TrainingAttendance(enrollment=e,session=s) for s in cohort.sessions.all()])
            TrainingAssessment.objects.bulk_create([TrainingAssessment(enrollment=e,module=code) for code,_ in MODULES])
            audit(cohort,request.user,'Applicant enrolled',enrollment=e)
        return Response(enrollment_data(e),status=201)


class AttendanceInput(serializers.Serializer):
    session_id=serializers.IntegerField()
    result=serializers.ChoiceField(choices=('pending','present','absent','makeup'))


class AssessmentInput(serializers.Serializer):
    module=serializers.ChoiceField(choices=[code for code,_ in MODULES])
    result=serializers.ChoiceField(choices=('pending','pass','retrain'))


class TrainingRecordInput(serializers.Serializer):
    expected_updated_at=serializers.DateTimeField()
    identity_checked=serializers.BooleanField()
    agreement_signed=serializers.BooleanField()
    attendance=AttendanceInput(many=True)
    assessments=AssessmentInput(many=True)


class TrainingEnrollmentDetailView(PortalView):
    def get(self,request,pk):
        return Response(enrollment_data(get_object_or_404(TrainingEnrollment.objects.select_related('application','cohort','certified_by'),pk=pk)))

    def patch(self,request,pk):
        require_training_editor(request.user)
        data=TrainingRecordInput(data=request.data);data.is_valid(raise_exception=True);values=data.validated_data
        with transaction.atomic():
            e=get_object_or_404(TrainingEnrollment.objects.select_for_update(),pk=pk)
            if e.updated_at!=values['expected_updated_at']:
                return Response({'detail':'This training record changed. Reload it before saving.'},status=409)
            if e.state!='enrolled':
                raise serializers.ValidationError('An authorized supervisor must reopen training before results can be changed.')
            sessions={a.session_id for a in e.attendance.all()};provided=[a['session_id'] for a in values['attendance']]
            modules={code for code,_ in MODULES};provided_modules=[a['module'] for a in values['assessments']]
            if set(provided)!=sessions or len(provided)!=len(sessions) or set(provided_modules)!=modules or len(provided_modules)!=len(modules):
                raise serializers.ValidationError('Submit exactly this cohort’s sessions and all eight modules once each.')
            before={'identity_checked':e.identity_checked,'agreement_signed':e.agreement_signed,'attendance':list(e.attendance.values('session_id','result')),'assessments':list(e.assessments.values('module','result'))}
            for item in values['attendance']: e.attendance.filter(session_id=item['session_id']).update(result=item['result'])
            for item in values['assessments']: e.assessments.filter(module=item['module']).update(result=item['result'])
            e.identity_checked=values['identity_checked'];e.agreement_signed=values['agreement_signed'];e.save(update_fields=['identity_checked','agreement_signed','updated_at'])
            after={key:values[key] for key in ('identity_checked','agreement_signed','attendance','assessments')}
            audit(e.cohort,request.user,'Training record updated',enrollment=e,record={'before':before,'after':after})
        return Response(enrollment_data(e))


class TrainingDecisionInput(serializers.Serializer):
    expected_updated_at=serializers.DateTimeField()
    decision=serializers.ChoiceField(choices=('certify','reopen','withdraw'))


class TrainingDecisionView(PortalView):
    def post(self,request,pk):
        require_supervisor(request.user)
        data=TrainingDecisionInput(data=request.data);data.is_valid(raise_exception=True);values=data.validated_data
        with transaction.atomic():
            e=get_object_or_404(TrainingEnrollment.objects.select_for_update(),pk=pk)
            if e.updated_at!=values['expected_updated_at']:
                return Response({'detail':'This training record changed. Reload it before deciding.'},status=409)
            TrainingCohort.objects.select_for_update().get(pk=e.cohort_id)
            old=e.state
            if values['decision']=='certify':
                if e.state!='enrolled': raise serializers.ValidationError('Only an enrolled trainee can be certified.')
                issues=readiness(e)
                if issues: raise serializers.ValidationError({'readiness':issues})
                e.state='certified';e.certified_by=request.user;e.certified_at=timezone.now()
            elif values['decision']=='reopen':
                if e.application.status in ('declined','withdrawn'): raise serializers.ValidationError('Reopen the closed application before reopening training.')
                if e.state=='withdrawn' and e.cohort.enrollments.exclude(state='withdrawn').count()>=12: raise serializers.ValidationError('This cohort is full.')
                e.state='enrolled';e.certified_by=None;e.certified_at=None
                e.assessments.update(result='pending')
            else:
                e.state='withdrawn';e.certified_by=None;e.certified_at=None
            e.save(update_fields=['state','certified_by','certified_at','updated_at'])
            audit(e.cohort,request.user,'Training '+values['decision'],enrollment=e,record={'before':old,'after':e.state})
        return Response(enrollment_data(e))
