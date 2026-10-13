from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import RequestFactory, SimpleTestCase

from payments.models import PaymentAttempt


class PaymentAttemptAdminSecurityTests(SimpleTestCase):
    sensitive_fields = {
        "provider_request_payload",
        "provider_response_payload",
        "provider_callback_payload",
        "provider_query_payload",
    }

    def setUp(self):
        self.model_admin = admin.site._registry[PaymentAttempt]
        self.factory = RequestFactory()
        self.user_model = get_user_model()

    def make_request(self, is_superuser):
        request = self.factory.get(
            "/admin/payments/paymentattempt/"
        )
        request.user = self.user_model(
            is_staff=True,
            is_superuser=is_superuser,
        )
        return request

    def test_superuser_can_view_raw_payloads(self):
        request = self.make_request(True)

        fields = set(self.model_admin.get_fields(request))

        self.assertTrue(
            self.sensitive_fields.issubset(fields)
        )

    def test_non_superuser_cannot_view_raw_payloads(self):
        request = self.make_request(False)

        fields = set(self.model_admin.get_fields(request))

        self.assertTrue(
            self.sensitive_fields.isdisjoint(fields)
        )

    def test_non_superuser_retains_summary_fields(self):
        request = self.make_request(False)

        fields = set(self.model_admin.get_fields(request))

        self.assertIn("payment", fields)
        self.assertIn("attempt_reference", fields)
        self.assertIn("status", fields)
        self.assertIn("requested_amount", fields)

    def test_superuser_cannot_change_attempt(self):
        request = self.make_request(True)

        self.assertFalse(
            self.model_admin.has_change_permission(request)
        )

    def test_staff_cannot_change_attempt(self):
        request = self.make_request(False)

        self.assertFalse(
            self.model_admin.has_change_permission(request)
        )

    def test_admin_cannot_add_or_delete_attempts(self):
        request = self.make_request(True)

        self.assertFalse(
            self.model_admin.has_add_permission(request)
        )
        self.assertFalse(
            self.model_admin.has_delete_permission(request)
        )


from django.contrib.auth.models import Permission
from django.test import TestCase


class PaymentAttemptFinanceStaffTests(TestCase):
    def setUp(self):
        self.model_admin = admin.site._registry[PaymentAttempt]
        self.user = get_user_model().objects.create_user(
            username="finance_security_staff",
            password="test-pass-123",
            is_staff=True,
        )

        permission = Permission.objects.get(
            content_type__app_label="payments",
            codename="view_paymentattempt",
        )
        self.user.user_permissions.add(permission)

        self.request = RequestFactory().get(
            "/admin/payments/paymentattempt/"
        )
        self.request.user = self.user

    def test_finance_staff_has_view_only_access(self):
        self.assertTrue(
            self.model_admin.has_view_permission(self.request)
        )
        self.assertFalse(
            self.model_admin.has_change_permission(self.request)
        )
        self.assertFalse(
            self.model_admin.has_add_permission(self.request)
        )
        self.assertFalse(
            self.model_admin.has_delete_permission(self.request)
        )

    def test_finance_staff_cannot_see_raw_payload_fields(self):
        fields = set(
            self.model_admin.get_fields(self.request)
        )

        sensitive_fields = {
            "provider_request_payload",
            "provider_response_payload",
            "provider_callback_payload",
            "provider_query_payload",
        }

        self.assertTrue(sensitive_fields.isdisjoint(fields))
        self.assertIn("payment", fields)
        self.assertIn("attempt_reference", fields)
        self.assertIn("status", fields)
