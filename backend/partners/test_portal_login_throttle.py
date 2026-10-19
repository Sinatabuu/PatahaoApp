from unittest.mock import patch
from django.contrib.auth.models import Permission
from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient
from accounts.models import User

URL='/api/staff/onboarding/login/'
ORIGIN={'HTTP_ORIGIN':'https://patahao.app'}


class StaffLoginThrottleTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user=User.objects.create_user(username='Sammy',email='sammy@example.test',password='TestPassword123!',is_staff=True)
        user.user_permissions.add(Permission.objects.get(codename='view_partnerapplication',content_type__app_label='partners'))

    def setUp(self):
        cache.clear();self.client=APIClient()

    def login(self,username='Sammy',password='TestPassword123!'):
        return self.client.post(URL,{'username':username,'password':password},format='json',**ORIGIN)

    def test_preflights_and_successful_signins_do_not_exhaust_failure_limit(self):
        for _ in range(20):
            self.assertEqual(self.client.options(URL,**ORIGIN).status_code,204)
            self.assertEqual(self.login().status_code,200)

    def test_failed_logins_block_with_readable_cors_but_preflight_still_works(self):
        for _ in range(10):self.assertIn(self.login(password='wrong').status_code,(401,403))
        response=self.login();self.assertEqual(response.status_code,429)
        self.assertEqual(response['Access-Control-Allow-Origin'],'https://patahao.app')
        self.assertIn('Retry-After',response)
        self.assertEqual(self.client.options(URL,**ORIGIN).status_code,204)

    def test_failures_for_one_account_do_not_lock_other_identifiers(self):
        for _ in range(10):self.login(username='other',password='wrong')
        self.assertEqual(self.login().status_code,200)

    def test_failure_window_expires_after_fifteen_minutes(self):
        clock=[1000.0]
        with patch('partners.staff_portal.PortalFailedLoginThrottle.timer',new=staticmethod(lambda:clock[0])):
            for _ in range(10):self.login(password='wrong')
            self.assertEqual(self.login().status_code,429)
            clock[0]+=901
            self.assertEqual(self.login().status_code,200)

    def test_post_volume_cap_does_not_block_options(self):
        for i in range(60):self.login(username=f'unknown-{i}',password='wrong')
        response=self.login();self.assertEqual(response.status_code,429)
        self.assertEqual(response['Access-Control-Allow-Origin'],'https://patahao.app')
        self.assertEqual(self.client.options(URL,**ORIGIN).status_code,204)
