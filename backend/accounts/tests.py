from rest_framework import status
from rest_framework.test import APITestCase

from .models import User


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
