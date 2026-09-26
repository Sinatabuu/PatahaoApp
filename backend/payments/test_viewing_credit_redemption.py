from datetime import time, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from core.models import ActivityLog
from notifications.models import Notification
from partners.models import Partner
from properties.models import Property
from viewings.models import Viewing, ViewingEvent

from .models import Payment, ViewingCredit, ViewingCreditRedemption


class ViewingCreditRedemptionTests(APITestCase):
    def setUp(self):
        self.customer = User.objects.create_user(
            username="credit_customer",
            email="credit-customer@example.com",
            password="TestPassword123!",
            role=User.ROLE_CUSTOMER,
        )
        self.other_customer = User.objects.create_user(
            username="other_credit_customer",
            email="other-credit-customer@example.com",
            password="TestPassword123!",
            role=User.ROLE_CUSTOMER,
        )
        self.staff = User.objects.create_user(
            username="credit_staff",
            email="credit-staff@example.com",
            password="TestPassword123!",
            role=User.ROLE_ADMIN,
            is_staff=True,
        )
        self.partner_user = User.objects.create_user(
            username="credit_partner",
            email="credit-partner@example.com",
            password="TestPassword123!",
            role=User.ROLE_PARTNER,
        )
        self.partner = Partner.objects.create(
            user=self.partner_user,
            business_name="Credit Homes",
            display_name="Credit Homes",
            partner_type=Partner.PARTNER_TYPE_AGENT,
            verification_status=Partner.STATUS_APPROVED,
            is_active=True,
        )
        self.property = Property.objects.create(
            partner=self.partner,
            title="Credit Redemption Rental",
            property_type=Property.TYPE_APARTMENT,
            listing_type=Property.LISTING_RENT,
            price=Decimal("25000.00"),
            county="Nairobi",
            town="Roysambu",
            estate="Roysambu",
            address="Credit Test Road",
            bedrooms=1,
            bathrooms=1,
            description="Property used to test viewing-credit redemption.",
            status=Property.STATUS_DRAFT,
        )
        self.credit = self._issue_credit(
            customer=self.customer,
            amount=Decimal("2000.00"),
        )
        self._issue_credit(
            customer=self.other_customer,
            amount=Decimal("900.00"),
        )
        self.target_viewing = self._new_viewing(
            customer=self.customer,
            fee=Decimal("400.00"),
        )
        self.client.force_authenticate(user=self.customer)

    def _new_viewing(self, *, customer, fee):
        return Viewing.objects.create(
            customer=customer,
            property=self.property,
            assigned_partner=self.partner,
            requested_date=timezone.localdate() + timedelta(days=3),
            requested_time=time(10, 0),
            fee_amount=fee,
            status=Viewing.Status.PENDING_PAYMENT,
        )

    def _issue_credit(self, *, customer, amount):
        source_viewing = Viewing.objects.create(
            customer=customer,
            property=self.property,
            assigned_partner=self.partner,
            requested_date=timezone.localdate() + timedelta(days=2),
            requested_time=time(9, 0),
            fee_amount=amount,
            status=Viewing.Status.CREDIT_ISSUED,
        )
        source_payment = Payment.objects.create(
            viewing=source_viewing,
            payer=customer,
            amount=amount,
            currency="KES",
            payment_method=Payment.PaymentMethod.MPESA,
            status=Payment.Status.SUCCESSFUL,
            paid_at=timezone.now(),
            provider_receipt_number=(
                f"SOURCE-{customer.pk}-{source_viewing.pk}"
            ),
            receipt_number=f"PHR-SOURCE-{source_viewing.pk}",
        )
        return ViewingCredit.objects.create(
            customer=customer,
            source_payment=source_payment,
            source_viewing=source_viewing,
            amount=amount,
            remaining_amount=amount,
            currency="KES",
            issued_by=self.staff,
        )

    def test_credit_balance_only_contains_authenticated_customer_credit(self):
        response = self.client.get("/api/payments/credit-balance/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["available_amount"], "2000.00")
        self.assertEqual(len(response.data["credits"]), 1)
        self.assertEqual(
            response.data["credits"][0]["credit_reference"],
            self.credit.credit_reference,
        )

    def test_available_credit_is_not_used_without_customer_opt_in(self):
        response = self.client.post(
            "/api/payments/",
            {
                "viewing": self.target_viewing.pk,
                "phone_number": "0712345678",
                "provider": Payment.PaymentMethod.MPESA,
                "use_viewing_credit": False,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            response.data,
        )
        self.assertEqual(response.data["credit_applied_amount"], "0.00")
        self.assertEqual(response.data["cash_amount"], "400.00")
        self.assertEqual(
            response.data["provider"],
            Payment.PaymentMethod.MPESA,
        )

        self.credit.refresh_from_db()
        self.assertEqual(self.credit.remaining_amount, Decimal("2000.00"))
        self.assertFalse(
            ViewingCreditRedemption.objects.filter(
                payment__viewing=self.target_viewing,
            ).exists()
        )

    def test_kes_2000_credit_pays_kes_400_and_leaves_kes_1600(self):
        response = self.client.post(
            "/api/payments/",
            {
                "viewing": self.target_viewing.pk,
                "phone_number": "",
                "provider": Payment.PaymentMethod.MPESA,
                "use_viewing_credit": True,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            response.data,
        )
        self.assertEqual(response.data["status"], Payment.Status.SUCCESSFUL)
        self.assertEqual(response.data["amount"], "400.00")
        self.assertEqual(response.data["credit_applied_amount"], "400.00")
        self.assertEqual(response.data["cash_amount"], "0.00")
        self.assertEqual(
            response.data["provider"],
            Payment.PaymentMethod.VIEWING_CREDIT,
        )
        self.assertTrue(response.data["receipt_number"])
        self.assertEqual(len(response.data["credit_redemptions"]), 1)

        self.credit.refresh_from_db()
        self.target_viewing.refresh_from_db()
        payment = Payment.objects.get(viewing=self.target_viewing)
        redemption = ViewingCreditRedemption.objects.get(payment=payment)

        self.assertEqual(
            self.credit.remaining_amount,
            Decimal("1600.00"),
        )
        self.assertEqual(self.credit.status, ViewingCredit.Status.ACTIVE)
        self.assertEqual(redemption.amount, Decimal("400.00"))
        self.assertEqual(
            self.target_viewing.status,
            Viewing.Status.PAID_PENDING_PARTNER,
        )
        self.assertTrue(
            ViewingEvent.objects.filter(
                viewing=self.target_viewing,
                event_type=ViewingEvent.EventType.PAYMENT_RECEIVED,
                metadata__credit_applied_amount="400.00",
                metadata__cash_amount="0.00",
            ).exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                user=self.partner_user,
                title="New paid viewing request",
            ).exists()
        )
        self.assertTrue(
            ActivityLog.objects.filter(
                actor=self.customer,
                action="viewing_credit_redeemed",
                entity_type="Viewing",
                entity_id=str(self.target_viewing.pk),
            ).exists()
        )

        balance = self.client.get("/api/payments/credit-balance/")
        self.assertEqual(balance.data["available_amount"], "1600.00")

    def test_partial_credit_only_sends_the_difference_to_mpesa(self):
        self.credit.remaining_amount = Decimal("250.00")
        self.credit.save(update_fields=["remaining_amount", "updated_at"])

        response = self.client.post(
            "/api/payments/",
            {
                "viewing": self.target_viewing.pk,
                "phone_number": "0712345678",
                "provider": Payment.PaymentMethod.MPESA,
                "use_viewing_credit": True,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            response.data,
        )
        self.assertEqual(response.data["status"], Payment.Status.PENDING)
        self.assertEqual(response.data["amount"], "400.00")
        self.assertEqual(response.data["credit_applied_amount"], "250.00")
        self.assertEqual(response.data["cash_amount"], "150.00")

        payment = Payment.objects.get(viewing=self.target_viewing)
        self.credit.refresh_from_db()
        self.assertEqual(self.credit.remaining_amount, Decimal("0.00"))
        self.assertEqual(self.credit.status, ViewingCredit.Status.CONSUMED)

        with patch(
            "payments.views.MpesaClient.stk_push",
            return_value=(
                {"Amount": 150},
                {
                    "ResponseCode": "0",
                    "MerchantRequestID": "MERCHANT-CREDIT-TOPUP",
                    "CheckoutRequestID": "CHECKOUT-CREDIT-TOPUP",
                    "CustomerMessage": "Success",
                },
            ),
        ) as stk_push:
            initiated = self.client.post(
                f"/api/payments/{payment.pk}/initiate/",
                {},
                format="json",
            )

        self.assertEqual(initiated.status_code, status.HTTP_200_OK)
        self.assertEqual(
            stk_push.call_args.kwargs["amount"],
            Decimal("150.00"),
        )
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.PROCESSING)
        self.assertEqual(
            payment.attempts.get().requested_amount,
            Decimal("150.00"),
        )

    def test_retry_returns_the_same_credit_backed_payment(self):
        self.credit.remaining_amount = Decimal("250.00")
        self.credit.save(update_fields=["remaining_amount", "updated_at"])

        first_response = self.client.post(
            "/api/payments/",
            {
                "viewing": self.target_viewing.pk,
                "phone_number": "0712345678",
                "use_viewing_credit": True,
            },
            format="json",
        )
        retry_response = self.client.post(
            "/api/payments/",
            {
                "viewing": self.target_viewing.pk,
                "phone_number": "0799999999",
                "use_viewing_credit": False,
            },
            format="json",
        )

        self.assertEqual(first_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(retry_response.status_code, status.HTTP_200_OK)
        self.assertEqual(retry_response.data["id"], first_response.data["id"])
        self.assertEqual(
            retry_response.data["credit_applied_amount"],
            "250.00",
        )
        self.assertEqual(retry_response.data["cash_amount"], "150.00")
        self.assertEqual(Payment.objects.count(), 3)
        self.assertEqual(ViewingCreditRedemption.objects.count(), 1)

        self.credit.refresh_from_db()
        self.assertEqual(self.credit.remaining_amount, Decimal("0.00"))

    def test_credit_request_without_available_credit_is_rejected_safely(self):
        self.credit.status = ViewingCredit.Status.VOID
        self.credit.save(update_fields=["status", "updated_at"])

        response = self.client.post(
            "/api/payments/",
            {
                "viewing": self.target_viewing.pk,
                "use_viewing_credit": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("available viewing credit", response.data["detail"])
        self.assertFalse(
            Payment.objects.filter(viewing=self.target_viewing).exists()
        )
