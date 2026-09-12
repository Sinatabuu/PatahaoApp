from datetime import timedelta
from decimal import Decimal

from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from notifications.models import Notification
from partners.models import Partner
from properties.models import (
    Property,
    PropertyPartner,
)
from viewings.models import (
    RENTAL_VIEWING_FEE,
    Viewing,
    ViewingEvent,
)

from .models import Payment


@override_settings(DEBUG=True)
class PaidViewingHandoffTests(APITestCase):
    def setUp(self):
        self.partner_user = User.objects.create_user(
            username="paid_handoff_partner",
            email="paid-handoff-partner@example.com",
            password="test-pass-123",
            role=User.ROLE_PARTNER,
        )
        self.partner = Partner.objects.create(
            user=self.partner_user,
            business_name="Paid Handoff Homes",
            display_name="Paid Handoff Homes",
            verification_status=Partner.STATUS_APPROVED,
            is_active=True,
            accepts_viewing_requests=True,
        )
        self.customer = User.objects.create_user(
            username="paid_handoff_customer",
            email="paid-handoff-customer@example.com",
            password="test-pass-123",
            role=User.ROLE_CUSTOMER,
        )
        self.property_obj = Property.objects.create(
            partner=self.partner,
            title="Paid Handoff Rental",
            property_type=Property.TYPE_APARTMENT,
            listing_type=Property.LISTING_RENT,
            price=Decimal("35000.00"),
            county="Nairobi",
            town="Roysambu",
            estate="Garden Estate",
            address="Paid Handoff Road",
            latitude=Decimal("-1.218000"),
            longitude=Decimal("36.886000"),
            bedrooms=2,
            bathrooms=1,
            description=(
                "A published rental used to protect the paid "
                "viewing handoff."
            ),
            status=Property.STATUS_DRAFT,
        )
        Property.objects.filter(
            pk=self.property_obj.pk,
        ).update(
            status=Property.STATUS_PUBLISHED,
        )
        self.property_obj.refresh_from_db()

        participation, _created = PropertyPartner.objects.get_or_create(
            property=self.property_obj,
            partner=self.partner,
            defaults={
                "role": PropertyPartner.Role.SOURCE,
                "status": PropertyPartner.Status.ACTIVE,
            },
        )
        participation.role = PropertyPartner.Role.SOURCE
        participation.status = PropertyPartner.Status.ACTIVE
        participation.save(
            update_fields=[
                "role",
                "status",
            ]
        )

    def _items(self, response):
        payload = response.data

        if isinstance(payload, dict):
            payload = payload.get("results", [])

        return payload

    def _create_viewing(self):
        self.client.force_authenticate(
            user=self.customer,
        )
        response = self.client.post(
            "/api/viewings/",
            {
                "property": self.property_obj.id,
                "requested_date": (
                    timezone.localdate() + timedelta(days=2)
                ).isoformat(),
                "requested_time": "10:30:00",
                "customer_message": (
                    "I would like to view this rental."
                ),
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            response.data,
        )
        self.assertEqual(
            response.data["status"],
            Viewing.Status.PENDING_PAYMENT,
        )
        self.assertEqual(
            response.data["fee_amount"],
            str(RENTAL_VIEWING_FEE),
        )

        return Viewing.objects.get(pk=response.data["id"])

    def _create_payment(self, viewing):
        self.client.force_authenticate(
            user=self.customer,
        )
        response = self.client.post(
            "/api/payments/",
            {
                "viewing": viewing.id,
                "phone_number": "0712345678",
                "provider": Payment.PaymentMethod.MPESA,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            response.data,
        )
        self.assertEqual(
            response.data["amount"],
            str(RENTAL_VIEWING_FEE),
        )

        viewing.refresh_from_db()
        self.assertEqual(
            viewing.status,
            Viewing.Status.PAYMENT_PROCESSING,
        )

        return Payment.objects.get(pk=response.data["id"])

    def _complete_mock_payment(self, payment, viewing):
        self.client.force_authenticate(
            user=self.customer,
        )
        response = self.client.post(
            f"/api/payments/{payment.id}/mock-success/",
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            response.data,
        )

        payment.refresh_from_db()
        viewing.refresh_from_db()

        self.assertEqual(
            payment.status,
            Payment.Status.SUCCESSFUL,
        )
        self.assertEqual(
            viewing.status,
            Viewing.Status.PAID_PENDING_PARTNER,
        )
        self.assertEqual(
            viewing.payment_reference,
            payment.payment_reference,
        )
        self.assertTrue(payment.receipt_number)
        self.assertTrue(
            ViewingEvent.objects.filter(
                viewing=viewing,
                event_type=(
                    ViewingEvent.EventType.PAYMENT_RECEIVED
                ),
                metadata__payment_id=payment.id,
            ).exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                user=self.partner_user,
                title="New paid viewing request",
            ).exists()
        )

    def _partner_inbox(self):
        self.client.force_authenticate(
            user=self.partner_user,
        )
        response = self.client.get(
            "/api/viewings/partner-inbox/",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        return self._items(response)

    def _create_paid_viewing(self):
        viewing = self._create_viewing()
        payment = self._create_payment(viewing)
        self._complete_mock_payment(payment, viewing)
        return viewing

    @override_settings(
        ENABLE_DEVELOPMENT_PAYMENT_HANDOFF=False,
    )
    def test_mock_payment_handoff_is_hidden_when_disabled(self):
        viewing = self._create_viewing()
        payment = self._create_payment(viewing)

        response = self.client.post(
            f"/api/payments/{payment.id}/mock-success/",
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
            response.data,
        )

        payment.refresh_from_db()
        viewing.refresh_from_db()
        self.assertNotEqual(
            payment.status,
            Payment.Status.SUCCESSFUL,
        )
        self.assertEqual(
            viewing.status,
            Viewing.Status.PAYMENT_PROCESSING,
        )

    def test_unpaid_viewing_is_hidden_then_paid_viewing_can_be_accepted(self):
        viewing = self._create_viewing()

        self.assertNotIn(
            viewing.id,
            {
                item["id"]
                for item in self._partner_inbox()
            },
        )

        payment = self._create_payment(viewing)

        self.assertNotIn(
            viewing.id,
            {
                item["id"]
                for item in self._partner_inbox()
            },
        )

        self._complete_mock_payment(payment, viewing)

        self.assertIn(
            viewing.id,
            {
                item["id"]
                for item in self._partner_inbox()
            },
        )

        response = self.client.post(
            f"/api/viewings/{viewing.id}/accept/",
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            response.data,
        )
        self.assertEqual(
            response.data["status"],
            Viewing.Status.CONFIRMED,
        )

        self.client.force_authenticate(
            user=self.customer,
        )
        customer_response = self.client.get(
            f"/api/viewings/{viewing.id}/",
        )

        self.assertEqual(
            customer_response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            customer_response.data["status"],
            Viewing.Status.CONFIRMED,
        )
        self.assertEqual(
            customer_response.data["confirmed_date"],
            viewing.requested_date.isoformat(),
        )
        self.assertEqual(
            customer_response.data["confirmed_time"],
            viewing.requested_time.strftime("%H:%M:%S"),
        )

    def test_paid_viewing_reschedule_is_visible_to_customer(self):
        viewing = self._create_paid_viewing()
        proposed_date = (
            timezone.localdate() + timedelta(days=3)
        )

        self.client.force_authenticate(
            user=self.partner_user,
        )
        response = self.client.post(
            f"/api/viewings/{viewing.id}/propose-reschedule/",
            {
                "proposed_date": proposed_date.isoformat(),
                "proposed_time": "14:30:00",
                "partner_response_message": (
                    "Please meet at 2:30 PM instead."
                ),
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            response.data,
        )
        self.assertEqual(
            response.data["status"],
            Viewing.Status.RESCHEDULE_PROPOSED,
        )

        self.client.force_authenticate(
            user=self.customer,
        )
        customer_response = self.client.get(
            f"/api/viewings/{viewing.id}/",
        )

        self.assertEqual(
            customer_response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            customer_response.data["status"],
            Viewing.Status.RESCHEDULE_PROPOSED,
        )
        self.assertEqual(
            customer_response.data["proposed_date"],
            proposed_date.isoformat(),
        )
        self.assertEqual(
            customer_response.data["proposed_time"],
            "14:30:00",
        )
        self.assertEqual(
            customer_response.data["partner_response_message"],
            "Please meet at 2:30 PM instead.",
        )

    def test_paid_viewing_decline_is_visible_to_customer(self):
        viewing = self._create_paid_viewing()
        decline_reason = (
            "The owner cannot accommodate this viewing time."
        )

        self.client.force_authenticate(
            user=self.partner_user,
        )
        response = self.client.post(
            f"/api/viewings/{viewing.id}/decline/",
            {
                "partner_response_message": decline_reason,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            response.data,
        )
        self.assertEqual(
            response.data["status"],
            Viewing.Status.DECLINED,
        )

        self.client.force_authenticate(
            user=self.customer,
        )
        customer_response = self.client.get(
            f"/api/viewings/{viewing.id}/",
        )

        self.assertEqual(
            customer_response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            customer_response.data["status"],
            Viewing.Status.DECLINED,
        )
        self.assertEqual(
            customer_response.data["partner_response_message"],
            decline_reason,
        )
