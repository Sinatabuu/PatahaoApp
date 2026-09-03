from datetime import date, time
from decimal import Decimal
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase

from deals.models import Deal
from partners.models import Partner
from properties.models import Property
from viewings.models import Viewing

from .services import (
    approve_commission_settlement,
    pay_commission_participant_outstanding,
    record_commission_payment,
)

from .models import (
    CommissionAgreement,
    CommissionSettlement,
    CommissionSettlementParticipant,
    CommissionSettlementPayment,
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
                "status": Deal.Status.COMMISSION_DUE,
                "customer_confirmed": True,
                "partner_confirmed": True,
            },
        )

        self.deal.monthly_rent = Decimal("50000.00")
        self.deal.status = Deal.Status.COMMISSION_DUE
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
                "status": Deal.Status.COMMISSION_DUE,
                "customer_confirmed": True,
                "partner_confirmed": True,
            },
        )

        self.other_deal.monthly_rent = Decimal("40000.00")
        self.other_deal.status = Deal.Status.COMMISSION_DUE
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
            created_by=self.admin_user,
        )

        self.agreement.accept_by_partner(
            user=self.partner_user,
        )
        self.agreement.save()

        self.agreement.verify(
            self.admin_user,
        )
        self.agreement.save()

        self.agreement.lock()
        self.agreement.save()
        
        self.other_agreement = CommissionAgreement.objects.create(
            property=self.other_property,
            owner_name="Other Property Owner",
            owner_phone_number="+254700000002",
            commission_method=(
                CommissionAgreement.CommissionMethod.PERCENTAGE
            ),
            commission_rate=Decimal("10.000"),
            transaction_value=Decimal("40000.00"),
            created_by=self.admin_user,
        )

        self.other_agreement.accept_by_partner(
            user=self.other_partner_user,
        )
        self.other_agreement.save()

        self.other_agreement.verify(
            self.admin_user,
        )
        self.other_agreement.save()

        self.other_agreement.lock()
        self.other_agreement.save()

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


    def test_approved_settlement_allocation_cannot_be_changed(self):
        self.partner_share.amount = Decimal("2999.00")

        with self.assertRaises(ValidationError):
            self.partner_share.save()

        self.partner_share.refresh_from_db()

        self.assertEqual(
            self.partner_share.amount,
            Decimal("3000.00"),
        )

    def test_approved_settlement_allocation_cannot_be_deleted(self):
        participant_id = self.partner_share.pk

        with self.assertRaises(ValidationError):
            self.partner_share.delete()

        self.assertTrue(
            CommissionSettlementParticipant.objects.filter(
                pk=participant_id,
            ).exists()
        )

    def test_approved_settlement_cannot_receive_new_allocation(self):
        with self.assertRaises(ValidationError):
            CommissionSettlementParticipant.objects.create(
                settlement=self.settlement,
                participant_type=(
                    CommissionSettlementParticipant
                    .ParticipantType
                    .OTHER
                ),
                participant_name="Late participant",
                amount=Decimal("1.00"),
                is_platform_share=False,
            )


    def test_approved_settlement_allows_paid_status_transition(self):
        self.settlement.status = CommissionSettlement.Status.PAID
        self.settlement.save()

        self.settlement.refresh_from_db()

        self.assertEqual(
            self.settlement.status,
            CommissionSettlement.Status.PAID,
        )

    def test_approved_settlement_gross_commission_cannot_change(self):
        original_amount = self.settlement.gross_commission_amount

        self.settlement.gross_commission_amount = Decimal("4999.00")

        with self.assertRaises(ValidationError):
            self.settlement.save()

        self.settlement.refresh_from_db()

        self.assertEqual(
            self.settlement.gross_commission_amount,
            original_amount,
        )

    def test_approved_settlement_currency_cannot_change(self):
        self.settlement.currency = "USD"

        with self.assertRaises(ValidationError):
            self.settlement.save()

        self.settlement.refresh_from_db()

        self.assertEqual(
            self.settlement.currency,
            "KES",
        )

    def test_approved_settlement_approval_evidence_cannot_change(self):
        original_approved_at = self.settlement.approved_at

        self.settlement.approved_at = timezone.now()

        with self.assertRaises(ValidationError):
            self.settlement.save()

        self.settlement.refresh_from_db()

        self.assertEqual(
            self.settlement.approved_at,
            original_approved_at,
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

class CommissionSettlementPaymentEvidenceTests(
    PartnerCommissionAPITestBase
):

    def test_payment_can_be_recorded_against_approved_allocation(self):
        payment = CommissionSettlementPayment.objects.create(
            participant=self.partner_share,
            amount=Decimal("1000.00"),
            currency="KES",
            payment_method=(
                CommissionSettlementPayment
                .PaymentMethod
                .MPESA
            ),
            payment_reference="MPESA-COMM-001",
            paid_at=timezone.now(),
            recorded_by=self.admin_user,
        )

        self.assertEqual(
            payment.amount,
            Decimal("1000.00"),
        )

        self.assertEqual(
            payment.participant,
            self.partner_share,
        )

    def test_payment_cannot_exceed_participant_allocation(self):
        with self.assertRaises(ValidationError):
            CommissionSettlementPayment.objects.create(
                participant=self.partner_share,
                amount=Decimal("3000.01"),
                currency="KES",
                payment_method=(
                    CommissionSettlementPayment
                    .PaymentMethod
                    .MPESA
                ),
                payment_reference="MPESA-TOO-MUCH",
                paid_at=timezone.now(),
                recorded_by=self.admin_user,
            )

    def test_multiple_payments_cannot_exceed_allocation(self):
        CommissionSettlementPayment.objects.create(
            participant=self.partner_share,
            amount=Decimal("2000.00"),
            currency="KES",
            payment_method=(
                CommissionSettlementPayment
                .PaymentMethod
                .MPESA
            ),
            payment_reference="MPESA-PART-001",
            paid_at=timezone.now(),
            recorded_by=self.admin_user,
        )

        with self.assertRaises(ValidationError):
            CommissionSettlementPayment.objects.create(
                participant=self.partner_share,
                amount=Decimal("1000.01"),
                currency="KES",
                payment_method=(
                    CommissionSettlementPayment
                    .PaymentMethod
                    .MPESA
                ),
                payment_reference="MPESA-PART-002",
                paid_at=timezone.now(),
                recorded_by=self.admin_user,
            )

    def test_payment_evidence_cannot_be_changed(self):
        payment = CommissionSettlementPayment.objects.create(
            participant=self.partner_share,
            amount=Decimal("1000.00"),
            currency="KES",
            payment_method=(
                CommissionSettlementPayment
                .PaymentMethod
                .BANK_TRANSFER
            ),
            payment_reference="BANK-COMM-001",
            paid_at=timezone.now(),
            recorded_by=self.admin_user,
        )

        payment.amount = Decimal("999.00")

        with self.assertRaises(ValidationError):
            payment.save()

        payment.refresh_from_db()

        self.assertEqual(
            payment.amount,
            Decimal("1000.00"),
        )

    def test_payment_evidence_cannot_be_deleted(self):
        payment = CommissionSettlementPayment.objects.create(
            participant=self.partner_share,
            amount=Decimal("1000.00"),
            currency="KES",
            payment_method=(
                CommissionSettlementPayment
                .PaymentMethod
                .MPESA
            ),
            payment_reference="MPESA-COMM-DELETE",
            paid_at=timezone.now(),
            recorded_by=self.admin_user,
        )

        payment_id = payment.pk

        with self.assertRaises(ValidationError):
            payment.delete()

        self.assertTrue(
            CommissionSettlementPayment.objects.filter(
                pk=payment_id,
            ).exists()
        )

    def test_payment_currency_must_match_settlement(self):
        with self.assertRaises(ValidationError):
            CommissionSettlementPayment.objects.create(
                participant=self.partner_share,
                amount=Decimal("1000.00"),
                currency="USD",
                payment_method=(
                    CommissionSettlementPayment
                    .PaymentMethod
                    .BANK_TRANSFER
                ),
                payment_reference="BANK-USD-001",
                paid_at=timezone.now(),
                recorded_by=self.admin_user,
            )

    def test_payment_cannot_be_recorded_before_approval(self):
        self.settlement.status = (
            CommissionSettlement.Status.ALLOCATED
        )
        self.settlement.save()

        with self.assertRaises(ValidationError):
            CommissionSettlementPayment.objects.create(
                participant=self.partner_share,
                amount=Decimal("1000.00"),
                currency="KES",
                payment_method=(
                    CommissionSettlementPayment
                    .PaymentMethod
                    .MPESA
                ),
                payment_reference="MPESA-NOT-APPROVED",
                paid_at=timezone.now(),
                recorded_by=self.admin_user,
            )


class CommissionSettlementPaymentServiceTests(
    PartnerCommissionAPITestBase
):

    def test_partial_partner_payout_moves_settlement_to_partially_paid(self):
        payment, settlement = record_commission_payment(
            participant_id=self.partner_share.id,
            actor=self.admin_user,
            amount=Decimal("1000.00"),
            payment_method=(
                CommissionSettlementPayment
                .PaymentMethod
                .MPESA
            ),
            payment_reference="PAYOUT-PARTIAL-001",
        )

        settlement.refresh_from_db()

        self.assertEqual(
            payment.amount,
            Decimal("1000.00"),
        )

        self.assertEqual(
            settlement.status,
            CommissionSettlement.Status.PARTIALLY_PAID,
        )

    def test_full_partner_payout_marks_settlement_paid(self):
        payment, settlement = record_commission_payment(
            participant_id=self.partner_share.id,
            actor=self.admin_user,
            amount=Decimal("3000.00"),
            payment_method=(
                CommissionSettlementPayment
                .PaymentMethod
                .BANK_TRANSFER
            ),
            payment_reference="PAYOUT-FULL-001",
        )

        settlement.refresh_from_db()

        self.assertEqual(
            payment.amount,
            Decimal("3000.00"),
        )

        self.assertEqual(
            settlement.status,
            CommissionSettlement.Status.PAID,
        )

    def test_two_partner_payouts_can_complete_settlement(self):
        record_commission_payment(
            participant_id=self.partner_share.id,
            actor=self.admin_user,
            amount=Decimal("1000.00"),
            payment_method=(
                CommissionSettlementPayment
                .PaymentMethod
                .MPESA
            ),
            payment_reference="PAYOUT-SPLIT-001",
        )

        _, settlement = record_commission_payment(
            participant_id=self.partner_share.id,
            actor=self.admin_user,
            amount=Decimal("2000.00"),
            payment_method=(
                CommissionSettlementPayment
                .PaymentMethod
                .BANK_TRANSFER
            ),
            payment_reference="PAYOUT-SPLIT-002",
        )

        settlement.refresh_from_db()

        self.assertEqual(
            self.partner_share.payments.count(),
            2,
        )

        self.assertEqual(
            settlement.status,
            CommissionSettlement.Status.PAID,
        )

    def test_platform_share_cannot_be_paid_out(self):
        with self.assertRaises(ValidationError):
            record_commission_payment(
                participant_id=self.platform_share.id,
                actor=self.admin_user,
                amount=Decimal("1000.00"),
                payment_method=(
                    CommissionSettlementPayment
                    .PaymentMethod
                    .BANK_TRANSFER
                ),
                payment_reference="PAYOUT-PLATFORM-001",
            )

        self.assertEqual(
            self.platform_share.payments.count(),
            0,
        )

    def test_non_staff_cannot_record_partner_payout(self):
        with self.assertRaises(ValidationError):
            record_commission_payment(
                participant_id=self.partner_share.id,
                actor=self.customer,
                amount=Decimal("1000.00"),
                payment_method=(
                    CommissionSettlementPayment
                    .PaymentMethod
                    .MPESA
                ),
                payment_reference="PAYOUT-NONSTAFF-001",
            )

        self.assertEqual(
            self.partner_share.payments.count(),
            0,
        )

    def test_overpayment_is_rejected_without_extra_payment(self):
        record_commission_payment(
            participant_id=self.partner_share.id,
            actor=self.admin_user,
            amount=Decimal("2500.00"),
            payment_method=(
                CommissionSettlementPayment
                .PaymentMethod
                .MPESA
            ),
            payment_reference="PAYOUT-OVER-001",
        )

        with self.assertRaises(ValidationError):
            record_commission_payment(
                participant_id=self.partner_share.id,
                actor=self.admin_user,
                amount=Decimal("500.01"),
                payment_method=(
                    CommissionSettlementPayment
                    .PaymentMethod
                    .MPESA
                ),
                payment_reference="PAYOUT-OVER-002",
            )

        self.settlement.refresh_from_db()

        self.assertEqual(
            self.partner_share.payments.count(),
            1,
        )

        self.assertEqual(
            self.settlement.status,
            CommissionSettlement.Status.PARTIALLY_PAID,
        )

    def test_payment_cannot_be_recorded_against_closed_settlement(self):
        self.settlement.status = (
            CommissionSettlement.Status.PAID
        )
        self.settlement.save()

        with self.assertRaises(ValidationError):
            record_commission_payment(
                participant_id=self.partner_share.id,
                actor=self.admin_user,
                amount=Decimal("1000.00"),
                payment_method=(
                    CommissionSettlementPayment
                    .PaymentMethod
                    .MPESA
                ),
                payment_reference="PAYOUT-CLOSED-001",
            )

        self.assertEqual(
            self.partner_share.payments.count(),
            0,
        )


class PartnerCommissionPayoutPrivacyTests(
    PartnerCommissionAPITestBase
):

    def test_partner_detail_exposes_only_own_payout_information(self):
        CommissionSettlementPayment.objects.create(
            participant=self.partner_share,
            amount=Decimal("1000.00"),
            currency="KES",
            payment_method=(
                CommissionSettlementPayment
                .PaymentMethod
                .MPESA
            ),
            payment_reference="PARTNER-PRIVATE-001",
            paid_at=timezone.now(),
            recorded_by=self.admin_user,
        )

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
            Decimal(response.data["my_paid_amount"]),
            Decimal("1000.00"),
        )

        self.assertEqual(
            Decimal(response.data["my_outstanding_amount"]),
            Decimal("2000.00"),
        )

        self.assertEqual(
            response.data["my_payment_status"],
            "partially_paid",
        )

        self.assertEqual(
            len(response.data["my_payments"]),
            1,
        )

        self.assertEqual(
            response.data["my_payments"][0]["payment_reference"],
            "PARTNER-PRIVATE-001",
        )

        self.assertNotIn(
            "participants",
            response.data,
        )

        response_text = str(response.data)

        self.assertNotIn(
            "Pata Hao Platform",
            response_text,
        )

    def test_partner_cannot_see_other_partners_payout_history(self):
        self.other_settlement.status = (
            CommissionSettlement.Status.APPROVED
        )
        self.other_settlement.save()

        CommissionSettlementPayment.objects.create(
            participant=self.other_partner_share,
            amount=Decimal("500.00"),
            currency="KES",
            payment_method=(
                CommissionSettlementPayment
                .PaymentMethod
                .MPESA
            ),
            payment_reference="OTHER-PARTNER-PRIVATE-001",
            paid_at=timezone.now(),
            recorded_by=self.admin_user,
        )

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

        response_text = str(response.data)

        self.assertNotIn(
            "OTHER-PARTNER-PRIVATE-001",
            response_text,
        )


