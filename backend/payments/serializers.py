from rest_framework import serializers
from .models import Deal, Payment


class PaymentSerializer(serializers.ModelSerializer):
    payer_name = serializers.CharField(source="payer.full_name", read_only=True)

    class Meta:
        model = Payment
        fields = [
            "id",
            "deal",
            "payer",
            "payer_name",
            "amount",
            "payment_method",
            "payment_type",
            "status",
            "transaction_reference",
            "receipt_number",
            "paid_at",
            "created_at",
        ]


class DealSerializer(serializers.ModelSerializer):
    payments = PaymentSerializer(many=True, read_only=True)
    property_title = serializers.CharField(source="property.title", read_only=True)
    customer_name = serializers.CharField(source="customer.full_name", read_only=True)
    partner_name = serializers.CharField(source="partner.business_name", read_only=True)

    class Meta:
        model = Deal
        fields = [
            "id",
            "property",
            "property_title",
            "viewing",
            "customer",
            "customer_name",
            "partner",
            "partner_name",
            "deal_type",
            "amount",
            "commission_rate",
            "commission_amount",
            "status",
            "payments",
            "created_at",
            "updated_at",
        ]
