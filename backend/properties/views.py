from rest_framework import permissions, viewsets
from rest_framework.exceptions import PermissionDenied

from core.models import ActivityLog
from partners.models import Partner

from .models import (
    Property,
    PropertyPhoto,
)
from .serializers import (
    PropertyPhotoSerializer,
    PropertyPhotoUploadSerializer,
    PropertySerializer,
)


class PropertyViewSet(viewsets.ModelViewSet):
    """
    Public/customer-facing property endpoint.

    Public users and ordinary authenticated customers may only see
    published properties.

    Staff users may see all properties and optionally filter by status.
    """

    serializer_class = PropertySerializer
    permission_classes = [
        permissions.IsAuthenticatedOrReadOnly,
    ]

    def get_queryset(self):
        queryset = (
            Property.objects
            .select_related("partner")
            .prefetch_related(
                "photos",
                "videos",
            )
            .order_by("-created_at")
        )

        listing_type = self.request.query_params.get(
            "listing_type",
        )

        town = self.request.query_params.get("town")

        requested_status = self.request.query_params.get(
            "status",
        )

        if listing_type:
            queryset = queryset.filter(
                listing_type=listing_type,
            )

        if town:
            queryset = queryset.filter(
                town__icontains=town,
            )

        if self.request.user.is_authenticated:
            if self.request.user.is_staff:
                if requested_status:
                    queryset = queryset.filter(
                        status=requested_status,
                    )

                return queryset

        # Public users and normal customers may only see
        # properties that are currently published.
        return queryset.filter(
            status=Property.STATUS_PUBLISHED,
        )

    def perform_create(self, serializer):
        property_obj = serializer.save()

        ActivityLog.objects.create(
            actor=(
                self.request.user
                if self.request.user.is_authenticated
                else None
            ),
            action="property_created",
            entity_type="Property",
            entity_id=str(property_obj.id),
            description=(
                f"Property created: {property_obj.title}"
            ),
        )


class PartnerPropertyViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Private partner inventory endpoint.

    A partner may only see properties assigned to their own
    approved and active partner profile.

    Current supported actions:

    GET /api/partner/properties/
    GET /api/partner/properties/<id>/
    """

    serializer_class = PropertySerializer
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def _get_partner(self):
        try:
            partner = Partner.objects.get(
                user=self.request.user,
            )
        except Partner.DoesNotExist as exc:
            raise PermissionDenied(
                "A partner profile is required to access this section."
            ) from exc

        if partner.verification_status != Partner.STATUS_APPROVED:
            raise PermissionDenied(
                "Your partner profile must be approved before "
                "you can manage properties."
            )

        if not partner.is_active:
            raise PermissionDenied(
                "Your partner profile is currently inactive."
            )

        return partner

    def get_queryset(self):
        partner = self._get_partner()

        queryset = (
            Property.objects
            .filter(partner=partner)
            .select_related("partner")
            .prefetch_related(
                "photos",
                "videos",
            )
            .order_by("-created_at")
        )

        requested_status = self.request.query_params.get(
            "status",
        )

        listing_type = self.request.query_params.get(
            "listing_type",
        )

        if requested_status:
            queryset = queryset.filter(
                status=requested_status,
            )

        if listing_type:
            queryset = queryset.filter(
                listing_type=listing_type,
            )

        return queryset

class PropertyPhotoViewSet(viewsets.ModelViewSet):
    """
    Partner photo management.

    Allows partners to:

    - Upload photos
    - List photos
    - Edit captions
    - Set cover photo
    - Delete photos

    Only photos belonging to the authenticated
    partner's own properties are accessible.
    """

    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def _get_partner(self):
        try:
            partner = Partner.objects.get(
                user=self.request.user,
            )
        except Partner.DoesNotExist as exc:
            raise PermissionDenied(
                "A partner profile is required."
            ) from exc

        if partner.verification_status != Partner.STATUS_APPROVED:
            raise PermissionDenied(
                "Partner profile is not approved."
            )

        if not partner.is_active:
            raise PermissionDenied(
                "Partner profile is inactive."
            )

        return partner

    def get_queryset(self):
        partner = self._get_partner()

        queryset = (
            PropertyPhoto.objects
            .select_related("property")
            .filter(
                property__partner=partner,
            )
        )

        property_id = self.request.query_params.get("property")

        if property_id:
            queryset = queryset.filter(
                property_id=property_id,
            )

        return queryset.order_by(
            "-is_cover",
            "uploaded_at",
        )

    def get_serializer_class(self):
        if self.action in (
            "create",
            "update",
            "partial_update",
        ):
            return PropertyPhotoUploadSerializer

        return PropertyPhotoSerializer

    def perform_create(self, serializer):
        partner = self._get_partner()

        property_obj = serializer.validated_data["property"]

        if property_obj.partner != partner:
            raise PermissionDenied(
                "You may only upload photos for your own properties."
            )

        photo = serializer.save()

        ActivityLog.objects.create(
            actor=self.request.user,
            action="property_photo_uploaded",
            entity_type="PropertyPhoto",
            entity_id=str(photo.id),
            description=(
                f"Uploaded photo for {property_obj.title}"
            ),
        )

    def perform_destroy(self, instance):
        property_obj = instance.property
        was_cover = instance.is_cover

        ActivityLog.objects.create(
            actor=self.request.user,
            action="property_photo_deleted",
            entity_type="PropertyPhoto",
            entity_id=str(instance.id),
            description=(
                f"Deleted photo from {property_obj.title}"
            ),
        )

        instance.delete()

        if was_cover:
            next_photo = (
                PropertyPhoto.objects
                .filter(
                    property=property_obj,
                )
                .first()
            )

            if next_photo:
                next_photo.is_cover = True
                next_photo.save()       