"""Deterministic watchdog: no external calls or business-state writes."""
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from payments.models import Payment
from viewings.models import Viewing
from partners.models import PartnerApplication, TrainingEnrollment
from .models import OperationsIssue, OperationsEvent, OperationsScan

CATEGORY_PERMISSIONS = {'payment': 'payments.view_payment', 'viewing': 'viewings.view_viewing', 'onboarding': 'partners.view_partnerapplication'}


def allowed_categories(user):
    return [key for key, permission in CATEGORY_PERMISSIONS.items() if user.has_perm(permission)]


def candidates(now=None):
    now = now or timezone.now()
    def item(category, rule, obj, reference, title, reason, action, priority=2):
        return dict(key=f'{rule}:{obj.pk}', category=category, rule=rule, source_id=obj.pk, reference=reference,
                    title=title, reason=reason, next_action=action, priority=priority)
    for p in Payment.objects.filter(status='processing').filter(Q(initiated_at__lte=now-timedelta(minutes=20)) | Q(initiated_at__isnull=True, updated_at__lte=now-timedelta(minutes=20))).iterator():
        yield item('payment', 'payment_processing', p, p.payment_reference or f'Payment {p.pk}', 'Payment needs reconciliation',
                   'Payment has remained processing for at least 20 minutes.',
                   'Use staff payment reconciliation in the app. A provider query alone must not credit a payment without the required receipt verification.', 1)
    for v in Viewing.objects.filter(status='paid_pending_partner', updated_at__lte=now-timedelta(hours=2)).iterator():
        yield item('viewing', 'partner_response', v, v.payment_reference or f'Viewing {v.pk}', 'Paid viewing awaiting partner',
                   'No partner decision has been recorded for at least two hours.',
                   'Contact the assigned partner and review this viewing in the app. Use the existing reschedule or fee-resolution process if needed.', 1)
    for v in Viewing.objects.filter(fee_resolution_choice__in=['refund', 'credit'], fee_resolution_processed_at__isnull=True, fee_resolution_requested_at__lte=now-timedelta(hours=24)).iterator():
        yield item('viewing', 'fee_resolution', v, v.payment_reference or f'Viewing {v.pk}', 'Refund or credit awaiting action',
                   'A customer fee-resolution request has remained unprocessed for at least 24 hours.',
                   'Review the request in the app finance queue. Only authorized staff may process money or credit.', 1)
    for a in PartnerApplication.objects.exclude(status__in=['declined', 'withdrawn']).filter(training_enrollment__isnull=True, updated_at__lte=now-timedelta(hours=48)).iterator():
        yield item('onboarding', 'application_unscheduled', a, a.reference, 'Applicant needs a training next step',
                   'Application has no training enrollment and no update for at least 48 hours.',
                   'Open the application, contact the applicant and help them reserve a suitable training session.')
    enrollments = TrainingEnrollment.objects.exclude(state='withdrawn').exclude(application__status__in=['declined', 'withdrawn']).filter(activation__isnull=True).select_related('application', 'cohort').prefetch_related('cohort__sessions')
    for e in enrollments.iterator(chunk_size=200):
        if e.state == 'certified':
            yield item('onboarding', 'activation_pending', e, e.application.reference, 'Certified applicant awaiting activation',
                       'Training is certified but partner activation has not been recorded.',
                       'Open the training record, check the matched app account and make the supervisor activation decision.')
        else:
            dates = [s.date for s in e.cohort.sessions.all()]
            last_day = max(dates) if dates else e.cohort.scheduled_date
            if last_day:
                end = datetime.combine(last_day, time(12 if e.cohort.slot == 'am' else 17), ZoneInfo('Africa/Nairobi'))
                if now >= end+timedelta(hours=24) and e.updated_at <= now-timedelta(hours=24):
                    yield item('onboarding', 'training_follow_up', e, e.application.reference, 'Training record needs follow-up',
                               'The scheduled class ended at least 24 hours ago without a recent training update.',
                               'Open the training record and record the real outcome: continue training, withdraw, or approve and activate when ready. The date is a reminder, not an approval gate.')


@transaction.atomic
def scan_operations(now=None):
    now = now or timezone.now()
    OperationsScan.objects.get_or_create(pk=1)
    scan = OperationsScan.objects.select_for_update().get(pk=1)
    seen = set()
    for values in candidates(now):
        key = values.pop('key')
        seen.add(key)
        issue, created = OperationsIssue.objects.get_or_create(key=key, defaults={**values, 'last_detected_at': now})
        if created:
            OperationsEvent.objects.create(issue=issue, action='detected', record={'rule': issue.rule})
            continue
        issue = OperationsIssue.objects.select_for_update().get(pk=issue.pk)
        changed = any(getattr(issue, key) != value for key, value in values.items())
        if issue.state == 'resolved' or (issue.follow_up_at and issue.follow_up_at <= now):
            issue.state = 'open'
            issue.follow_up_at = None
            issue.resolved_at = None
            OperationsEvent.objects.create(issue=issue, action='follow_up_due')
            changed = True
        for key, value in values.items():
            setattr(issue, key, value)
        issue.last_detected_at = now
        if changed:
            issue.revision += 1
        issue.save()
    for issue in OperationsIssue.objects.select_for_update().exclude(state='resolved').exclude(key__in=seen):
        issue.state = 'resolved'
        issue.follow_up_at = None
        issue.resolved_at = now
        issue.revision += 1
        issue.save()
        OperationsEvent.objects.create(issue=issue, action='source_cleared')
    scan.completed_at = now
    scan.save()
    return len(seen)
