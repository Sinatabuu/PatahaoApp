import re
from datetime import timedelta

from django.core import mail
from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from .models import PasswordResetChallenge, User
from .services import PASSWORD_RESET_RESPONSE


class CustomerRegistrationTests(APITestCase):
    endpoint = "/api/auth/register/"

    def registration_data(self, **overrides):
        data = {
            "username": "new_customer",
            "email": "new-customer@example.com",
            "phone_number": "0712345678",
            "full_name": "New Customer",
            "password": "SecurePataHao!2026",
            "password_confirm": "SecurePataHao!2026",
        }
        data.update(overrides)
        return data

    def test_anonymous_user_can_create_customer_account(self):
        response = self.client.post(
            self.endpoint,
            self.registration_data(role=User.ROLE_ADMIN),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            response.data,
        )

        user = User.objects.get(username="new_customer")
        self.assertEqual(user.role, User.ROLE_CUSTOMER)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.check_password("SecurePataHao!2026"))
        self.assertNotIn("password", response.data["user"])

    def test_registration_rejects_password_mismatch(self):
        response = self.client.post(
            self.endpoint,
            self.registration_data(
                password_confirm="DifferentPassword!2026",
            ),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn("password_confirm", response.data)
        self.assertFalse(
            User.objects.filter(username="new_customer").exists()
        )

    def test_registration_applies_django_password_validation(self):
        response = self.client.post(
            self.endpoint,
            self.registration_data(
                password="12345678",
                password_confirm="12345678",
            ),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn("password", response.data)
        self.assertFalse(
            User.objects.filter(username="new_customer").exists()
        )

    def test_registration_rejects_case_insensitive_duplicates(self):
        User.objects.create_user(
            username="ExistingCustomer",
            email="existing@example.com",
            password="ExistingPassword!2026",
            role=User.ROLE_CUSTOMER,
        )

        username_response = self.client.post(
            self.endpoint,
            self.registration_data(username="existingcustomer"),
            format="json",
        )
        email_response = self.client.post(
            self.endpoint,
            self.registration_data(
                username="another_customer",
                email="EXISTING@example.com",
            ),
            format="json",
        )

        self.assertEqual(
            username_response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn("username", username_response.data)
        self.assertEqual(
            email_response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn("email", email_response.data)

    def test_registration_requires_full_name(self):
        response = self.client.post(
            self.endpoint,
            self.registration_data(full_name="  "),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn("full_name", response.data)


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="Pata HAO <no-reply@test.patahao>",
)
class PasswordRecoveryTests(APITestCase):
    request_endpoint = "/api/auth/password-reset/request/"
    confirm_endpoint = "/api/auth/password-reset/confirm/"

    def setUp(self):
        self.user = User.objects.create_user(
            username="recovery_partner",
            email="partner@example.com",
            phone_number="0711223344",
            full_name="Recovery Partner",
            password="OriginalSecure!2026",
            role=User.ROLE_PARTNER,
        )

    def request_code(self, identifier="partner@example.com"):
        response = self.client.post(
            self.request_endpoint,
            {"identifier": identifier},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        match = re.search(r"\b(\d{8})\b", mail.outbox[-1].body)
        self.assertIsNotNone(match)
        return response, match.group(1)

    def test_request_uses_generic_response_and_stores_only_code_digest(self):
        response, code = self.request_code()
        challenge = PasswordResetChallenge.objects.get(user=self.user)

        self.assertEqual(response.data, {"message": PASSWORD_RESET_RESPONSE})
        self.assertNotEqual(challenge.code_digest, code)
        self.assertNotIn(code, challenge.code_digest)
        self.assertEqual(challenge.request_ip, "127.0.0.1")

        mail.outbox.clear()
        missing_response = self.client.post(
            self.request_endpoint,
            {"identifier": "missing@example.com"},
            format="json",
        )

        self.assertEqual(missing_response.status_code, status.HTTP_200_OK)
        self.assertEqual(missing_response.data, response.data)
        self.assertEqual(len(mail.outbox), 0)

    def test_reset_changes_password_verifies_email_and_revokes_old_token(self):
        login_response = self.client.post(
            "/api/auth/login/",
            {
                "username": self.user.username,
                "password": "OriginalSecure!2026",
            },
            format="json",
        )
        old_access_token = login_response.data["access"]
        old_refresh_token = login_response.data["refresh"]
        _, code = self.request_code(identifier=self.user.username)

        response = self.client.post(
            self.confirm_endpoint,
            {
                "identifier": self.user.username,
                "code": code,
                "new_password": "AnotherSecure!2026",
                "new_password_confirm": "AnotherSecure!2026",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("AnotherSecure!2026"))
        self.assertTrue(self.user.is_email_verified)
        self.assertIsNotNone(
            PasswordResetChallenge.objects.get(user=self.user).used_at
        )

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {old_access_token}")
        revoked_response = self.client.get("/api/auth/me/")
        self.assertEqual(revoked_response.status_code, status.HTTP_401_UNAUTHORIZED)

        self.client.credentials()
        revoked_refresh_response = self.client.post(
            "/api/auth/refresh/",
            {"refresh": old_refresh_token},
            format="json",
        )
        self.assertEqual(
            revoked_refresh_response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

        repeat_response = self.client.post(
            self.confirm_endpoint,
            {
                "identifier": self.user.email,
                "code": code,
                "new_password": "ThirdSecurePassword!2026",
                "new_password_confirm": "ThirdSecurePassword!2026",
            },
            format="json",
        )
        self.assertEqual(repeat_response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_wrong_code_is_locked_after_five_attempts(self):
        _, code = self.request_code()
        wrong_code = "00000000" if code != "00000000" else "11111111"

        for _ in range(5):
            response = self.client.post(
                self.confirm_endpoint,
                {
                    "identifier": self.user.email,
                    "code": wrong_code,
                    "new_password": "AnotherSecure!2026",
                    "new_password_confirm": "AnotherSecure!2026",
                },
                format="json",
            )
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        challenge = PasswordResetChallenge.objects.get(user=self.user)
        self.assertEqual(challenge.failed_attempts, 5)
        self.assertIsNotNone(challenge.used_at)

        correct_response = self.client.post(
            self.confirm_endpoint,
            {
                "identifier": self.user.email,
                "code": code,
                "new_password": "AnotherSecure!2026",
                "new_password_confirm": "AnotherSecure!2026",
            },
            format="json",
        )
        self.assertEqual(correct_response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_expired_code_is_rejected(self):
        _, code = self.request_code()
        PasswordResetChallenge.objects.filter(user=self.user).update(
            expires_at=timezone.now() - timedelta(seconds=1)
        )

        response = self.client.post(
            self.confirm_endpoint,
            {
                "identifier": self.user.email,
                "code": code,
                "new_password": "AnotherSecure!2026",
                "new_password_confirm": "AnotherSecure!2026",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("code", response.data)

    def test_login_accepts_email_or_phone_as_account_identifier(self):
        for identifier in (self.user.email.upper(), self.user.phone_number):
            response = self.client.post(
                "/api/auth/login/",
                {
                    "username": identifier,
                    "password": "OriginalSecure!2026",
                },
                format="json",
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
            self.assertIn("access", response.data)
            self.assertIn("refresh", response.data)