class PartnerCommissionSummaryEvidenceTests(
    PartnerCommissionAPITestBase
):

    def test_summary_reports_paid_to_date_and_outstanding_amount(self):
        CommissionSettlementPayment.objects.create(
            participant=self.partner_share,
            amount=Decimal("1000.00"),
            currency="KES",
            payment_method=(
                CommissionSettlementPayment
                .PaymentMethod
                .MPESA
            ),
            payment_reference="SUMMARY-PAID-001",
            paid_at=timezone.now(),
            recorded_by=self.admin_user,
        )

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
            Decimal(response.data["paid_to_date"]),
            Decimal("1000.00"),
        )

        self.assertEqual(
            Decimal(response.data["outstanding_commission"]),
            Decimal("2000.00"),
        )

    def test_summary_payment_evidence_is_partner_isolated(self):
        self.other_settlement.status = (
            CommissionSettlement.Status.APPROVED
        )
        self.other_settlement.save()

        CommissionSettlementPayment.objects.create(
            participant=self.other_partner_share,
            amount=Decimal("500.00"),
            currency="KES",
            payment_method=(
                CommissionSettlementPayment
                .PaymentMethod
                .MPESA
            ),
            payment_reference="SUMMARY-OTHER-001",
            paid_at=timezone.now(),
            recorded_by=self.admin_user,
        )

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
            Decimal(response.data["paid_to_date"]),
            Decimal("0.00"),
        )

        self.assertEqual(
            Decimal(response.data["outstanding_commission"]),
            Decimal("3000.00"),
        )


class BackendDerivedCommissionPayoutTests(
    PartnerCommissionAPITestBase
):

    def test_backend_derives_full_outstanding_partner_payout(self):
        payment, settlement = (
            pay_commission_participant_outstanding(
                participant_id=self.partner_share.id,
                actor=self.admin_user,
                payment_method=(
                    CommissionSettlementPayment
                    .PaymentMethod
                    .MPESA
                ),
                payment_reference="AUTO-PAYOUT-FULL-001",
            )
        )

        settlement.refresh_from_db()

        self.assertEqual(
            payment.amount,
            self.partner_share.amount,
        )

        self.assertEqual(
            payment.amount,
            Decimal("3000.00"),
        )

        self.assertEqual(
            settlement.status,
            CommissionSettlement.Status.PAID,
        )

    def test_backend_derives_remaining_amount_after_partial_evidence(self):
        record_commission_payment(
            participant_id=self.partner_share.id,
            actor=self.admin_user,
            amount=Decimal("1000.00"),
            payment_method=(
                CommissionSettlementPayment
                .PaymentMethod
                .MPESA
            ),
            payment_reference="HISTORICAL-PARTIAL-001",
        )

        payment, settlement = (
            pay_commission_participant_outstanding(
                participant_id=self.partner_share.id,
                actor=self.admin_user,
                payment_method=(
                    CommissionSettlementPayment
                    .PaymentMethod
                    .BANK_TRANSFER
                ),
                payment_reference="AUTO-REMAINDER-001",
            )
        )

        settlement.refresh_from_db()

        self.assertEqual(
            payment.amount,
            Decimal("2000.00"),
        )

        total_paid = sum(
            (
                item.amount
                for item in self.partner_share.payments.all()
            ),
            Decimal("0.00"),
        )

        self.assertEqual(
            total_paid,
            Decimal("3000.00"),
        )

        self.assertEqual(
            settlement.status,
            CommissionSettlement.Status.PAID,
        )

    def test_fully_paid_participant_cannot_be_paid_twice(self):
        first_payment, settlement = (
            pay_commission_participant_outstanding(
                participant_id=self.partner_share.id,
                actor=self.admin_user,
                payment_method=(
                    CommissionSettlementPayment
                    .PaymentMethod
                    .MPESA
                ),
                payment_reference="AUTO-ONCE-001",
            )
        )

        self.assertEqual(
            first_payment.amount,
            Decimal("3000.00"),
        )

        self.assertEqual(
            settlement.status,
            CommissionSettlement.Status.PAID,
        )

        with self.assertRaises(ValidationError):
            pay_commission_participant_outstanding(
                participant_id=self.partner_share.id,
                actor=self.admin_user,
                payment_method=(
                    CommissionSettlementPayment
                    .PaymentMethod
                    .MPESA
                ),
                payment_reference="AUTO-TWICE-001",
            )

        self.assertEqual(
            self.partner_share.payments.count(),
            1,
        )

    def test_platform_retained_revenue_cannot_be_paid_out(self):
        with self.assertRaises(ValidationError):
            pay_commission_participant_outstanding(
                participant_id=self.platform_share.id,
                actor=self.admin_user,
                payment_method=(
                    CommissionSettlementPayment
                    .PaymentMethod
                    .BANK_TRANSFER
                ),
                payment_reference="AUTO-PLATFORM-001",
            )

        self.assertEqual(
            self.platform_share.payments.count(),
            0,
        )


