from rest_framework import serializers

from commissions.models import CommissionAgreement
from .models import PropertyMandate, PropertyOwner


class PropertyOwnerSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyOwner
        fields = [
            "id",
            "owner_number",
            "legal_name",
            "phone_number",
            "owner_type",
        ]
        read_only_fields = fields


class CommissionAgreementSummarySerializer(serializers.ModelSerializer):
    commission_method_display = serializers.CharField(
        source="get_commission_method_display",
        read_only=True,
    )
    commission_basis_display = serializers.CharField(
        source="get_commission_basis_display",
        read_only=True,
    )

    class Meta:
        model = CommissionAgreement
        fields = [
            "id",
            "agreement_number",
            "commission_method",
            "commission_method_display",
            "commission_basis",
            "commission_basis_display",
            "commission_rate",
            "fixed_commission_amount",
            "transaction_value",
            "expected_total_commission",
            "currency",
            "partner_accepted",
            "partner_accepted_at",
            "is_verified",
            "is_locked",
            "status",
        ]
        read_only_fields = fields


class PropertyMandateSerializer(serializers.ModelSerializer):
    owner = serializers.PrimaryKeyRelatedField(
        read_only=True,
    )

    owner_name = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=False,
        max_length=255,
    )

    owner_phone_number = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=False,
        max_length=30,
    )

    owner_type = serializers.ChoiceField(
        write_only=True,
        required=False,
        choices=PropertyOwner.OwnerType.choices,
        default=PropertyOwner.OwnerType.INDIVIDUAL,
    )

    owner_detail = PropertyOwnerSummarySerializer(
        source="owner",
        read_only=True,
    )

    commission_detail = CommissionAgreementSummarySerializer(
        source="commission_agreement",
        read_only=True,
    )

    property_title = serializers.CharField(
        source="property.title",
        read_only=True,
    )

    partner_name = serializers.SerializerMethodField()

    authorization_method_display = serializers.CharField(
        source="get_authorization_method_display",
        read_only=True,
    )

    status_display = serializers.CharField(
        source="get_status_display",
        read_only=True,
    )

    is_currently_valid = serializers.BooleanField(
        read_only=True,
    )

    class Meta:
        model = PropertyMandate
        fields = [
            "id",
            "mandate_number",
            "version",
            "property",
            "property_title",
            "owner",
            "owner_name",
            "owner_phone_number",
            "owner_type",
            "owner_detail",
            "partner",
            "partner_name",
            "commission_agreement",
            "commission_detail",
            "status",
            "status_display",
            "authorization_method",
            "authorization_method_display",
            "authorization_notes",
            "effective_date",
            "expiry_date",
            "protection_period_days",
            "owner_authority_confirmed",
            "no_cash_acknowledged",
            "anti_circumvention_acknowledged",
            "partner_declared",
            "partner_declared_at",
            "declaration_version",
            "declared_by",
            "submitted_at",
            "approved_by",
            "approved_at",
            "rejection_reason",
            "is_currently_valid",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "mandate_number",
            "version",
            "property_title",
            "owner",
            "partner",
            "partner_name",
            "status",
            "status_display",
            "partner_declared",
            "partner_declared_at",
            "declaration_version",
            "declared_by",
            "submitted_at",
            "approved_by",
            "approved_at",
            "rejection_reason",
            "is_currently_valid",
            "created_at",
            "updated_at",
        ]

    def get_partner_name(self, mandate):
        partner = mandate.partner

        return (
            getattr(partner, "display_name", "")
            or getattr(partner, "business_name", "")
            or partner.user.get_full_name().strip()
            or getattr(partner.user, "full_name", "")
            or partner.user.email
            or partner.user.username
        )

    def validate(self, attrs):
        instance = getattr(self, "instance", None)

        property_obj = attrs.get(
            "property",
            getattr(instance, "property", None),
        )

        agreement = attrs.get(
            "commission_agreement",
            getattr(instance, "commission_agreement", None),
        )

        if property_obj is None:
            raise serializers.ValidationError(
                {
                    "property": "A property is required.",
                }
            )

        if instance is None:
            owner_name = (
                attrs.get("owner_name", "")
                or ""
            ).strip()

            owner_phone = (
                attrs.get("owner_phone_number", "")
                or ""
            ).strip()

            if not owner_name:
                raise serializers.ValidationError(
                    {
                        "owner_name": (
                            "The owner or landlord name is required."
                        ),
                    }
                )

            if not owner_phone:
                raise serializers.ValidationError(
                    {
                        "owner_phone_number": (
                            "The owner or landlord phone number is required."
                        ),
                    }
                )

        if (
            agreement is not None
            and agreement.property_id != property_obj.id
        ):
            raise serializers.ValidationError(
                {
                    "commission_agreement": (
                        "The commission agreement must belong "
                        "to this property."
                    ),
                }
            )

        return attrs

    def create(self, validated_data):
        request = self.context.get("request")

        if request is None:
            raise serializers.ValidationError(
                "A request context is required."
            )

        owner_name = validated_data.pop(
            "owner_name",
        ).strip()

        owner_phone = validated_data.pop(
            "owner_phone_number",
        ).strip()

        owner_type = validated_data.pop(
            "owner_type",
            PropertyOwner.OwnerType.INDIVIDUAL,
        )

        owner = (
            PropertyOwner.objects
            .filter(
                phone_number=owner_phone,
                is_active=True,
            )
            .order_by("-id")
            .first()
        )

        if owner is None:
            owner = PropertyOwner.objects.create(
                legal_name=owner_name,
                phone_number=owner_phone,
                owner_type=owner_type,
                created_by=request.user,
            )

        validated_data["owner"] = owner

        return super().create(
            validated_data,
        )


class PartnerMandateDeclarationSerializer(serializers.Serializer):
    owner_authority_confirmed = serializers.BooleanField()
    no_cash_acknowledged = serializers.BooleanField()
    anti_circumvention_acknowledged = serializers.BooleanField()

    authorization_method = serializers.ChoiceField(
        choices=PropertyMandate.AuthorizationMethod.choices,
    )

    authorization_notes = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
    )

    def validate_owner_authority_confirmed(self, value):
        if not value:
            raise serializers.ValidationError(
                "You must confirm that you have authority "
                "to market this property."
            )

        return value

    def validate_no_cash_acknowledged(self, value):
        if not value:
            raise serializers.ValidationError(
                "You must acknowledge the Pata Hao payment policy."
            )

        return value

    def validate_anti_circumvention_acknowledged(
        self,
        value,
    ):
        if not value:
            raise serializers.ValidationError(
                "You must acknowledge the anti-circumvention rule."
            )

        return value
