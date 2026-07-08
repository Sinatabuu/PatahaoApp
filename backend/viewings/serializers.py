from rest_framework import serializers
from .models import Viewing


class ViewingSerializer(serializers.ModelSerializer):
    property_title = serializers.CharField(source="property.title", read_only=True)
    customer_name = serializers.CharField(source="customer.full_name", read_only=True)
    partner_name = serializers.CharField(source="partner.business_name", read_only=True)

    class Meta:
        model = Viewing
        fields = [
            "id",
            "property",
            "property_title",
            "customer",
            "customer_name",
            "partner",
            "partner_name",
            "preferred_date",
            "preferred_time",
            "scheduled_date",
            "scheduled_time",
            "message",
            "status",
            "created_at",
            "updated_at",
        ]
