from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.decorators import api_view
from math import asin, cos, radians, sin, sqrt
from core.models import ActivityLog
from partners.models import Partner
from django.db.models import Q
from .models import (
    Property,
    PropertyPartner,
    PropertyPhoto,
    PropertyFavorite
)
from .serializers import (
    PartnerPropertySerializer,
    PropertyPhotoSerializer,
    PropertyPhotoUploadSerializer,
    PropertySerializer,
)
from django.db import transaction
from django.shortcuts import get_object_or_404

def calculate_distance_meters(
    latitude_1,
    longitude_1,
    latitude_2,
    longitude_2,
):
    """
    Return approximate distance in meters between two GPS points.
    """

    earth_radius_m = 6371000

    lat1 = radians(float(latitude_1))
    lon1 = radians(float(longitude_1))
    lat2 = radians(float(latitude_2))
    lon2 = radians(float(longitude_2))

    delta_lat = lat2 - lat1
    delta_lon = lon2 - lon1

    a = (
        sin(delta_lat / 2) ** 2
        + cos(lat1)
        * cos(lat2)
        * sin(delta_lon / 2) ** 2
    )

    c = 2 * asin(sqrt(a))

    return earth_radius_m * c

@api_view(["GET"])
def property_types(request):
    return Response(
        [
            {
                "value": value,
                "label": label,
            }
            for value, label in Property.PROPERTY_TYPE_CHOICES
        ]
    )

