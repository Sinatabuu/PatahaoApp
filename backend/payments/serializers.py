import re

from rest_framework import serializers

from viewings.models import Viewing

from .models import Payment


class PaymentSerializer(serializers.ModelSerializer):
    provider = serializers.ChoiceField(
        source="payment_method",
        choices=Payment.PaymentMethod.choices,
        required=False,
        default=Payment.PaymentMethod.MPESA,
    )

    provider_label = serializers.CharField(
        source="get_payment_method_display",
        read_only=True,
    )

    viewing_status = serializers.CharField(
        source="viewing.status",
        read_only=True,
    )

    property_title = serializers.CharField(
        source="viewing.property.title",
        read_only=True,
    )

    class Meta:
        model = Payment

        fields = [
            "id",
            "viewing",
            "viewing_status",
            "property_title",
            "payer",
            "amount",
            "currency",
            "phone_number",
            "provider",
            "provider_label",
            "purpose",
            "status",
            "payment_reference",
            "provider_transaction_id",
            "provider_receipt_number",
            "receipt_number",
            "failure_reason",
            "initiated_at",
            "paid_at",
            "failed_at",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "payer",
            "amount",
            "currency",
            "purpose",
            "status",
            "payment_reference",
            "provider_transaction_id",
            "provider_receipt_number",
            "receipt_number",
            "failure_reason",
            "initiated_at",
            "paid_at",
            "failed_at",
            "created_at",
            "updated_at",
        ]

    def validate_viewing(self, viewing):
        request = self.context.get("request")

        if request and viewing.customer_id != request.user.id:
            raise serializers.ValidationError(
                "You cannot pay for another customer's viewing."
            )

        if viewing.status != Viewing.Status.PENDING_PAYMENT:
            raise serializers.ValidationError(
                "This viewing is not awaiting payment."
            )

        existing_payment = Payment.objects.filter(
            viewing=viewing,
        ).first()

        if existing_payment:
            raise serializers.ValidationError(
                "A payment intent already exists for this viewing."
            )

        return viewing

    def validate_phone_number(self, value):
        cleaned = re.sub(
            r"[^0-9]",
            "",
            str(value),
        )

        if cleaned.startswith("0") and len(cleaned) == 10:
            cleaned = f"254{cleaned[1:]}"

        if cleaned.startswith("7") and len(cleaned) == 9:
            cleaned = f"254{cleaned}"

        if cleaned.startswith("1") and len(cleaned) == 9:
            cleaned = f"254{cleaned}"

        if not re.fullmatch(r"254(7|1)\d{8}", cleaned):
            raise serializers.ValidationError(
                "Enter a valid Kenyan mobile number, "
                "for example 0712345678 or 254712345678."
            )

        return cleaned

    def validate(self, attrs):
        payment_method = attrs.get(
            "payment_method",
            Payment.PaymentMethod.MPESA,
        )

        attrs["payment_method"] = payment_method

        phone_number = attrs.get(
            "phone_number",
            "",
        )

        if (
            payment_method == Payment.PaymentMethod.MPESA
            and not phone_number.startswith("254")
        ):
            raise serializers.ValidationError(
                {
                    "phone_number": (
                        "Enter a valid M-Pesa phone number."
                    )
                }
            )

        return attrs