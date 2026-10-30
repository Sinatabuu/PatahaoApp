from datetime import timedelta
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied, APIException
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from partners.staff_portal import PortalView, TrustedPortalOrigin
from partners.models import PartnerApplication, TrainingEnrollment
from payments.models import Payment
from viewings.models import Viewing
from .models import OperationsIssue, OperationsEvent, OperationsScan
from .operations import allowed_categories, scan_operations


class CanUseOperations(BasePermission):
    def has_permission(self, request, view):
        u = request.user
        return bool(u.is_authenticated and u.is_active and u.is_staff and u.has_perm('core.view_operationsissue'))


class OperationsView(PortalView):
    permission_classes = [TrustedPortalOrigin, CanUseOperations]


def visible(user):
    return OperationsIssue.objects.filter(category__in=allowed_categories(user)).select_related('owner')


def label(user):
    return (user.full_name or user.username) if user else None


def serialize(issue):
    return {key: getattr(issue, key) for key in ('id', 'category', 'rule', 'source_id', 'reference', 'title', 'reason', 'next_action', 'priority', 'state', 'follow_up_at', 'first_detected_at', 'last_detected_at', 'resolved_at', 'revision')} | {'owner': label(issue.owner)}


def source_record(issue):
    if issue.category == 'payment':
        p = Payment.objects.filter(pk=issue.source_id).first()
        return {'type': 'payment', 'id': issue.source_id, 'status': p.status if p else 'Record unavailable', 'amount': str(p.cash_amount) if p else '', 'currency': p.currency if p else '', 'viewing_id': p.viewing_id if p else None}
    if issue.category == 'viewing':
        v = Viewing.objects.filter(pk=issue.source_id).first()
        return {'type': 'viewing', 'id': issue.source_id, 'status': v.status if v else 'Record unavailable', 'requested_date': v.requested_date if v else None, 'requested_time': v.requested_time if v else None, 'assigned_partner_id': v.assigned_partner_id if v else None, 'fee_resolution_choice': v.fee_resolution_choice if v else ''}
    if issue.rule == 'application_unscheduled':
        a = PartnerApplication.objects.filter(pk=issue.source_id).first()
        return {'type': 'application', 'id': issue.source_id, 'status': a.status if a else 'Record unavailable'}
    e = TrainingEnrollment.objects.filter(pk=issue.source_id).first()
    return {'type': 'training', 'id': issue.source_id, 'status': e.state if e else 'Record unavailable', 'cohort_id': e.cohort_id if e else None}


class OperationsListView(OperationsView):
    def get(self, request):
        state = request.query_params.get('state', 'active')
        if state not in ['active', 'open', 'following', 'snoozed', 'resolved']:
            raise serializers.ValidationError({'state': 'Invalid queue filter.'})
        qs = visible(request.user)
        counts = {s: qs.filter(state=s).count() for s in ['open', 'following', 'snoozed', 'resolved']}
        qs = qs.exclude(state='resolved') if state == 'active' else qs.filter(state=state)
        pager = PageNumberPagination(); pager.page_size = 25
        page = pager.paginate_queryset(qs, request)
        result = pager.get_paginated_response([serialize(i) for i in page])
        scan = OperationsScan.objects.filter(pk=1).first()
        completed = scan.completed_at if scan else None
        result.data.update(counts=counts, last_scan_at=completed,
                           stale=not completed or completed < timezone.now()-timedelta(minutes=30),
                           can_manage=request.user.has_perm('core.change_operationsissue'),
                           categories=allowed_categories(request.user))
        return result


class OperationsScanView(OperationsView):
    def post(self, request):
        if not request.user.has_perm('core.change_operationsissue'):
            raise PermissionDenied('Follow-up management permission is required.')
        scan_operations()
        return Response({'detail': 'Queue checked against current records. No messages were sent and no payment, viewing or partner status was changed.'})


class ActionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=['claim', 'release', 'defer', 'reopen'])
    revision = serializers.IntegerField(min_value=1)
    follow_up_at = serializers.DateTimeField(required=False)

    def validate(self, data):
        if data['action'] == 'defer':
            due = data.get('follow_up_at')
            now = timezone.now()
            if due is None or not now < due <= now+timedelta(days=7):
                raise serializers.ValidationError('Choose a follow-up within the next seven days.')
        return data


class StaleIssue(APIException):
    status_code = 409
    default_detail = 'This follow-up changed. Reload it before saving.'


class OperationsDetailView(OperationsView):
    def get(self, request, pk):
        issue = get_object_or_404(visible(request.user), pk=pk)
        result = serialize(issue)
        result['source'] = source_record(issue)
        result['history'] = [{'action': e.action, 'actor': label(e.actor) or 'Operations watchdog', 'created_at': e.created_at, 'record': e.record} for e in issue.events.select_related('actor')[:30]]
        return Response(result)

    @transaction.atomic
    def patch(self, request, pk):
        if not request.user.has_perm('core.change_operationsissue'):
            raise PermissionDenied('Follow-up management permission is required.')
        data = ActionSerializer(data=request.data); data.is_valid(raise_exception=True); data = data.validated_data
        # Lock only the issue, never the nullable owner join (PostgreSQL).
        issue = get_object_or_404(OperationsIssue.objects.select_for_update(), pk=pk, category__in=allowed_categories(request.user))
        if issue.revision != data['revision'] or issue.state == 'resolved':
            raise StaleIssue()
        before = {'state': issue.state, 'owner_id': issue.owner_id, 'follow_up_at': issue.follow_up_at.isoformat() if issue.follow_up_at else None}
        action = data['action']
        if action == 'claim':
            issue.owner = request.user; issue.state = 'following'; issue.follow_up_at = timezone.now()+timedelta(hours=24)
        elif action == 'release':
            issue.owner = None; issue.state = 'open'; issue.follow_up_at = None
        elif action == 'defer':
            issue.owner = request.user; issue.state = 'snoozed'; issue.follow_up_at = data['follow_up_at']
        else:
            issue.state = 'open'; issue.follow_up_at = None
        issue.revision += 1; issue.save()
        OperationsEvent.objects.create(issue=issue, actor=request.user, action=action, record={'before': before, 'state': issue.state, 'owner_id': issue.owner_id, 'follow_up_at': issue.follow_up_at.isoformat() if issue.follow_up_at else None})
        return Response(serialize(issue))
