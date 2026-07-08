from rest_framework import serializers
from .models import Partner


class PartnerSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    user_full_name = serializers.CharField(source="user.full_name", read_only=True)

    class Meta:
        model = Partner
        fields = [
            "id",
            "user",
            "user_email",
            "user_full_name",
            "business_name",
            "partner_type",
            "county",
            "town",
            "phone_number",
            "verification_status",
            "commission_rate",
            "created_at",
        ]
