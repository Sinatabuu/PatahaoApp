from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

from config.environment import validate_mpesa_configuration


class MpesaProductionConfigurationTests(SimpleTestCase):
    def setUp(self):
        self.token = "a" * 40
        self.url = (
            "https://example.com/api/payments/mpesa/callback/"
        )
        self.config = {
            "application_environment": "production",
            "development_handoff_enabled": False,
            "mpesa_environment": "production",
            "live_payments_enabled": True,
            "consumer_key": "test-key",
            "consumer_secret": "test-secret",
            "shortcode": "123456",
            "passkey": "test-passkey",
            "transaction_type": "CustomerPayBillOnline",
        }

    def validate(self, token, url):
        return validate_mpesa_configuration(
            **self.config,
            callback_token=token,
            callback_url=url,
        )

    def test_missing_callback_token_is_rejected(self):
        with self.assertRaises(ImproperlyConfigured):
            self.validate("", self.url)

    def test_short_callback_token_is_rejected(self):
        with self.assertRaises(ImproperlyConfigured):
            self.validate(
                "short",
                self.url + "?token=short",
            )

    def test_mismatched_callback_token_is_rejected(self):
        with self.assertRaises(ImproperlyConfigured):
            self.validate(
                self.token,
                self.url + "?token=wrong",
            )

    def test_matching_callback_token_is_accepted(self):
        self.validate(
            self.token,
            self.url + "?token=" + self.token,
        )


class MpesaAuditRedactionTests(SimpleTestCase):
    def test_sensitive_request_fields_are_redacted(self):
        from payments.services.mpesa import MpesaClient

        secret = "test-secret-never-store"

        original = {
            "Password": "test-password",
            "SecurityCredential": "test-credential",
            "Authorization": "Bearer test-token",
            "CallBackURL": (
                "https://example.com/api/payments/mpesa/callback/"
                "?token=" + secret
            ),
            "Amount": 400,
            "BusinessShortCode": "174379",
        }

        safe = MpesaClient._safe_audit_payload(original)

        for field in (
            "Password",
            "SecurityCredential",
            "Authorization",
            "CallBackURL",
        ):
            with self.subTest(field=field):
                self.assertEqual(safe[field], "[REDACTED]")

        self.assertNotIn(secret, str(safe))
        self.assertEqual(safe["Amount"], 400)
        self.assertEqual(safe["BusinessShortCode"], "174379")

    def test_redaction_does_not_modify_original_payload(self):
        from payments.services.mpesa import MpesaClient

        original = {
            "Password": "original-password",
            "CallBackURL": "https://example.com/?token=secret",
            "Amount": 400,
        }

        safe = MpesaClient._safe_audit_payload(original)

        self.assertEqual(
            original["Password"],
            "original-password",
        )
        self.assertEqual(
            original["CallBackURL"],
            "https://example.com/?token=secret",
        )
        self.assertEqual(safe["Password"], "[REDACTED]")
        self.assertEqual(safe["CallBackURL"], "[REDACTED]")
