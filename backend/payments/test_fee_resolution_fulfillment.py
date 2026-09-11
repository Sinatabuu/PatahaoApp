from datetime import date, time
from decimal import Decimal

from django.urls import reverse
from django.utils import timezone

from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from core.models import ActivityLog
from governance.models import PartnerTier
from notifications.models import Notification
from partners.models import Partner
from properties.models import Property
from viewings.models import Viewing, ViewingEvent

from .models import Payment, ViewingCredit


class ViewingFeeResolutionFulfillmentTests(APITestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username="fee_resolution_staff",
            email="fee-resolution-staff@example.com",
            password="TestPassword123!",
            role=User.ROLE_ADMIN,
            is_staff=True,
        )
        self.customer = User.objects.create_user(
            username="fee_resolution_customer",
            email="fee-resolution-customer@example.com",
            password="TestPassword123!",
            role=User.ROLE_CUSTOMER,
        )
        self.partner_user = User.objects.create_user(
            username="fee_resolution_partner",
            email="fee-resolution-partner@example.com",
            password="TestPassword123!",
            role=User.ROLE_PARTNER,
        )
        self.partner = Partner.objects.create(
            user=self.partner_user,
            business_name="Resolution Homes",
            display_name="Resolution Homes",
            partner_type=Partner.PARTNER_TYPE_AGENT,
            verification_status=Partner.STATUS_APPROVED,
            is_active=True,
        )
        PartnerTier.objects.create(
            code="bronze",
            name="Bronze",
            rank=1,
            property_limit=20,
            minimum_completed_deals=0,
            minimum_trust_score=Decimal("0.00"),
            active=True,
        )
        self.property = Property.objects.create(
            partner=self.partner,
            title="Fee Resolution Home",
            property_type=Property.TYPE_APARTMENT,
            listing_type=Property.LISTING_RENT,
            price=Decimal("30000.00"),
            county="Nairobi",
            town="Roysambu",
            estate="Roysambu",
            address="Resolution Test Address",
            bedrooms=2,
            bathrooms=1,
            description="Property used to test staff fee fulfillment.",
            status=Property.STATUS_DRAFT,
        )
        self.viewing, self.payment = self._create_resolution_request(
            choice=Viewing.FeeResolutionChoice.REFUND,
        )

    def _create_resolution_request(self, *, choice):
        viewing = Viewing.objects.create(
            customer=self.customer,
            property=self.property,
            assigned_partner=self.partner,
            requested_date=date(2027, 3, 10),
            requested_time=time(10, 0),
            status=Viewing.Status.SCHEDULING_FAILED,
            reschedule_decline_count=2,
            fee_resolution_choice=choice,
            fee_resolution_requested_at=timezone.now(),
        )
        payment = Payment.objects.create(
            viewing=viewing,
            payer=self.customer,
            amount=Decimal("400.00"),
            currency="KES",
            purpose="viewing_fee",
            payment_method=Payment.PaymentMethod.MPESA,
            status=Payment.Status.SUCCESSFUL,
            paid_at=timezone.now(),
            provider_receipt_number=(
                f"PAID-{viewing.pk}"
            ),
            receipt_number=f"PHR-RESOLUTION-{viewing.pk}",
        )
        viewing.payment_reference = payment.payment_reference
        viewing.save(
            update_fields=[
                "payment_reference",
                "updated_at",
            ]
        )

        return viewing, payment

    def _process(self, viewing, *, data=None, user=None):
        self.client.force_authenticate(user=user or self.staff)

        return self.client.post(
            reverse(
                "admin-viewing-process-fee-resolution",
                kwargs={"viewing_id": viewing.pk},
            ),
            data or {},
            format="json",
        )

    def test_non_staff_cannot_process_a_fee_resolution(self):
        response = self._process(
            self.viewing,
            data={"provider_reference": "REFUND-UNAUTHORIZED"},
            user=self.customer,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Status.SUCCESSFUL)

    def test_refund_requires_provider_evidence(self):
        response = self._process(self.viewing)

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn("provider_reference", response.data)

        self.viewing.refresh_from_db()
        self.payment.refresh_from_db()
        self.assertEqual(
            self.viewing.status,
            Viewing.Status.SCHEDULING_FAILED,
        )
        self.assertEqual(self.payment.status, Payment.Status.SUCCESSFUL)
        self.assertIsNone(self.viewing.fee_resolution_processed_at)

    def test_staff_can_confirm_a_refund_with_provider_evidence(self):
        response = self._process(
            self.viewing,
            data={
                "provider_reference": "MPESA-REFUND-0001",
                "notes": "Confirmed in the provider portal.",
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            response.data,
        )
        self.assertFalse(response.data["already_processed"])
        self.assertEqual(
            response.data["viewing"]["status"],
            Viewing.Status.REFUNDED,
        )
        self.assertEqual(
            response.data["payment"]["status"],
            Payment.Status.REFUNDED,
        )
        self.assertIsNone(response.data["credit"])

        self.viewing.refresh_from_db()
        self.payment.refresh_from_db()
        self.assertEqual(self.viewing.status, Viewing.Status.REFUNDED)
        self.assertEqual(self.payment.status, Payment.Status.REFUNDED)
        self.assertEqual(
            self.payment.refund_reference,
            "MPESA-REFUND-0001",
        )
        self.assertEqual(self.payment.refunded_by, self.staff)
        self.assertIsNotNone(self.payment.refunded_at)
        self.assertEqual(
            self.viewing.fee_resolution_reference,
            "MPESA-REFUND-0001",
        )
        self.assertEqual(
            self.viewing.fee_resolution_processed_by,
            self.staff,
        )
        self.assertTrue(
            ViewingEvent.objects.filter(
                viewing=self.viewing,
                event_type=ViewingEvent.EventType.REFUND_ISSUED,
                actor=self.staff,
                metadata__resolution_reference="MPESA-REFUND-0001",
            ).exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                user=self.customer,
                title="Viewing fee refunded",
            ).exists()
        )
        self.assertTrue(
            ActivityLog.objects.filter(
                actor=self.staff,
                action="viewing_refund_processed",
                entity_id=str(self.viewing.pk),
            ).exists()
        )

    def test_customer_can_still_open_the_receipt_after_refund(self):
        processed = self._process(
            self.viewing,
            data={"provider_reference": "MPESA-REFUND-RECEIPT"},
        )
        self.assertEqual(processed.status_code, status.HTTP_200_OK)

        self.client.force_authenticate(user=self.customer)
        response = self.client.get(
            reverse(
                "payment-viewing-receipt",
                kwargs={"viewing_id": self.viewing.pk},
            )
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], Payment.Status.REFUNDED)
        self.assertEqual(
            response.data["refund_reference"],
            "MPESA-REFUND-RECEIPT",
        )

    def test_refund_processing_is_idempotent(self):
        first = self._process(
            self.viewing,
            data={"provider_reference": "MPESA-REFUND-0002"},
        )
        second = self._process(self.viewing)

        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertTrue(second.data["already_processed"])
        self.assertEqual(
            ViewingEvent.objects.filter(
                viewing=self.viewing,
                event_type=ViewingEvent.EventType.REFUND_ISSUED,
            ).count(),
            1,
        )
        self.assertEqual(
            Notification.objects.filter(
                user=self.customer,
                title="Viewing fee refunded",
            ).count(),
            1,
        )

    def test_processed_refund_rejects_a_different_retry_reference(self):
        first = self._process(
            self.viewing,
            data={"provider_reference": "MPESA-REFUND-ORIGINAL"},
        )
        second = self._process(
            self.viewing,
            data={"provider_reference": "MPESA-REFUND-DIFFERENT"},
        )

        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertEqual(second.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("provider_reference", second.data)
        self.payment.refresh_from_db()
        self.assertEqual(
            self.payment.refund_reference,
            "MPESA-REFUND-ORIGINAL",
        )

    def test_refund_reference_cannot_be_reused(self):
        first = self._process(
            self.viewing,
            data={"provider_reference": "MPESA-REFUND-UNIQUE"},
        )
        other_viewing, other_payment = self._create_resolution_request(
            choice=Viewing.FeeResolutionChoice.REFUND,
        )
        second = self._process(
            other_viewing,
            data={"provider_reference": "MPESA-REFUND-UNIQUE"},
        )

        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertEqual(second.status_code, status.HTTP_400_BAD_REQUEST)
        other_viewing.refresh_from_db()
        other_payment.refresh_from_db()
        self.assertEqual(
            other_viewing.status,
            Viewing.Status.SCHEDULING_FAILED,
        )
        self.assertEqual(
            other_payment.status,
            Payment.Status.SUCCESSFUL,
        )

    def test_staff_can_issue_one_transferable_viewing_credit(self):
        self.viewing.fee_resolution_choice = (
            Viewing.FeeResolutionChoice.CREDIT
        )
        self.viewing.save(
            update_fields=[
                "fee_resolution_choice",
                "updated_at",
            ]
        )

        response = self._process(
            self.viewing,
            data={"notes": "Credit approved after scheduling failure."},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            response.data,
        )
        self.assertEqual(
            response.data["viewing"]["status"],
            Viewing.Status.CREDIT_ISSUED,
        )
        self.assertEqual(
            response.data["payment"]["status"],
            Payment.Status.SUCCESSFUL,
        )
        self.assertIsNotNone(response.data["credit"])

        credit = ViewingCredit.objects.get(
            source_payment=self.payment,
        )
        self.viewing.refresh_from_db()
        self.assertEqual(credit.customer, self.customer)
        self.assertEqual(credit.source_viewing, self.viewing)
        self.assertEqual(credit.amount, Decimal("400.00"))
        self.assertEqual(credit.remaining_amount, Decimal("400.00"))
        self.assertEqual(credit.status, ViewingCredit.Status.ACTIVE)
        self.assertEqual(credit.issued_by, self.staff)
        self.assertEqual(
            self.viewing.fee_resolution_reference,
            credit.credit_reference,
        )
        self.assertTrue(
            ViewingEvent.objects.filter(
                viewing=self.viewing,
                event_type=ViewingEvent.EventType.CREDIT_ISSUED,
                actor=self.staff,
            ).exists()
        )

    def test_credit_processing_is_idempotent(self):
        self.viewing.fee_resolution_choice = (
            Viewing.FeeResolutionChoice.CREDIT
        )
        self.viewing.save(
            update_fields=[
                "fee_resolution_choice",
                "updated_at",
            ]
        )

        first = self._process(self.viewing)
        second = self._process(self.viewing)

        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertTrue(second.data["already_processed"])
        self.assertEqual(
            ViewingCredit.objects.filter(
                source_payment=self.payment,
            ).count(),
            1,
        )
        self.assertEqual(
            ViewingEvent.objects.filter(
                viewing=self.viewing,
                event_type=ViewingEvent.EventType.CREDIT_ISSUED,
            ).count(),
            1,
        )
