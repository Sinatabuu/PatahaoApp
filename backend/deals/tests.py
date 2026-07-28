from datetime import date, time
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase

from partners.models import Partner
from properties.models import Property
from viewings.models import Viewing

from .models import Deal, DealOutcome


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
            status=Property.STATUS_PUBLISHED,
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
            status=Property.STATUS_PUBLISHED,
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
            status=Property.STATUS_PUBLISHED,
        )

        self.viewing = Viewing.objects.create(
            customer=self.customer,
            property=self.rental_property,
            assigned_partner=self.partner,
            requested_date=date(2027, 1, 15),
            requested_time=time(10, 30),
            customer_message="Rental deal API test.",
            status=Viewing.Status.CONFIRMED,
        )

        self.sale_viewing = Viewing.objects.create(
            customer=self.customer,
            property=self.sale_property,
            assigned_partner=self.partner,
            requested_date=date(2027, 1, 16),
            requested_time=time(11, 30),
            customer_message="Sale deal API test.",
            status=Viewing.Status.CONFIRMED,
        )

        self.other_viewing = Viewing.objects.create(
            customer=self.other_customer,
            property=self.other_property,
            assigned_partner=self.other_partner,
            requested_date=date(2027, 1, 17),
            requested_time=time(12, 30),
            customer_message="Other customer's viewing.",
            status=Viewing.Status.CONFIRMED,
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
            Deal.Status.PENDING_CONFIRMATION,
        )

        self.assertFalse(
            self.deal.customer_confirmed,
        )

        self.assertFalse(
            self.deal.partner_confirmed,
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
            Deal.Status.CONFIRMED,
        )

        self.assertTrue(
            self.deal.customer_confirmed,
        )

        self.assertTrue(
            self.deal.partner_confirmed,
        )

        self.assertEqual(
            self.rental_property.status,
            Property.STATUS_RESERVED,
        )

    def test_matching_purchase_outcomes_confirm_sale_deal(self):
        self.submit_customer_outcome(
            self.sale_deal,
            DealOutcome.Outcome.PURCHASED,
        )

        response = self.submit_partner_outcome(
            self.sale_deal,
            DealOutcome.Outcome.PURCHASED,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.sale_deal.refresh_from_db()
        self.sale_property.refresh_from_db()

        self.assertEqual(
            self.sale_deal.status,
            Deal.Status.CONFIRMED,
        )

        self.assertTrue(
            self.sale_deal.customer_confirmed,
        )

        self.assertTrue(
            self.sale_deal.partner_confirmed,
        )

        self.assertEqual(
            self.sale_property.status,
            Property.STATUS_RESERVED,
        )

    def test_conflicting_outcomes_mark_deal_disputed(self):
        self.submit_customer_outcome(
            self.deal,
            DealOutcome.Outcome.RENTED,
        )

        response = self.submit_partner_outcome(
            self.deal,
            DealOutcome.Outcome.DECLINED,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.deal.refresh_from_db()

        self.assertEqual(
            self.deal.status,
            Deal.Status.DISPUTED,
        )

        self.assertFalse(
            self.deal.customer_confirmed,
        )

        self.assertFalse(
            self.deal.partner_confirmed,
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

        self.deal.refresh_from_db()

        self.assertEqual(
            self.deal.status,
            Deal.Status.DISPUTED,
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

        self.deal.refresh_from_db()

        self.assertEqual(
            self.deal.status,
            Deal.Status.CANCELLED,
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

        self.deal.refresh_from_db()

        self.assertEqual(
            self.deal.status,
            Deal.Status.CANCELLED,
        )

    def test_matching_still_deciding_outcomes_keep_deal_pending(self):
        self.submit_customer_outcome(
            self.deal,
            DealOutcome.Outcome.STILL_DECIDING,
        )

        self.submit_partner_outcome(
            self.deal,
            DealOutcome.Outcome.STILL_DECIDING,
        )

        self.deal.refresh_from_db()

        self.assertEqual(
            self.deal.status,
            Deal.Status.PENDING_CONFIRMATION,
        )

    def test_repeated_submission_updates_existing_outcome(self):
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
            status.HTTP_200_OK,
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
            DealOutcome.Outcome.RENTED,
        )

        self.assertEqual(
            saved_outcome.notes,
            "I have now accepted the property.",
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