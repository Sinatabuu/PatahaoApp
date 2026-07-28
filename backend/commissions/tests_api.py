from datetime import date, time
from decimal import Decimal
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase

from deals.models import Deal
from partners.models import Partner
from properties.models import Property
from viewings.models import Viewing

from .models import (
    CommissionAgreement,
    CommissionSettlement,
    CommissionSettlementParticipant,
)


User = get_user_model()


class PartnerCommissionAPITestBase(APITestCase):
    """
    Shared records for the partner commission API tests.
    """

    def setUp(self):
        self.admin_user = User.objects.create_user(
            username="commission_admin",
            email="commission.admin@example.com",
            password="TestPassword123!",
            role=User.ROLE_ADMIN,
            is_staff=True,
        )

        self.customer = User.objects.create_user(
            username="commission_customer",
            email="commission.customer@example.com",
            password="TestPassword123!",
            role=User.ROLE_CUSTOMER,
        )

        self.partner_user = User.objects.create_user(
            username="commission_partner",
            email="commission.partner@example.com",
            password="TestPassword123!",
            role=User.ROLE_PARTNER,
        )

        self.other_partner_user = User.objects.create_user(
            username="other_commission_partner",
            email="other.commission.partner@example.com",
            password="TestPassword123!",
            role=User.ROLE_PARTNER,
        )

        self.unapproved_partner_user = User.objects.create_user(
            username="unapproved_commission_partner",
            email="unapproved.commission.partner@example.com",
            password="TestPassword123!",
            role=User.ROLE_PARTNER,
        )

        self.partner = Partner.objects.create(
            user=self.partner_user,
            business_name="Main Commission Partner",
            display_name="Main Partner",
            partner_type=Partner.PARTNER_TYPE_AGENT,
            verification_status=Partner.STATUS_APPROVED,
            is_active=True,
        )

        self.other_partner = Partner.objects.create(
            user=self.other_partner_user,
            business_name="Other Commission Partner",
            display_name="Other Partner",
            partner_type=Partner.PARTNER_TYPE_AGENT,
            verification_status=Partner.STATUS_APPROVED,
            is_active=True,
        )

        self.unapproved_partner = Partner.objects.create(
            user=self.unapproved_partner_user,
            business_name="Unapproved Partner",
            display_name="Unapproved Partner",
            partner_type=Partner.PARTNER_TYPE_AGENT,
            verification_status=Partner.STATUS_PENDING,
            is_active=True,
        )

        self.property = Property.objects.create(
            partner=self.partner,
            title="Commission API Rental",
            property_type=Property.TYPE_APARTMENT,
            listing_type=Property.LISTING_RENT,
            price=Decimal("50000.00"),
            county="Nairobi",
            town="Roysambu",
            estate="Roysambu",
            address="Commission API Test Address",
            bedrooms=2,
            bathrooms=1,
            description="Rental property for partner commission API tests.",
            status=Property.STATUS_RESERVED,
        )

        self.other_property = Property.objects.create(
            partner=self.other_partner,
            title="Other Partner Commission Rental",
            property_type=Property.TYPE_APARTMENT,
            listing_type=Property.LISTING_RENT,
            price=Decimal("40000.00"),
            county="Nairobi",
            town="Kasarani",
            estate="Kasarani",
            address="Other Commission Test Address",
            bedrooms=1,
            bathrooms=1,
            description="Property belonging to another partner.",
            status=Property.STATUS_RESERVED,
        )

        self.viewing = Viewing.objects.create(
            customer=self.customer,
            property=self.property,
            assigned_partner=self.partner,
            requested_date=date(2027, 2, 10),
            requested_time=time(10, 30),
            customer_message="Commission API viewing.",
            status=Viewing.Status.COMPLETED,
        )

        self.other_viewing = Viewing.objects.create(
            customer=self.customer,
            property=self.other_property,
            assigned_partner=self.other_partner,
            requested_date=date(2027, 2, 11),
            requested_time=time(11, 30),
            customer_message="Other commission API viewing.",
            status=Viewing.Status.COMPLETED,
        )

        # Completing a viewing may automatically create its Deal through
        # the project's viewing signal. Use get_or_create so the tests
        # remain safe with or without that signal.
        self.deal, _ = Deal.objects.get_or_create(
            viewing=self.viewing,
            defaults={
                "customer": self.customer,
                "partner": self.partner,
                "property": self.property,
                "monthly_rent": Decimal("50000.00"),
                "status": Deal.Status.CONFIRMED,
                "customer_confirmed": True,
                "partner_confirmed": True,
            },
        )

        self.deal.monthly_rent = Decimal("50000.00")
        self.deal.status = Deal.Status.CONFIRMED
        self.deal.customer_confirmed = True
        self.deal.partner_confirmed = True
        self.deal.save(
            update_fields=[
                "monthly_rent",
                "status",
                "customer_confirmed",
                "partner_confirmed",
                "updated_at",
            ]
        )

        self.other_deal, _ = Deal.objects.get_or_create(
            viewing=self.other_viewing,
            defaults={
                "customer": self.customer,
                "partner": self.other_partner,
                "property": self.other_property,
                "monthly_rent": Decimal("40000.00"),
                "status": Deal.Status.CONFIRMED,
                "customer_confirmed": True,
                "partner_confirmed": True,
            },
        )

        self.other_deal.monthly_rent = Decimal("40000.00")
        self.other_deal.status = Deal.Status.CONFIRMED
        self.other_deal.customer_confirmed = True
        self.other_deal.partner_confirmed = True
        self.other_deal.save(
            update_fields=[
                "monthly_rent",
                "status",
                "customer_confirmed",
                "partner_confirmed",
                "updated_at",
            ]
        )

        self.agreement = CommissionAgreement.objects.create(
            property=self.property,
            owner_name="Commission Property Owner",
            owner_phone_number="+254700000001",
            commission_method=(
                CommissionAgreement.CommissionMethod.PERCENTAGE
            ),
            commission_rate=Decimal("10.000"),
            transaction_value=Decimal("50000.00"),
            status=CommissionAgreement.Status.LOCKED,

            owner_confirmed=True,
            owner_confirmed_at=timezone.now(),

            is_verified=True,
            verified_by=self.admin_user,
            verified_at=timezone.now(),

            is_locked=True,
            locked_at=timezone.now(),

            created_by=self.admin_user,
        )
        
        self.other_agreement = CommissionAgreement.objects.create(
            property=self.other_property,
            owner_name="Other Property Owner",
            owner_phone_number="+254700000002",
            commission_method=(
                CommissionAgreement.CommissionMethod.PERCENTAGE
            ),
            commission_rate=Decimal("10.000"),
            transaction_value=Decimal("40000.00"),
            status=CommissionAgreement.Status.LOCKED,

            owner_confirmed=True,
            owner_confirmed_at=timezone.now(),

            is_verified=True,
            verified_by=self.admin_user,
            verified_at=timezone.now(),

            is_locked=True,
            locked_at=timezone.now(),

            created_by=self.admin_user,
        )


        self.settlement = CommissionSettlement.objects.create(
            deal=self.deal,
            agreement=self.agreement,
            gross_commission_amount=Decimal("5000.00"),
            status=CommissionSettlement.Status.DRAFT,
            created_by=self.admin_user,
        )

        self.other_settlement = CommissionSettlement.objects.create(
            deal=self.other_deal,
            agreement=self.other_agreement,
            gross_commission_amount=Decimal("4000.00"),
            status=CommissionSettlement.Status.DRAFT,
            created_by=self.admin_user,
        )

        self.partner_share = (
            CommissionSettlementParticipant.objects.create(
                settlement=self.settlement,
                participant_type=(
                    CommissionSettlementParticipant
                    .ParticipantType
                    .LISTING_PARTNER
                ),
                partner=self.partner,
                amount=Decimal("3000.00"),
                is_platform_share=False,
            )
        )

        self.platform_share = (
            CommissionSettlementParticipant.objects.create(
                settlement=self.settlement,
                participant_type=(
                    CommissionSettlementParticipant
                    .ParticipantType
                    .PATA_HAO
                ),
                participant_name="Pata Hao",
                amount=Decimal("2000.00"),
                is_platform_share=True,
            )
        )

        self.other_partner_share = (
            CommissionSettlementParticipant.objects.create(
                settlement=self.other_settlement,
                participant_type=(
                    CommissionSettlementParticipant
                    .ParticipantType
                    .LISTING_PARTNER
                ),
                partner=self.other_partner,
                amount=Decimal("2500.00"),
                is_platform_share=False,
            )
        )

        self.other_platform_share = (
            CommissionSettlementParticipant.objects.create(
                settlement=self.other_settlement,
                participant_type=(
                    CommissionSettlementParticipant
                    .ParticipantType
                    .PATA_HAO
                ),
                participant_name="Pata Hao",
                amount=Decimal("1500.00"),
                is_platform_share=True,
            )
        )

        # Approve only after both settlements are fully allocated.
        self.settlement.refresh_from_db()
        self.settlement.approve(
            approved_by=self.admin_user,
        )
        self.settlement.save()

        self.other_settlement.refresh_from_db()
        self.other_settlement.approve(
            approved_by=self.admin_user,
        )
        self.other_settlement.save()

        # The second fixture represents a fully paid commission.
        self.other_settlement.status = (
            CommissionSettlement.Status.PAID
        )
        self.other_settlement.save()


    def settlement_list_url(self):
        return reverse(
            "partner-commission-settlement-list"
        )

    def settlement_detail_url(self, settlement):
        return reverse(
            "partner-commission-settlement-detail",
            kwargs={
                "pk": settlement.pk,
            },
        )

    def summary_url(self):
        return reverse(
            "partner-commission-summary"
        )


