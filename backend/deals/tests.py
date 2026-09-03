from datetime import date, time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from rest_framework import status
from rest_framework.test import APITestCase

from commissions.models import (
    CommissionAgreement,
    CommissionSettlement,
    CommissionSettlementParticipant,
    CommissionSettlementPayment,
)
from governance.models import (
    PartnerTier,
    PartnerTierAssignment,
)
from commissions.services import (
    allocate_commission_settlement,
    approve_commission_settlement,
    pay_commission_participant_outstanding,
)
from governance.services import (
    enforce_partner_operational_access,
)
from introductions.models import ProtectedIntroduction
from mandates.models import (
    PropertyMandate,
    PropertyOwner,
)
from partners.models import Partner
from properties.models import Property
from viewings.models import Viewing

from .models import (
    CommissionInvoice,
    CommissionReceipt,
    Deal,
    DealEvent,
    DealOutcome,
    OwnerConfirmationToken,
)
from .services import (
    close_commission_paid_deal,
    complete_agreed_deal_and_raise_commission,
    ensure_commission_invoice_for_due_deal,
    evaluate_deal_outcomes,
    record_commission_receipt,
)
User = get_user_model()


class DealAPITestBase(APITestCase):
    """
    Common records used by the Deals REST API tests.
    """

    def setUp(self):
        self.customer = User.objects.create_user(
            username="deal_customer",
            email="deal.customer@example.com",
            password="TestPassword123!",
            role=User.ROLE_CUSTOMER,
        )

        self.other_customer = User.objects.create_user(
            username="other_deal_customer",
            email="other.customer@example.com",
            password="TestPassword123!",
            role=User.ROLE_CUSTOMER,
        )

        self.partner_user = User.objects.create_user(
            username="deal_partner",
            email="deal.partner@example.com",
            password="TestPassword123!",
            role=User.ROLE_PARTNER,
        )

        self.other_partner_user = User.objects.create_user(
            username="other_deal_partner",
            email="other.partner@example.com",
            password="TestPassword123!",
            role=User.ROLE_PARTNER,
        )

        self.staff_user = User.objects.create_user(
            username="deal_staff",
            email="deal.staff@example.com",
            password="TestPassword123!",
            role=User.ROLE_ADMIN,
            is_staff=True,
        )

        self.partner = Partner.objects.create(
            user=self.partner_user,
            business_name="Deal Test Partner",
            display_name="Main Partner",
            partner_type=Partner.PARTNER_TYPE_AGENT,
            verification_status=Partner.STATUS_APPROVED,
            is_active=True,
        )

        self.other_partner = Partner.objects.create(
            user=self.other_partner_user,
            business_name="Other Deal Partner",
            display_name="Other Partner",
            partner_type=Partner.PARTNER_TYPE_AGENT,
            verification_status=Partner.STATUS_APPROVED,
            is_active=True,
        )

        self.rental_property = Property.objects.create(
            partner=self.partner,
            title="Deal Test Rental Apartment",
            property_type=Property.TYPE_APARTMENT,
            listing_type=Property.LISTING_RENT,
            price=Decimal("50000.00"),
            county="Nairobi",
            town="Roysambu",
            estate="Roysambu",
            address="Test Rental Address",
            bedrooms=2,
            bathrooms=1,
            description="Rental property used by the Deals API tests.",
            status=Property.STATUS_DRAFT,
        )

        self.sale_property = Property.objects.create(
            partner=self.partner,
            title="Deal Test Sale House",
            property_type=Property.TYPE_HOUSE,
            listing_type=Property.LISTING_SALE,
            price=Decimal("8500000.00"),
            county="Nairobi",
            town="Roysambu",
            estate="Garden Estate",
            address="Test Sale Address",
            bedrooms=4,
            bathrooms=3,
            description="Sale property used by the Deals API tests.",
            status=Property.STATUS_DRAFT,
        )

        self.other_property = Property.objects.create(
            partner=self.other_partner,
            title="Other Partner Apartment",
            property_type=Property.TYPE_APARTMENT,
            listing_type=Property.LISTING_RENT,
            price=Decimal("40000.00"),
            county="Nairobi",
            town="Kasarani",
            estate="Kasarani",
            address="Other Partner Address",
            bedrooms=1,
            bathrooms=1,
            description="Property belonging to another partner.",
            status=Property.STATUS_DRAFT,
        )

        Property.objects.filter(
            pk__in=[
                self.rental_property.pk,
                self.sale_property.pk,
                self.other_property.pk,
            ]
        ).update(
            status=Property.STATUS_PUBLISHED,
        )

        self.rental_property.refresh_from_db()
        self.sale_property.refresh_from_db()
        self.other_property.refresh_from_db()

        self.viewing = Viewing.objects.create(
            customer=self.customer,
            property=self.rental_property,
            assigned_partner=self.partner,
            requested_date=date(2027, 1, 15),
            requested_time=time(10, 30),
            customer_message="Rental deal API test.",
            
        )

        self.sale_viewing = Viewing.objects.create(
            customer=self.customer,
            property=self.sale_property,
            assigned_partner=self.partner,
            requested_date=date(2027, 1, 16),
            requested_time=time(11, 30),
            customer_message="Sale deal API test.",
            
        )

        self.other_viewing = Viewing.objects.create(
            customer=self.other_customer,
            property=self.other_property,
            assigned_partner=self.other_partner,
            requested_date=date(2027, 1, 17),
            requested_time=time(12, 30),
            customer_message="Other customer's viewing.",
            
        )

        self.deal = Deal.objects.create(
            customer=self.customer,
            partner=self.partner,
            property=self.rental_property,
            viewing=self.viewing,
            monthly_rent=Decimal("50000.00"),
        )

        self.sale_deal = Deal.objects.create(
            customer=self.customer,
            partner=self.partner,
            property=self.sale_property,
            viewing=self.sale_viewing,
            sale_price=Decimal("8500000.00"),
        )

        self.other_deal = Deal.objects.create(
            customer=self.other_customer,
            partner=self.other_partner,
            property=self.other_property,
            viewing=self.other_viewing,
            monthly_rent=Decimal("40000.00"),
        )

    def deal_list_url(self):
        return reverse("deal-list")

    def deal_detail_url(self, deal):
        return reverse(
            "deal-detail",
            kwargs={"pk": deal.pk},
        )

    def customer_outcome_url(self, deal):
        return reverse(
            "deal-customer-outcome",
            kwargs={"pk": deal.pk},
        )

    def partner_outcome_url(self, deal):
        return reverse(
            "deal-partner-outcome",
            kwargs={"pk": deal.pk},
        )


