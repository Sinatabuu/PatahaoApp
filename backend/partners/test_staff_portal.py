import uuid
from unittest.mock import patch
from django.contrib.auth.models import Permission
from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken
from accounts.models import User
from partners.models import PartnerApplication, PartnerApplicationEvent, Partner

BASE = '/api/staff/onboarding/'
ORIGIN = {'HTTP_ORIGIN': 'https://patahao.app'}


class StaffPortalTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.staff = User.objects.create_user(username='recruiter', email='staff@example.test', password='TestingPassword123!', is_staff=True)
        cls.staff.user_permissions.add(*Permission.objects.filter(content_type__app_label='partners', codename__in=['view_partnerapplication', 'change_partnerapplication']))
        cls.reader = User.objects.create_user(username='reader', email='reader@example.test', password='TestingPassword123!', is_staff=True)
        cls.reader.user_permissions.add(Permission.objects.get(content_type__app_label='partners', codename='view_partnerapplication'))
        cls.customer = User.objects.create_user(username='customer', email='customer@example.test', password='TestingPassword123!')

    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.a = PartnerApplication.objects.create(submission_key=uuid.uuid4(), full_name='Applicant Test', phone_number='254712345678', county='Nairobi', operating_area='Roysambu', partner_type='new', experience='new', training_availability='flexible')

    def authenticate(self, user=None):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + str(AccessToken.for_user(user or self.staff)))

    def payload(self, **extra):
        return dict(status='screening', office_appointment=None, expected_updated_at=self.a.updated_at.isoformat(), action='screening', **extra)

    def test_anonymous_and_customer_cannot_read_applicants(self):
        self.assertEqual(self.client.get(BASE+'applications/', **ORIGIN).status_code, 401)
        self.authenticate(self.customer)
        self.assertEqual(self.client.get(BASE+'applications/', **ORIGIN).status_code, 403)
        self.assertEqual(self.client.get(BASE+f'applications/{self.a.pk}/', **ORIGIN).status_code, 403)

    def test_login_only_issues_access_token_to_authorized_staff(self):
        r = self.client.post(BASE+'login/', {'username':'recruiter', 'password':'TestingPassword123!'}, format='json', **ORIGIN)
        self.assertEqual(r.status_code, 200, r.data)
        self.assertIn('access', r.data)
        self.assertNotIn('refresh', r.data)
        self.assertTrue(r.data['staff']['can_change'])
        r = self.client.post(BASE+'login/', {'username':'customer', 'password':'TestingPassword123!'}, format='json', **ORIGIN)
        self.assertEqual(r.status_code, 403)
        self.assertNotIn('access', r.data)

    def test_staff_search_and_detail_do_not_expose_submission_key(self):
        self.authenticate()
        r = self.client.get(BASE+'applications/?search=Roysambu', **ORIGIN)
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data['count'], 1)
        self.assertEqual(r.data['counts'], {'submitted':1})
        self.assertNotIn('submission_key', r.data['results'][0])
        r = self.client.get(BASE+f'applications/{self.a.pk}/', **ORIGIN)
        self.assertEqual(r.data['history'], [])
        self.assertNotIn('submission_key', r.data)

    def test_read_only_staff_cannot_change(self):
        self.authenticate(self.reader)
        self.assertEqual(self.client.get(BASE+'applications/', **ORIGIN).status_code, 200)
        r = self.client.patch(BASE+f'applications/{self.a.pk}/', self.payload(), format='json', **ORIGIN)
        self.assertEqual(r.status_code, 403)
        self.assertEqual(PartnerApplicationEvent.objects.count(), 0)

    def test_screening_updates_are_audited_and_visible_to_applicant(self):
        self.authenticate()
        r = self.client.patch(BASE+f'applications/{self.a.pk}/', self.payload(), format='json', **ORIGIN)
        self.assertEqual(r.status_code, 200, r.data)
        event = PartnerApplicationEvent.objects.get()
        self.assertEqual(event.actor, self.staff)
        self.assertEqual((event.previous_status,event.new_status), ('submitted','screening'))
        self.client.credentials()
        r = self.client.post('/api/partner-applications/status/', {'reference':self.a.reference, 'phone_number':self.a.phone_number}, format='json', **ORIGIN)
        self.assertEqual(r.data['status'], 'Staff screening')
        self.assertNotIn('history', r.data)

    def test_kenya_appointment_keeps_intended_office_time(self):
        self.authenticate()
        data = self.payload()
        data.update(status='invited', office_appointment='2026-10-21T09:00:00+03:00', action='appointment')
        r = self.client.patch(BASE+f'applications/{self.a.pk}/', data, format='json', **ORIGIN)
        self.assertEqual(r.status_code, 200, r.data)
        self.a.refresh_from_db()
        self.assertEqual(self.a.office_appointment.hour, 6)
        self.assertEqual(self.a.status, 'invited')
        self.assertEqual(Partner.objects.count(), 0)

    def test_invitation_needs_date_and_certification_is_not_an_option(self):
        self.authenticate()
        data=self.payload();data['status']='invited'
        self.assertEqual(self.client.patch(BASE+f'applications/{self.a.pk}/', data, format='json', **ORIGIN).status_code, 400)
        data['status']='certified'
        self.assertEqual(self.client.patch(BASE+f'applications/{self.a.pk}/', data, format='json', **ORIGIN).status_code, 400)

    def test_stale_edit_is_rejected(self):
        self.authenticate()
        data=self.payload()
        first=self.client.patch(BASE+f'applications/{self.a.pk}/', data, format='json', **ORIGIN)
        self.assertEqual(first.status_code, 200)
        second=self.client.patch(BASE+f'applications/{self.a.pk}/', data, format='json', **ORIGIN)
        self.assertEqual(second.status_code, 409)
        self.assertEqual(PartnerApplicationEvent.objects.count(), 1)

    def test_audit_failure_rolls_back_status(self):
        self.authenticate()
        with patch('partners.staff_portal.PartnerApplicationEvent.objects.create', side_effect=RuntimeError('audit failure')):
            with self.assertRaises(RuntimeError):
                self.client.patch(BASE+f'applications/{self.a.pk}/', self.payload(), format='json', **ORIGIN)
        self.a.refresh_from_db()
        self.assertEqual(self.a.status, 'submitted')

    def test_cors_allows_bearer_preflight_and_preserves_auth_errors(self):
        r=self.client.options(BASE+'applications/', **ORIGIN)
        self.assertEqual(r.status_code, 204)
        self.assertIn('Authorization',r['Access-Control-Allow-Headers'])
        r=self.client.get(BASE+'applications/', **ORIGIN)
        self.assertEqual(r.status_code,401)
        self.assertEqual(r['Access-Control-Allow-Origin'], 'https://patahao.app')
        r=self.client.options(BASE+'applications/', HTTP_ORIGIN='https://untrusted.example')
        self.assertEqual(r.status_code,403)
        self.assertNotIn('Access-Control-Allow-Origin',r)

    def test_staff_permission_removed_invalidates_access_immediately(self):
        self.authenticate()
        User.objects.filter(pk=self.staff.pk).update(is_staff=False)
        self.assertEqual(self.client.get(BASE+'applications/', **ORIGIN).status_code,403)

    def test_event_cannot_be_edited_or_deleted(self):
        self.authenticate()
        self.client.patch(BASE+f'applications/{self.a.pk}/', self.payload(),format='json', **ORIGIN)
        event=PartnerApplicationEvent.objects.get()
        with self.assertRaises(ValueError): event.save()
        with self.assertRaises(ValueError): event.delete()