class PartnerCommissionAccessTests(
    PartnerCommissionAPITestBase
):

    def test_unauthenticated_user_cannot_list_settlements(self):
        response = self.client.get(
            self.settlement_list_url(),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_customer_cannot_access_partner_commissions(self):
        self.client.force_authenticate(
            user=self.customer,
        )

        response = self.client.get(
            self.settlement_list_url(),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_staff_cannot_access_partner_commission_endpoint(self):
        self.client.force_authenticate(
            user=self.admin_user,
        )

        response = self.client.get(
            self.settlement_list_url(),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_unapproved_partner_cannot_access_commissions(self):
        self.client.force_authenticate(
            user=self.unapproved_partner_user,
        )

        response = self.client.get(
            self.settlement_list_url(),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_approved_partner_can_access_commissions(self):
        self.client.force_authenticate(
            user=self.partner_user,
        )

        response = self.client.get(
            self.settlement_list_url(),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )


class PartnerCommissionIsolationTests(
    PartnerCommissionAPITestBase
):

    def test_partner_sees_only_their_own_settlement(self):
        self.client.force_authenticate(
            user=self.partner_user,
        )

        response = self.client.get(
            self.settlement_list_url(),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        settlement_ids = {
            item["id"]
            for item in response.data
        }

        self.assertEqual(
            settlement_ids,
            {
                self.settlement.id,
            },
        )

        self.assertNotIn(
            self.other_settlement.id,
            settlement_ids,
        )

    def test_partner_cannot_retrieve_other_partner_settlement(self):
        self.client.force_authenticate(
            user=self.partner_user,
        )

        response = self.client.get(
            self.settlement_detail_url(
                self.other_settlement
            ),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_platform_share_does_not_grant_partner_access(self):
        """
        Platform participation alone must not expose a settlement to an
        unrelated partner.
        """

        self.client.force_authenticate(
            user=self.partner_user,
        )

        response = self.client.get(
            self.settlement_detail_url(
                self.other_settlement
            ),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )


class PartnerCommissionSerializationTests(
    PartnerCommissionAPITestBase
):

    def test_settlement_detail_contains_partner_share(self):
        self.client.force_authenticate(
            user=self.partner_user,
        )

        response = self.client.get(
            self.settlement_detail_url(
                self.settlement
            ),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            Decimal(response.data["my_share"]),
            Decimal("3000.00"),
        )

        self.assertEqual(
            response.data["my_participant_type"],
            self.partner_share.participant_type,
        )

        self.assertEqual(
            response.data["agreement_number"],
            self.agreement.agreement_number,
        )

        self.assertEqual(
            response.data["property_title"],
            self.property.title,
        )

    def test_settlement_endpoint_is_read_only(self):
        self.client.force_authenticate(
            user=self.partner_user,
        )

        response = self.client.post(
            self.settlement_list_url(),
            {
                "gross_commission_amount": "999999.00",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def test_partner_cannot_update_settlement(self):
        self.client.force_authenticate(
            user=self.partner_user,
        )

        response = self.client.patch(
            self.settlement_detail_url(
                self.settlement
            ),
            {
                "status": CommissionSettlement.Status.PAID,
                "gross_commission_amount": "999999.00",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )

        self.settlement.refresh_from_db()

        self.assertEqual(
            self.settlement.status,
            CommissionSettlement.Status.APPROVED,
        )

        self.assertEqual(
            self.settlement.gross_commission_amount,
            Decimal("5000.00"),
        )


class PartnerCommissionSummaryTests(
    PartnerCommissionAPITestBase
):

    def test_partner_summary_contains_only_partner_amounts(self):
        self.client.force_authenticate(
            user=self.partner_user,
        )

        response = self.client.get(
            self.summary_url(),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            Decimal(response.data["total_commission"]),
            Decimal("3000.00"),
        )

        self.assertEqual(
            Decimal(response.data["approved_commission"]),
            Decimal("3000.00"),
        )

        self.assertEqual(
            Decimal(response.data["paid_commission"]),
            Decimal("0.00"),
        )

        self.assertEqual(
            response.data["settlement_count"],
            1,
        )

    def test_other_partner_summary_is_isolated(self):
        self.client.force_authenticate(
            user=self.other_partner_user,
        )

        response = self.client.get(
            self.summary_url(),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            Decimal(response.data["total_commission"]),
            Decimal("2500.00"),
        )

        self.assertEqual(
            Decimal(response.data["paid_commission"]),
            Decimal("2500.00"),
        )

        self.assertEqual(
            Decimal(response.data["approved_commission"]),
            Decimal("0.00"),
        )

        self.assertEqual(
            response.data["settlement_count"],
            1,
        )

    def test_platform_amount_is_not_in_partner_summary(self):
        self.client.force_authenticate(
            user=self.partner_user,
        )

        response = self.client.get(
            self.summary_url(),
        )

        self.assertNotEqual(
            Decimal(response.data["total_commission"]),
            self.settlement.gross_commission_amount,
        )

        self.assertEqual(
            Decimal(response.data["total_commission"]),
            self.partner_share.amount,
        )

    def test_customer_cannot_access_commission_summary(self):
        self.client.force_authenticate(
            user=self.customer,
        )

        response = self.client.get(
            self.summary_url(),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )