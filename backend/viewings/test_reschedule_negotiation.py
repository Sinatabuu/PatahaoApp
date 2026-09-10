from datetime import date, time
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from rest_framework import status
from rest_framework.test import APITestCase

from notifications.models import Notification
from governance.models import PartnerTier
from partners.models import Partner
from payments.models import Payment
from properties.models import Property

from .models import Viewing, ViewingEvent


User = get_user_model()


class CustomerRescheduleNegotiationTests(APITestCase):
    def setUp(self):
        self.partner_user = User.objects.create_user(
            username="reschedule_partner",
            email="reschedule-partner@example.com",
            password="TestPassword123!",
            role=User.ROLE_PARTNER,
        )
        self.customer = User.objects.create_user(
            username="reschedule_customer",
            email="reschedule-customer@example.com",
            password="TestPassword123!",
            role=User.ROLE_CUSTOMER,
        )
        self.other_customer = User.objects.create_user(
            username="other_reschedule_customer",
            email="other-reschedule-customer@example.com",
            password="TestPassword123!",
            role=User.ROLE_CUSTOMER,
        )
        self.partner = Partner.objects.create(
            user=self.partner_user,
            business_name="Reschedule Partner",
            display_name="Reschedule Partner",
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
            title="New Wine",
            property_type=Property.TYPE_APARTMENT,
            listing_type=Property.LISTING_RENT,
            price=Decimal("25000.00"),
            county="Nairobi",
            town="Roysambu",
            estate="Roysambu",
            address="Reschedule Test Address",
            bedrooms=2,
            bathrooms=1,
            description="Property used to test viewing-time negotiation.",
            status=Property.STATUS_DRAFT,
        )
        self.viewing = Viewing.objects.create(
            customer=self.customer,
            property=self.property,
            assigned_partner=self.partner,
            requested_date=date(2027, 2, 10),
            requested_time=time(10, 0),
            proposed_date=date(2027, 2, 11),
            proposed_time=time(14, 30),
            partner_response_message="Can we meet the following afternoon?",
            status=Viewing.Status.RESCHEDULE_PROPOSED,
        )
        self.payment = Payment.objects.create(
            viewing=self.viewing,
            payer=self.customer,
            amount=self.viewing.fee_amount,
            currency="KES",
            purpose="viewing_fee",
            payment_method=Payment.PaymentMethod.MPESA,
            status=Payment.Status.SUCCESSFUL,
            paid_at=timezone.now(),
            provider_receipt_number="TEST-RESCHEDULE-RECEIPT",
            receipt_number="PHR-TEST-RESCHEDULE",
        )
        self.viewing.payment_reference = self.payment.payment_reference
        self.viewing.save(
            update_fields=[
                "payment_reference",
                "updated_at",
            ]
        )

    def _post_as_customer(self, route_name, *, data=None):
        self.client.force_authenticate(user=self.customer)

        return self.client.post(
            reverse(
                route_name,
                kwargs={"pk": self.viewing.pk},
            ),
            data or {},
            format="json",
        )

    def test_customer_can_accept_partner_reschedule(self):
        response = self._post_as_customer(
            "viewing-accept-reschedule",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            response.data,
        )
        self.assertEqual(
            response.data["viewing"]["status"],
            Viewing.Status.CONFIRMED,
        )

        self.viewing.refresh_from_db()
        self.assertEqual(self.viewing.status, Viewing.Status.CONFIRMED)
        self.assertEqual(self.viewing.confirmed_date, date(2027, 2, 11))
        self.assertEqual(self.viewing.confirmed_time, time(14, 30))
        self.assertIsNone(self.viewing.proposed_date)
        self.assertIsNone(self.viewing.proposed_time)
        self.assertTrue(
            self.viewing.events.filter(
                event_type=(
                    ViewingEvent.EventType.CUSTOMER_ACCEPTED_RESCHEDULE
                ),
                actor=self.customer,
            ).exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                user=self.partner_user,
                title="Customer accepted viewing time",
            ).exists()
        )

    def test_first_decline_requests_one_more_partner_proposal(self):
        response = self._post_as_customer(
            "viewing-decline-reschedule",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            response.data,
        )
        self.assertFalse(response.data["fee_resolution_required"])
        self.assertEqual(
            response.data["viewing"]["status"],
            Viewing.Status.PAID_PENDING_PARTNER,
        )
        self.assertEqual(
            response.data["viewing"]["reschedule_decline_count"],
            1,
        )
        self.assertEqual(
            response.data["viewing"]["remaining_reschedule_proposals"],
            1,
        )

        self.viewing.refresh_from_db()
        self.assertEqual(
            self.viewing.status,
            Viewing.Status.PAID_PENDING_PARTNER,
        )
        self.assertEqual(self.viewing.reschedule_decline_count, 1)
        self.assertIsNone(self.viewing.proposed_date)
        self.assertIsNone(self.viewing.proposed_time)
        self.assertTrue(
            self.viewing.events.filter(
                event_type=(
                    ViewingEvent.EventType.CUSTOMER_DECLINED_RESCHEDULE
                ),
                actor=self.customer,
                metadata__decline_count=1,
            ).exists()
        )

    def test_second_decline_requires_credit_or_refund_choice(self):
        self.viewing.reschedule_decline_count = 1
        self.viewing.save(
            update_fields=[
                "reschedule_decline_count",
                "updated_at",
            ]
        )

        response = self._post_as_customer(
            "viewing-decline-reschedule",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            response.data,
        )
        self.assertTrue(response.data["fee_resolution_required"])
        self.assertEqual(
            response.data["viewing"]["status"],
            Viewing.Status.SCHEDULING_FAILED,
        )
        self.assertTrue(
            response.data["viewing"]["requires_fee_resolution"]
        )
        self.assertEqual(
            response.data["viewing"]["remaining_reschedule_proposals"],
            0,
        )

        self.viewing.refresh_from_db()
        self.assertEqual(
            self.viewing.status,
            Viewing.Status.SCHEDULING_FAILED,
        )
        self.assertEqual(self.viewing.reschedule_decline_count, 2)
        self.assertTrue(
            self.viewing.events.filter(
                event_type=ViewingEvent.EventType.SCHEDULING_FAILED,
            ).exists()
        )

    def test_partner_cannot_replace_a_proposal_awaiting_customer(self):
        self.client.force_authenticate(user=self.partner_user)

        response = self.client.post(
            reverse(
                "viewing-propose-reschedule",
                kwargs={"pk": self.viewing.pk},
            ),
            {
                "proposed_date": "2027-02-12",
                "proposed_time": "16:00:00",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.viewing.refresh_from_db()
        self.assertEqual(self.viewing.proposed_date, date(2027, 2, 11))
        self.assertEqual(self.viewing.proposed_time, time(14, 30))

    def test_partner_can_make_the_second_and_final_proposal(self):
        first_decline = self._post_as_customer(
            "viewing-decline-reschedule",
        )
        self.assertEqual(first_decline.status_code, status.HTTP_200_OK)

        self.client.force_authenticate(user=self.partner_user)
        response = self.client.post(
            reverse(
                "viewing-propose-reschedule",
                kwargs={"pk": self.viewing.pk},
            ),
            {
                "proposed_date": "2027-02-12",
                "proposed_time": "16:00:00",
                "partner_response_message": "One final option.",
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
        self.assertEqual(
            response.data["remaining_reschedule_proposals"],
            1,
        )
        self.assertTrue(
            self.viewing.events.filter(
                event_type=ViewingEvent.EventType.RESCHEDULE_PROPOSED,
                metadata__proposal_number=2,
            ).exists()
        )

    def test_customer_can_choose_refund_after_scheduling_fails(self):
        self.viewing.status = Viewing.Status.SCHEDULING_FAILED
        self.viewing.reschedule_decline_count = 2
        self.viewing.proposed_date = None
        self.viewing.proposed_time = None
        self.viewing.save(
            update_fields=[
                "status",
                "reschedule_decline_count",
                "proposed_date",
                "proposed_time",
                "updated_at",
            ]
        )

        response = self._post_as_customer(
            "viewing-choose-fee-resolution",
            data={"choice": Viewing.FeeResolutionChoice.REFUND},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            response.data,
        )
        self.assertEqual(
            response.data["viewing"]["fee_resolution_choice"],
            Viewing.FeeResolutionChoice.REFUND,
        )
        self.assertFalse(
            response.data["viewing"]["requires_fee_resolution"]
        )

        self.viewing.refresh_from_db()
        self.payment.refresh_from_db()
        self.assertEqual(
            self.viewing.fee_resolution_choice,
            Viewing.FeeResolutionChoice.REFUND,
        )
        self.assertIsNotNone(self.viewing.fee_resolution_requested_at)
        self.assertEqual(
            self.payment.status,
            Payment.Status.SUCCESSFUL,
        )
        self.assertTrue(
            self.viewing.events.filter(
                event_type=(
                    ViewingEvent.EventType.FEE_RESOLUTION_CHOSEN
                ),
                metadata__choice=Viewing.FeeResolutionChoice.REFUND,
            ).exists()
        )

    def test_fee_choice_is_idempotent_but_cannot_be_changed(self):
        self.viewing.status = Viewing.Status.SCHEDULING_FAILED
        self.viewing.reschedule_decline_count = 2
        self.viewing.fee_resolution_choice = (
            Viewing.FeeResolutionChoice.CREDIT
        )
        self.viewing.fee_resolution_requested_at = timezone.now()
        self.viewing.save(
            update_fields=[
                "status",
                "reschedule_decline_count",
                "fee_resolution_choice",
                "fee_resolution_requested_at",
                "updated_at",
            ]
        )

        same_response = self._post_as_customer(
            "viewing-choose-fee-resolution",
            data={"choice": Viewing.FeeResolutionChoice.CREDIT},
        )
        changed_response = self._post_as_customer(
            "viewing-choose-fee-resolution",
            data={"choice": Viewing.FeeResolutionChoice.REFUND},
        )

        self.assertEqual(same_response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            changed_response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_another_customer_cannot_respond_to_the_proposal(self):
        self.client.force_authenticate(user=self.other_customer)

        response = self.client.post(
            reverse(
                "viewing-decline-reschedule",
                kwargs={"pk": self.viewing.pk},
            ),
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
