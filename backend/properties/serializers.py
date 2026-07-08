from rest_framework import serializers
from .models import Property, PropertyPhoto


class PropertyPhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyPhoto
        fields = [
            "id",
            "image",
            "caption",
            "is_cover",
            "uploaded_at",
        ]


class PropertySerializer(serializers.ModelSerializer):
    photos = PropertyPhotoSerializer(many=True, read_only=True)
    partner_name = serializers.CharField(source="partner.business_name", read_only=True)

    class Meta:
        model = Property
        fields = [
            "id",
            "partner",
            "partner_name",
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
            "trust_badge",
            "photos",
            "created_at",
            "updated_at",
        ]
