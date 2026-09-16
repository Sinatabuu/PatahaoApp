from datetime import date, time
from decimal import Decimal
from unittest.mock import patch

from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from notifications.models import Notification
from partners.models import Partner
from properties.models import Property
from viewings.models import Viewing, ViewingEvent

from .models import Payment, PaymentAttempt
from .services import MpesaAPIError, MpesaClient


class MpesaHardeningTests(APITestCase):
    callback_url = "/api/payments/mpesa/callback/"

    def setUp(self):
        self.partner_user = User.objects.create_user(
            username="mpesa_hardening_partner",
            email="mpesa-hardening-partner@example.com",
            password="test-pass-123",
            role=User.ROLE_PARTNER,
        )
        self.partner = Partner.objects.create(
            user=self.partner_user,
            business_name="M-Pesa Hardening Homes",
            display_name="M-Pesa Hardening Homes",
            verification_status=Partner.STATUS_APPROVED,
            is_active=True,
            accepts_viewing_requests=True,
        )
        self.customer = User.objects.create_user(
            username="mpesa_hardening_customer",
            email="mpesa-hardening-customer@example.com",
            password="test-pass-123",
            role=User.ROLE_CUSTOMER,
        )
        self.staff = User.objects.create_user(
            username="mpesa_hardening_staff",
            email="mpesa-hardening-staff@example.com",
            password="test-pass-123",
            role=User.ROLE_ADMIN,
            is_staff=True,
        )
        self.property_obj = Property.objects.create(
            partner=self.partner,
            title="M-Pesa Hardening Rental",
            property_type=Property.TYPE_APARTMENT,
            listing_type=Property.LISTING_RENT,
            price=Decimal("35000.00"),
            county="Nairobi",
            town="Roysambu",
            estate="Garden Estate",
            address="Hardening Road",
            latitude=Decimal("-1.218000"),
            longitude=Decimal("36.886000"),
            bedrooms=2,
            bathrooms=1,
            description="Payment hardening test property.",
            status=Property.STATUS_DRAFT,
        )

        self.payment, self.attempt = self._create_payment_attempt(
            checkout_request_id="CHECKOUT-HARDENING-001",
            merchant_request_id="MERCHANT-HARDENING-001",
        )

    def _create_payment_attempt(
        self,
        *,
        checkout_request_id,
        merchant_request_id,
    ):
        viewing = Viewing.objects.create(
            customer=self.customer,
            property=self.property_obj,
            assigned_partner=self.partner,
            requested_date=date(2026, 9, 20),
            requested_time=time(10, 30),
            fee_amount=Decimal("400.00"),
            status=Viewing.Status.PAYMENT_PROCESSING,
        )
        payment = Payment.objects.create(
            viewing=viewing,
            payer=self.customer,
            amount=Decimal("400.00"),
            phone_number="254712345678",
            payment_method=Payment.PaymentMethod.MPESA,
            status=Payment.Status.PROCESSING,
            merchant_request_id=merchant_request_id,
            checkout_request_id=checkout_request_id,
        )
        viewing.payment_reference = payment.payment_reference
        viewing.save(
            update_fields=[
                "payment_reference",
                "updated_at",
            ]
        )
        attempt = PaymentAttempt.objects.create(
            payment=payment,
            status=PaymentAttempt.Status.PROCESSING,
            merchant_request_id=merchant_request_id,
            checkout_request_id=checkout_request_id,
            requested_amount=payment.amount,
            phone_number=payment.phone_number,
            provider_response_code="0",
            provider_response_description="Accepted",
        )

        return payment, attempt

    def _success_callback(
        self,
        *,
        checkout_request_id=None,
        merchant_request_id=None,
        amount="400.00",
        receipt="MPESAHARD001",
        phone=254712345678,
        transaction_date=20260916120000,
        result_code=0,
        result_description="The service request is processed successfully.",
    ):
        return {
            "Body": {
                "stkCallback": {
                    "MerchantRequestID": (
                        merchant_request_id
                        or self.attempt.merchant_request_id
                    ),
                    "CheckoutRequestID": (
                        checkout_request_id
                        or self.attempt.checkout_request_id
                    ),
                    "ResultCode": result_code,
                    "ResultDesc": result_description,
                    "CallbackMetadata": {
                        "Item": [
                            {
                                "Name": "Amount",
                                "Value": amount,
                            },
                            {
                                "Name": "MpesaReceiptNumber",
                                "Value": receipt,
                            },
                            {
                                "Name": "TransactionDate",
                                "Value": transaction_date,
                            },
                            {
                                "Name": "PhoneNumber",
                                "Value": phone,
                            },
                        ]
                    },
                }
            }
        }

    def test_verified_callback_completes_payment_and_attempt(self):
        response = self.client.post(
            self.callback_url,
            self._success_callback(),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.payment.refresh_from_db()
        self.attempt.refresh_from_db()

        self.assertEqual(
            self.payment.status,
            Payment.Status.SUCCESSFUL,
        )
        self.assertEqual(
            self.payment.provider_receipt_number,
            "MPESAHARD001",
        )
        self.assertEqual(
            self.attempt.status,
            PaymentAttempt.Status.SUCCESSFUL,
        )
        self.assertEqual(
            self.attempt.callback_amount,
            Decimal("400.00"),
        )
        self.assertEqual(
            self.payment.viewing.status,
            Viewing.Status.PAID_PENDING_PARTNER,
        )

    def test_duplicate_callback_is_idempotent(self):
        payload = self._success_callback()

        first = self.client.post(
            self.callback_url,
            payload,
            format="json",
        )
        second = self.client.post(
            self.callback_url,
            payload,
            format="json",
        )

        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(
            ViewingEvent.objects.filter(
                viewing=self.payment.viewing,
                event_type=ViewingEvent.EventType.PAYMENT_RECEIVED,
            ).count(),
            1,
        )
        self.assertEqual(
            Notification.objects.filter(
                user=self.partner_user,
                title="New paid viewing request",
            ).count(),
            1,
        )

    def test_fractional_amount_mismatch_requires_review(self):
        response = self.client.post(
            self.callback_url,
            self._success_callback(amount="400.99"),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.payment.refresh_from_db()
        self.attempt.refresh_from_db()

        self.assertEqual(
            self.payment.status,
            Payment.Status.PROCESSING,
        )
        self.assertEqual(
            self.attempt.status,
            PaymentAttempt.Status.REVIEW_REQUIRED,
        )
        self.assertIn(
            "exactly match",
            self.attempt.failure_reason,
        )

    def test_subcent_callback_amount_is_not_rounded_into_success(self):
        response = self.client.post(
            self.callback_url,
            self._success_callback(amount="400.001"),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.payment.refresh_from_db()
        self.attempt.refresh_from_db()

        self.assertEqual(
            self.payment.status,
            Payment.Status.PROCESSING,
        )
        self.assertEqual(
            self.attempt.status,
            PaymentAttempt.Status.REVIEW_REQUIRED,
        )

    def test_phone_number_mismatch_requires_review(self):
        response = self.client.post(
            self.callback_url,
            self._success_callback(phone=254700000000),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.payment.refresh_from_db()
        self.attempt.refresh_from_db()

        self.assertEqual(
            self.payment.status,
            Payment.Status.PROCESSING,
        )
        self.assertEqual(
            self.attempt.status,
            PaymentAttempt.Status.REVIEW_REQUIRED,
        )

    def test_malformed_callback_metadata_requires_review(self):
        payload = self._success_callback()
        payload["Body"]["stkCallback"]["CallbackMetadata"] = []

        response = self.client.post(
            self.callback_url,
            payload,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.payment.refresh_from_db()
        self.attempt.refresh_from_db()

        self.assertEqual(
            self.payment.status,
            Payment.Status.PROCESSING,
        )
        self.assertEqual(
            self.attempt.status,
            PaymentAttempt.Status.REVIEW_REQUIRED,
        )

    def test_malformed_result_code_requires_review_without_server_error(self):
        response = self.client.post(
            self.callback_url,
            self._success_callback(result_code="invalid"),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.attempt.refresh_from_db()
        self.assertEqual(
            self.attempt.status,
            PaymentAttempt.Status.REVIEW_REQUIRED,
        )

    def test_merchant_request_mismatch_requires_review(self):
        response = self.client.post(
            self.callback_url,
            self._success_callback(
                merchant_request_id="WRONG-MERCHANT",
            ),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.attempt.refresh_from_db()
        self.assertEqual(
            self.attempt.status,
            PaymentAttempt.Status.REVIEW_REQUIRED,
        )

    def test_duplicate_provider_receipt_requires_review(self):
        self.attempt.status = PaymentAttempt.Status.SUCCESSFUL
        self.attempt.provider_receipt_number = "DUPLICATE001"
        self.attempt.completed_at = self.attempt.initiated_at
        self.attempt.save(
            update_fields=[
                "status",
                "provider_receipt_number",
                "completed_at",
                "updated_at",
            ]
        )

        other_payment, other_attempt = self._create_payment_attempt(
            checkout_request_id="CHECKOUT-HARDENING-002",
            merchant_request_id="MERCHANT-HARDENING-002",
        )

        response = self.client.post(
            self.callback_url,
            self._success_callback(
                checkout_request_id=other_attempt.checkout_request_id,
                merchant_request_id=other_attempt.merchant_request_id,
                receipt="duplicate001",
            ),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        other_payment.refresh_from_db()
        other_attempt.refresh_from_db()

        self.assertEqual(
            other_payment.status,
            Payment.Status.PROCESSING,
        )
        self.assertEqual(
            other_attempt.status,
            PaymentAttempt.Status.REVIEW_REQUIRED,
        )

    def test_delayed_valid_callback_for_earlier_attempt_is_preserved(self):
        old_attempt = self.attempt
        new_attempt = PaymentAttempt.objects.create(
            payment=self.payment,
            status=PaymentAttempt.Status.PROCESSING,
            merchant_request_id="MERCHANT-HARDENING-NEW",
            checkout_request_id="CHECKOUT-HARDENING-NEW",
            requested_amount=self.payment.amount,
            phone_number=self.payment.phone_number,
        )
        self.payment.merchant_request_id = new_attempt.merchant_request_id
        self.payment.checkout_request_id = new_attempt.checkout_request_id
        self.payment.save(
            update_fields=[
                "merchant_request_id",
                "checkout_request_id",
                "updated_at",
            ]
        )

        response = self.client.post(
            self.callback_url,
            self._success_callback(
                checkout_request_id=old_attempt.checkout_request_id,
                merchant_request_id=old_attempt.merchant_request_id,
                receipt="MPESAOLD001",
            ),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.payment.refresh_from_db()
        old_attempt.refresh_from_db()
        new_attempt.refresh_from_db()

        self.assertEqual(
            self.payment.status,
            Payment.Status.SUCCESSFUL,
        )
        self.assertEqual(
            self.payment.checkout_request_id,
            old_attempt.checkout_request_id,
        )
        self.assertEqual(
            old_attempt.status,
            PaymentAttempt.Status.SUCCESSFUL,
        )
        self.assertEqual(
            new_attempt.status,
            PaymentAttempt.Status.PROCESSING,
        )

    def test_staff_reconciliation_never_invents_successful_receipt(self):
        self.client.force_authenticate(user=self.staff)

        with patch(
            "payments.views.MpesaClient.query_stk_push",
            return_value=(
                {
                    "CheckoutRequestID": (
                        self.attempt.checkout_request_id
                    ),
                    "Password": "[REDACTED]",
                },
                {
                    "ResponseCode": "0",
                    "ResultCode": "0",
                    "ResultDesc": "The service request succeeded.",
                },
            ),
        ):
            response = self.client.post(
                f"/api/payments/{self.payment.id}/reconcile/",
                {},
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.payment.refresh_from_db()
        self.attempt.refresh_from_db()

        self.assertEqual(
            self.payment.status,
            Payment.Status.PROCESSING,
        )
        self.assertFalse(self.payment.provider_receipt_number)
        self.assertEqual(
            self.attempt.status,
            PaymentAttempt.Status.REVIEW_REQUIRED,
        )

    def test_reconciliation_cannot_downgrade_verified_callback(self):
        callback_response = self.client.post(
            self.callback_url,
            self._success_callback(),
            format="json",
        )
        self.assertEqual(
            callback_response.status_code,
            status.HTTP_200_OK,
        )

        self.client.force_authenticate(user=self.staff)

        with patch(
            "payments.views.MpesaClient.query_stk_push",
            return_value=(
                {
                    "CheckoutRequestID": (
                        self.attempt.checkout_request_id
                    ),
                    "Password": "[REDACTED]",
                },
                {
                    "ResponseCode": "0",
                    "ResultCode": "1032",
                    "ResultDesc": "Request cancelled by user.",
                },
            ),
        ):
            response = self.client.post(
                f"/api/payments/{self.payment.id}/reconcile/",
                {},
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.payment.refresh_from_db()
        self.attempt.refresh_from_db()

        self.assertEqual(
            self.payment.status,
            Payment.Status.SUCCESSFUL,
        )
        self.assertEqual(
            self.attempt.status,
            PaymentAttempt.Status.SUCCESSFUL,
        )

    def test_non_staff_cannot_reconcile_payment(self):
        self.client.force_authenticate(user=self.customer)

        response = self.client.post(
            f"/api/payments/{self.payment.id}/reconcile/",
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    @override_settings(
        IS_PRODUCTION=True,
        MPESA_LIVE_PAYMENTS_ENABLED=False,
    )
    def test_production_initiation_is_blocked_until_live_setup(self):
        self.client.force_authenticate(user=self.customer)

        response = self.client.post(
            f"/api/payments/{self.payment.id}/initiate/",
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    def test_audit_request_payload_redacts_daraja_password(self):
        client = MpesaClient()

        with patch.object(
            client,
            "initiate_stk_push",
            return_value={
                "ResponseCode": "0",
                "MerchantRequestID": "MERCHANT-REDACT",
                "CheckoutRequestID": "CHECKOUT-REDACT",
                "_request_payload": {
                    "BusinessShortCode": "174379",
                    "Password": "reversible-secret-value",
                    "PhoneNumber": "254712345678",
                },
            },
        ):
            request_payload, _response = client.stk_push(
                phone_number="254712345678",
                amount=Decimal("400.00"),
                account_reference="PH-TEST",
                description="Viewing fee",
            )

        self.assertEqual(
            request_payload["Password"],
            "[REDACTED]",
        )
        self.assertNotIn(
            "reversible-secret-value",
            str(request_payload),
        )

    def test_fractional_stk_amount_is_rejected_before_request(self):
        client = MpesaClient()

        with patch.object(client, "_validate_configuration"):
            with self.assertRaisesRegex(
                MpesaAPIError,
                "positive whole number",
            ):
                client.initiate_stk_push(
                    phone_number="254712345678",
                    amount=Decimal("400.50"),
                    account_reference="PH-TEST",
                    transaction_description="Viewing fee",
                )
