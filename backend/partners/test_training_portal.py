import uuid
from datetime import timedelta
from unittest.mock import patch
from django.contrib.auth.models import Permission
from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken
from accounts.models import User
from partners.models import Partner, PartnerApplication, TrainingCohort, TrainingEnrollment, TrainingEvent
from partners.training_models import MODULES

BASE='/api/staff/onboarding/training/'
ORIGIN={'HTTP_ORIGIN':'https://patahao.app'}


class TrainingPortalTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.trainer=User.objects.create_user(username='trainer',email='trainer@example.test',password='Testing123!',is_staff=True)
        cls.supervisor=User.objects.create_user(username='supervisor',email='supervisor@example.test',password='Testing123!',is_staff=True)
        cls.reader=User.objects.create_user(username='reader',email='reader@example.test',password='Testing123!',is_staff=True)
        for user in (cls.trainer,cls.supervisor,cls.reader):
            user.user_permissions.add(Permission.objects.get(codename='view_partnerapplication',content_type__app_label='partners'))
        for user in (cls.trainer,cls.supervisor):
            user.user_permissions.add(Permission.objects.get(codename='change_partnerapplication',content_type__app_label='partners'))
        cls.supervisor.user_permissions.add(Permission.objects.get(codename='certify_partner_training',content_type__app_label='partners'))

    def setUp(self):
        cache.clear();self.client=APIClient();self.auth(self.trainer)
        past=timezone.localdate()-timedelta(days=10)
        r=self.client.post(BASE+'cohorts/',{'name':'Roysambu one','trainer_name':'Trainer Test','location':'Test office','dates':[(past+timedelta(days=i)).isoformat() for i in range(3)]},format='json',**ORIGIN)
        self.assertEqual(r.status_code,201,r.data);self.cohort=r.data['id']
        self.application=PartnerApplication.objects.create(submission_key=uuid.uuid4(),full_name='Trainee Test',phone_number='254712345678',county='Nairobi',operating_area='Roysambu',partner_type='new',experience='new',training_availability='flexible',status='invited')

    def auth(self,user):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer '+str(AccessToken.for_user(user)))

    def enroll(self):
        r=self.client.post(BASE+f'cohorts/{self.cohort}/',{'application_reference':self.application.reference},format='json',**ORIGIN)
        self.assertEqual(r.status_code,201,r.data);return r.data

    def complete(self,e):
        data={'expected_updated_at':e['updated_at'],'identity_checked':True,'agreement_signed':True,'attendance':[{'session_id':a['session_id'],'result':'present'} for a in e['attendance']],'assessments':[{'module':a['module'],'result':'pass'} for a in e['assessments']]}
        r=self.client.patch(BASE+f'enrollments/{e["id"]}/',data,format='json',**ORIGIN);self.assertEqual(r.status_code,200,r.data);return r.data

    def decide(self,e,decision='certify'):
        return self.client.post(BASE+f'enrollments/{e["id"]}/decision/',{'expected_updated_at':e['updated_at'],'decision':decision},format='json',**ORIGIN)

    def test_cohort_limit_and_unique_application(self):
        self.enroll()
        for i in range(11):
            a=PartnerApplication.objects.create(submission_key=uuid.uuid4(),full_name=f'Test {i}',phone_number='254712345678',county='Nairobi',operating_area='Roysambu',partner_type='new',experience='new',training_availability='flexible',status='screening')
            r=self.client.post(BASE+f'cohorts/{self.cohort}/',{'application_reference':a.reference},format='json',**ORIGIN);self.assertEqual(r.status_code,201)
        a=PartnerApplication.objects.create(submission_key=uuid.uuid4(),full_name='Thirteenth',phone_number='254712345678',county='Nairobi',operating_area='Roysambu',partner_type='new',experience='new',training_availability='flexible',status='invited')
        r=self.client.post(BASE+f'cohorts/{self.cohort}/',{'application_reference':a.reference},format='json',**ORIGIN);self.assertEqual(r.status_code,400)
        self.assertEqual(TrainingEnrollment.objects.count(),12)

    def test_duplicate_enrollment_and_unscreened_applicant_rejected(self):
        self.enroll()
        r=self.client.post(BASE+f'cohorts/{self.cohort}/',{'application_reference':self.application.reference},format='json',**ORIGIN);self.assertEqual(r.status_code,400)
        self.application.status='withdrawn';self.application.save()
        self.assertEqual(self.client.post(BASE+f'cohorts/{self.cohort}/',{'application_reference':self.application.reference},format='json',**ORIGIN).status_code,400)

    def test_training_record_has_all_eight_modules_and_sessions(self):
        e=self.enroll();self.assertEqual(len(e['attendance']),3);self.assertEqual(len(e['assessments']),8)
        self.assertEqual(set(a['module'] for a in e['assessments']),{code for code,_ in MODULES})
        completed=self.complete(e);self.assertEqual(completed['readiness_issues'],[])
        self.assertEqual(completed['state'],'enrolled')
        self.assertEqual(Partner.objects.count(),0)

    def test_only_supervisor_can_certify_and_no_account_is_activated(self):
        e=self.complete(self.enroll())
        self.assertEqual(self.decide(e).status_code,403)
        self.auth(self.supervisor);r=self.decide(e);self.assertEqual(r.status_code,200,r.data)
        self.assertEqual(r.data['state'],'certified');self.assertEqual(r.data['certified_by'],'supervisor')
        self.assertEqual(Partner.objects.count(),0)
        self.assertEqual(User.objects.filter(role='partner').count(),0)
        self.assertTrue(TrainingEvent.objects.filter(action='Training certify').exists())

    def test_incomplete_and_future_training_cannot_be_certified(self):
        e=self.enroll();self.auth(self.supervisor);self.assertEqual(self.decide(e).status_code,400)
        e=self.complete(e)
        c=TrainingCohort.objects.get(pk=self.cohort)
        first=c.sessions.first();first.date=timezone.localdate()+timedelta(days=20);first.save()
        self.assertEqual(self.decide(e).status_code,400)

    def test_stale_updates_rejected(self):
        e=self.enroll();self.complete(e)
        self.auth(self.supervisor);self.assertEqual(self.decide(e).status_code,409)

    def test_readonly_staff_cannot_change_training(self):
        self.auth(self.reader)
        self.assertEqual(self.client.get(BASE+'cohorts/',**ORIGIN).status_code,200)
        self.assertEqual(self.client.post(BASE+f'cohorts/{self.cohort}/',{'application_reference':self.application.reference},format='json',**ORIGIN).status_code,403)

    def test_certificate_requires_reopening_before_edits(self):
        e=self.complete(self.enroll());self.auth(self.supervisor);r=self.decide(e);self.assertEqual(r.status_code,200)
        reopened=self.decide(r.data,'reopen');self.assertEqual(reopened.status_code,200)
        self.assertEqual(reopened.data['state'],'enrolled')
        self.assertTrue(all(a['result']=='pending' for a in reopened.data['assessments']))

    def test_training_progress_is_private_to_reference_phone_lookup(self):
        self.enroll();self.client.credentials()
        r=self.client.post('/api/partner-applications/status/',{'reference':self.application.reference,'phone_number':self.application.phone_number},format='json',**ORIGIN)
        self.assertEqual(r.data['status'],'In training');self.assertEqual(r.data['training']['modules_required'],8)
        self.assertNotIn('identity_checked',r.data['training']);self.assertNotIn('history',r.data)

    def test_audit_failure_rolls_back_enrollment(self):
        with patch('partners.training_portal.TrainingEvent.objects.create',side_effect=RuntimeError('audit failed')):
            with self.assertRaises(RuntimeError):
                self.client.post(BASE+f'cohorts/{self.cohort}/',{'application_reference':self.application.reference},format='json',**ORIGIN)
        self.assertEqual(TrainingEnrollment.objects.count(),0)

    def test_invalid_duplicate_training_dates_rejected(self):
        r=self.client.post(BASE+'cohorts/',{'name':'Bad dates','trainer_name':'Trainer','location':'Office','dates':['2026-10-01','2026-10-01']},format='json',**ORIGIN)
        self.assertEqual(r.status_code,400)

    def test_anonymous_training_access_denied(self):
        self.client.credentials();self.assertEqual(self.client.get(BASE+'cohorts/',**ORIGIN).status_code,401)
