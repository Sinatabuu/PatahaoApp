from rest_framework import serializers

from .models import Deal, DealOutcome


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

    partner_name = serializers.SerializerMethodField()

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

    outcomes = DealOutcomeSerializer(
        many=True,
        read_only=True,
    )

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

            "status",
            "customer_confirmed",
            "partner_confirmed",
            "owner_confirmed",
            "customer_confirmed_at",
            "partner_confirmed_at",
            "owner_confirmed_at",
            "agreed_at",
            "completed_at",
            "cancelled_at",
            "cancellation_reason",

            "outcomes",

            "created_at",
            "updated_at",
            
        ]

        read_only_fields = fields

    def get_customer_name(self, deal):
        full_name = deal.customer.get_full_name().strip()

        return (
            full_name
            or getattr(deal.customer, "full_name", "")
            or deal.customer.email
            or deal.customer.username
        )

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