class StaffBackendDerivedCommissionPayoutAPITests(
    PartnerCommissionAPITestBase
):

    def payout_url(self, participant):
        return (
            "/api/admin/commission-participants/"
            f"{participant.id}/payout/"
        )

    def test_staff_can_authorize_backend_derived_payout(self):
        self.client.force_authenticate(
            user=self.admin_user,
        )

        response = self.client.post(
            self.payout_url(
                self.partner_share,
            ),
            {
                "payment_method": "mpesa",
                "payment_reference": "API-AUTO-PAYOUT-001",
                "notes": "Authorized partner payout.",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertEqual(
            response.data["payment"]["amount"],
            "3000.00",
        )

        self.assertEqual(
            response.data["payment"]["participant_id"],
            self.partner_share.id,
        )

        self.settlement.refresh_from_db()

        self.assertEqual(
            self.settlement.status,
            CommissionSettlement.Status.PAID,
        )

    def test_client_cannot_supply_payout_amount(self):
        self.client.force_authenticate(
            user=self.admin_user,
        )

        response = self.client.post(
            self.payout_url(
                self.partner_share,
            ),
            {
                "amount": "1.00",
                "payment_method": "mpesa",
                "payment_reference": "API-MANIPULATE-001",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn(
            "amount",
            response.data,
        )

        self.assertEqual(
            self.partner_share.payments.count(),
            0,
        )

    def test_non_staff_cannot_authorize_payout(self):
        self.client.force_authenticate(
            user=self.customer,
        )

        response = self.client.post(
            self.payout_url(
                self.partner_share,
            ),
            {
                "payment_method": "mpesa",
                "payment_reference": "API-NONSTAFF-001",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

        self.assertEqual(
            self.partner_share.payments.count(),
            0,
        )

    def test_platform_share_cannot_be_paid_through_api(self):
        self.client.force_authenticate(
            user=self.admin_user,
        )

        response = self.client.post(
            self.payout_url(
                self.platform_share,
            ),
            {
                "payment_method": "bank_transfer",
                "payment_reference": "API-PLATFORM-001",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertEqual(
            self.platform_share.payments.count(),
            0,
        )

    def test_payment_reference_is_required(self):
        self.client.force_authenticate(
            user=self.admin_user,
        )

        response = self.client.post(
            self.payout_url(
                self.partner_share,
            ),
            {
                "payment_method": "mpesa",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertEqual(
            self.partner_share.payments.count(),
            0,
        )


class StaffCommissionSettlementDetailAPITests(
    PartnerCommissionAPITestBase
):

    def detail_url(self):
        return (
            "/api/admin/deals/"
            f"{self.settlement.deal_id}/"
            "commission-settlement/"
        )

    def test_staff_can_read_backend_settlement_accounting(self):
        self.client.force_authenticate(
            user=self.admin_user,
        )

        response = self.client.get(
            self.detail_url(),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["id"],
            self.settlement.id,
        )

        self.assertEqual(
            str(
                response.data[
                    "gross_commission_amount"
                ]
            ),
            str(self.settlement.gross_commission_amount),
        )

        participants = response.data[
            "participants"
        ]

        self.assertEqual(
            len(participants),
            2,
        )

        partner = next(
            item
            for item in participants
            if not item["is_platform_share"]
        )

        platform = next(
            item
            for item in participants
            if item["is_platform_share"]
        )

        self.assertEqual(
            str(partner["amount"]),
            str(self.partner_share.amount),
        )

        self.assertEqual(
            str(partner["paid_amount"]),
            "0.00",
        )

        self.assertEqual(
            str(
                partner[
                    "outstanding_amount"
                ]
            ),
            str(self.partner_share.amount),
        )

        self.assertEqual(
            partner["payment_status"],
            "unpaid",
        )

        self.assertEqual(
            str(platform["amount"]),
            str(self.platform_share.amount),
        )

    def test_partner_cannot_read_staff_settlement_accounting(self):
        self.client.force_authenticate(
            user=self.partner_user,
        )

        response = self.client.get(
            self.detail_url(),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_customer_cannot_read_staff_settlement_accounting(self):
        self.client.force_authenticate(
            user=self.customer,
        )

        response = self.client.get(
            self.detail_url(),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )


class BackendCommissionSettlementApprovalTests(
    PartnerCommissionAPITestBase
):

    def setUp(self):
        super().setUp()

        # The shared fixture deliberately creates an already-approved
        # settlement. These approval tests need the immediately preceding
        # ALLOCATED state.
        #
        # Use queryset.update() only to prepare the isolated test fixture;
        # production code must never rewind approved financial evidence.
        CommissionSettlement.objects.filter(
            pk=self.settlement.pk,
        ).update(
            status=CommissionSettlement.Status.ALLOCATED,
            approved_by=None,
            approved_at=None,
        )

        self.settlement.refresh_from_db()

    def test_staff_can_approve_fully_allocated_settlement(self):
        settlement, created = (
            approve_commission_settlement(
                settlement_id=self.settlement.id,
                actor=self.admin_user,
            )
        )

        settlement.refresh_from_db()

        self.assertTrue(created)

        self.assertEqual(
            settlement.status,
            CommissionSettlement.Status.APPROVED,
        )

        self.assertEqual(
            settlement.approved_by_id,
            self.admin_user.id,
        )

        self.assertIsNotNone(
            settlement.approved_at,
        )

    def test_approval_is_idempotent(self):
        first, first_created = (
            approve_commission_settlement(
                settlement_id=self.settlement.id,
                actor=self.admin_user,
            )
        )

        second, second_created = (
            approve_commission_settlement(
                settlement_id=self.settlement.id,
                actor=self.admin_user,
            )
        )

        self.assertTrue(first_created)
        self.assertFalse(second_created)

        self.assertEqual(
            first.id,
            second.id,
        )

    def test_non_staff_cannot_approve_settlement(self):
        with self.assertRaises(ValidationError):
            approve_commission_settlement(
                settlement_id=self.settlement.id,
                actor=self.customer,
            )

    def test_non_allocated_settlement_cannot_be_approved(self):
        self.settlement.status = (
            CommissionSettlement.Status.ALLOCATION_PENDING
        )
        self.settlement.save()

        with self.assertRaises(ValidationError):
            approve_commission_settlement(
                settlement_id=self.settlement.id,
                actor=self.admin_user,
            )


class StaffCommissionSettlementApprovalAPITests(
    PartnerCommissionAPITestBase
):

    def setUp(self):
        super().setUp()

        # Shared fixture is already approved. Rewind only the isolated
        # test record so this class can exercise the approval endpoint.
        CommissionSettlement.objects.filter(
            pk=self.settlement.pk,
        ).update(
            status=CommissionSettlement.Status.ALLOCATED,
            approved_by=None,
            approved_at=None,
        )

        self.settlement.refresh_from_db()

        self.url = (
            f"/api/admin/commission-settlements/"
            f"{self.settlement.id}/approve/"
        )

    def test_staff_can_approve_settlement_without_financial_input(self):
        self.client.force_authenticate(
            user=self.admin_user,
        )

        response = self.client.post(
            self.url,
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.settlement.refresh_from_db()

        self.assertEqual(
            self.settlement.status,
            CommissionSettlement.Status.APPROVED,
        )

        self.assertEqual(
            self.settlement.approved_by_id,
            self.admin_user.id,
        )

        self.assertIsNotNone(
            self.settlement.approved_at,
        )

        self.assertTrue(
            response.data["approved"],
        )

    def test_non_staff_cannot_approve_settlement(self):
        self.client.force_authenticate(
            user=self.customer,
        )

        response = self.client.post(
            self.url,
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

        self.settlement.refresh_from_db()

        self.assertEqual(
            self.settlement.status,
            CommissionSettlement.Status.ALLOCATED,
        )

    def test_approval_rejects_financial_input(self):
        self.client.force_authenticate(
            user=self.admin_user,
        )

        response = self.client.post(
            self.url,
            {
                "amount": "1.00",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.settlement.refresh_from_db()

        self.assertEqual(
            self.settlement.status,
            CommissionSettlement.Status.ALLOCATED,
        )

    def test_repeated_approval_is_idempotent(self):
        self.client.force_authenticate(
            user=self.admin_user,
        )

        first = self.client.post(
            self.url,
            {},
            format="json",
        )

        self.assertEqual(
            first.status_code,
            status.HTTP_200_OK,
        )

        self.assertTrue(
            first.data["approved"],
        )

        second = self.client.post(
            self.url,
            {},
            format="json",
        )

        self.assertEqual(
            second.status_code,
            status.HTTP_200_OK,
        )

        self.assertFalse(
            second.data["approved"],
        )

        self.settlement.refresh_from_db()

        self.assertEqual(
            self.settlement.status,
            CommissionSettlement.Status.APPROVED,
        )


class StaffCommissionReportAPITests(
    PartnerCommissionAPITestBase
):

    def report_url(self):
        return "/api/admin/commission-report/"

    def test_staff_can_read_commission_report(self):
        self.client.force_authenticate(
            user=self.admin_user,
        )

        response = self.client.get(
            self.report_url(),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertIn(
            "gross_commission",
            response.data,
        )

        self.assertIn(
            "pata_hao_retained_revenue",
            response.data,
        )

        self.assertIn(
            "external_payouts",
            response.data,
        )

        self.assertIn(
            "outstanding_payouts",
            response.data,
        )

        self.assertIn(
            "recent_deals",
            response.data,
        )

    def test_non_staff_cannot_read_commission_report(self):
        self.client.force_authenticate(
            user=self.customer,
        )

        response = self.client.get(
            self.report_url(),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_platform_share_is_reported_as_retained_revenue(self):
        self.client.force_authenticate(
            user=self.admin_user,
        )

        response = self.client.get(
            self.report_url(),
            {
                "closed_only": "false",
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        expected_platform_share = sum(
            (
                participant.amount
                for participant in
                CommissionSettlementParticipant.objects.filter(
                    is_platform_share=True,
                    settlement__status__in=[
                        CommissionSettlement.Status.APPROVED,
                        CommissionSettlement.Status.PARTIALLY_PAID,
                        CommissionSettlement.Status.PAID,
                    ],
                )
            ),
            Decimal("0.00"),
        )

        self.assertEqual(
            Decimal(
                response.data[
                    "pata_hao_retained_revenue"
                ]
            ),
            expected_platform_share,
        )

    def test_external_payouts_come_from_payment_evidence(self):
        self.client.force_authenticate(
            user=self.admin_user,
        )

        response = self.client.get(
            self.report_url(),
            {
                "closed_only": "false",
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        expected_paid = sum(
            (
                payment.amount
                for payment in
                CommissionSettlementPayment.objects.filter(
                    participant__is_platform_share=False,
                    participant__settlement__status__in=[
                        CommissionSettlement.Status.APPROVED,
                        CommissionSettlement.Status.PARTIALLY_PAID,
                        CommissionSettlement.Status.PAID,
                    ],
                )
            ),
            Decimal("0.00"),
        )

        self.assertEqual(
            Decimal(
                response.data[
                    "external_payouts"
                ]
            ),
            expected_paid,
        )


class StaffCommissionReportAuditQueryTests(
    PartnerCommissionAPITestBase
):

    url = "/api/admin/commission-report/"

    def setUp(self):
        super().setUp()

        self.client.force_authenticate(
            user=self.admin_user,
        )

    def test_report_exposes_pagination_metadata(self):
        response = self.client.get(
            self.url,
            {
                "page": 1,
                "page_size": 25,
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["page"],
            1,
        )

        self.assertEqual(
            response.data["page_size"],
            25,
        )

        self.assertIn(
            "count",
            response.data,
        )

        self.assertIn(
            "total_pages",
            response.data,
        )

        self.assertIn(
            "has_next",
            response.data,
        )

        self.assertIn(
            "has_previous",
            response.data,
        )

    def test_page_size_is_capped_at_100(self):
        response = self.client.get(
            self.url,
            {
                "page_size": 5000,
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["page_size"],
            100,
        )

    def test_invalid_closed_date_is_rejected(self):
        response = self.client.get(
            self.url,
            {
                "closed_from": "not-a-date",
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_invalid_payout_state_is_rejected(self):
        response = self.client.get(
            self.url,
            {
                "payout_state": "mystery",
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_search_returns_filtered_result_set(self):
        settlement = self.settlement

        response = self.client.get(
            self.url,
            {
                "search": settlement.deal.deal_number,
                "closed_only": "false",
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertGreaterEqual(
            response.data["count"],
            1,
        )

        ids = {
            item["deal_id"]
            for item in response.data[
                "recent_deals"
            ]
        }

        self.assertIn(
            settlement.deal_id,
            ids,
        )

    def test_non_matching_search_returns_zero_results(self):
        response = self.client.get(
            self.url,
            {
                "search": (
                    "THIS-DEAL-CANNOT-POSSIBLY-EXIST-"
                    "A982EC"
                ),
                "closed_only": "false",
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["count"],
            0,
        )

        self.assertEqual(
            response.data["recent_deals"],
            [],
        )


class PartnerTransactionHistoryAPITests(
    PartnerCommissionAPITestBase
):
    """
    Security and financial-integrity tests for the
    partner transaction history endpoint.
    """

    def transaction_history_url(self):
        return reverse(
            "partner-transaction-history"
        )

    def test_partner_can_read_own_transaction_history(self):
        self.client.force_authenticate(
            user=self.partner_user,
        )

        response = self.client.get(
            self.transaction_history_url()
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertIn(
            "results",
            response.data,
        )

        self.assertIn(
            "count",
            response.data,
        )

    def test_customer_cannot_read_partner_transaction_history(self):
        self.client.force_authenticate(
            user=self.customer,
        )

        response = self.client.get(
            self.transaction_history_url()
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_partner_history_never_exposes_platform_share(self):
        self.client.force_authenticate(
            user=self.partner_user,
        )

        response = self.client.get(
            self.transaction_history_url()
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        forbidden_fields = {
            "pata_hao_retained_revenue",
            "platform_share",
            "platform_amount",
            "gross_commission",
            "external_allocations",
        }

        for item in response.data["results"]:
            self.assertTrue(
                forbidden_fields.isdisjoint(
                    item.keys()
                )
            )

    def test_partner_history_has_pagination_metadata(self):
        self.client.force_authenticate(
            user=self.partner_user,
        )

        response = self.client.get(
            self.transaction_history_url(),
            {
                "page": 1,
                "page_size": 25,
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        for field in (
            "count",
            "page",
            "page_size",
            "total_pages",
            "has_next",
            "has_previous",
            "results",
        ):
            self.assertIn(
                field,
                response.data,
            )

        self.assertEqual(
            response.data["page"],
            1,
        )

        self.assertEqual(
            response.data["page_size"],
            25,
        )


class PartnerTransactionHistoryIsolationTests(
    PartnerCommissionAPITestBase
):

    def test_other_partner_cannot_see_another_partners_transaction(self):
        User = get_user_model()

        other_partner_user = User.objects.create_user(
            username="other_history_partner",
            email="other.history.partner@example.com",
            password="TestPassword123!",
            role=User.ROLE_PARTNER,
        )

        other_partner = Partner.objects.create(
            user=other_partner_user,
            display_name="Other History Partner",
            business_name="Other History Partner",
            verification_status=Partner.STATUS_APPROVED,
            is_active=True,
        )

        self.client.force_authenticate(
            user=other_partner_user,
        )

        response = self.client.get(
            reverse(
                "partner-transaction-history"
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        deal_ids = {
            item["deal_id"]
            for item in response.data["results"]
        }

        self.assertNotIn(
            self.settlement.deal_id,
            deal_ids,
        )

        self.assertEqual(
            response.data["count"],
            0,
        )
