from rest_framework import serializers

from partners.models import Partner

from .models import (
    Property,
    PropertyFavorite,
    PropertyPhoto,
    PropertyVideo,
)


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


class PropertyPhotoUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyPhoto
        fields = (
            "id",
            "property",
            "image",
            "caption",
            "is_cover",
        )

    def create(self, validated_data):
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
        instance.caption = validated_data.get(
            "caption",
            instance.caption,
        )

        instance.is_cover = validated_data.get(
            "is_cover",
            instance.is_cover,
        )

        if "image" in validated_data:
            instance.image = validated_data["image"]

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
        return self._get_customer_favorite(obj) is not None

    def get_favorite_id(self, obj):
        favorite = self._get_customer_favorite(obj)

        if favorite is None:
            return None

        return favorite.id

