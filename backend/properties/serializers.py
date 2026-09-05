from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from partners.models import Partner

from .models import (
    Property,
    PropertyFavorite,
    PropertyPartner,
    PropertyPhoto,
    PropertyVideo,
)

from .media_quality import analyze_property_photo
from .photo_coverage import evaluate_photo_coverage

class PublicPartnerSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    is_verified = serializers.SerializerMethodField()
    profile_photo_url = serializers.SerializerMethodField()

    class Meta:
        model = Partner
        fields = (
            "id",
            "name",
            "business_name",
            "partner_code",
            "partner_type",
            "profile_photo",
            "profile_photo_url",
            "bio",
            "county",
            "town",
            "service_area",
            "is_verified",
        )

    def get_name(self, obj):
        return obj.display_name or obj.business_name

    def get_is_verified(self, obj):
        return obj.is_verified

    def get_profile_photo_url(self, obj):
        request = self.context.get("request")

        if not obj.profile_photo:
            return None

        if request:
            return request.build_absolute_uri(
                obj.profile_photo.url,
            )

        return obj.profile_photo.url


class PropertyPhotoSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = PropertyPhoto
        fields = [
            "id",
            "image",
            "image_url",
            "caption",
            "is_cover",
        ]

    def get_image_url(self, obj):
        request = self.context.get("request")

        if not obj.image:
            return None

        if request:
            return request.build_absolute_uri(
                obj.image.url,
            )

        return obj.image.url


class PartnerPropertyPhotoSerializer(
    PropertyPhotoSerializer,
):
    class Meta(PropertyPhotoSerializer.Meta):
        fields = [
            *PropertyPhotoSerializer.Meta.fields,
            "photo_type",
            "image_width",
            "image_height",
            "file_size",
            "quality_status",
            "quality_score",
            "quality_warnings",
        ]


class PropertyPhotoUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyPhoto
        fields = (
            "id",
            "property",
            "image",
            "caption",
            "photo_type",
            "is_cover",
            "image_width",
            "image_height",
            "file_size",
            "quality_status",
            "quality_score",
            "quality_warnings",
        )
        read_only_fields = (
            "image_width",
            "image_height",
            "file_size",
            "quality_status",
            "quality_score",
            "quality_warnings",
        )

    def validate(self, attrs):
        attrs = super().validate(attrs)

        image = attrs.get("image")

        if image is None:
            return attrs

        property_obj = attrs.get("property")

        if property_obj is None and self.instance is not None:
            property_obj = self.instance.property

        try:
            analysis = analyze_property_photo(image)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(
                {
                    "image": exc.messages,
                }
            ) from exc

        duplicates = PropertyPhoto.objects.filter(
            property=property_obj,
            content_sha256=analysis.content_sha256,
        )

        if self.instance is not None:
            duplicates = duplicates.exclude(
                pk=self.instance.pk,
            )

        if duplicates.exists():
            raise serializers.ValidationError(
                {
                    "image": (
                        "This exact photo has already been uploaded "
                        "for the property."
                    )
                }
            )

        self._photo_quality_analysis = analysis

        return attrs

    def _add_quality_metadata(self, validated_data):
        analysis = getattr(
            self,
            "_photo_quality_analysis",
            None,
        )

        if analysis is None:
            return

        validated_data.update(
            {
                "image_width": analysis.width,
                "image_height": analysis.height,
                "file_size": analysis.file_size,
                "content_sha256": analysis.content_sha256,
                "quality_status": analysis.quality_status,
                "quality_score": analysis.quality_score,
                "quality_warnings": list(
                    analysis.quality_warnings,
                ),
            }
        )

    def create(self, validated_data):
        self._add_quality_metadata(validated_data)

        property_obj = validated_data["property"]

        if not PropertyPhoto.objects.filter(
            property=property_obj,
        ).exists():
            validated_data["is_cover"] = True

        photo = PropertyPhoto.objects.create(
            **validated_data,
        )

        if photo.is_cover:
            PropertyPhoto.objects.filter(
                property=property_obj,
            ).exclude(
                id=photo.id,
            ).update(
                is_cover=False,
            )

        return photo

    def update(self, instance, validated_data):
        replacing_image = "image" in validated_data

        if replacing_image:
            self._add_quality_metadata(validated_data)

        instance.caption = validated_data.get(
            "caption",
            instance.caption,
        )

        instance.is_cover = validated_data.get(
            "is_cover",
            instance.is_cover,
        )

        if replacing_image:
            instance.image = validated_data["image"]
            instance.image_width = validated_data[
                "image_width"
            ]
            instance.image_height = validated_data[
                "image_height"
            ]
            instance.file_size = validated_data[
                "file_size"
            ]
            instance.content_sha256 = validated_data[
                "content_sha256"
            ]
            instance.quality_status = validated_data[
                "quality_status"
            ]
            instance.quality_score = validated_data[
                "quality_score"
            ]
            instance.quality_warnings = validated_data[
                "quality_warnings"
            ]

        instance.save()

        if instance.is_cover:
            PropertyPhoto.objects.filter(
                property=instance.property,
            ).exclude(
                id=instance.id,
            ).update(
                is_cover=False,
            )

        return instance


class PropertyVideoSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyVideo
        fields = (
            "id",
            "video",
            "title",
            "uploaded_at",
        )


class PropertySerializer(serializers.ModelSerializer):
    photos = PropertyPhotoSerializer(
        many=True,
        read_only=True,
    )

    videos = PropertyVideoSerializer(
        many=True,
        read_only=True,
    )

    partner = PublicPartnerSerializer(
        read_only=True,
    )

    is_available = serializers.BooleanField(
        read_only=True,
    )

    is_success_broadcast_active = (
        serializers.BooleanField(
            read_only=True,
        )
    )

    success_badge = serializers.CharField(
        read_only=True,
    )

    transaction_completed_at = (
        serializers.DateTimeField(
            read_only=True,
        )
    )

    success_broadcast_until = (
        serializers.DateTimeField(
            read_only=True,
        )
    )

    is_favorite = serializers.SerializerMethodField()
    favorite_id = serializers.SerializerMethodField()

    class Meta:
        model = Property
        fields = (
            "id",
            "partner",
            "title",
            "property_type",
            "listing_type",
            "price",
            "county",
            "town",
            "estate",
            "address",
            "latitude",
            "longitude",
            "bedrooms",
            "bathrooms",
            "description",
            "status",
            "is_available",
            "is_success_broadcast_active",
            "success_badge",
            "transaction_completed_at",
            "success_broadcast_until",
            "is_favorite",
            "favorite_id",
            "trust_badge",
            "photos",
            "videos",
            "created_at",
            "updated_at",

        )
    def _get_customer_favorite(self, obj):
        request = self.context.get("request")

        if (
            request is None
            or not request.user.is_authenticated
        ):
            return None

        return (
            PropertyFavorite.objects
            .filter(
                customer=request.user,
                property=obj,
            )
            .first()
        )

    def get_is_favorite(self, obj):
        return (
            self._get_customer_favorite(obj)
            is not None
        )

    def get_favorite_id(self, obj):
        favorite = self._get_customer_favorite(obj)

        if favorite is None:
            return None

        return favorite.id

class PartnerPropertySerializer(PropertySerializer):
    photos = PartnerPropertyPhotoSerializer(
        many=True,
        read_only=True,
    )
    partner_role = serializers.SerializerMethodField()
    participation_status = serializers.SerializerMethodField()
    photo_coverage = serializers.SerializerMethodField()

    class Meta(PropertySerializer.Meta):
        fields = PropertySerializer.Meta.fields + (
            "partner_role",
            "participation_status",
            "photo_coverage",

        )

    def get_photo_coverage(self, obj):
        return evaluate_photo_coverage(
            obj,
            obj.photos.all(),
        )

    def _get_partner(self):
        request = self.context.get("request")

        if not request or not request.user.is_authenticated:
            return None

        try:
            return Partner.objects.get(user=request.user)
        except Partner.DoesNotExist:
            return None

    def _get_participation(self, obj):
        partner = self._get_partner()

        if partner is None:
            return None

        return (
            obj.partner_participations
            .filter(partner=partner)
            .first()
        )

    def get_partner_role(self, obj):
        participation = self._get_participation(obj)

        if participation:
            return participation.role

        partner = self._get_partner()

        if partner and obj.partner_id == partner.id:
            return PropertyPartner.Role.SOURCE

        return None

    def get_participation_status(self, obj):
        participation = self._get_participation(obj)

        if participation:
            return participation.status

        partner = self._get_partner()

        if partner and obj.partner_id == partner.id:
            return PropertyPartner.Status.ACTIVE

        return None
