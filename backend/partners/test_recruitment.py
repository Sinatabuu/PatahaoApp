import uuid
from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient
from accounts.models import User
from partners.models import Partner, PartnerApplication


class RecruitmentTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.data = dict(submission_key=str(uuid.uuid4()), full_name='Test Applicant', phone_number='0712345678', email='', county='Nairobi', operating_area='Roysambu', partner_type='new', experience='new', training_availability='flexible', consent=True, office_training=True, no_cash_policy=True)

    def submit(self, data=None, origin='https://patahao.app'):
        return self.client.post('/api/partner-applications/', data or self.data, format='json', HTTP_ORIGIN=origin)

    def test_application_does_not_create_user_or_partner(self):
        r = self.submit()
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(User.objects.count(), 0)
        self.assertEqual(Partner.objects.count(), 0)
        a = PartnerApplication.objects.get()
        self.assertEqual(a.phone_number, '254712345678')
        self.assertEqual(a.status, 'submitted')
        self.assertEqual(r['Access-Control-Allow-Origin'], 'https://patahao.app')
        self.assertNotIn('phone_number', r.data)

    def test_retry_returns_same_reference_without_duplicate(self):
        first = self.submit()
        second = self.submit()
        self.assertEqual(second.status_code, 200, second.data)
        self.assertEqual(first.data['reference'], second.data['reference'])
        self.assertEqual(PartnerApplication.objects.count(), 1)

    def test_reused_key_with_changed_details_rejected(self):
        self.submit()
        self.data['full_name'] = 'Changed'
        self.assertEqual(self.submit().status_code, 409)

    def test_consent_and_office_training_required(self):
        for field in ('consent', 'office_training'):
            with self.subTest(field=field):
                data = dict(self.data, **{field: False})
                self.assertEqual(self.submit(data).status_code, 400)
        self.assertEqual(PartnerApplication.objects.count(), 0)

    def test_invalid_phone_and_untrusted_origin(self):
        self.assertEqual(self.submit(dict(self.data, phone_number='123')).status_code, 400)
        self.assertEqual(self.submit(origin='https://untrusted.example').status_code, 403)

    def test_status_requires_reference_and_matching_phone(self):
        ref = self.submit().data['reference']
        url = '/api/partner-applications/status/'
        r = self.client.post(url, {'reference': ref, 'phone_number': '0799999999'}, format='json', HTTP_ORIGIN='https://patahao.app')
        self.assertEqual(r.status_code, 404)
        r = self.client.post(url, {'reference': ref, 'phone_number': '0712345678'}, format='json', HTTP_ORIGIN='https://patahao.app')
        self.assertEqual(r.status_code, 200)
        self.assertNotIn('full_name', r.data)
        self.assertNotIn('email', r.data)

    def test_preflight_and_no_public_listing(self):
        r = self.client.options('/api/partner-applications/', HTTP_ORIGIN='https://patahao.app')
        self.assertEqual(r.status_code, 204)
        self.assertEqual(r['Access-Control-Allow-Headers'], 'Content-Type')
        self.assertEqual(self.client.get('/api/partner-applications/').status_code, 405)

    def test_untrusted_fields_cannot_activate_an_account(self):
        r = self.submit(dict(self.data, status='certified', is_staff=True, is_active=True))
        self.assertEqual(r.status_code, 201)
        self.assertEqual(PartnerApplication.objects.get().status, 'submitted')
        self.assertEqual(Partner.objects.count(), 0)

    def test_browser_submission_without_session_or_csrf_cookie(self):
        self.client = APIClient(enforce_csrf_checks=True)
        self.assertEqual(self.submit().status_code, 201)

    def test_rate_limit_response_includes_cors(self):
        from unittest.mock import patch
        with patch('partners.recruitment.RecruitmentThrottle.allow_request', return_value=False), patch('partners.recruitment.RecruitmentThrottle.wait', return_value=60):
            r = self.submit()
        self.assertEqual(r.status_code, 429)
        self.assertEqual(r['Access-Control-Allow-Origin'], 'https://patahao.app')
