import re
from unittest.mock import Mock, patch

import requests
from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework.test import APIClient

from accounts.email_backend import EmailDeliveryError, ResendEmailBackend
from accounts.models import PasswordResetChallenge
from accounts.services import PASSWORD_RESET_RESPONSE

SETTINGS = dict(EMAIL_BACKEND='accounts.email_backend.ResendEmailBackend',
                RESEND_API_KEY='test-provider-key', DEFAULT_FROM_EMAIL='Pata Hao <noreply@test.example>')


@override_settings(**SETTINGS)
class HttpsEmailBackendTests(SimpleTestCase):
    def setUp(self):
        self.message = EmailMessage('Reset password', 'Private code: 12345678', to=['user@example.com'])

    @patch('accounts.email_backend.requests.post')
    def test_send_uses_fixed_https_and_bounded_timeout(self, post):
        post.return_value = Mock(status_code=200, json=Mock(return_value={'id': 'provider-id'}))
        self.assertEqual(ResendEmailBackend().send_messages([self.message]), 1)
        args, kwargs = post.call_args
        self.assertEqual(args, ('https://api.resend.com/emails',))
        self.assertEqual(kwargs['timeout'], (3, 8))
        self.assertFalse(kwargs['allow_redirects'])
        self.assertEqual(kwargs['headers']['Authorization'], 'Bearer test-provider-key')
        self.assertEqual(kwargs['json'], {'from': SETTINGS['DEFAULT_FROM_EMAIL'], 'to': ['user@example.com'], 'subject': 'Reset password', 'text': 'Private code: 12345678'})
        first_key = kwargs['headers']['Idempotency-Key']
        ResendEmailBackend().send_messages([self.message])
        self.assertEqual(post.call_args.kwargs['headers']['Idempotency-Key'], first_key)

    @patch('accounts.email_backend.requests.post')
    def test_html_and_recipient_options(self, post):
        post.return_value = Mock(status_code=200, json=Mock(return_value={'id': 'id'}))
        message = EmailMultiAlternatives('Subject', 'Plain', to=['user@example.com'], cc=['cc@example.com'], bcc=['bcc@example.com'], reply_to=['reply@example.com'])
        message.attach_alternative('<p>HTML</p>', 'text/html')
        self.assertEqual(ResendEmailBackend().send_messages([message]), 1)
        payload = post.call_args.kwargs['json']
        self.assertEqual(payload['html'], '<p>HTML</p>')
        self.assertEqual(payload['text'], 'Plain')
        self.assertEqual(payload['reply_to'], ['reply@example.com'])
        self.assertEqual(payload['cc'], ['cc@example.com'])
        self.assertEqual(payload['bcc'], ['bcc@example.com'])

    @override_settings(RESEND_API_KEY='')
    @patch('accounts.email_backend.requests.post')
    def test_missing_key_never_sends(self, post):
        with self.assertRaises(ImproperlyConfigured):
            ResendEmailBackend().send_messages([self.message])
        post.assert_not_called()

    @patch('accounts.email_backend.requests.post')
    def test_provider_rejection_redirect_and_malformed_success_not_counted(self, post):
        for response in (Mock(status_code=403, text='sensitive provider response'), Mock(status_code=307),
                         Mock(status_code=200, json=Mock(side_effect=ValueError('private body'))),
                         Mock(status_code=200, json=Mock(return_value={})),
                         Mock(status_code=200, json=Mock(return_value=[]))):
            post.return_value = response
            with self.assertRaises(EmailDeliveryError) as error:
                ResendEmailBackend().send_messages([self.message])
            self.assertNotIn('sensitive', str(error.exception))
            self.assertNotIn('12345678', str(error.exception))
            self.assertEqual(ResendEmailBackend(fail_silently=True).send_messages([self.message]), 0)

    @patch('accounts.email_backend.requests.post', side_effect=requests.Timeout('private request data'))
    def test_timeout_is_safe_and_no_automatic_retry(self, post):
        with self.assertRaises(EmailDeliveryError) as error:
            ResendEmailBackend().send_messages([self.message])
        self.assertNotIn('private request data', str(error.exception))
        self.assertIsNone(error.exception.__cause__)
        self.assertEqual(post.call_count, 1)

    @patch('accounts.email_backend.requests.post')
    def test_empty_messages_do_not_contact_provider(self, post):
        self.assertEqual(ResendEmailBackend().send_messages([]), 0)
        self.assertEqual(ResendEmailBackend().send_messages([EmailMessage('Empty', 'Body')]), 0)
        post.assert_not_called()


@override_settings(**SETTINGS)
class RecoveryHttpsIntegrationTests(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.user = get_user_model().objects.create_user(username='https-recovery', email='recovery@example.com', password='OldPassword!2026')
        self.client = APIClient()

    @patch('accounts.email_backend.requests.post')
    def test_real_recovery_flow_uses_https_and_code_is_single_use(self, post):
        post.return_value = Mock(status_code=200, json=Mock(return_value={'id': 'accepted'}))
        response = self.client.post('/api/auth/password-reset/request/', {'identifier': self.user.email}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {'message': PASSWORD_RESET_RESPONSE})
        payload = post.call_args.kwargs['json']
        code = re.search(r'\b\d{8}\b', payload['text']).group()
        challenge = PasswordResetChallenge.objects.get(user=self.user)
        self.assertNotEqual(challenge.code_digest, code)
        self.assertNotIn(code, str(response.data))
        values = {'identifier': self.user.email, 'code': code, 'new_password': 'NewPassword!2026', 'new_password_confirm': 'NewPassword!2026'}
        response = self.client.post('/api/auth/password-reset/confirm/', values, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewPassword!2026'))
        self.assertEqual(self.client.post('/api/auth/password-reset/confirm/', values, format='json').status_code, 400)

    @patch('accounts.email_backend.requests.post', side_effect=requests.Timeout())
    def test_delivery_failure_invalidates_challenge_without_account_disclosure(self, post):
        with self.assertLogs('accounts.services', level='ERROR') as logs:
            response = self.client.post('/api/auth/password-reset/request/', {'identifier': self.user.email}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {'message': PASSWORD_RESET_RESPONSE})
        self.assertIsNotNone(PasswordResetChallenge.objects.get().used_at)
        unknown = self.client.post('/api/auth/password-reset/request/', {'identifier': 'missing@example.com'}, format='json')
        self.assertEqual(unknown.data, response.data)
        self.assertEqual(post.call_count, 1)
        for entry in logs.output:
            self.assertNotIn('test-provider-key', entry)
            self.assertNotIn(self.user.email, entry)
