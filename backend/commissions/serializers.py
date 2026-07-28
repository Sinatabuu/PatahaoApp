from decimal import Decimal

from rest_framework import serializers

from .models import (
    CommissionAgreement,
    CommissionSettlement,
    CommissionSettlementParticipant,
)


class PartnerCommissionAgreementSerializer(
    serializers.ModelSerializer
):
    property_title = serializers.CharField(
        source="property.title",
        read_only=True,
    )

    commission_method_label = serializers.CharField(
        source="get_commission_method_display",
        read_only=True,
    )

    status_label = serializers.CharField(
        source="get_status_display",
        read_only=True,
    )

    class Meta:
        model = CommissionAgreement

        fields = [
            "id",
            "agreement_number",

            "property",
            "property_title",

            "commission_method",
            "commission_method_label",

            "commission_rate",
            "fixed_commission_amount",
            "transaction_value",
            "expected_total_commission",
            "currency",

            "status",
            "status_label",

            "owner_confirmed",
            "owner_confirmed_at",

            "is_verified",
            "verified_at",

            "is_locked",
            "locked_at",

            "created_at",
            "updated_at",
        ]

        read_only_fields = fields

class PartnerCommissionParticipantSerializer(
    serializers.ModelSerializer
):
    partner_name = serializers.SerializerMethodField()

    participant_type_label = serializers.CharField(
        source="get_commission_method_display",
        read_only=True,
    )

    class Meta:
        model = CommissionSettlementParticipant

        fields = [
            "id",
            "partner",
            "partner_name",
            "participant_type",
            "participant_type_label",
            "amount",
            "percentage_of_total",
            "is_platform_share",
            "created_at",
            "updated_at",
        ]

        read_only_fields = fields

    def get_partner_name(self, participant):
        partner = participant.partner

        if partner is None:
            return "Pata Hao Platform"

        if partner.display_name:
            return partner.display_name

        if partner.business_name:
            return partner.business_name

        full_name = partner.user.get_full_name().strip()

        return (
            full_name
            or getattr(partner.user, "full_name", "")
            or partner.user.email
            or partner.user.username
        )


class PartnerCommissionSettlementSerializer(
    serializers.ModelSerializer
):
    deal_status = serializers.CharField(
        source="deal.status",
        read_only=True,
    )

    property_title = serializers.CharField(
        source="deal.property.title",
        read_only=True,
    )

    customer_name = serializers.SerializerMethodField()

    agreement_number = serializers.CharField(
        source="agreement.agreement_number",
        read_only=True,
    )

    status_label = serializers.CharField(
        source="get_status_display",
        read_only=True,
    )

    my_share = serializers.SerializerMethodField()

    my_percentage = serializers.SerializerMethodField()

    my_participant_type = serializers.SerializerMethodField()

    agreement = PartnerCommissionAgreementSerializer(
        read_only=True,
    )

    participants = PartnerCommissionParticipantSerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = CommissionSettlement

        fields = [
            "id",
            "deal",
            "deal_status",
            "property_title",
            "customer_name",

            "agreement",
            "agreement_number",

            "gross_commission_amount",
            "allocated_amount",
            "unallocated_amount",

            "my_share",
            "my_percentage",
            "my_participant_type",

            "status",
            "status_label",

            "participants",

            "approved_at",
            "created_at",
            "updated_at",
        ]

        read_only_fields = fields

    def _get_partner_participation(self, settlement):
        request = self.context.get("request")

        if request is None:
            return None

        partner = getattr(
            request.user,
            "partner_profile",
            None,
        )

        if partner is None:
            return None

        for participant in settlement.participants.all():
            if participant.partner_id == partner.id:
                return participant

        return None

    def get_customer_name(self, settlement):
        customer = settlement.deal.customer

        full_name = customer.get_full_name().strip()

        return (
            full_name
            or getattr(customer, "full_name", "")
            or customer.email
            or customer.username
        )

    def get_my_share(self, settlement):
        participant = self._get_partner_participation(
            settlement,
        )

        if participant is None:
            return Decimal("0.00")

        return participant.amount

    def get_my_percentage(self, settlement):
        participant = self._get_partner_participation(
            settlement,
        )

        if participant is None:
            return Decimal("0.00")

        return participant.percentage_of_total

    def get_my_participant_type(self, settlement):
        participant = self._get_partner_participation(
            settlement,
        )

        if participant is None:
            return None

        return participant.participant_type
