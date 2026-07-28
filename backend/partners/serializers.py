from rest_framework import serializers

from properties.models import Property
from viewings.models import Viewing

from .models import Partner


class PartnerDashboardProfileSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    class Meta:
        model = Partner
        fields = [
            "id",
            "name",
            "business_name",
            "display_name",
            "partner_type",
            "partner_code",
            "profile_photo",
            "county",
            "town",
            "service_area",
            "public_phone_number",
            "verification_status",
            "commission_rate",
            "accepts_viewing_requests",
        ]

    def get_name(self, partner):
        if partner.display_name:
            return partner.display_name

        if partner.business_name:
            return partner.business_name

        full_name = partner.user.get_full_name()
        if full_name:
            return full_name

        return partner.user.email


class PartnerDashboardPropertySerializer(serializers.ModelSerializer):
    class Meta:
        model = Property
        fields = [
            "id",
            "title",
            "property_type",
            "listing_type",
            "county",
            "town",
            "estate",
            "status",
            "trust_badge",
            "created_at",
            "updated_at",
        ]


class PartnerDashboardViewingSerializer(serializers.ModelSerializer):
    customer_name = serializers.SerializerMethodField()

    customer_email = serializers.EmailField(
        source="customer.email",
        read_only=True,
    )

    property_title = serializers.CharField(
        source="property.title",
        read_only=True,
    )

    class Meta:
        model = Viewing

        fields = [
            "id",
            "customer",
            "customer_name",
            "customer_email",
            "property",
            "property_title",

            "requested_date",
            "requested_time",
            "customer_message",

            "fee_amount",
            "status",
            "payment_reference",

            "proposed_date",
            "proposed_time",

            "confirmed_date",
            "confirmed_time",

            "partner_response_message",
            "partner_responded_at",

            "created_at",
            "updated_at",
        ]

        read_only_fields = fields

    def get_customer_name(self, viewing):
        full_name = viewing.customer.get_full_name()

        if full_name:
            return full_name

        return viewing.customer.email