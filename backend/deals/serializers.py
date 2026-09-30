from rest_framework import serializers

from .models import (
    CommissionInvoice,
    Deal,
    DealOutcome,
)
from .services import get_owner_confirmation_status


class DealOutcomeSerializer(serializers.ModelSerializer):
    reporter_label = serializers.CharField(
        source="get_reporter_display",
        read_only=True,
    )

    outcome_label = serializers.CharField(
        source="get_outcome_display",
        read_only=True,
    )

    class Meta:
        model = DealOutcome
        fields = [
            "id",
            "reporter",
            "reporter_label",
            "outcome",
            "outcome_label",
            "notes",
            "created_at",
        ]

        read_only_fields = fields


class DealOutcomeSubmissionSerializer(serializers.ModelSerializer):
    """
    Validates an outcome submitted by either the customer or partner.

    The deal and reporter are assigned by the API. They cannot be selected
    by the person submitting the outcome.
    """

    class Meta:
        model = DealOutcome
        fields = [
            "outcome",
            "notes",
        ]

    def validate_notes(self, value):
        value = value.strip()

        if len(value) > 2000:
            raise serializers.ValidationError(
                "Notes cannot exceed 2,000 characters."
            )

        return value


class DealSerializer(serializers.ModelSerializer):
    customer_name = serializers.SerializerMethodField()
    customer_outcome_submitted = serializers.SerializerMethodField()
    partner_name = serializers.SerializerMethodField()
    commission_invoice = serializers.SerializerMethodField()
    owner_confirmation_status = serializers.SerializerMethodField()
    owner_confirmation_status_label = serializers.SerializerMethodField()

    property_title = serializers.CharField(
        source="property.title",
        read_only=True,
    )

    listing_type = serializers.CharField(
        source="property.listing_type",
        read_only=True,
    )

    viewing_status = serializers.CharField(
        source="viewing.status",
        read_only=True,
    )

    requested_date = serializers.DateField(
        source="viewing.requested_date",
        read_only=True,
    )

    requested_time = serializers.TimeField(
        source="viewing.requested_time",
        read_only=True,
    )

    outcomes = serializers.SerializerMethodField()

    class Meta:
        model = Deal

        fields = [
            "id",

            "customer",
            "customer_name",

            "partner",
            "partner_name",

            "property",
            "property_title",
            "listing_type",

            "viewing",
            "viewing_status",
            "requested_date",
            "requested_time",

            "monthly_rent",
            "sale_price",
            "commission_amount",
            "commission_invoice",

            "status",
            "customer_confirmed",
            "customer_outcome_submitted",
            "partner_confirmed",
            "owner_confirmed",
            "owner_confirmation_status",
            "owner_confirmation_status_label",
            "customer_confirmed_at",
            "partner_confirmed_at",
            "owner_confirmed_at",
            "agreed_at",
            "completed_at",
            "closed_at",
            "cancelled_at",
            "cancellation_reason",

            "outcomes",

            "created_at",
            "updated_at",
            
        ]

        read_only_fields = fields

    def get_customer_outcome_submitted(self, deal):
        return any(
            outcome.reporter == DealOutcome.Reporter.CUSTOMER
            for outcome in deal.outcomes.all()
        )

    def get_owner_confirmation_status(self, deal):
        return get_owner_confirmation_status(deal)["code"]

    def get_owner_confirmation_status_label(self, deal):
        return get_owner_confirmation_status(deal)["label"]

    def get_outcomes(self, deal):
        request = self.context.get("request")
        outcomes = list(deal.outcomes.all())

        if request is None:
            outcomes = []
        elif not request.user.is_staff:
            reporter = (
                DealOutcome.Reporter.PARTNER
                if getattr(request.user, "role", None) == "partner"
                else DealOutcome.Reporter.CUSTOMER
            )
            outcomes = [
                outcome
                for outcome in outcomes
                if outcome.reporter == reporter
            ]

        return DealOutcomeSerializer(
            outcomes,
            many=True,
        ).data

    def get_customer_name(self, deal):
        full_name = deal.customer.get_full_name().strip()

        return (
            full_name
            or getattr(deal.customer, "full_name", "")
            or deal.customer.email
            or deal.customer.username
        )

    def get_commission_invoice(self, deal):
        request = self.context.get("request")

        if request is None or not request.user.is_staff:
            return None

        try:
            invoice = deal.commission_invoice
        except CommissionInvoice.DoesNotExist:
            return None

        receipts = list(
            invoice.receipts.all()
        )

        total_received = sum(
            (
                receipt.amount
                for receipt in receipts
            ),
            0,
        )

        outstanding_amount = (
            invoice.amount
            - total_received
        )

        return {
            "id": invoice.id,
            "invoice_number": invoice.invoice_number,
            "amount": invoice.amount,
            "currency": invoice.currency,
            "status": invoice.status,
            "issued_at": invoice.issued_at,
            "paid_at": invoice.paid_at,
            "total_received": total_received,
            "outstanding_amount": outstanding_amount,
            "owner_number": (
                invoice.owner_number_snapshot
            ),
            "owner_name": (
                invoice.owner_legal_name_snapshot
            ),
            "agreement_number": (
                invoice.agreement_number_snapshot
            ),
            "receipts": [
                {
                    "id": receipt.id,
                    "amount": receipt.amount,
                    "currency": receipt.currency,
                    "payment_method": (
                        receipt.payment_method
                    ),
                    "payment_reference": (
                        receipt.payment_reference
                    ),
                    "received_at": (
                        receipt.received_at
                    ),
                    "notes": receipt.notes,
                }
                for receipt in receipts
            ],
        }

    def get_partner_name(self, deal):
        if deal.partner.display_name:
            return deal.partner.display_name

        if deal.partner.business_name:
            return deal.partner.business_name

        full_name = deal.partner.user.get_full_name().strip()

        return (
            full_name
            or getattr(deal.partner.user, "full_name", "")
            or deal.partner.user.email
        )