class PropertyFavoriteViewSet(viewsets.ModelViewSet):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    http_method_names = [
        "get",
        "post",
        "delete",
        "head",
        "options",
    ]

    def get_queryset(self):
        return (
            PropertyFavorite.objects
            .select_related(
                "property",
                "property__partner",
            )
            .filter(
                customer=self.request.user,
            )
            .order_by("-created_at")
        )

    def list(self, request, *args, **kwargs):
        favorites = self.get_queryset()

        data = []

        for favorite in favorites:
            data.append(
                {
                    "id": favorite.id,
                    "customer": favorite.customer_id,
                    "property": favorite.property_id,
                    "property_details": PropertySerializer(
                        favorite.property,
                        context={
                            "request": request,
                        },
                    ).data,
                    "created_at": favorite.created_at,
                }
            )

        return Response(data)

    def create(self, request, *args, **kwargs):
        property_id = request.data.get("property")

        if not property_id:
            return Response(
                {
                    "property": [
                        "A property is required.",
                    ],
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        property_obj = get_object_or_404(
            Property,
            pk=property_id,
            status=Property.STATUS_PUBLISHED,
        )

        favorite, created = PropertyFavorite.objects.get_or_create(
            customer=request.user,
            property=property_obj,
        )

        response_status = (
            status.HTTP_201_CREATED
            if created
            else status.HTTP_200_OK
        )

        return Response(
            {
                "id": favorite.id,
                "customer": favorite.customer_id,
                "property": favorite.property_id,
                "property_details": PropertySerializer(
                    property_obj,
                    context={
                        "request": request,
                    },
                ).data,
                "created_at": favorite.created_at,
            },
            status=response_status,
        )
    def destroy(self, request, *args, **kwargs):
        favorite = get_object_or_404(
            self.get_queryset(),
            pk=kwargs["pk"],
        )

        favorite.delete()

        return Response(
            status=status.HTTP_204_NO_CONTENT,
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
    @action(
        detail=True,
        methods=["post"],
        url_path="join",
        permission_classes=[permissions.IsAuthenticated],
    )
    def join(self, request, pk=None):
        """
        Allow an approved partner to request participation
        in an existing Pata Hao property.

        Participation begins as pending and must be approved
        before the partner can receive viewing assignments.
        """

        try:
            partner = Partner.objects.get(
                user=request.user,
            )
        except Partner.DoesNotExist as exc:
            raise PermissionDenied(
                "A partner profile is required."
            ) from exc

        if partner.verification_status != Partner.STATUS_APPROVED:
            raise PermissionDenied(
                "Your partner profile must be approved "
                "before joining a property."
            )

        if not partner.is_active:
            raise PermissionDenied(
                "Your partner profile is currently inactive."
            )

        property_obj = self.get_object()

        existing = PropertyPartner.objects.filter(
            property=property_obj,
            partner=partner,
        ).first()

        if existing:
            return Response(
                {
                    "detail": (
                        "You already have a participation "
                        "record for this property."
                    ),
                    "participation_id": existing.id,
                    "role": existing.role,
                    "status": existing.status,
                },
                status=status.HTTP_200_OK,
            )

        participation = PropertyPartner.objects.create(
            property=property_obj,
            partner=partner,
            role=PropertyPartner.Role.PARTICIPATING,
            status=PropertyPartner.Status.PENDING,
        )

        ActivityLog.objects.create(
            actor=request.user,
            action="property_participation_requested",
            entity_type="PropertyPartner",
            entity_id=str(participation.id),
            description=(
                f"{partner} requested participation in "
                f"{property_obj.title}"
            ),
        )

        return Response(
            {
                "detail": (
                    "Your request to participate in this "
                    "property has been submitted for approval."
                ),
                "participation_id": participation.id,
                "property_id": property_obj.id,
                "property_title": property_obj.title,
                "partner_id": partner.id,
                "role": participation.role,
                "status": participation.status,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=False,
        methods=["get"],
        url_path="nearby",
    )
    def nearby(self, request):
        latitude = request.query_params.get("latitude")
        longitude = request.query_params.get("longitude")

        if latitude is None or longitude is None:
            return Response(
                {
                    "detail": (
                        "latitude and longitude are required."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            latitude = float(latitude)
            longitude = float(longitude)
        except (TypeError, ValueError):
            return Response(
                {
                    "detail": (
                        "latitude and longitude must be valid numbers."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        partner = None

        if request.user.is_authenticated:
            partner = (
                Partner.objects
                .filter(user=request.user)
                .first()
            )

        candidates = []

        queryset = (
            Property.objects
            .exclude(latitude__isnull=True)
            .exclude(longitude__isnull=True)
            .select_related("partner")
            .prefetch_related(
                "photos",
                "partner_participations",
            )
        )

        for property_obj in queryset:
            distance_meters = calculate_distance_meters(
                latitude,
                longitude,
                property_obj.latitude,
                property_obj.longitude,
            )

            if distance_meters > 50:
                continue

            if distance_meters <= 10:
                proximity = "very_near"
            elif distance_meters <= 25:
                proximity = "near"
            else:
                proximity = "weak"

            is_mine = False
            my_participation_status = None

            if partner is not None:
                participation = (
                    PropertyPartner.objects
                    .filter(
                        property=property_obj,
                        partner=partner,
                    )
                    .first()
                )

                if participation is not None:
                    is_mine = True
                    my_participation_status = (
                        participation.status
                    )

            candidates.append(
                {
                    "id": property_obj.id,
                    "title": property_obj.title,
                    "property_type":
                        property_obj.property_type,
                    "listing_type":
                        property_obj.listing_type,
                    "county": property_obj.county,
                    "town": property_obj.town,
                    "estate": property_obj.estate,
                    "address": property_obj.address,
                    "latitude": str(
                        property_obj.latitude
                    ),
                    "longitude": str(
                        property_obj.longitude
                    ),
                    "distance_meters": round(
                        distance_meters,
                        1,
                    ),
                    "proximity": proximity,
                    "is_mine": is_mine,
                    "my_participation_status":
                        my_participation_status,
                }
            )

        candidates.sort(
            key=lambda item: item["distance_meters"]
        )

        return Response(
            {
                "count": len(candidates),
                "radius_meters": 50,
                "candidates": candidates,
            }
        )
    @action(
        detail=False,
        methods=["post"],
        url_path="confirm-different",
        permission_classes=[permissions.IsAuthenticated],
    )
    def confirm_different(self, request):
        try:
            partner = Partner.objects.get(
                user=request.user,
            )
        except Partner.DoesNotExist as exc:
            raise PermissionDenied(
                "A partner profile is required."
            ) from exc

        if partner.verification_status != Partner.STATUS_APPROVED:
            raise PermissionDenied(
                "Your partner profile must be approved."
            )

        if not partner.is_active:
            raise PermissionDenied(
                "Your partner profile is currently inactive."
            )

        latitude = request.data.get("latitude")
        longitude = request.data.get("longitude")
        candidate_ids = request.data.get(
            "candidate_ids",
            [],
        )

        if latitude is None or longitude is None:
            return Response(
                {
                    "detail": (
                        "latitude and longitude are required."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not isinstance(candidate_ids, list):
            return Response(
                {
                    "detail": (
                        "candidate_ids must be a list."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        ActivityLog.objects.create(
            actor=request.user,
            action="property_duplicate_candidates_rejected",
            entity_type="PropertyCandidateReview",
            entity_id="new-property",
            description=(
                f"{partner} reviewed nearby property candidates "
                f"{candidate_ids} and confirmed this is a "
                "different property."
            ),
        )

        return Response(
            {
                "detail": (
                    "Different-property confirmation recorded."
                ),
                "latitude": str(latitude),
                "longitude": str(longitude),
                "candidate_ids": candidate_ids,
                "confirmed_different": True,
            },
            status=status.HTTP_200_OK,
        )

class PartnerPropertyViewSet(
        mixins.CreateModelMixin,
        viewsets.ReadOnlyModelViewSet,
    ):
    """
    Private partner inventory endpoint.

    A partner may only see properties assigned to their own
    approved and active partner profile.

    Current supported actions:

    GET /api/partner/properties/
    GET /api/partner/properties/<id>/
    """

    serializer_class = PartnerPropertySerializer
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

    @transaction.atomic
    def perform_create(self, serializer):
        partner = self._get_partner()

        property_obj = serializer.save(
            partner=partner,
            status=Property.STATUS_DRAFT,
        )

        PropertyPartner.objects.get_or_create(
            property=property_obj,
            partner=partner,
            defaults={
                "role": PropertyPartner.Role.SOURCE,
                "status": PropertyPartner.Status.ACTIVE,
            },
        )

        ActivityLog.objects.create(
            actor=self.request.user,
            action="partner_property_created",
            entity_type="Property",
            entity_id=str(property_obj.id),
            description=(
                f"{partner} created property "
                f"{property_obj.title}"
            ),
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="submit-verification",
    )
    @transaction.atomic
    def submit_verification(self, request, pk=None):
        """
        Allow the source partner to submit a completed
        draft property for Pata Hao verification.

        Allowed transition:

        draft -> pending

        Publishing remains an administrative action.
        """

        partner = self._get_partner()

        property_obj = self.get_object()

        # Only the source/owning partner may submit
        # the property for verification.
        if property_obj.partner_id != partner.id:
            raise PermissionDenied(
                "Only the source partner may submit this "
                "property for verification."
            )

        if property_obj.status != Property.STATUS_DRAFT:
            return Response(
                {
                    "detail": (
                        "Only draft properties can be "
                        "submitted for verification."
                    ),
                    "property_id": property_obj.id,
                    "status": property_obj.status,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        missing_fields = []

        if not property_obj.title.strip():
            missing_fields.append("title")

        if not property_obj.property_type:
            missing_fields.append("property type")

        if not property_obj.listing_type:
            missing_fields.append("listing type")

        if property_obj.price is None or property_obj.price <= 0:
            missing_fields.append("price")

        if not property_obj.county.strip():
            missing_fields.append("county")

        if not property_obj.town.strip():
            missing_fields.append("town")

        if not property_obj.description.strip():
            missing_fields.append("description")

        if property_obj.latitude is None:
            missing_fields.append("GPS latitude")

        if property_obj.longitude is None:
            missing_fields.append("GPS longitude")

        if missing_fields:
            return Response(
                {
                    "detail": (
                        "Complete the required property information "
                        "before submitting for verification."
                    ),
                    "missing_fields": missing_fields,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        photos = PropertyPhoto.objects.filter(
            property=property_obj,
        )

        photo_count = photos.count()

        if photo_count == 0:
            return Response(
                {
                    "detail": (
                        "Add at least one property photo before "
                        "submitting for verification."
                    ),
                    "photo_count": 0,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        cover_photo = photos.filter(
            is_cover=True,
        ).first()

        if cover_photo is None:
            return Response(
                {
                    "detail": (
                        "Select a cover photo before submitting "
                        "for verification."
                    ),
                    "photo_count": photo_count,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )


        property_obj.status = Property.STATUS_PENDING

        property_obj.save(
            update_fields=[
                "status",

                "updated_at",
            ]
        )

        ActivityLog.objects.create(
            actor=request.user,
            action="property_submitted_for_verification",
            entity_type="Property",
            entity_id=str(property_obj.id),
            description=(
                f"{partner} submitted property "
                f"{property_obj.title} for verification."
            ),
        )

        return Response(
            {
                "detail": (
                    "Property submitted for Pata Hao verification."
                ),
                "property_id": property_obj.id,
                "property_title": property_obj.title,
                "status": property_obj.status,
                "photo_count": photo_count,
                "cover_photo_id": cover_photo.id,
            },
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="join",
    )
    @transaction.atomic
    def join(self, request, pk=None):
        """
        Allow an approved partner to request participation
        in an existing Pata Hao property.

        This partner endpoint may operate on draft, pending,
        or published properties because duplicate prevention
        happens before publication.
        """

        partner = self._get_partner()

        property_obj = (
            Property.objects
            .select_related("partner")
            .filter(pk=pk)
            .first()
        )

        if property_obj is None:
            return Response(
                {
                    "detail": "Property not found.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        existing = PropertyPartner.objects.filter(
            property=property_obj,
            partner=partner,
        ).first()

        if existing:
            return Response(
                {
                    "detail": (
                        "You already have a participation "
                        "record for this property."
                    ),
                    "participation_id": existing.id,
                    "role": existing.role,
                    "status": existing.status,
                    "property_id": property_obj.id,
                },
                status=status.HTTP_200_OK,
            )

        participation = PropertyPartner.objects.create(
            property=property_obj,
            partner=partner,
            role=PropertyPartner.Role.PARTICIPATING,
            status=PropertyPartner.Status.PENDING,
        )

        ActivityLog.objects.create(
            actor=request.user,
            action="property_participation_requested",
            entity_type="PropertyPartner",
            entity_id=str(participation.id),
            description=(
                f"{partner} requested participation in "
                f"{property_obj.title}"
            ),
        )

        return Response(
            {
                "detail": (
                    "Your request to participate in this "
                    "property has been submitted for approval."
                ),
                "participation_id": participation.id,
                "property_id": property_obj.id,
                "property_title": property_obj.title,
                "partner_id": partner.id,
                "role": participation.role,
                "status": participation.status,
            },
            status=status.HTTP_201_CREATED,
        )

    def get_queryset(self):
        partner = self._get_partner()

        queryset = (
            Property.objects
            .filter(
                Q(partner=partner)
                | Q(
                    partner_participations__partner=partner,
                    partner_participations__status__in=[
                        PropertyPartner.Status.PENDING,
                        PropertyPartner.Status.ACTIVE,
                    ],
                )
            )
            .select_related("partner")
            .prefetch_related(
                "photos",
                "videos",
                "partner_participations",
            )
            .distinct()
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