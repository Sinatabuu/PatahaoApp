import uuid
from datetime import timedelta, time
from unittest.mock import patch
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken
from accounts.models import User
from partners.models import Partner, PartnerApplication, TrainingCohort, TrainingSession, TrainingEnrollment
from payments.models import Payment
from properties.models import Property
from viewings.models import Viewing
from .models import OperationsIssue, OperationsEvent, OperationsScan
from .operations import scan_operations

BASE='/api/staff/onboarding/operations/'
ORIGIN={'HTTP_ORIGIN':'https://patahao.app'}


class OperationsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin=User.objects.create_superuser(username='ops-admin',email='ops@example.test',password='TestingPassword123!')
        cls.customer=User.objects.create_user(username='ops-customer',email='customer@example.test',password='TestingPassword123!')
        cls.reader=User.objects.create_user(username='ops-reader',email='reader@example.test',password='TestingPassword123!',is_staff=True)
        cls.reader.user_permissions.add(*Permission.objects.filter(codename__in=['view_operationsissue','view_partnerapplication']))
        cls.partner=Partner.objects.create(user=cls.admin, business_name='Ops',display_name='Ops',partner_type='agent')
        cls.property=Property.objects.create(partner=cls.partner,title='Ops property',property_type='apartment',listing_type='rent',price='20000',county='Nairobi',town='Roysambu',estate='Roysambu',address='Private address',description='Private description')

    def setUp(self):
        self.now=timezone.now()
        self.client=APIClient()
        self.login(self.admin)

    def login(self,user):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer '+str(AccessToken.for_user(user)))

    def payment(self):
        return Payment.objects.create(payer=self.customer,status='processing',initiated_at=self.now-timedelta(minutes=21),phone_number='254722229022',provider_request_payload={'Password':'PRIVATE'})

    def application(self):
        a=PartnerApplication.objects.create(submission_key=uuid.uuid4(),full_name='Ops applicant',phone_number='254722229023',county='Nairobi',operating_area='Roysambu',partner_type='new',experience='new',training_availability='flexible')
        PartnerApplication.objects.filter(pk=a.pk).update(updated_at=self.now-timedelta(days=3))
        return a

    def viewing(self,**kwargs):
        v=Viewing.objects.create(customer=self.customer,property=self.property,requested_date=timezone.localdate(),requested_time=time(10),**kwargs)
        Viewing.objects.filter(pk=v.pk).update(updated_at=self.now-timedelta(hours=3))
        return v

    def test_scan_idempotent_and_never_changes_payment_or_viewing(self):
        p=self.payment();v=self.viewing(status='paid_pending_partner')
        before=Payment.objects.values().get(pk=p.pk)
        self.assertEqual(scan_operations(self.now),2)
        scan_operations(self.now)
        self.assertEqual(OperationsIssue.objects.count(),2)
        self.assertEqual(OperationsEvent.objects.count(),2)
        self.assertEqual(before,Payment.objects.values().get(pk=p.pk))
        v.refresh_from_db();self.assertEqual(v.status,'paid_pending_partner')

    def test_age_thresholds_and_terminal_statuses(self):
        p=self.payment();Payment.objects.filter(pk=p.pk).update(initiated_at=self.now)
        self.viewing(status='confirmed')
        self.assertEqual(scan_operations(self.now),0)
        Payment.objects.filter(pk=p.pk).update(initiated_at=self.now-timedelta(minutes=20))
        self.assertEqual(scan_operations(self.now),1)
        Payment.objects.filter(pk=p.pk).update(status='successful')
        scan_operations(self.now)
        self.assertEqual(OperationsIssue.objects.get().state,'resolved')
        self.assertEqual(OperationsEvent.objects.last().action,'detected')
        self.assertTrue(OperationsEvent.objects.filter(action='source_cleared').exists())

    def test_fee_resolution_does_not_disappear_when_only_claimed(self):
        self.viewing(status='declined',fee_resolution_choice='refund',fee_resolution_requested_at=self.now-timedelta(days=2))
        scan_operations(self.now);i=OperationsIssue.objects.get()
        r=self.client.patch(BASE+f'{i.pk}/',{'action':'claim','revision':i.revision},format='json',**ORIGIN)
        self.assertEqual(r.status_code,200,r.data)
        scan_operations(self.now);i.refresh_from_db();self.assertEqual(i.state,'following')
        self.assertEqual(Viewing.objects.get().fee_resolution_processed_at,None)

    def test_claim_and_defer_reappear_at_due_time(self):
        self.payment();scan_operations(self.now);i=OperationsIssue.objects.get()
        due=self.now+timedelta(hours=2)
        r=self.client.patch(BASE+f'{i.pk}/',{'action':'defer','revision':i.revision,'follow_up_at':due.isoformat()},format='json',**ORIGIN)
        self.assertEqual(r.status_code,200,r.data)
        scan_operations(self.now+timedelta(hours=1));i.refresh_from_db();self.assertEqual(i.state,'snoozed')
        scan_operations(due);i.refresh_from_db();self.assertEqual(i.state,'open');self.assertIsNone(i.follow_up_at)
        self.assertEqual(i.owner,self.admin)
        self.assertEqual(i.events.filter(action='follow_up_due').count(),1)

    def test_deferral_validation_stale_edits_and_no_arbitrary_close(self):
        self.payment();scan_operations(self.now);i=OperationsIssue.objects.get()
        for data in [{'action':'defer','revision':i.revision}, {'action':'defer','revision':i.revision,'follow_up_at':(self.now+timedelta(days=8)).isoformat()}, {'action':'resolve','revision':i.revision}]:
            self.assertEqual(self.client.patch(BASE+f'{i.pk}/',data,format='json',**ORIGIN).status_code,400)
        self.assertEqual(self.client.patch(BASE+f'{i.pk}/',{'action':'claim','revision':999},format='json',**ORIGIN).status_code,409)
        self.assertEqual(OperationsEvent.objects.count(),1)

    def test_permissions_hide_finance_counts_and_details(self):
        self.payment();self.application();scan_operations(self.now)
        finance=OperationsIssue.objects.get(category='payment')
        self.login(self.reader)
        r=self.client.get(BASE,**ORIGIN)
        self.assertEqual(r.status_code,200,r.data);self.assertEqual(r.data['count'],1)
        self.assertEqual(r.data['counts']['open'],1)
        self.assertEqual(self.client.get(BASE+f'{finance.pk}/',**ORIGIN).status_code,404)
        issue=OperationsIssue.objects.get(category='onboarding')
        self.assertEqual(self.client.patch(BASE+f'{issue.pk}/',{'action':'claim','revision':1},format='json',**ORIGIN).status_code,403)
        self.assertEqual(self.client.post(BASE+'scan/',{},format='json',**ORIGIN).status_code,403)

    def test_customer_anonymous_and_untrusted_origins_blocked(self):
        self.login(self.customer);self.assertEqual(self.client.get(BASE,**ORIGIN).status_code,403)
        self.client.credentials();self.assertEqual(self.client.get(BASE,**ORIGIN).status_code,401)
        self.login(self.admin);self.assertEqual(self.client.get(BASE,HTTP_ORIGIN='https://evil.test').status_code,403)
        r=self.client.options(BASE,**ORIGIN);self.assertEqual(r.status_code,204)
        self.assertEqual(r['Access-Control-Allow-Origin'],'https://patahao.app')

    def test_source_projection_and_history_are_safe(self):
        self.payment();scan_operations(self.now);i=OperationsIssue.objects.get()
        r=self.client.get(BASE+f'{i.pk}/',**ORIGIN)
        self.assertEqual(r.status_code,200,r.data)
        self.assertNotIn('PRIVATE',str(r.data));self.assertNotIn('254722229022',str(r.data));self.assertNotIn('provider_request_payload',str(r.data))
        self.assertEqual(r['Cache-Control'],'no-store')
        event=i.events.get();event.action='changed'
        with self.assertRaises(ValueError):event.save()
        with self.assertRaises(ValueError):event.delete()

    def test_onboarding_withdrawn_and_future_training_not_flagged(self):
        a=self.application();cohort=TrainingCohort.objects.create(name='Future',scheduled_date=timezone.localdate()+timedelta(days=2),slot='am',location='Nairobi',trainer_name='Trainer',created_by=self.admin)
        TrainingEnrollment.objects.create(application=a,cohort=cohort)
        self.assertEqual(scan_operations(self.now),0)
        PartnerApplication.objects.filter(pk=a.pk).update(status='withdrawn')
        TrainingEnrollment.objects.filter(application=a).update(state='certified')
        self.assertEqual(scan_operations(self.now),0)

    def test_training_follow_up_and_certified_activation_pending(self):
        a=self.application();day=timezone.localdate()-timedelta(days=3)
        cohort=TrainingCohort.objects.create(name='Past',scheduled_date=day,slot='am',location='Nairobi',trainer_name='Trainer',created_by=self.admin)
        TrainingSession.objects.create(cohort=cohort,date=day)
        e=TrainingEnrollment.objects.create(application=a,cohort=cohort)
        TrainingEnrollment.objects.filter(pk=e.pk).update(updated_at=self.now-timedelta(days=2))
        self.assertEqual(scan_operations(self.now),1)
        self.assertEqual(OperationsIssue.objects.get(state='open').rule,'training_follow_up')
        TrainingEnrollment.objects.filter(pk=e.pk).update(state='certified')
        scan_operations(self.now)
        self.assertEqual(OperationsIssue.objects.get(state='open').rule,'activation_pending')
        self.assertEqual(OperationsIssue.objects.get(rule='training_follow_up').state,'resolved')

    def test_failed_scan_rolls_back_without_resolving_queue(self):
        self.payment();scan_operations(self.now);completed=OperationsScan.objects.get().completed_at
        with patch('core.operations.candidates',side_effect=RuntimeError('source unavailable')):
            with self.assertRaises(RuntimeError):scan_operations(self.now+timedelta(hours=1))
        self.assertEqual(OperationsIssue.objects.get().state,'open')
        self.assertEqual(OperationsScan.objects.get().completed_at,completed)

    def test_scan_and_source_clearing_api(self):
        p=self.payment()
        r=self.client.post(BASE+'scan/',{},format='json',**ORIGIN);self.assertEqual(r.status_code,200,r.data)
        r=self.client.get(BASE,**ORIGIN);self.assertFalse(r.data['stale']);self.assertEqual(r.data['count'],1)
        Payment.objects.filter(pk=p.pk).update(status='failed')
        self.client.post(BASE+'scan/',{},format='json',**ORIGIN)
        self.assertEqual(self.client.get(BASE,**ORIGIN).data['count'],0)
        self.assertEqual(self.client.get(BASE+'?state=resolved',**ORIGIN).data['count'],1)
