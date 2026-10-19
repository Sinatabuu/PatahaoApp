import csv
import io
import uuid
from datetime import datetime, timezone as dt_timezone
from unittest.mock import patch
from django.contrib.auth.models import Permission
from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken
from accounts.models import User
from partners.models import PartnerApplication

BASE = '/api/staff/onboarding/reports/'
ORIGIN = {'HTTP_ORIGIN': 'https://patahao.app'}
NOW = datetime(2026, 10, 19, 12, tzinfo=dt_timezone.utc)


class StaffReportTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.staff = User.objects.create_user(username='reporter', email='reporter@example.test', password='TestPassword123!', is_staff=True)
        cls.staff.user_permissions.add(*Permission.objects.filter(content_type__app_label='partners', codename__in=['view_partnerapplication', 'change_partnerapplication']))
        cls.reader = User.objects.create_user(username='reader', email='readonly@example.test', password='TestPassword123!', is_staff=True)
        cls.reader.user_permissions.add(Permission.objects.get(content_type__app_label='partners', codename='view_partnerapplication'))
        cls.customer = User.objects.create_user(username='visitor', email='visitor@example.test', password='TestPassword123!')

    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.auth(self.staff)

    def auth(self, user):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer '+str(AccessToken.for_user(user)))

    def application(self, **fields):
        data = dict(submission_key=uuid.uuid4(), full_name='Test Applicant', phone_number='254712345678', county='Nairobi', operating_area='Roysambu', partner_type='agent', experience='new', training_availability='flexible')
        data.update(fields)
        return PartnerApplication.objects.create(**data)

    def test_report_access_requires_staff_permission(self):
        self.client.credentials()
        self.assertEqual(self.client.get(BASE, **ORIGIN).status_code, 401)
        self.auth(self.customer)
        self.assertEqual(self.client.get(BASE, **ORIGIN).status_code, 403)
        self.auth(self.reader)
        r = self.client.get(BASE, **ORIGIN)
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.data['can_export'])
        self.assertEqual(self.client.get(BASE+'export/', **ORIGIN).status_code, 403)

    def test_pipeline_current_status_and_county_counts(self):
        self.application(status='screening')
        self.application(status='invited')
        self.application(county='Kiambu', status='declined')
        r = self.client.get(BASE+'?county=nairobi', **ORIGIN)
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data['pipeline']['total'], 2)
        self.assertEqual(r.data['pipeline']['counties'], [{'county':'Nairobi','count':2}])
        counts = {a['status']:a['count'] for a in r.data['pipeline']['statuses']}
        self.assertEqual(counts['screening'],1)
        self.assertEqual(counts['invited'],1)
        self.assertEqual(counts['declined'],0)

    def test_date_filter_uses_kenya_midnight_and_inclusive_end(self):
        before=self.application();start=self.application();end=self.application();after=self.application()
        for a, stamp in [(before,'2026-10-18T20:59:59+00:00'),(start,'2026-10-18T21:00:00+00:00'),(end,'2026-10-19T20:59:59+00:00'),(after,'2026-10-19T21:00:00+00:00')]:
            PartnerApplication.objects.filter(pk=a.pk).update(created_at=datetime.fromisoformat(stamp))
        r=self.client.get(BASE+'?date_from=2026-10-19&date_to=2026-10-19', **ORIGIN)
        self.assertEqual(r.data['pipeline']['total'],2)

    def test_appointments_filter_on_appointment_not_submission(self):
        self.application(status='invited', office_appointment=datetime.fromisoformat('2026-10-21T06:00:00+00:00'))
        with patch('partners.staff_reports.timezone.now', return_value=NOW):
            r=self.client.get(BASE+'?date_from=2026-10-21&date_to=2026-10-21', **ORIGIN)
        self.assertEqual(r.data['pipeline']['total'],0)
        self.assertEqual(r.data['appointments']['count'],1)

    def test_schedule_counts_and_excludes_closed_applications(self):
        for state,hour in [('invited',10),('screening',14),('declined',15),('withdrawn',16)]:
            self.application(status=state, office_appointment=NOW.replace(hour=hour))
        with patch('partners.staff_reports.timezone.now',return_value=NOW):
            r=self.client.get(BASE, **ORIGIN)
            past=self.client.get(BASE+'?appointment_scope=past', **ORIGIN)
        self.assertEqual(r.data['appointments']['upcoming_count'],1)
        self.assertEqual(r.data['appointments']['past_count'],1)
        self.assertEqual(r.data['appointments']['count'],1)
        self.assertEqual(past.data['appointments']['count'],1)
        self.assertNotIn('phone_number',r.data['appointments']['results'][0])
        self.assertNotIn('email',r.data['appointments']['results'][0])

    def test_invalid_filters_return_errors(self):
        for query in ['date_from=not-a-date','date_from=2026-10-22&date_to=2026-10-21','appointment_scope=attended']:
            self.assertEqual(self.client.get(BASE+'?'+query, **ORIGIN).status_code,400)

    def test_schedule_pagination(self):
        for index in range(21):
            self.application(office_appointment=NOW+__import__('datetime').timedelta(days=1,minutes=index))
        with patch('partners.staff_reports.timezone.now',return_value=NOW):
            r=self.client.get(BASE, **ORIGIN)
            second=self.client.get(BASE+'?page=2', **ORIGIN)
        self.assertEqual(r.data['appointments']['count'],21)
        self.assertEqual(len(r.data['appointments']['results']),20)
        self.assertEqual(len(second.data['appointments']['results']),1)
        self.assertTrue(r.data['appointments']['next'])

    def test_csv_escapes_formulas_and_uses_kenya_time(self):
        self.application(full_name='=HYPERLINK("bad")', county='@malicious', office_appointment=datetime.fromisoformat('2026-10-21T06:00:00+00:00'))
        r=self.client.get(BASE+'export/?report=appointments&appointment_scope=all', **ORIGIN)
        self.assertEqual(r.status_code,200)
        rows=list(csv.reader(io.StringIO(r.content.decode('utf-8-sig'))))
        self.assertTrue(rows[1][1].startswith("'="))
        self.assertTrue(rows[1][2].startswith("'@"))
        self.assertEqual(rows[1][-1],'2026-10-21 09:00')
        self.assertEqual(r['Cache-Control'],'no-store')
        self.assertEqual(r['Access-Control-Allow-Origin'],'https://patahao.app')
        self.assertNotIn('254712345678',r.content.decode())

    def test_pipeline_csv_matches_summary_and_filter(self):
        self.application(status='screening')
        self.application(status='invited',county='Kiambu')
        r=self.client.get(BASE+'export/?county=Nairobi', **ORIGIN)
        rows=list(csv.reader(io.StringIO(r.content.decode('utf-8-sig'))))
        self.assertIn(['Staff screening','1'],rows)
        self.assertIn(['Total','1'],rows)
        self.assertEqual(self.client.get(BASE+'export/?report=unknown', **ORIGIN).status_code,400)
