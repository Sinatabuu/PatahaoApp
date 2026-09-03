from decimal import Decimal

from rest_framework import serializers

from .models import (
    CommissionAgreement,
    CommissionSettlement,
    CommissionSettlementParticipant,
    CommissionSettlementPayment,
)


class PartnerCommissionAgreementSerializer(serializers.ModelSerializer):
    property_title = serializers.CharField(
        source="property.title",
        read_only=True,
    )

    commission_method_label = serializers.CharField(
        source="get_commission_method_display",
        read_only=True,
    )

    commission_basis_label = serializers.CharField(
        source="get_commission_basis_display",
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
            "owner_name",
            "owner_phone_number",
            "commission_method",
            "commission_method_label",
            "commission_basis",
            "commission_basis_label",
            "commission_rate",
            "fixed_commission_amount",
            "transaction_value",
            "expected_total_commission",
            "currency",
            "partner_accepted",
            "partner_accepted_at",
            "accepted_by",
            "status",
            "status_label",
            "is_verified",
            "verified_at",
            "is_locked",
            "locked_at",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "agreement_number",
            "property_title",
            "commission_method_label",
            "commission_basis_label",
            "expected_total_commission",
            "currency",
            "partner_accepted",
            "partner_accepted_at",
            "accepted_by",
            "status",
            "status_label",
            "is_verified",
            "verified_at",
            "is_locked",
            "locked_at",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        instance = getattr(self, "instance", None)

        if instance is not None and (
            instance.partner_accepted
            or instance.is_verified
            or instance.is_locked
        ):
            editable_fields = {
                "owner_name",
                "owner_phone_number",
                "commission_method",
                "commission_basis",
                "commission_rate",
                "fixed_commission_amount",
                "transaction_value",
                "property",
            }

            if any(field in attrs for field in editable_fields):
                raise serializers.ValidationError(
                    "Commission terms cannot be changed after partner acceptance."
                )

        commission_method = attrs.get(
            "commission_method",
            getattr(instance, "commission_method", None),
        )

        commission_basis = attrs.get(
            "commission_basis",
            getattr(instance, "commission_basis", None),
        )

        commission_rate = attrs.get(
            "commission_rate",
            getattr(instance, "commission_rate", None),
        )

        fixed_amount = attrs.get(
            "fixed_commission_amount",
            getattr(instance, "fixed_commission_amount", None),
        )

        transaction_value = attrs.get(
            "transaction_value",
            getattr(instance, "transaction_value", None),
        )

        if (
            transaction_value is None
            or transaction_value <= Decimal("0.00")
        ):
            raise serializers.ValidationError(
                {
                    "transaction_value": (
                        "The transaction value must be greater than zero."
                    )
                }
            )

        if commission_method == CommissionAgreement.CommissionMethod.PERCENTAGE:
            if commission_rate is None:
                raise serializers.ValidationError(
                    {
                        "commission_rate": (
                            "A commission rate is required "
                            "for a percentage agreement."
                        )
                    }
                )

            if fixed_amount is not None:
                raise serializers.ValidationError(
                    {
                        "fixed_commission_amount": (
                            "Do not enter a fixed amount for "
                            "a percentage agreement."
                        )
                    }
                )

        if commission_method == CommissionAgreement.CommissionMethod.FIXED:
            if fixed_amount is None:
                raise serializers.ValidationError(
                    {
                        "fixed_commission_amount": (
                            "A fixed commission amount is required "
                            "for a fixed agreement."
                        )
                    }
                )

            if commission_rate is not None:
                raise serializers.ValidationError(
                    {
                        "commission_rate": (
                            "Do not enter a commission rate "
                            "for a fixed agreement."
                        )
                    }
                )

        if commission_basis is None:
            raise serializers.ValidationError(
                {
                    "commission_basis": (
                        "A commission basis is required."
                    )
                }
            )

        return attrs


class PartnerCommissionParticipantSerializer(serializers.ModelSerializer):
    partner_name = serializers.SerializerMethodField()

    participant_type_label = serializers.CharField(
        source="get_participant_type_display",
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


class PartnerCommissionPaymentSerializer(serializers.ModelSerializer):
    payment_method_label = serializers.CharField(
        source="get_payment_method_display",
        read_only=True,
    )

    class Meta:
        model = CommissionSettlementPayment
        fields = [
            "id",
            "amount",
            "currency",
            "payment_method",
            "payment_method_label",
            "payment_reference",
            "paid_at",
            "notes",
            "created_at",
        ]

        read_only_fields = fields


class PartnerCommissionSettlementSerializer(serializers.ModelSerializer):
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
    my_paid_amount = serializers.SerializerMethodField()
    my_outstanding_amount = serializers.SerializerMethodField()
    my_payment_status = serializers.SerializerMethodField()
    my_payments = serializers.SerializerMethodField()

    agreement = PartnerCommissionAgreementSerializer(
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
            "my_paid_amount",
            "my_outstanding_amount",
            "my_payment_status",
            "my_payments",
            "status",
            "status_label",
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
        participant = self._get_partner_participation(settlement)

        if participant is None:
            return Decimal("0.00")

        return participant.amount

    def get_my_percentage(self, settlement):
        participant = self._get_partner_participation(settlement)

        if participant is None:
            return Decimal("0.00")

        return participant.percentage_of_total

    def get_my_participant_type(self, settlement):
        participant = self._get_partner_participation(settlement)

        if participant is None:
            return None

        return participant.participant_type

    def _get_my_payments(self, settlement):
        participant = self._get_partner_participation(settlement)

        if participant is None:
            return []

        return list(
            participant.payments.all()
        )

    def get_my_paid_amount(self, settlement):
        payments = self._get_my_payments(settlement)

        return sum(
            (
                payment.amount
                for payment in payments
            ),
            Decimal("0.00"),
        )

    def get_my_outstanding_amount(self, settlement):
        participant = self._get_partner_participation(settlement)

        if participant is None:
            return Decimal("0.00")

        paid = self.get_my_paid_amount(settlement)

        return (
            participant.amount - paid
        ).quantize(
            Decimal("0.01")
        )

    def get_my_payment_status(self, settlement):
        participant = self._get_partner_participation(settlement)

        if participant is None:
            return None

        paid = self.get_my_paid_amount(settlement)

        if paid <= Decimal("0.00"):
            return "unpaid"

        if paid < participant.amount:
            return "partially_paid"

        return "paid"

    def get_my_payments(self, settlement):
        payments = self._get_my_payments(settlement)

        return PartnerCommissionPaymentSerializer(
            payments,
            many=True,
            context=self.context,
        ).data


class StaffCommissionPayoutSerializer(serializers.Serializer):
    """
    Evidence supplied by staff when authorizing a participant payout.

    The payout amount is deliberately absent. It is calculated by the
    backend from the participant's approved allocation minus immutable
    payment evidence already recorded.
    """

    payment_method = serializers.ChoiceField(
        choices=CommissionSettlementPayment.PaymentMethod.choices,
    )

    payment_reference = serializers.CharField(
        max_length=150,
        trim_whitespace=True,
    )

    paid_at = serializers.DateTimeField(
        required=False,
        allow_null=True,
    )

    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=2000,
        trim_whitespace=True,
    )

    def validate(self, attrs):
        if "amount" in self.initial_data:
            raise serializers.ValidationError(
                {
                    "amount": (
                        "Payout amount is calculated by Pata Hao "
                        "and cannot be supplied by the client."
                    )
                }
            )

        return attrs

    def validate_payment_reference(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Payment reference is required."
            )

        return value


class StaffCommissionSettlementParticipantSerializer(
    serializers.ModelSerializer
):
    participant_type_label = serializers.CharField(
        source="get_participant_type_display",
        read_only=True,
    )
    recipient_name = serializers.SerializerMethodField()
    paid_amount = serializers.SerializerMethodField()
    outstanding_amount = serializers.SerializerMethodField()
    payment_status = serializers.SerializerMethodField()
    payments = serializers.SerializerMethodField()

    class Meta:
        model = CommissionSettlementParticipant
        fields = [
            "id",
            "participant_type",
            "participant_type_label",
            "recipient_name",
            "is_platform_share",
            "amount",
            "percentage_of_total",
            "paid_amount",
            "outstanding_amount",
            "payment_status",
            "payments",
        ]

        read_only_fields = fields

    def get_recipient_name(self, participant):
        if participant.is_platform_share:
            return "Pata Hao"

        if participant.partner_id:
            partner = participant.partner

            return (
                partner.display_name
                or partner.business_name
                or partner.user.get_full_name()
                or partner.user.email
            )

        return (
            participant.participant_name
            or participant.get_participant_type_display()
        )

    def _payments(self, participant):
        return list(participant.payments.all())

    def get_paid_amount(self, participant):
        return sum(
            (
                payment.amount
                for payment in self._payments(participant)
            ),
            Decimal("0.00"),
        )

    def get_outstanding_amount(self, participant):
        paid = self.get_paid_amount(participant)

        outstanding = participant.amount - paid

        return max(
            outstanding,
            Decimal("0.00"),
        )

    def get_payment_status(self, participant):
        paid = self.get_paid_amount(participant)

        if paid <= Decimal("0.00"):
            return "unpaid"

        if paid < participant.amount:
            return "partially_paid"

        return "paid"

    def get_payments(self, participant):
        return [
            {
                "id": payment.id,
                "amount": payment.amount,
                "currency": payment.currency,
                "payment_method": payment.payment_method,
                "payment_reference": payment.payment_reference,
                "paid_at": payment.paid_at,
                "notes": payment.notes,
                "created_at": payment.created_at,
            }
            for payment in self._payments(participant)
        ]


class StaffCommissionSettlementSerializer(
    serializers.ModelSerializer
):
    deal_number = serializers.CharField(
        source="deal.deal_number",
        read_only=True,
    )
    property_title = serializers.CharField(
        source="deal.property.title",
        read_only=True,
    )
    status_label = serializers.CharField(
        source="get_status_display",
        read_only=True,
    )
    participants = (
        StaffCommissionSettlementParticipantSerializer(
            many=True,
            read_only=True,
        )
    )

    class Meta:
        model = CommissionSettlement
        fields = [
            "id",
            "deal",
            "deal_number",
            "property_title",
            "gross_commission_amount",
            "allocated_amount",
            "unallocated_amount",
            "currency",
            "status",
            "status_label",
            "approved_at",
            "participants",
            "created_at",
            "updated_at",
        ]

        read_only_fields = fields