class CustomerCompletedDealSerializer(serializers.ModelSerializer):
    """
    Minimal customer-facing record of a completed transaction.

    Deliberately excludes commission, invoice, settlement,
    payout, and internal governance information.
    """

    property_title = serializers.CharField(
        source="property.title",
        read_only=True,
    )

    partner_name = serializers.SerializerMethodField()

    class Meta:
        model = Deal

        fields = [
            "id",
            "deal_number",
            "property",
            "property_title",
            "deal_type",
            "partner_name",
            "status",
            "completed_at",
            "closed_at",
        ]

        read_only_fields = fields

    def get_partner_name(self, deal):
        user = getattr(deal.partner, "user", None)

        if user is None:
            return ""

        full_name = user.get_full_name().strip()

        return (
            full_name
            or getattr(user, "full_name", "")
            or user.username
        )

class OwnerOutcomeSubmissionSerializer(serializers.Serializer):
    token = serializers.CharField(
        write_only=True,
        trim_whitespace=True,
    )

    outcome = serializers.ChoiceField(
        choices=DealOutcome.Outcome.choices,
    )

    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=2000,
    )

class DealTimelineItemSerializer(serializers.Serializer):
    timestamp = serializers.DateTimeField()
    event_type = serializers.CharField()
    title = serializers.CharField()
    description = serializers.CharField(
        allow_blank=True,
    )
    actor = serializers.CharField(
        allow_null=True,
        required=False,
    )
    source = serializers.CharField()
    source_id = serializers.IntegerField(
        allow_null=True,
        required=False,
    )
    metadata = serializers.JSONField()


class DealTimelineSerializer(serializers.Serializer):
    deal = serializers.DictField()
    timeline = DealTimelineItemSerializer(
        many=True,
    )
