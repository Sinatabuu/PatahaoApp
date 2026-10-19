import uuid
from datetime import timedelta, datetime
from unittest.mock import patch
from django.utils import timezone
from django.test import TestCase
from partners import test_training_portal as helpers
BASE, ORIGIN = helpers.BASE, helpers.ORIGIN
from partners.models import PartnerApplication, TrainingCohort, TrainingEnrollment, PartnerApplicationEvent
from partners.training_schedule import KENYA


class TrainingScheduleTests(TestCase):
    setUpTestData = classmethod(helpers.TrainingPortalTests.setUpTestData.__func__)
    auth = helpers.TrainingPortalTests.auth
    complete = helpers.TrainingPortalTests.complete
    decide = helpers.TrainingPortalTests.decide
    # Reuse fixtures/helpers while keeping the allocation cases explicit.
    def setUp(self):
        helpers.TrainingPortalTests.setUp(self)
        self.date=timezone.localdate(timezone=KENYA)+timedelta(days=2)

    def open_date(self, day=None, **extra):
        return self.client.post(BASE+'dates/', {'date':(day or self.date).isoformat(), **extra}, format='json', **ORIGIN)

    def application_for(self, number):
        return PartnerApplication.objects.create(submission_key=uuid.uuid4(),full_name=f'Applicant {number}',phone_number='254712345678',county='Nairobi',operating_area='Roysambu',partner_type='new',experience='new',training_availability='flexible')

    def schedule(self,a,day=None):
        return self.client.post(f'/api/staff/onboarding/applications/{a.pk}/schedule/', {'date':(day or self.date).isoformat(),'expected_updated_at':a.updated_at.isoformat()},format='json',**ORIGIN)

    def test_open_date_creates_two_classes_and_reuses_details(self):
        self.assertEqual(self.open_date().status_code,400)
        self.assertEqual(self.open_date(trainer_name='Sammy',location='Roysambu office').status_code,201)
        self.assertEqual(self.open_date(self.date+timedelta(days=1)).status_code,201)
        classes=TrainingCohort.objects.filter(scheduled_date__isnull=False)
        self.assertEqual(classes.count(),4)
        self.assertEqual(set(classes.values_list('slot',flat=True)),{'am','pm'})
        self.assertTrue(all(c.location=='Roysambu office' and c.sessions.count()==1 for c in classes))
        self.assertEqual(self.open_date().status_code,409)
        self.assertEqual(classes.count(),4)

    def test_fill_morning_then_afternoon_then_next_open_date(self):
        self.open_date(trainer_name='Sammy',location='Office')
        self.open_date(self.date+timedelta(days=3))
        for i in range(25):
            a=self.application_for(i)
            r=self.schedule(a)
            self.assertEqual(r.status_code,201,r.data)
            expected_slot='am' if i<12 or i==24 else 'pm'
            expected_date=self.date if i<24 else self.date+timedelta(days=3)
            self.assertEqual(r.data['class']['slot'],expected_slot)
            self.assertEqual(r.data['class']['scheduled_date'],expected_date)
            self.assertEqual(r.data['overflow'],i==24)
            a.refresh_from_db()
            self.assertEqual(a.status,'invited')
            self.assertEqual(a.office_appointment.astimezone(KENYA).hour,9 if expected_slot=='am' else 14)
            self.assertEqual(a.training_enrollment.application.reference,a.reference)
        self.assertFalse(any(c.enrollments.count()>12 for c in TrainingCohort.objects.all()))
        days=self.client.get(BASE+'dates/',**ORIGIN).data['dates']
        self.assertEqual(days[0]['remaining'],0)
        self.assertEqual(days[1]['remaining'],23)

    def test_full_no_next_date_does_not_change_application(self):
        self.open_date(trainer_name='Sammy',location='Office')
        for i in range(24): self.assertEqual(self.schedule(self.application_for(i)).status_code,201)
        a=self.application_for(25);before=a.updated_at
        self.assertEqual(self.schedule(a).status_code,409)
        a.refresh_from_db();self.assertEqual(a.status,'submitted');self.assertEqual(a.updated_at,before)
        self.assertFalse(TrainingEnrollment.objects.filter(application=a).exists())

    def test_duplicate_and_stale_and_closed_application(self):
        self.open_date(trainer_name='Sammy',location='Office')
        a=self.application_for(1);self.assertEqual(self.schedule(a).status_code,201)
        self.assertEqual(self.schedule(a).status_code,409)
        a.refresh_from_db();self.assertEqual(self.schedule(a).status_code,409)
        self.assertEqual(TrainingEnrollment.objects.filter(application=a).count(),1)
        closed=self.application_for(2);closed.status='declined';closed.save()
        self.assertEqual(self.schedule(closed).status_code,400)

    def test_readonly_cannot_open_or_schedule(self):
        self.auth(self.reader)
        self.assertEqual(self.open_date(trainer_name='Sammy',location='Office').status_code,403)
        self.assertEqual(self.schedule(self.application).status_code,403)

    def test_audit_failure_rolls_back_schedule_and_appointment(self):
        self.open_date(trainer_name='Sammy',location='Office');a=self.application_for(1)
        with patch('partners.training_schedule.audit',side_effect=RuntimeError('Audit unavailable')):
            with self.assertRaises(RuntimeError):self.schedule(a)
        a.refresh_from_db();self.assertEqual(a.status,'submitted');self.assertIsNone(a.office_appointment)
        self.assertFalse(TrainingEnrollment.objects.filter(application=a).exists())
        self.assertFalse(PartnerApplicationEvent.objects.filter(application=a).exists())

    def test_past_and_unopened_dates_rejected(self):
        self.assertEqual(self.open_date(self.date-timedelta(days=4),trainer_name='Sammy',location='Office').status_code,400)
        self.assertEqual(self.schedule(self.application).status_code,400)

    def test_started_class_skipped_and_end_time_gates_certification(self):
        self.open_date(trainer_name='Sammy',location='Office')
        now=datetime.combine(self.date,datetime.min.time(),tzinfo=KENYA).replace(hour=10)
        with patch('django.utils.timezone.now',return_value=now):
            r=self.schedule(self.application);self.assertEqual(r.status_code,201,r.data)
            self.assertEqual(r.data['class']['slot'],'pm')
            record=self.complete(r.data['enrollment']);self.auth(self.supervisor)
            response=self.decide(record);self.assertEqual(response.status_code,400)
            self.assertIn('must finish',str(response.data))

    def test_public_status_includes_assigned_time_and_location(self):
        self.open_date(trainer_name='Sammy',location='Office')
        self.schedule(self.application)
        response=self.client.post('/api/partner-applications/status/',{'reference':self.application.reference,'phone_number':self.application.phone_number},format='json',**ORIGIN)
        self.assertEqual(response.status_code,200,response.data)
        self.assertEqual(response.data['training']['location'],'Office')
        self.assertEqual(response.data['training']['time'],'9 a.m.–noon')