class DealAccessTests(DealAPITestBase):

    def test_unauthenticated_user_cannot_list_deals(self):
        response = self.client.get(
            self.deal_list_url(),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_customer_sees_only_their_own_deals(self):
        self.client.force_authenticate(
            user=self.customer,
        )

        response = self.client.get(
            self.deal_list_url(),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        returned_ids = {
            item["id"]
            for item in response.data
        }

        self.assertEqual(
            returned_ids,
            {
                self.deal.id,
                self.sale_deal.id,
            },
        )

        self.assertNotIn(
            self.other_deal.id,
            returned_ids,
        )

    def test_customer_cannot_retrieve_another_customers_deal(self):
        self.client.force_authenticate(
            user=self.customer,
        )

        response = self.client.get(
            self.deal_detail_url(self.other_deal),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_partner_sees_only_assigned_deals(self):
        self.client.force_authenticate(
            user=self.partner_user,
        )

        response = self.client.get(
            self.deal_list_url(),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        returned_ids = {
            item["id"]
            for item in response.data
        }

        self.assertEqual(
            returned_ids,
            {
                self.deal.id,
                self.sale_deal.id,
            },
        )

        self.assertNotIn(
            self.other_deal.id,
            returned_ids,
        )

    def test_partner_cannot_retrieve_another_partners_deal(self):
        self.client.force_authenticate(
            user=self.partner_user,
        )

        response = self.client.get(
            self.deal_detail_url(self.other_deal),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_staff_user_can_see_all_deals(self):
        self.client.force_authenticate(
            user=self.staff_user,
        )

        response = self.client.get(
            self.deal_list_url(),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        returned_ids = {
            item["id"]
            for item in response.data
        }

        self.assertEqual(
            returned_ids,
            {
                self.deal.id,
                self.sale_deal.id,
                self.other_deal.id,
            },
        )


class DealOutcomePermissionTests(DealAPITestBase):

    def test_customer_cannot_submit_partner_outcome(self):
        self.client.force_authenticate(
            user=self.customer,
        )

        response = self.client.post(
            self.partner_outcome_url(self.deal),
            {
                "outcome": DealOutcome.Outcome.RENTED,
                "notes": "Trying to report as the partner.",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

        self.assertFalse(
            DealOutcome.objects.filter(
                deal=self.deal,
                reporter=DealOutcome.Reporter.PARTNER,
            ).exists()
        )

    def test_partner_cannot_submit_customer_outcome(self):
        self.client.force_authenticate(
            user=self.partner_user,
        )

        response = self.client.post(
            self.customer_outcome_url(self.deal),
            {
                "outcome": DealOutcome.Outcome.RENTED,
                "notes": "Trying to report as the customer.",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

        self.assertFalse(
            DealOutcome.objects.filter(
                deal=self.deal,
                reporter=DealOutcome.Reporter.CUSTOMER,
            ).exists()
        )

    def test_customer_cannot_submit_outcome_for_another_customers_deal(self):
        self.client.force_authenticate(
            user=self.customer,
        )

        response = self.client.post(
            self.customer_outcome_url(self.other_deal),
            {
                "outcome": DealOutcome.Outcome.RENTED,
                "notes": "This deal does not belong to me.",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_partner_cannot_submit_outcome_for_another_partners_deal(self):
        self.client.force_authenticate(
            user=self.partner_user,
        )

        response = self.client.post(
            self.partner_outcome_url(self.other_deal),
            {
                "outcome": DealOutcome.Outcome.RENTED,
                "notes": "This deal belongs to another partner.",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_staff_cannot_submit_customer_outcome(self):
        self.client.force_authenticate(
            user=self.staff_user,
        )

        response = self.client.post(
            self.customer_outcome_url(self.deal),
            {
                "outcome": DealOutcome.Outcome.RENTED,
                "notes": "Staff must not impersonate the customer.",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_staff_cannot_submit_partner_outcome(self):
        self.client.force_authenticate(
            user=self.staff_user,
        )

        response = self.client.post(
            self.partner_outcome_url(self.deal),
            {
                "outcome": DealOutcome.Outcome.RENTED,
                "notes": "Staff must not impersonate the partner.",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )


class DealOutcomeWorkflowTests(DealAPITestBase):

    def submit_customer_outcome(
        self,
        deal,
        outcome,
        notes="Customer outcome.",
    ):
        self.client.force_authenticate(
            user=deal.customer,
        )

        return self.client.post(
            self.customer_outcome_url(deal),
            {
                "outcome": outcome,
                "notes": notes,
            },
            format="json",
        )

    def submit_partner_outcome(
        self,
        deal,
        outcome,
        notes="Partner outcome.",
    ):
        self.client.force_authenticate(
            user=deal.partner.user,
        )

        return self.client.post(
            self.partner_outcome_url(deal),
            {
                "outcome": outcome,
                "notes": notes,
            },
            format="json",
        )

    def submit_owner_outcome(
        self,
        deal,
        outcome,
        notes="Owner outcome.",
    ):
        owner_outcome = DealOutcome.objects.create(
            deal=deal,
            reporter=DealOutcome.Reporter.OWNER,
            outcome=outcome,
            notes=notes,
        )

        evaluate_deal_outcomes(
            deal.id,
        )

        return owner_outcome

    def test_first_outcome_keeps_deal_pending_confirmation(self):
        response = self.submit_customer_outcome(
            self.deal,
            DealOutcome.Outcome.RENTED,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.deal.refresh_from_db()

        self.assertEqual(
            self.deal.status,
            Deal.Status.AWAITING_CONFIRMATIONS,
        )

        self.assertTrue(
            self.deal.customer_confirmed,
        )

        self.assertFalse(
            self.deal.partner_confirmed,
        )

        self.assertFalse(
            self.deal.owner_confirmed,
        )

    def test_matching_rental_outcomes_confirm_deal(self):
        customer_response = self.submit_customer_outcome(
            self.deal,
            DealOutcome.Outcome.RENTED,
            notes="I rented the apartment.",
        )

        partner_response = self.submit_partner_outcome(
            self.deal,
            DealOutcome.Outcome.RENTED,
            notes="The customer accepted the rental.",
        )

        self.submit_owner_outcome(
            self.deal,
            DealOutcome.Outcome.RENTED,
            notes=(
                "I confirm the customer rented "
                "the property."
            ),
        )

        self.assertEqual(
            customer_response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertEqual(
            partner_response.status_code,
            status.HTTP_201_CREATED,
        )

        self.deal.refresh_from_db()
        self.rental_property.refresh_from_db()

        self.assertEqual(
            self.deal.status,
            Deal.Status.AGREED,
        )

        self.assertTrue(
            self.deal.customer_confirmed,
        )

        self.assertTrue(
            self.deal.partner_confirmed,
        )

        self.assertTrue(
            self.deal.owner_confirmed,
        )

        self.assertIsNotNone(
            self.deal.customer_confirmed_at,
        )

        self.assertIsNotNone(
            self.deal.partner_confirmed_at,
        )

        self.assertIsNotNone(
            self.deal.owner_confirmed_at,
        )

        self.assertIsNotNone(
            self.deal.agreed_at,
        )

        self.assertEqual(
            self.rental_property.status,
            Property.STATUS_RESERVED,
        )

    def test_matching_purchase_outcomes_confirm_sale_deal(self):
        customer_response = self.submit_customer_outcome(
            self.sale_deal,
            DealOutcome.Outcome.PURCHASED,
        )

        partner_response = self.submit_partner_outcome(
            self.sale_deal,
            DealOutcome.Outcome.PURCHASED,
        )

        self.submit_owner_outcome(
            self.sale_deal,
            DealOutcome.Outcome.PURCHASED,
        )

        self.assertEqual(
            customer_response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertEqual(
            partner_response.status_code,
            status.HTTP_201_CREATED,
        )

        self.sale_deal.refresh_from_db()
        self.sale_property.refresh_from_db()

        self.assertEqual(
            self.sale_deal.status,
            Deal.Status.AGREED,
        )

        self.assertTrue(
            self.sale_deal.customer_confirmed,
        )

        self.assertTrue(
            self.sale_deal.partner_confirmed,
        )

        self.assertTrue(
            self.sale_deal.owner_confirmed,
        )

        self.assertEqual(
            self.sale_property.status,
            Property.STATUS_RESERVED,
        )

    def test_conflicting_outcomes_mark_deal_disputed(self):
        customer_response = self.submit_customer_outcome(
            self.deal,
            DealOutcome.Outcome.RENTED,
        )

        partner_response = self.submit_partner_outcome(
            self.deal,
            DealOutcome.Outcome.DECLINED,
        )

        self.submit_owner_outcome(
            self.deal,
            DealOutcome.Outcome.RENTED,
        )

        self.assertEqual(
            customer_response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertEqual(
            partner_response.status_code,
            status.HTTP_201_CREATED,
        )

        self.deal.refresh_from_db()

        self.assertEqual(
            self.deal.status,
            Deal.Status.DISPUTED,
        )

        self.assertTrue(
            self.deal.customer_confirmed,
        )

        self.assertTrue(
            self.deal.partner_confirmed,
        )

        self.assertTrue(
            self.deal.owner_confirmed,
        )

    def test_wrong_success_outcome_for_listing_type_is_disputed(self):
        self.submit_customer_outcome(
            self.deal,
            DealOutcome.Outcome.PURCHASED,
        )

        self.submit_partner_outcome(
            self.deal,
            DealOutcome.Outcome.PURCHASED,
        )

        self.submit_owner_outcome(
            self.deal,
            DealOutcome.Outcome.PURCHASED,
        )

        self.deal.refresh_from_db()
        self.rental_property.refresh_from_db()

        self.assertEqual(
            self.deal.status,
            Deal.Status.DISPUTED,
        )

        self.assertEqual(
            self.rental_property.status,
            Property.STATUS_PUBLISHED,
        )

    def test_matching_declined_outcomes_cancel_deal(self):
        self.submit_customer_outcome(
            self.deal,
            DealOutcome.Outcome.DECLINED,
        )

        self.submit_partner_outcome(
            self.deal,
            DealOutcome.Outcome.DECLINED,
        )

        self.submit_owner_outcome(
            self.deal,
            DealOutcome.Outcome.DECLINED,
        )

        self.deal.refresh_from_db()

        self.assertEqual(
            self.deal.status,
            Deal.Status.CANCELLED,
        )

        self.assertTrue(
            self.deal.customer_confirmed,
        )

        self.assertTrue(
            self.deal.partner_confirmed,
        )

        self.assertTrue(
            self.deal.owner_confirmed,
        )

        self.assertIsNotNone(
            self.deal.cancelled_at,
        )

        self.assertTrue(
            self.deal.cancellation_reason,
        )

    def test_matching_no_show_outcomes_cancel_deal(self):
        self.submit_customer_outcome(
            self.deal,
            DealOutcome.Outcome.NO_SHOW,
        )

        self.submit_partner_outcome(
            self.deal,
            DealOutcome.Outcome.NO_SHOW,
        )

        self.submit_owner_outcome(
            self.deal,
            DealOutcome.Outcome.NO_SHOW,
        )

        self.deal.refresh_from_db()

        self.assertEqual(
            self.deal.status,
            Deal.Status.CANCELLED,
        )

        self.assertTrue(
            self.deal.customer_confirmed,
        )

        self.assertTrue(
            self.deal.partner_confirmed,
        )

        self.assertTrue(
            self.deal.owner_confirmed,
        )

    def test_matching_still_deciding_outcomes_keep_deal_negotiating(
        self,
    ):
        self.submit_customer_outcome(
            self.deal,
            DealOutcome.Outcome.STILL_DECIDING,
        )

        self.submit_partner_outcome(
            self.deal,
            DealOutcome.Outcome.STILL_DECIDING,
        )

        self.submit_owner_outcome(
            self.deal,
            DealOutcome.Outcome.STILL_DECIDING,
        )

        self.deal.refresh_from_db()
        self.rental_property.refresh_from_db()

        self.assertEqual(
            self.deal.status,
            Deal.Status.NEGOTIATING,
        )

        self.assertTrue(
            self.deal.customer_confirmed,
        )

        self.assertTrue(
            self.deal.partner_confirmed,
        )

        self.assertTrue(
            self.deal.owner_confirmed,
        )

        self.assertEqual(
            self.rental_property.status,
            Property.STATUS_PUBLISHED,
        )

    def test_repeated_submission_is_rejected(self):
        first_response = self.submit_customer_outcome(
            self.deal,
            DealOutcome.Outcome.STILL_DECIDING,
            notes="I need more time.",
        )

        second_response = self.submit_customer_outcome(
            self.deal,
            DealOutcome.Outcome.RENTED,
            notes="I have now accepted the property.",
        )

        self.assertEqual(
            first_response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertEqual(
            second_response.status_code,
            status.HTTP_409_CONFLICT,
        )

        customer_outcomes = DealOutcome.objects.filter(
            deal=self.deal,
            reporter=DealOutcome.Reporter.CUSTOMER,
        )

        self.assertEqual(
            customer_outcomes.count(),
            1,
        )

        saved_outcome = customer_outcomes.get()

        self.assertEqual(
            saved_outcome.outcome,
            DealOutcome.Outcome.STILL_DECIDING,
        )

        self.assertEqual(
            saved_outcome.notes,
            "I need more time.",
        )

    def test_invalid_outcome_is_rejected(self):
        self.client.force_authenticate(
            user=self.customer,
        )

        response = self.client.post(
            self.customer_outcome_url(self.deal),
            {
                "outcome": "invalid_result",
                "notes": "This is not a valid choice.",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn(
            "outcome",
            response.data,
        )

    def test_long_notes_are_rejected(self):
        self.client.force_authenticate(
            user=self.customer,
        )

        response = self.client.post(
            self.customer_outcome_url(self.deal),
            {
                "outcome": DealOutcome.Outcome.RENTED,
                "notes": "x" * 2001,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn(
            "notes",
            response.data,
        )
class DealTimelineTests(DealAPITestBase):

    def timeline_url(self, deal):
        return reverse(
            "deal-timeline",
            kwargs={"pk": deal.pk},
        )

    def test_customer_can_view_own_timeline(self):
        self.client.force_authenticate(
            user=self.customer,
        )

        response = self.client.get(
            self.timeline_url(self.deal),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertIn(
            "deal",
            response.data,
        )

        self.assertIn(
            "timeline",
            response.data,
        )

    def test_customer_cannot_view_other_customer_timeline(self):
        self.client.force_authenticate(
            user=self.customer,
        )

        response = self.client.get(
            self.timeline_url(self.other_deal),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_partner_can_view_assigned_timeline(self):
        self.client.force_authenticate(
            user=self.partner_user,
        )

        response = self.client.get(
            self.timeline_url(self.deal),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

    def test_partner_cannot_view_other_partner_timeline(self):
        self.client.force_authenticate(
            user=self.partner_user,
        )

        response = self.client.get(
            self.timeline_url(self.other_deal),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_staff_can_view_any_timeline(self):
        self.client.force_authenticate(
            user=self.staff_user,
        )

        response = self.client.get(
            self.timeline_url(self.deal),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

class DealCompletionCommissionTests(
    DealAPITestBase
):
    def setUp(self):
        super().setUp()

        now = timezone.now()

        #
        # Governance tier
        #
        self.bronze_tier = PartnerTier.objects.create(
            code="bronze",
            name="Bronze",
            description="Entry level partner.",
            rank=1,
            property_limit=20,
            minimum_completed_deals=0,
            minimum_trust_score=Decimal("0.00"),
            commission_share_rate=Decimal("20.00"),
            active=True,
        )

        PartnerTierAssignment.objects.create(
            partner=self.partner,
            tier=self.bronze_tier,
            assigned_by=self.staff_user,
            reason=(
                "Default Bronze tier for commission "
                "completion test."
            ),
            active=True,
        )

        #
        # Verified property owner
        #
        self.owner = PropertyOwner.objects.create(
            legal_name="Deal Completion Test Owner",
            phone_number="254700000001",
            verification_status=(
                PropertyOwner
                .VerificationStatus
                .VERIFIED
            ),
            verified_by=self.staff_user,
            verified_at=now,
            is_active=True,
            created_by=self.staff_user,
        )

        #
        # Commission agreement
        #
        self.commission_agreement = (
            CommissionAgreement.objects.create(
                property=self.rental_property,
                owner_name=self.owner.legal_name,
                owner_phone_number=(
                    self.owner.phone_number
                ),
                commission_method=(
                    CommissionAgreement
                    .CommissionMethod
                    .FIXED
                ),
                commission_basis=(
                    CommissionAgreement
                    .CommissionBasis
                    .FIRST_MONTH_RENT
                ),
                fixed_commission_amount=(
                    Decimal("10000.00")
                ),
                transaction_value=(
                    Decimal("50000.00")
                ),
                created_by=self.staff_user,
            )
        )

        self.commission_agreement.accept_by_partner(
            user=self.partner_user,
        )
        self.commission_agreement.save()

        self.commission_agreement.verify(
            self.staff_user,
        )
        self.commission_agreement.save()

        self.commission_agreement.lock()
        self.commission_agreement.save()

        #
        # Approved property mandate
        #
        self.mandate = PropertyMandate.objects.create(
            property=self.rental_property,
            owner=self.owner,
            partner=self.partner,
            commission_agreement=(
                self.commission_agreement
            ),
            authorization_method=(
                PropertyMandate
                .AuthorizationMethod
                .VERBAL
            ),
            owner_authority_confirmed=True,
            no_cash_acknowledged=True,
            anti_circumvention_acknowledged=True,
            created_by=self.staff_user,
        )

        self.mandate.declare_by_partner(
            user=self.partner_user,
        )
        self.mandate.save()

        self.mandate.submit_for_review()
        self.mandate.save()

        self.mandate.approve(
            approved_by=self.staff_user,
        )
        self.mandate.save()

        #
        # PIC requires a completed viewing.
        #
        self.viewing.status = Viewing.Status.COMPLETED
        self.viewing.completed_at = now
        self.viewing.save(
            update_fields=[
                "status",
                "completed_at",
                "updated_at",
            ]
        )

        protected_from = now
        protected_until = (
            protected_from
            + timedelta(
                days=self.mandate.protection_period_days,
            )
        )

        self.introduction = (
            ProtectedIntroduction.objects.create(
                customer=self.customer,
                property=self.rental_property,
                partner=self.partner,
                viewing=self.viewing,
                mandate=self.mandate,
                commission_agreement=(
                    self.commission_agreement
                ),
                protected_from=protected_from,
                protected_until=protected_until,
                protection_period_days=(
                    self.mandate.protection_period_days
                ),
                customer_name_snapshot=(
                    self.customer.get_full_name()
                ),
                property_title_snapshot=(
                    self.rental_property.title
                ),
                listing_type_snapshot=(
                    self.rental_property.listing_type
                ),
                property_price_snapshot=(
                    self.rental_property.price
                ),
                owner_name_snapshot=(
                    self.owner.legal_name
                ),
                partner_name_snapshot=(
                    self.partner.display_name
                ),
                mandate_number_snapshot=(
                    self.mandate.mandate_number
                ),
                commission_agreement_number_snapshot=(
                    self.commission_agreement
                    .agreement_number
                ),
                commission_method_snapshot=(
                    self.commission_agreement
                    .commission_method
                ),
                commission_rate_snapshot=(
                    self.commission_agreement
                    .commission_rate
                ),
                fixed_commission_snapshot=(
                    self.commission_agreement
                    .fixed_commission_amount
                ),
                expected_commission_snapshot=(
                    self.commission_agreement
                    .expected_total_commission
                ),
                currency_snapshot=(
                    self.commission_agreement.currency
                ),
                viewing_fee_snapshot=(
                    self.viewing.fee_amount
                ),
                viewing_payment_reference=(
                    self.viewing.payment_reference
                ),
            )
        )

        self.deal.introduction = self.introduction
        self.deal.save(
            update_fields=[
                "introduction",
                "updated_at",
            ]
        )

    def test_agreed_deal_completion_allocates_commission(
        self,
    ):
        #
        # Drive the deal into AGREED through the same immutable
        # three-party outcome records used in production.
        #
        DealOutcome.objects.create(
            deal=self.deal,
            reporter=DealOutcome.Reporter.CUSTOMER,
            outcome=DealOutcome.Outcome.RENTED,
            notes="Customer confirms rental.",
        )

        DealOutcome.objects.create(
            deal=self.deal,
            reporter=DealOutcome.Reporter.PARTNER,
            outcome=DealOutcome.Outcome.RENTED,
            notes="Partner confirms rental.",
        )

        DealOutcome.objects.create(
            deal=self.deal,
            reporter=DealOutcome.Reporter.OWNER,
            outcome=DealOutcome.Outcome.RENTED,
            notes="Owner confirms rental.",
        )

        evaluate_deal_outcomes(
            self.deal.id,
        )

        self.deal.refresh_from_db()

        self.assertEqual(
            self.deal.status,
            Deal.Status.AGREED,
        )

        #
        # Complete the agreed transaction.
        #
        (
            completed_deal,
            commission_settlement,
            settlement_created,
        ) = complete_agreed_deal_and_raise_commission(
            deal_id=self.deal.id,
            actor=self.staff_user,
            notes=(
                "Verified completed transaction."
            ),
        )

        completed_deal.refresh_from_db()
        commission_settlement.refresh_from_db()
        self.rental_property.refresh_from_db()

        self.assertEqual(
            self.rental_property.status,
            Property.STATUS_RENTED,
        )
        self.assertEqual(
            self.rental_property.transaction_completed_at,
            completed_deal.completed_at,
        )
        self.assertEqual(
            self.rental_property.success_broadcast_until,
            completed_deal.completed_at
            + timedelta(
                days=Property.RENT_SUCCESS_BROADCAST_DAYS,
            ),
        )
        self.assertTrue(
            self.rental_property.is_success_broadcast_active,
        )

        broadcast_event = DealEvent.objects.get(
            deal=completed_deal,
            action="property_success_broadcast_started",
        )

        self.assertEqual(
            broadcast_event.metadata["new_property_status"],
            Property.STATUS_RENTED,
        )
        self.assertEqual(
            broadcast_event.metadata["broadcast_days"],
            Property.RENT_SUCCESS_BROADCAST_DAYS,
        )

        self.assertTrue(
            settlement_created,
        )

        self.assertEqual(
            completed_deal.status,
            Deal.Status.COMMISSION_DUE,
        )

        self.assertEqual(
            completed_deal.commission_amount,
            Decimal("10000.00"),
        )

        self.assertEqual(
            commission_settlement.status,
            CommissionSettlement.Status.ALLOCATED,
        )

        self.assertEqual(
            commission_settlement.gross_commission_amount,
            Decimal("10000.00"),
        )

        self.assertEqual(
            commission_settlement.allocated_amount,
            Decimal("10000.00"),
        )

        self.assertEqual(
            commission_settlement.unallocated_amount,
            Decimal("0.00"),
        )

        commission_invoice = (
            CommissionInvoice.objects
            .select_related(
                "deal",
                "settlement",
                "agreement",
                "owner",
                "created_by",
            )
            .get(
                deal=completed_deal,
            )
        )

        self.assertEqual(
            commission_invoice.status,
            CommissionInvoice.Status.PENDING,
        )

        self.assertEqual(
            commission_invoice.settlement_id,
            commission_settlement.id,
        )

        self.assertEqual(
            commission_invoice.agreement_id,
            self.commission_agreement.id,
        )

        self.assertEqual(
            commission_invoice.owner_id,
            self.owner.id,
        )

        self.assertEqual(
            commission_invoice.amount,
            Decimal("10000.00"),
        )

        self.assertEqual(
            commission_invoice.currency,
            "KES",
        )

        self.assertEqual(
            commission_invoice.owner_number_snapshot,
            self.owner.owner_number,
        )

        self.assertEqual(
            commission_invoice.owner_legal_name_snapshot,
            self.owner.legal_name,
        )

        self.assertEqual(
            commission_invoice.owner_phone_number_snapshot,
            self.owner.phone_number,
        )

        self.assertEqual(
            commission_invoice.agreement_number_snapshot,
            self.commission_agreement.agreement_number,
        )

        self.assertEqual(
            commission_invoice.created_by_id,
            self.staff_user.id,
        )

        self.assertTrue(
            commission_invoice.invoice_number.startswith(
                "PH-COM-"
            )
        )

        self.assertTrue(
            DealEvent.objects.filter(
                deal=completed_deal,
                action="commission_invoice_issued",
            ).exists()
        )

        participants = list(
            commission_settlement.participants
            .order_by("id")
        )

        self.assertEqual(
            len(participants),
            2,
        )

        partner_share = next(
            participant
            for participant in participants
            if (
                participant.participant_type
                == CommissionSettlementParticipant
                .ParticipantType
                .LISTING_PARTNER
            )
        )

        platform_share = next(
            participant
            for participant in participants
            if (
                participant.participant_type
                == CommissionSettlementParticipant
                .ParticipantType
                .PATA_HAO
            )
        )

        self.assertEqual(
            partner_share.partner_id,
            self.partner.id,
        )

        self.assertFalse(
            partner_share.is_platform_share,
        )

        self.assertEqual(
            partner_share.amount,
            Decimal("2000.00"),
        )

        self.assertEqual(
            partner_share.percentage_of_total,
            Decimal("20.0000"),
        )

        self.assertTrue(
            platform_share.is_platform_share,
        )

        self.assertEqual(
            platform_share.amount,
            Decimal("8000.00"),
        )

        self.assertEqual(
            platform_share.percentage_of_total,
            Decimal("80.0000"),
        )

class CommissionReceiptEvidenceTests(
    DealCompletionCommissionTests
):

    test_agreed_deal_completion_allocates_commission = None

    def setUp(self):
        super().setUp()

        now = timezone.now()

        Deal.objects.filter(
            pk=self.deal.pk,
        ).update(
            status=Deal.Status.AGREED,
            customer_confirmed=True,
            partner_confirmed=True,
            owner_confirmed=True,
            customer_confirmed_at=now,
            partner_confirmed_at=now,
            owner_confirmed_at=now,
            agreed_at=now,
        )

        self.deal.refresh_from_db()

        (
            self.completed_deal,
            self.commission_settlement,
            _,
        ) = complete_agreed_deal_and_raise_commission(
            deal_id=self.deal.id,
            actor=self.staff_user,
        )

        self.invoice = CommissionInvoice.objects.get(
            deal=self.completed_deal,
        )

    def test_partial_commission_receipt_can_be_recorded(self):
        receipt = CommissionReceipt.objects.create(
            invoice=self.invoice,
            amount=Decimal("4000.00"),
            currency="KES",
            payment_method=(
                CommissionReceipt.PaymentMethod.MPESA
            ),
            payment_reference="COMM-RECEIPT-001",
            received_at=timezone.now(),
            recorded_by=self.staff_user,
        )

        self.assertEqual(
            receipt.amount,
            Decimal("4000.00"),
        )

        self.assertEqual(
            receipt.invoice_id,
            self.invoice.id,
        )

    def test_multiple_receipts_may_equal_invoice_amount(self):
        CommissionReceipt.objects.create(
            invoice=self.invoice,
            amount=Decimal("4000.00"),
            currency="KES",
            payment_method=(
                CommissionReceipt.PaymentMethod.MPESA
            ),
            payment_reference="COMM-RECEIPT-002",
            received_at=timezone.now(),
            recorded_by=self.staff_user,
        )

        CommissionReceipt.objects.create(
            invoice=self.invoice,
            amount=Decimal("6000.00"),
            currency="KES",
            payment_method=(
                CommissionReceipt.PaymentMethod.BANK_TRANSFER
            ),
            payment_reference="COMM-RECEIPT-003",
            received_at=timezone.now(),
            recorded_by=self.staff_user,
        )

        total = (
            self.invoice.receipts.aggregate(
                total=models.Sum("amount")
            )["total"]
        )

        self.assertEqual(
            total,
            Decimal("10000.00"),
        )

    def test_receipts_cannot_exceed_invoice_amount(self):
        CommissionReceipt.objects.create(
            invoice=self.invoice,
            amount=Decimal("9000.00"),
            currency="KES",
            payment_method=(
                CommissionReceipt.PaymentMethod.MPESA
            ),
            payment_reference="COMM-RECEIPT-004",
            received_at=timezone.now(),
            recorded_by=self.staff_user,
        )

        with self.assertRaises(ValidationError):
            CommissionReceipt.objects.create(
                invoice=self.invoice,
                amount=Decimal("1000.01"),
                currency="KES",
                payment_method=(
                    CommissionReceipt.PaymentMethod.MPESA
                ),
                payment_reference="COMM-RECEIPT-005",
                received_at=timezone.now(),
                recorded_by=self.staff_user,
            )

    def test_receipt_currency_must_match_invoice(self):
        with self.assertRaises(ValidationError):
            CommissionReceipt.objects.create(
                invoice=self.invoice,
                amount=Decimal("1000.00"),
                currency="USD",
                payment_method=(
                    CommissionReceipt.PaymentMethod.BANK_TRANSFER
                ),
                payment_reference="COMM-RECEIPT-USD",
                received_at=timezone.now(),
                recorded_by=self.staff_user,
            )

    def test_receipt_evidence_is_immutable(self):
        receipt = CommissionReceipt.objects.create(
            invoice=self.invoice,
            amount=Decimal("1000.00"),
            currency="KES",
            payment_method=(
                CommissionReceipt.PaymentMethod.MPESA
            ),
            payment_reference="COMM-RECEIPT-IMMUTABLE",
            received_at=timezone.now(),
            recorded_by=self.staff_user,
        )

        receipt.amount = Decimal("999.00")

        with self.assertRaises(ValidationError):
            receipt.save()

        receipt.refresh_from_db()

        self.assertEqual(
            receipt.amount,
            Decimal("1000.00"),
        )

    def test_receipt_evidence_cannot_be_deleted(self):
        receipt = CommissionReceipt.objects.create(
            invoice=self.invoice,
            amount=Decimal("1000.00"),
            currency="KES",
            payment_method=(
                CommissionReceipt.PaymentMethod.MPESA
            ),
            payment_reference="COMM-RECEIPT-DELETE",
            received_at=timezone.now(),
            recorded_by=self.staff_user,
        )

        receipt_id = receipt.id

        with self.assertRaises(ValidationError):
            receipt.delete()

        self.assertTrue(
            CommissionReceipt.objects.filter(
                id=receipt_id,
            ).exists()
        )

    def test_cancelled_invoice_cannot_receive_money(self):
        self.invoice.status = (
            CommissionInvoice.Status.CANCELLED
        )
        self.invoice.save()

        with self.assertRaises(ValidationError):
            CommissionReceipt.objects.create(
                invoice=self.invoice,
                amount=Decimal("1000.00"),
                currency="KES",
                payment_method=(
                    CommissionReceipt.PaymentMethod.MPESA
                ),
                payment_reference="COMM-CANCELLED",
                received_at=timezone.now(),
                recorded_by=self.staff_user,
            )

    def test_refunded_invoice_cannot_receive_money(self):
        self.invoice.status = (
            CommissionInvoice.Status.REFUNDED
        )
        self.invoice.save()

        with self.assertRaises(ValidationError):
            CommissionReceipt.objects.create(
                invoice=self.invoice,
                amount=Decimal("1000.00"),
                currency="KES",
                payment_method=(
                    CommissionReceipt.PaymentMethod.MPESA
                ),
                payment_reference="COMM-REFUNDED",
                received_at=timezone.now(),
                recorded_by=self.staff_user,
            )


class CommissionReceiptServiceTests(
    DealCompletionCommissionTests
):

    test_agreed_deal_completion_allocates_commission = None

    def setUp(self):
        super().setUp()

        now = timezone.now()

        Deal.objects.filter(
            pk=self.deal.pk,
        ).update(
            status=Deal.Status.AGREED,
            customer_confirmed=True,
            partner_confirmed=True,
            owner_confirmed=True,
            customer_confirmed_at=now,
            partner_confirmed_at=now,
            owner_confirmed_at=now,
            agreed_at=now,
        )

        self.deal.refresh_from_db()

        (
            self.completed_deal,
            self.commission_settlement,
            _,
        ) = complete_agreed_deal_and_raise_commission(
            deal_id=self.deal.id,
            actor=self.staff_user,
        )

        self.invoice = CommissionInvoice.objects.get(
            deal=self.completed_deal,
        )

    def test_partial_receipt_moves_invoice_to_partially_paid(self):
        receipt, invoice = record_commission_receipt(
            invoice_id=self.invoice.id,
            actor=self.staff_user,
            amount=Decimal("4000.00"),
            payment_method=CommissionReceipt.PaymentMethod.MPESA,
            payment_reference="SERVICE-PARTIAL-001",
        )

        invoice.refresh_from_db()
        self.completed_deal.refresh_from_db()

        self.assertEqual(
            receipt.amount,
            Decimal("4000.00"),
        )

        self.assertEqual(
            invoice.status,
            CommissionInvoice.Status.PARTIALLY_PAID,
        )

        self.assertIsNone(
            invoice.paid_at,
        )

        self.assertEqual(
            self.completed_deal.status,
            Deal.Status.COMMISSION_DUE,
        )

        self.assertTrue(
            DealEvent.objects.filter(
                deal=self.completed_deal,
                action="commission_partially_received",
            ).exists()
        )

    def test_full_receipt_marks_invoice_and_deal_paid(self):
        receipt, invoice = record_commission_receipt(
            invoice_id=self.invoice.id,
            actor=self.staff_user,
            amount=Decimal("10000.00"),
            payment_method=CommissionReceipt.PaymentMethod.BANK_TRANSFER,
            payment_reference="SERVICE-FULL-001",
        )

        invoice.refresh_from_db()
        self.completed_deal.refresh_from_db()

        self.assertEqual(
            invoice.status,
            CommissionInvoice.Status.PAID,
        )

        self.assertIsNotNone(
            invoice.paid_at,
        )

        self.assertEqual(
            invoice.paid_at,
            receipt.received_at,
        )

        self.assertEqual(
            self.completed_deal.status,
            Deal.Status.COMMISSION_PAID,
        )

        self.assertTrue(
            DealEvent.objects.filter(
                deal=self.completed_deal,
                action="commission_paid",
            ).exists()
        )

    def test_two_receipts_can_complete_invoice(self):
        record_commission_receipt(
            invoice_id=self.invoice.id,
            actor=self.staff_user,
            amount=Decimal("4000.00"),
            payment_method=CommissionReceipt.PaymentMethod.MPESA,
            payment_reference="SERVICE-SPLIT-001",
        )

        receipt, invoice = record_commission_receipt(
            invoice_id=self.invoice.id,
            actor=self.staff_user,
            amount=Decimal("6000.00"),
            payment_method=CommissionReceipt.PaymentMethod.BANK_TRANSFER,
            payment_reference="SERVICE-SPLIT-002",
        )

        invoice.refresh_from_db()
        self.completed_deal.refresh_from_db()

        total_received = (
            invoice.receipts.aggregate(
                total=models.Sum("amount")
            )["total"]
        )

        self.assertEqual(
            total_received,
            Decimal("10000.00"),
        )

        self.assertEqual(
            invoice.status,
            CommissionInvoice.Status.PAID,
        )

        self.assertEqual(
            self.completed_deal.status,
            Deal.Status.COMMISSION_PAID,
        )

        self.assertEqual(
            invoice.paid_at,
            receipt.received_at,
        )

    def test_non_staff_cannot_record_commission_receipt(self):
        with self.assertRaises(ValidationError):
            record_commission_receipt(
                invoice_id=self.invoice.id,
                actor=self.customer,
                amount=Decimal("1000.00"),
                payment_method=CommissionReceipt.PaymentMethod.MPESA,
                payment_reference="SERVICE-NONSTAFF",
            )

        self.assertEqual(
            self.invoice.receipts.count(),
            0,
        )

    def test_overpayment_is_rejected_without_extra_receipt(self):
        record_commission_receipt(
            invoice_id=self.invoice.id,
            actor=self.staff_user,
            amount=Decimal("9000.00"),
            payment_method=CommissionReceipt.PaymentMethod.MPESA,
            payment_reference="SERVICE-OVERPAY-001",
        )

        with self.assertRaises(ValidationError):
            record_commission_receipt(
                invoice_id=self.invoice.id,
                actor=self.staff_user,
                amount=Decimal("1000.01"),
                payment_method=CommissionReceipt.PaymentMethod.MPESA,
                payment_reference="SERVICE-OVERPAY-002",
            )

        self.invoice.refresh_from_db()

        self.assertEqual(
            self.invoice.receipts.count(),
            1,
        )

        self.assertEqual(
            self.invoice.status,
            CommissionInvoice.Status.PARTIALLY_PAID,
        )

    def test_full_payment_rolls_back_when_deal_status_is_invalid(self):
        Deal.objects.filter(
            pk=self.completed_deal.pk,
        ).update(
            status=Deal.Status.DISPUTED,
        )

        self.completed_deal.refresh_from_db()

        with self.assertRaises(ValidationError):
            record_commission_receipt(
                invoice_id=self.invoice.id,
                actor=self.staff_user,
                amount=Decimal("10000.00"),
                payment_method=CommissionReceipt.PaymentMethod.BANK_TRANSFER,
                payment_reference="SERVICE-ROLLBACK-001",
            )

        self.invoice.refresh_from_db()

        self.assertEqual(
            self.invoice.status,
            CommissionInvoice.Status.PENDING,
        )

        self.assertIsNone(
            self.invoice.paid_at,
        )

        self.assertEqual(
            self.invoice.receipts.count(),
            0,
        )


class DealFinalClosureServiceTests(
    DealCompletionCommissionTests
):

    test_agreed_deal_completion_allocates_commission = None

    def setUp(self):
        super().setUp()

        now = timezone.now()

        Deal.objects.filter(
            pk=self.deal.pk,
        ).update(
            status=Deal.Status.AGREED,
            customer_confirmed=True,
            partner_confirmed=True,
            owner_confirmed=True,
            customer_confirmed_at=now,
            partner_confirmed_at=now,
            owner_confirmed_at=now,
            agreed_at=now,
        )

        self.deal.refresh_from_db()

        (
            self.completed_deal,
            self.commission_settlement,
            _,
        ) = complete_agreed_deal_and_raise_commission(
            deal_id=self.deal.id,
            actor=self.staff_user,
        )

        self.invoice = CommissionInvoice.objects.get(
            deal=self.completed_deal,
        )

    def pay_invoice_in_full(self):
        record_commission_receipt(
            invoice_id=self.invoice.id,
            actor=self.staff_user,
            amount=self.invoice.amount,
            payment_method=CommissionReceipt.PaymentMethod.MPESA,
            payment_reference="FINAL-CLOSURE-PAID",
        )

        self.invoice.refresh_from_db()
        self.completed_deal.refresh_from_db()

    def complete_commission_settlement(self):
        self.commission_settlement.refresh_from_db()

        if (
            self.commission_settlement.status
            == CommissionSettlement.Status.ALLOCATED
        ):
            approve_commission_settlement(
                settlement_id=self.commission_settlement.id,
                actor=self.staff_user,
            )

        self.commission_settlement.refresh_from_db()

        external_participants = (
            self.commission_settlement.participants
            .filter(
                is_platform_share=False,
            )
            .order_by("id")
        )

        for participant in external_participants:
            pay_commission_participant_outstanding(
                participant_id=participant.id,
                actor=self.staff_user,
                payment_method=(
                    CommissionSettlementPayment
                    .PaymentMethod
                    .MPESA
                ),
                payment_reference=(
                    f"FINAL-CLOSURE-PAYOUT-"
                    f"{participant.id}"
                ),
            )

        self.commission_settlement.refresh_from_db()

        self.assertEqual(
            self.commission_settlement.status,
            CommissionSettlement.Status.PAID,
        )

    def test_commission_paid_deal_can_be_closed(self):
        self.pay_invoice_in_full()
        self.complete_commission_settlement()

        original_completed_at = self.completed_deal.completed_at

        closed_deal = close_commission_paid_deal(
            deal_id=self.completed_deal.id,
            actor=self.staff_user,
        )

        closed_deal.refresh_from_db()

        self.assertEqual(
            closed_deal.status,
            Deal.Status.COMPLETED,
        )

        self.assertIsNotNone(
            closed_deal.closed_at,
        )

        self.assertEqual(
            closed_deal.completed_at,
            original_completed_at,
        )

        self.assertTrue(
            DealEvent.objects.filter(
                deal=closed_deal,
                action="deal_closed",
            ).exists()
        )

    def test_non_staff_cannot_close_deal(self):
        self.pay_invoice_in_full()

        with self.assertRaises(ValidationError):
            close_commission_paid_deal(
                deal_id=self.completed_deal.id,
                actor=self.customer,
            )

        self.completed_deal.refresh_from_db()

        self.assertEqual(
            self.completed_deal.status,
            Deal.Status.COMMISSION_PAID,
        )

        self.assertIsNone(
            self.completed_deal.closed_at,
        )

    def test_unpaid_invoice_deal_cannot_be_closed(self):
        Deal.objects.filter(
            pk=self.completed_deal.pk,
        ).update(
            status=Deal.Status.COMMISSION_PAID,
        )

        self.completed_deal.refresh_from_db()

        with self.assertRaises(ValidationError):
            close_commission_paid_deal(
                deal_id=self.completed_deal.id,
                actor=self.staff_user,
            )

        self.completed_deal.refresh_from_db()

        self.assertEqual(
            self.completed_deal.status,
            Deal.Status.COMMISSION_PAID,
        )

        self.assertIsNone(
            self.completed_deal.closed_at,
        )

    def test_paid_invoice_with_unpaid_settlement_cannot_be_closed(self):
        self.pay_invoice_in_full()

        self.commission_settlement.refresh_from_db()

        self.assertNotEqual(
            self.commission_settlement.status,
            CommissionSettlement.Status.PAID,
        )

        with self.assertRaises(ValidationError):
            close_commission_paid_deal(
                deal_id=self.completed_deal.id,
                actor=self.staff_user,
            )

        self.completed_deal.refresh_from_db()

        self.assertEqual(
            self.completed_deal.status,
            Deal.Status.COMMISSION_PAID,
        )

        self.assertIsNone(
            self.completed_deal.closed_at,
        )

    def test_wrong_status_deal_cannot_be_closed(self):
        with self.assertRaises(ValidationError):
            close_commission_paid_deal(
                deal_id=self.completed_deal.id,
                actor=self.staff_user,
            )

        self.completed_deal.refresh_from_db()

        self.assertEqual(
            self.completed_deal.status,
            Deal.Status.COMMISSION_DUE,
        )

        self.assertIsNone(
            self.completed_deal.closed_at,
        )

    def test_final_closure_preserves_transaction_completion_time(self):
        self.pay_invoice_in_full()
        self.complete_commission_settlement()

        original_completed_at = self.completed_deal.completed_at

        close_commission_paid_deal(
            deal_id=self.completed_deal.id,
            actor=self.staff_user,
        )

        self.completed_deal.refresh_from_db()

        self.assertEqual(
            self.completed_deal.completed_at,
            original_completed_at,
        )

        self.assertIsNotNone(
            self.completed_deal.closed_at,
        )


class DealFinalClosureAPITests(
    DealFinalClosureServiceTests
):

    test_commission_paid_deal_can_be_closed = None
    test_non_staff_cannot_close_deal = None
    test_unpaid_invoice_deal_cannot_be_closed = None
    test_wrong_status_deal_cannot_be_closed = None
    test_final_closure_preserves_transaction_completion_time = None

    def close_url(self):
        return reverse(
            "deal-close-deal",
            kwargs={
                "pk": self.completed_deal.id,
            },
        )

    def test_staff_can_close_commission_paid_deal_via_api(self):
        self.pay_invoice_in_full()
        self.complete_commission_settlement()

        self.client.force_authenticate(
            user=self.staff_user,
        )

        response = self.client.post(
            self.close_url(),
            {
                "notes": "Final administrative closure.",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.completed_deal.refresh_from_db()

        self.assertEqual(
            self.completed_deal.status,
            Deal.Status.COMPLETED,
        )

        self.assertIsNotNone(
            self.completed_deal.closed_at,
        )

        self.assertTrue(
            DealEvent.objects.filter(
                deal=self.completed_deal,
                action="deal_closed",
            ).exists()
        )

    def test_customer_cannot_close_deal_via_api(self):
        self.pay_invoice_in_full()

        self.client.force_authenticate(
            user=self.customer,
        )

        response = self.client.post(
            self.close_url(),
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

        self.completed_deal.refresh_from_db()

        self.assertEqual(
            self.completed_deal.status,
            Deal.Status.COMMISSION_PAID,
        )

    def test_staff_cannot_close_deal_before_commission_paid(self):
        self.client.force_authenticate(
            user=self.staff_user,
        )

        response = self.client.post(
            self.close_url(),
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.completed_deal.refresh_from_db()

        self.assertEqual(
            self.completed_deal.status,
            Deal.Status.COMMISSION_DUE,
        )


class CommissionReceiptAPITests(
    DealCompletionCommissionTests
):

    test_agreed_deal_completion_allocates_commission = None

    def setUp(self):
        super().setUp()

        now = timezone.now()

        Deal.objects.filter(
            pk=self.deal.pk,
        ).update(
            status=Deal.Status.AGREED,
            customer_confirmed=True,
            partner_confirmed=True,
            owner_confirmed=True,
            customer_confirmed_at=now,
            partner_confirmed_at=now,
            owner_confirmed_at=now,
            agreed_at=now,
        )

        self.deal.refresh_from_db()

        (
            self.completed_deal,
            self.commission_settlement,
            _,
        ) = complete_agreed_deal_and_raise_commission(
            deal_id=self.deal.id,
            actor=self.staff_user,
        )

        self.invoice = CommissionInvoice.objects.get(
            deal=self.completed_deal,
        )

        self.receipt_url = (
            f"/api/deals/{self.completed_deal.id}/"
            "record-commission-receipt/"
        )

    def test_staff_can_record_partial_commission_receipt(self):
        self.client.force_authenticate(
            user=self.staff_user,
        )

        response = self.client.post(
            self.receipt_url,
            {
                "amount": "4000.00",
                "payment_method": "mpesa",
                "payment_reference": "API-COMM-001",
                "notes": "Partial owner commission payment.",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.invoice.refresh_from_db()
        self.completed_deal.refresh_from_db()

        self.assertEqual(
            self.invoice.status,
            CommissionInvoice.Status.PARTIALLY_PAID,
        )

        self.assertEqual(
            self.completed_deal.status,
            Deal.Status.COMMISSION_DUE,
        )

        self.assertEqual(
            self.invoice.receipts.count(),
            1,
        )

        self.assertEqual(
            Decimal(
                str(
                    response.data[
                        "invoice"
                    ][
                        "outstanding_amount"
                    ]
                )
            ),
            self.invoice.amount - Decimal("4000.00"),
        )

    def test_full_commission_receipt_marks_deal_commission_paid(self):
        self.client.force_authenticate(
            user=self.staff_user,
        )

        response = self.client.post(
            self.receipt_url,
            {
                "amount": str(self.invoice.amount),
                "payment_method": "bank_transfer",
                "payment_reference": "API-COMM-FULL-001",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.invoice.refresh_from_db()
        self.completed_deal.refresh_from_db()

        self.assertEqual(
            self.invoice.status,
            CommissionInvoice.Status.PAID,
        )

        self.assertEqual(
            self.completed_deal.status,
            Deal.Status.COMMISSION_PAID,
        )

        self.assertIsNotNone(
            self.invoice.paid_at,
        )

        self.assertTrue(
            DealEvent.objects.filter(
                deal=self.completed_deal,
                action="commission_paid",
            ).exists()
        )

    def test_customer_cannot_record_commission_receipt(self):
        self.client.force_authenticate(
            user=self.customer,
        )

        response = self.client.post(
            self.receipt_url,
            {
                "amount": "1000.00",
                "payment_method": "mpesa",
                "payment_reference": "CUSTOMER-NOT-ALLOWED",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

        self.assertEqual(
            self.invoice.receipts.count(),
            0,
        )

    def test_commission_receipt_cannot_overpay_invoice(self):
        self.client.force_authenticate(
            user=self.staff_user,
        )

        response = self.client.post(
            self.receipt_url,
            {
                "amount": str(
                    self.invoice.amount
                    + Decimal("0.01")
                ),
                "payment_method": "mpesa",
                "payment_reference": "API-COMM-OVERPAY",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.invoice.refresh_from_db()

        self.assertEqual(
            self.invoice.receipts.count(),
            0,
        )

        self.assertEqual(
            self.invoice.status,
            CommissionInvoice.Status.PENDING,
        )

    def test_receipt_requires_payment_reference(self):
        self.client.force_authenticate(
            user=self.staff_user,
        )

        response = self.client.post(
            self.receipt_url,
            {
                "amount": "1000.00",
                "payment_method": "mpesa",
                "payment_reference": "",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertEqual(
            self.invoice.receipts.count(),
            0,
        )

    def test_partial_then_final_receipt_completes_invoice(self):
        self.client.force_authenticate(
            user=self.staff_user,
        )

        first_amount = (
            self.invoice.amount
            / Decimal("2")
        ).quantize(
            Decimal("0.01")
        )

        first_response = self.client.post(
            self.receipt_url,
            {
                "amount": str(first_amount),
                "payment_method": "mpesa",
                "payment_reference": "API-COMM-PART-001",
            },
            format="json",
        )

        self.assertEqual(
            first_response.status_code,
            status.HTTP_201_CREATED,
        )

        second_amount = (
            self.invoice.amount
            - first_amount
        )

        second_response = self.client.post(
            self.receipt_url,
            {
                "amount": str(second_amount),
                "payment_method": "bank_transfer",
                "payment_reference": "API-COMM-PART-002",
            },
            format="json",
        )

        self.assertEqual(
            second_response.status_code,
            status.HTTP_201_CREATED,
        )

        self.invoice.refresh_from_db()
        self.completed_deal.refresh_from_db()

        self.assertEqual(
            self.invoice.receipts.count(),
            2,
        )

        self.assertEqual(
            self.invoice.status,
            CommissionInvoice.Status.PAID,
        )

        self.assertEqual(
            self.completed_deal.status,
            Deal.Status.COMMISSION_PAID,
        )


class CommissionInvoiceDealPrivacyTests(
    CommissionReceiptAPITests
):

    test_commission_receipt_cannot_overpay_invoice = None
    test_customer_cannot_record_commission_receipt = None
    test_full_commission_receipt_marks_deal_commission_paid = None
    test_partial_then_final_receipt_completes_invoice = None
    test_receipt_requires_payment_reference = None
    test_staff_can_record_partial_commission_receipt = None

    def test_staff_deal_detail_exposes_commission_invoice(self):
        self.client.force_authenticate(
            user=self.staff_user,
        )

        response = self.client.get(
            f"/api/deals/{self.completed_deal.id}/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertIsNotNone(
            response.data["commission_invoice"],
        )

        self.assertEqual(
            response.data[
                "commission_invoice"
            ][
                "id"
            ],
            self.invoice.id,
        )

    def test_customer_deal_detail_hides_commission_invoice(self):
        self.client.force_authenticate(
            user=self.customer,
        )

        response = self.client.get(
            f"/api/deals/{self.completed_deal.id}/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertIsNone(
            response.data["commission_invoice"],
        )


class MissingCommissionInvoiceRepairTests(
    DealCompletionCommissionTests
):

    test_agreed_deal_completion_allocates_commission = None

    def setUp(self):
        super().setUp()

        now = timezone.now()

        Deal.objects.filter(
            pk=self.deal.pk,
        ).update(
            status=Deal.Status.AGREED,
            customer_confirmed=True,
            partner_confirmed=True,
            owner_confirmed=True,
            customer_confirmed_at=now,
            partner_confirmed_at=now,
            owner_confirmed_at=now,
            agreed_at=now,
        )

        self.deal.refresh_from_db()

        (
            self.completed_deal,
            self.settlement,
            _,
        ) = complete_agreed_deal_and_raise_commission(
            deal_id=self.deal.id,
            actor=self.staff_user,
        )

        CommissionInvoice.objects.filter(
            deal=self.completed_deal,
        ).delete()

        DealEvent.objects.filter(
            deal=self.completed_deal,
            action="commission_invoice_issued",
        ).delete()

    def test_missing_invoice_can_be_restored(self):
        original_completed_at = (
            self.completed_deal.completed_at
        )

        invoice, created = (
            ensure_commission_invoice_for_due_deal(
                deal_id=self.completed_deal.id,
                actor=self.staff_user,
            )
        )

        self.completed_deal.refresh_from_db()

        self.assertTrue(created)

        self.assertEqual(
            invoice.deal_id,
            self.completed_deal.id,
        )

        self.assertEqual(
            invoice.settlement_id,
            self.settlement.id,
        )

        self.assertEqual(
            invoice.amount,
            self.settlement.gross_commission_amount,
        )

        self.assertEqual(
            self.completed_deal.status,
            Deal.Status.COMMISSION_DUE,
        )

        self.assertEqual(
            self.completed_deal.completed_at,
            original_completed_at,
        )

        self.assertTrue(
            DealEvent.objects.filter(
                deal=self.completed_deal,
                action="commission_invoice_issued",
            ).exists()
        )

    def test_invoice_repair_is_idempotent(self):
        first_invoice, first_created = (
            ensure_commission_invoice_for_due_deal(
                deal_id=self.completed_deal.id,
                actor=self.staff_user,
            )
        )

        second_invoice, second_created = (
            ensure_commission_invoice_for_due_deal(
                deal_id=self.completed_deal.id,
                actor=self.staff_user,
            )
        )

        self.assertTrue(first_created)
        self.assertFalse(second_created)

        self.assertEqual(
            first_invoice.id,
            second_invoice.id,
        )

        self.assertEqual(
            CommissionInvoice.objects.filter(
                deal=self.completed_deal,
            ).count(),
            1,
        )


class CustomerCompletedDealHistoryTests(DealAPITestBase):
    def completed_history_url(self):
        return reverse("deal-my-completed")

    def _close_deal(self, deal):
        now = timezone.now()

        Deal.objects.filter(
            pk=deal.pk,
        ).update(
            status=Deal.Status.COMPLETED,
            completed_at=now,
            closed_at=now,
        )

        deal.refresh_from_db()

    def test_customer_sees_only_own_closed_completed_deals(self):
        self._close_deal(self.deal)
        self._close_deal(self.other_deal)

        self.client.force_authenticate(
            user=self.customer,
        )

        response = self.client.get(
            self.completed_history_url(),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        returned_ids = {
            item["id"]
            for item in response.data
        }

        self.assertEqual(
            returned_ids,
            {
                self.deal.id,
            },
        )

        self.assertNotIn(
            self.other_deal.id,
            returned_ids,
        )

    def test_unclosed_or_non_completed_deals_are_excluded(self):
        now = timezone.now()

        Deal.objects.filter(
            pk=self.deal.pk,
        ).update(
            status=Deal.Status.COMPLETED,
            completed_at=now,
            closed_at=None,
        )

        Deal.objects.filter(
            pk=self.sale_deal.pk,
        ).update(
            status=Deal.Status.AGREED,
            completed_at=None,
            closed_at=None,
        )

        self.client.force_authenticate(
            user=self.customer,
        )

        response = self.client.get(
            self.completed_history_url(),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data,
            [],
        )

    def test_customer_history_contains_only_safe_fields(self):
        self._close_deal(self.deal)

        self.client.force_authenticate(
            user=self.customer,
        )

        response = self.client.get(
            self.completed_history_url(),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            len(response.data),
            1,
        )

        item = response.data[0]

        expected_fields = {
            "id",
            "deal_number",
            "property",
            "property_title",
            "deal_type",
            "partner_name",
            "status",
            "completed_at",
            "closed_at",
        }

        self.assertEqual(
            set(item.keys()),
            expected_fields,
        )

        forbidden_fields = {
            "commission_amount",
            "commission_invoice",
            "monthly_rent",
            "sale_price",
            "outcomes",
            "customer_confirmed",
            "partner_confirmed",
            "owner_confirmed",
            "settlement",
            "payments",
            "payouts",
        }

        self.assertTrue(
            forbidden_fields.isdisjoint(item.keys()),
        )

    def test_partner_cannot_access_customer_completed_history(self):
        self._close_deal(self.deal)

        self.client.force_authenticate(
            user=self.partner_user,
        )

        response = self.client.get(
            self.completed_history_url(),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_staff_cannot_access_customer_completed_history(self):
        self._close_deal(self.deal)

        self.client.force_authenticate(
            user=self.staff_user,
        )

        response = self.client.get(
            self.completed_history_url(),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_unauthenticated_user_cannot_access_customer_completed_history(self):
        response = self.client.get(
            self.completed_history_url(),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
