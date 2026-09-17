from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.files.base import ContentFile
from django.db import transaction
from rest_framework import serializers

from partners.models import Partner

from .models import (
    Property,
    PropertyAmenity,
    PropertyFavorite,
    PropertyPartner,
    PropertyPhoto,
    PropertyVideo,
)

from .media_quality import analyze_property_photo
from .photo_coverage import evaluate_photo_coverage
from .video_quality import analyze_property_video

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


class PropertyAmenitySerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyAmenity
        fields = (
            "id",
            "name",
            "slug",
            "icon",
            "display_order",
        )


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
    video_url = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()

    class Meta:
        model = PropertyVideo
        fields = (
            "id",
            "video",
            "video_url",
            "thumbnail",
            "thumbnail_url",
            "title",
            "description",
            "duration",
            "width",
            "height",
            "is_featured",
            "uploaded_at",
        )

    def _absolute_file_url(self, file_field):
        if not file_field:
            return None

        request = self.context.get("request")

        if request:
            return request.build_absolute_uri(file_field.url)

        return file_field.url

    def get_video_url(self, obj):
        return self._absolute_file_url(obj.video)

    def get_thumbnail_url(self, obj):
        return self._absolute_file_url(obj.thumbnail)


class PartnerPropertyVideoSerializer(PropertyVideoSerializer):
    class Meta(PropertyVideoSerializer.Meta):
        fields = (
            *PropertyVideoSerializer.Meta.fields,
            "file_size",
            "video_codec",
            "audio_codec",
            "review_status",
            "rejection_reason",
            "reviewed_at",
        )


class PropertyVideoUploadSerializer(PartnerPropertyVideoSerializer):
    class Meta(PartnerPropertyVideoSerializer.Meta):
        model = PropertyVideo
        fields = (
            *PartnerPropertyVideoSerializer.Meta.fields,
            "property",
        )
        read_only_fields = (
            "id",
            "video_url",
            "thumbnail",
            "thumbnail_url",
            "duration",
            "width",
            "height",
            "file_size",
            "video_codec",
            "audio_codec",
            "review_status",
            "rejection_reason",
            "reviewed_at",
            "uploaded_at",
            "is_featured",
        )

    def validate(self, attrs):
        attrs = super().validate(attrs)
        video = attrs.get("video")
        property_obj = attrs.get("property")

        if video is None or property_obj is None:
            return attrs

        if property_obj.status not in {
            Property.STATUS_DRAFT,
            Property.STATUS_PENDING,
            Property.STATUS_PUBLISHED,
        }:
            raise serializers.ValidationError(
                {
                    "property": (
                        "Videos cannot be changed for a closed or "
                        "archived property."
                    )
                }
            )

        if PropertyVideo.objects.filter(
            property=property_obj,
            review_status=PropertyVideo.ReviewStatus.PENDING,
        ).exists():
            raise serializers.ValidationError(
                {
                    "video": (
                        "A walkthrough is already awaiting staff review. "
                        "Wait for the decision or delete it before "
                        "uploading another."
                    )
                }
            )

        try:
            analysis = analyze_property_video(video)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(
                {"video": exc.messages}
            ) from exc

        if PropertyVideo.objects.filter(
            property=property_obj,
            content_sha256=analysis.content_sha256,
        ).exists():
            raise serializers.ValidationError(
                {
                    "video": (
                        "This exact video has already been uploaded "
                        "for the property."
                    )
                }
            )

        self._video_quality_analysis = analysis
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        analysis = self._video_quality_analysis
        property_obj = Property.objects.select_for_update().get(
            pk=validated_data["property"].pk,
        )

        if PropertyVideo.objects.filter(
            property=property_obj,
            review_status=PropertyVideo.ReviewStatus.PENDING,
        ).exists():
            raise serializers.ValidationError(
                {
                    "video": (
                        "A walkthrough is already awaiting staff review. "
                        "Wait for the decision or delete it before "
                        "uploading another."
                    )
                }
            )

        if PropertyVideo.objects.filter(
            property=property_obj,
            content_sha256=analysis.content_sha256,
        ).exists():
            raise serializers.ValidationError(
                {
                    "video": (
                        "This exact video has already been uploaded "
                        "for the property."
                    )
                }
            )

        validated_data["property"] = property_obj
        validated_data.update(
            {
                "file_size": analysis.file_size,
                "content_sha256": analysis.content_sha256,
                "width": analysis.width,
                "height": analysis.height,
                "duration": analysis.duration,
                "video_codec": analysis.video_codec,
                "audio_codec": analysis.audio_codec,
            }
        )

        current_videos = PropertyVideo.objects.filter(
            property=property_obj,
        )
        approved_video_exists = current_videos.filter(
            review_status=PropertyVideo.ReviewStatus.APPROVED,
        ).exists()

        # A returned upload is replaced immediately. An approved video stays
        # live while its new pending replacement is reviewed by staff.
        current_videos.filter(
            review_status=PropertyVideo.ReviewStatus.REJECTED,
        ).delete()

        validated_data["is_featured"] = not approved_video_exists

        video = PropertyVideo(**validated_data)
        video.thumbnail.save(
            "walkthrough-thumbnail.jpg",
            ContentFile(analysis.thumbnail_bytes),
            save=False,
        )

        video.save()
        return video


class PropertyVideoUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyVideo
        fields = (
            "title",
            "description",
        )


class PropertySerializer(serializers.ModelSerializer):
    photos = PropertyPhotoSerializer(
        many=True,
        read_only=True,
    )

    videos = serializers.SerializerMethodField()

    amenities = PropertyAmenitySerializer(
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
            "amenities",
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

    def get_videos(self, obj):
        videos = [
            video
            for video in obj.videos.all()
            if video.review_status
            == PropertyVideo.ReviewStatus.APPROVED
        ]

        return PropertyVideoSerializer(
            videos,
            many=True,
            context=self.context,
        ).data


class PropertyCardSerializer(PropertySerializer):
    """
    Compact representation used by the paginated public property feed.

    The full serializer remains available on the detail endpoint. Keeping
    feed cards small avoids returning every photo, video, amenity, partner,
    and long description for properties that the customer has not opened.
    """

    photos = serializers.SerializerMethodField()
    videos = serializers.SerializerMethodField()

    class Meta:
        model = Property
        fields = (
            "id",
            "title",
            "property_type",
            "listing_type",
            "price",
            "county",
            "town",
            "estate",
            "bedrooms",
            "bathrooms",
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
        )

    def _favorite_ids(self):
        return self.context.get(
            "favorite_id_by_property_id",
        )

    def get_is_favorite(self, obj):
        favorite_ids = self._favorite_ids()

        if favorite_ids is None:
            return super().get_is_favorite(obj)

        return obj.pk in favorite_ids

    def get_favorite_id(self, obj):
        favorite_ids = self._favorite_ids()

        if favorite_ids is None:
            return super().get_favorite_id(obj)

        return favorite_ids.get(obj.pk)

    def get_photos(self, obj):
        photos = list(obj.photos.all())

        if not photos:
            return []

        cover = next(
            (
                photo
                for photo in photos
                if photo.is_cover
            ),
            photos[0],
        )

        return [
            PropertyPhotoSerializer(
                cover,
                context=self.context,
            ).data
        ]

    def get_videos(self, obj):
        video = next(
            (
                item
                for item in obj.videos.all()
                if item.review_status
                == PropertyVideo.ReviewStatus.APPROVED
            ),
            None,
        )

        if video is None:
            return []

        return [
            PropertyVideoSerializer(
                video,
                context=self.context,
            ).data
        ]

class PropertyAmenitiesUpdateSerializer(serializers.Serializer):
    amenities = serializers.SlugRelatedField(
        many=True,
        slug_field="slug",
        queryset=PropertyAmenity.objects.filter(
            is_active=True,
        ),
    )


class PartnerPropertySerializer(PropertySerializer):
    photos = PartnerPropertyPhotoSerializer(
        many=True,
        read_only=True,
    )
    videos = serializers.SerializerMethodField()
    partner_role = serializers.SerializerMethodField()
    participation_status = serializers.SerializerMethodField()
    photo_coverage = serializers.SerializerMethodField()
    can_delete_draft = serializers.SerializerMethodField()

    class Meta(PropertySerializer.Meta):
        fields = PropertySerializer.Meta.fields + (
            "partner_role",
            "participation_status",
            "photo_coverage",
            "can_delete_draft",

        )

    def get_photo_coverage(self, obj):
        return evaluate_photo_coverage(
            obj,
            obj.photos.all(),
        )

    def get_videos(self, obj):
        partner = self._get_partner()
        videos = list(obj.videos.all())

        if partner is None or obj.partner_id != partner.id:
            videos = [
                video
                for video in videos
                if video.review_status
                == PropertyVideo.ReviewStatus.APPROVED
            ]

        return PartnerPropertyVideoSerializer(
            videos,
            many=True,
            context=self.context,
        ).data

    def get_can_delete_draft(self, obj):
        partner = self._get_partner()

        return (
            partner is not None
            and obj.partner_id == partner.id
            and obj.status == Property.STATUS_DRAFT
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
