import uuid
from datetime import timedelta
from unittest.mock import patch
from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from accounts.models import User
from partners.models import (PartnerApplication, Partner, TrainingCohort, TrainingSession,
                             TrainingEnrollment, TrainingEvent)
from partners.training_schedule import KENYA

BASE='/api/partner-applications/'
ORIGIN={'HTTP_ORIGIN':'https://patahao.app'}


class ApplicantTrainingBookingTests(TestCase):
    def setUp(self):
        cache.clear();self.client=APIClient(enforce_csrf_checks=True)
        trainer=User.objects.create_user(username='trainer',email='trainer@example.test')
        day=timezone.localdate(timezone=KENYA)+timedelta(days=2)
        self.cohort=TrainingCohort.objects.create(name='Morning',scheduled_date=day,slot='am',trainer_name='Trainer',location='Roysambu office',created_by=trainer)
        TrainingSession.objects.create(cohort=self.cohort,date=day)
        self.data=dict(submission_key=str(uuid.uuid4()),full_name='Applicant Test',phone_number='0712345678',email='',county='Nairobi',operating_area='Roysambu',partner_type='new',experience='new',consent=True,office_training=True, no_cash_policy=True,training_session=self.cohort.pk)

    def submit(self,**changes):
        return self.client.post(BASE+'reserve/',{**self.data,**changes},format='json',**ORIGIN)

    def test_submission_reserves_place_and_returns_details_without_account(self):
        response=self.submit();self.assertEqual(response.status_code,201,response.data)
        application=PartnerApplication.objects.get()
        self.assertEqual(application.reference,response.data['reference'])
        self.assertEqual(application.training_enrollment.cohort,self.cohort)
        self.assertEqual(application.training_enrollment.assessments.count(),8)
        self.assertEqual(application.training_enrollment.attendance.count(),1)
        self.assertEqual(application.status,'submitted')
        self.assertEqual(application.consent_version,'recruitment-nocash-2026-10')
        self.assertEqual(application.office_appointment.astimezone(KENYA).hour,9)
        self.assertEqual(response.data['training']['time'],'9 a.m.–noon')
        self.assertEqual(response.data['training']['location'],'Roysambu office')
        self.assertEqual(Partner.objects.count(),0);self.assertEqual(User.objects.count(),1)
        event=TrainingEvent.objects.get();self.assertIsNone(event.actor)
        self.assertEqual(response['Access-Control-Allow-Origin'],'https://patahao.app')

    def test_retry_does_not_duplicate_and_works_after_class_starts(self):
        first=self.submit()
        with patch('partners.recruitment_booking.timezone.now',return_value=timezone.now()+timedelta(days=3)):
            second=self.submit()
        self.assertEqual(second.status_code,200,second.data)
        self.assertEqual(first.data['reference'],second.data['reference'])
        self.assertEqual(PartnerApplication.objects.count(),1)
        self.assertEqual(TrainingEnrollment.objects.count(),1)
        self.assertEqual(TrainingEvent.objects.count(),1)

    def test_twelfth_place_fills_and_thirteenth_rolls_back_application(self):
        for i in range(12):
            response=self.submit(submission_key=str(uuid.uuid4()),full_name=f'Applicant {i}')
            self.assertEqual(response.status_code,201,response.data)
        self.assertEqual(self.submit().status_code,409)
        self.assertEqual(PartnerApplication.objects.count(),12)
        self.assertEqual(TrainingEnrollment.objects.count(),12)
        self.assertEqual(self.client.get(BASE+'sessions/',**ORIGIN).data['sessions'],[])

    def test_availability_only_exposes_open_future_sessions(self):
        response=self.client.get(BASE+'sessions/',**ORIGIN)
        self.assertEqual(response.status_code,200)
        session=response.data['sessions'][0]
        self.assertEqual(set(session),{'id','date','time','location','remaining','timezone'})
        self.assertEqual(session['remaining'],12)
        self.assertEqual(response['Cache-Control'],'no-store')
        self.assertEqual(response['Access-Control-Allow-Origin'],'https://patahao.app')
        with patch('partners.recruitment_booking.timezone.now',return_value=timezone.now()+timedelta(days=3)):
            self.assertEqual(self.client.get(BASE+'sessions/',**ORIGIN).data['sessions'],[])
            self.assertEqual(self.submit().status_code,409)
        self.assertFalse(PartnerApplication.objects.exists())

    def test_reused_key_cannot_change_details_or_session(self):
        self.submit()
        self.assertEqual(self.submit(full_name='Changed').status_code,409)
        other=TrainingCohort.objects.create(name='Afternoon',scheduled_date=self.cohort.scheduled_date,slot='pm',trainer_name='Trainer',location='Office',created_by=self.cohort.created_by)
        TrainingSession.objects.create(cohort=other,date=other.scheduled_date)
        self.assertEqual(self.submit(training_session=other.pk).status_code,409)
        self.assertEqual(TrainingEnrollment.objects.count(),1)

    def test_invalid_or_missing_session_and_consent_rejected(self):
        data=dict(self.data);data.pop('training_session')
        self.assertEqual(self.client.post(BASE+'reserve/',data,format='json',**ORIGIN).status_code,400)
        self.assertEqual(self.submit(training_session=9999).status_code,409)
        self.assertEqual(self.submit(consent=False).status_code,400)
        self.assertEqual(self.submit(no_cash_policy=False).status_code,400)
        missing_policy=dict(self.data);missing_policy.pop('no_cash_policy')
        self.assertEqual(self.client.post(BASE+'reserve/',missing_policy,format='json',**ORIGIN).status_code,400)
        self.assertFalse(PartnerApplication.objects.exists())

    def test_untrusted_origin_preflight_and_no_listing(self):
        self.assertEqual(self.client.get(BASE+'sessions/',HTTP_ORIGIN='https://bad.example').status_code,403)
        response=self.client.options(BASE+'sessions/',**ORIGIN)
        self.assertEqual(response.status_code,204)
        self.assertIn('GET',response['Access-Control-Allow-Methods'])
        self.assertEqual(self.client.get(BASE+'reserve/',**ORIGIN).status_code,405)

    def test_audit_failure_rolls_back_both_records(self):
        with patch('partners.recruitment_booking.audit',side_effect=RuntimeError('Unavailable')):
            with self.assertRaises(RuntimeError):self.submit()
        self.assertFalse(PartnerApplication.objects.exists())
        self.assertFalse(TrainingEnrollment.objects.exists())
