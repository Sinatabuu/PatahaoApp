from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from commissions.models import CommissionAgreement
from core.models import ActivityLog
from properties.models import Property, PropertyVideo
from mandates.models import MandateEvent, PropertyMandate
from mandates.services import evaluate_property_publication
from properties.service import PublishingEngine
from viewings.models import Viewing
from .services import (
    enforce_partner_operational_access,
    get_partner_capacity_summary,
    validate_partner_property_limit,
    request_deal_governance_review,
    staff_decide_deal_governance_case,

)
from django.utils import timezone

from deals.models import Deal
from partners.models import Partner
from governance.services import (
    enforce_partner_operational_access,
    request_deal_governance_review,
)

from .serializers import StaffDealGovernanceDecisionSerializer




def _validation_error_detail(exc):
    message_dict = getattr(exc, "message_dict", None)
    if message_dict is not None:
        return message_dict

    messages = getattr(exc, "messages", None)
    if messages is not None:
        return messages

    return str(exc)


def _latest_mandate(property_obj):
    return (
        PropertyMandate.objects
        .select_related(
            "owner",
            "partner",
            "partner__user",
            "commission_agreement",
            "commission_agreement__accepted_by",
            "commission_agreement__verified_by",
            "declared_by",
            "approved_by",
        )
        .filter(property=property_obj)
        .order_by("-version", "-id")
        .first()
    )


def _commission_agreement(property_obj):
    try:
        return property_obj.commission_agreement
    except CommissionAgreement.DoesNotExist:
        return None


def _capacity_result(property_obj):
    try:
        result = validate_partner_property_limit(property_obj)
        return {
            "allowed": True,
            "detail": result,
            "reasons": [],
        }
    except ValidationError as exc:
        return {
            "allowed": False,
            "detail": None,
            "reasons": [_validation_error_detail(exc)],
        }


def _flatten_reasons(value):
    results = []

    if isinstance(value, dict):
        for nested in value.values():
            results.extend(_flatten_reasons(nested))
        return results

    if isinstance(value, (list, tuple)):
        for nested in value:
            results.extend(_flatten_reasons(nested))
        return results

    text = str(value).strip()
    if text:
        results.append(text)

    return results


def _absolute_media_url(request, file_field):
    if not file_field:
        return None

    try:
        url = file_field.url
    except ValueError:
        return None

    if request is None:
        return url

    return request.build_absolute_uri(url)


def _video_payload(video, request=None):
    return {
        "id": video.id,
        "title": video.title,
        "description": video.description,
        "video_url": _absolute_media_url(request, video.video),
        "thumbnail_url": _absolute_media_url(
            request,
            video.thumbnail,
        ),
        "duration": video.duration,
        "file_size": video.file_size,
        "width": video.width,
        "height": video.height,
        "video_codec": video.video_codec,
        "audio_codec": video.audio_codec,
        "is_featured": video.is_featured,
        "review_status": video.review_status,
        "review_status_display": video.get_review_status_display(),
        "rejection_reason": video.rejection_reason,
        "reviewed_at": video.reviewed_at,
        "uploaded_at": video.uploaded_at,
    }


def _review_payload(property_obj, request=None):
    publishing = PublishingEngine.evaluate(property_obj)
    mandate_readiness = evaluate_property_publication(property_obj)
    capacity = _capacity_result(property_obj)
    agreement = _commission_agreement(property_obj)
    mandate = _latest_mandate(property_obj)

    photos = list(property_obj.photos.all())
    videos = list(property_obj.videos.all())
    photo_count = len(photos)
    cover_photo = next((photo for photo in photos if photo.is_cover), None)
    pending_videos = [
        video
        for video in videos
        if video.review_status == PropertyVideo.ReviewStatus.PENDING
    ]
    pending_video = pending_videos[0] if pending_videos else None

    property_review_required = (
        property_obj.status == Property.STATUS_PENDING
    )
    video_review_required = pending_video is not None

    if property_review_required and video_review_required:
        review_scope = "property_and_video"
        review_scope_display = "Property and video review"
    elif video_review_required:
        review_scope = "video"
        review_scope_display = "Video replacement review"
    else:
        review_scope = "property"
        review_scope_display = "Property review"

    queue_submitted_at = property_obj.updated_at

    if (
        property_obj.status == Property.STATUS_PUBLISHED
        and pending_video is not None
    ):
        queue_submitted_at = pending_video.uploaded_at

    commission_data = None
    if agreement is not None:
        commission_data = {
            "id": agreement.id,
            "agreement_number": agreement.agreement_number,
            "commission_method": agreement.commission_method,
            "commission_method_display": agreement.get_commission_method_display(),
            "commission_basis": agreement.commission_basis,
            "commission_basis_display": agreement.get_commission_basis_display(),
            "commission_rate": agreement.commission_rate,
            "fixed_commission_amount": agreement.fixed_commission_amount,
            "transaction_value": agreement.transaction_value,
            "expected_total_commission": agreement.expected_total_commission,
            "currency": agreement.currency,
            "partner_accepted": agreement.partner_accepted,
            "partner_accepted_at": agreement.partner_accepted_at,
            "is_verified": agreement.is_verified,
            "verified_at": agreement.verified_at,
            "is_locked": agreement.is_locked,
            "locked_at": agreement.locked_at,
            "status": agreement.status,
            "publish_ready": agreement.is_publish_ready(),
        }

    mandate_data = None
    if mandate is not None:
        mandate_data = {
            "id": mandate.id,
            "mandate_number": mandate.mandate_number,
            "version": mandate.version,
            "status": mandate.status,
            "status_display": mandate.get_status_display(),
            "authorization_method": mandate.authorization_method,
            "authorization_method_display": mandate.get_authorization_method_display(),
            "authorization_notes": mandate.authorization_notes,
            "owner": {
                "id": mandate.owner_id,
                "owner_number": mandate.owner.owner_number,
                "legal_name": mandate.owner.legal_name,
                "phone_number": mandate.owner.phone_number,
                "owner_type": mandate.owner.owner_type,
            },
            "owner_authority_confirmed": mandate.owner_authority_confirmed,
            "no_cash_acknowledged": mandate.no_cash_acknowledged,
            "anti_circumvention_acknowledged": mandate.anti_circumvention_acknowledged,
            "partner_declared": mandate.partner_declared,
            "partner_declared_at": mandate.partner_declared_at,
            "declaration_version": mandate.declaration_version,
            "submitted_at": mandate.submitted_at,
            "approved_at": mandate.approved_at,
            "rejection_reason": mandate.rejection_reason,
            "is_currently_valid": mandate.is_currently_valid,
        }

    blockers = list(publishing.missing_requirements)
    blockers.extend(mandate_readiness.reasons)

    if not capacity["allowed"]:
        blockers.extend(_flatten_reasons(capacity["reasons"]))

    ready_to_publish = (
        property_obj.status == Property.STATUS_PENDING
        and publishing.can_publish
        and mandate_readiness.allowed
        and capacity["allowed"]
    )

    partner = property_obj.partner
    partner_data = None
    if partner is not None:
        partner_data = {
            "id": partner.id,
            "display_name": (
                getattr(partner, "display_name", "")
                or getattr(partner, "business_name", "")
                or partner.user.get_full_name().strip()
                or partner.user.username
            ),
            "verification_status": partner.verification_status,
            "is_active": partner.is_active,
            "accepts_viewing_requests": partner.accepts_viewing_requests,
            "commission_plan_id": partner.commission_plan_id,
        }

    return {
        "property": {
            "id": property_obj.id,
            "title": property_obj.title,
            "property_type": property_obj.property_type,
            "listing_type": property_obj.listing_type,
            "price": property_obj.price,
            "county": property_obj.county,
            "town": property_obj.town,
            "estate": property_obj.estate,
            "latitude": property_obj.latitude,
            "longitude": property_obj.longitude,
            "status": property_obj.status,
            "verification_return_reason": property_obj.verification_return_reason,
            "amenities": [
                {
                    "id": amenity.id,
                    "name": amenity.name,
                    "slug": amenity.slug,
                    "icon": amenity.icon,
                    "display_order": amenity.display_order,
                }
                for amenity in property_obj.amenities.all()
            ],
            "created_at": property_obj.created_at,
            "updated_at": property_obj.updated_at,
        },
        "partner": partner_data,
        "photos": {
            "count": photo_count,
            "required_for_publication": PublishingEngine.REQUIRED_PHOTO_COUNT,
            "cover_photo_id": cover_photo.id if cover_photo is not None else None,
        },
        "videos": [_video_payload(video, request) for video in videos],
        "video_review": {
            "required": video_review_required,
            "pending_count": len(pending_videos),
            "pending_video_id": (
                pending_video.id
                if pending_video is not None
                else None
            ),
            "has_approved_video": any(
                video.review_status
                == PropertyVideo.ReviewStatus.APPROVED
                for video in videos
            ),
        },
        "review_scope": review_scope,
        "review_scope_display": review_scope_display,
        "property_review_required": property_review_required,
        "queue_submitted_at": queue_submitted_at,
        "commission": commission_data,
        "mandate": mandate_data,
        "publishing": {
            "can_publish": publishing.can_publish,
            "readiness_score": publishing.readiness_score,
            "passed_checks": publishing.passed_checks,
            "missing_requirements": publishing.missing_requirements,
        },
        "commercial_readiness": {
            "allowed": mandate_readiness.allowed,
            "reasons": list(mandate_readiness.reasons),
        },
        "capacity": capacity,
        "blockers": blockers,
        "ready_to_publish": ready_to_publish,
    }


class AdminOperationsSummaryView(APIView):
    """
    Staff-only operational summary for the Pata Hao admin dashboard.
    """

    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get(self, request):
        if not request.user.is_staff:
            return Response(
                {
                    "detail": (
                        "Only Pata Hao administrators may access "
                        "the operations dashboard."
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        today = timezone.localdate()

        pending_reviews = (
            Property.objects
            .filter(
                Q(status=Property.STATUS_PENDING)
                | Q(
                    status=Property.STATUS_PUBLISHED,
                    videos__review_status=(
                        PropertyVideo.ReviewStatus.PENDING
                    ),
                )
            )
            .distinct()
            .count()
        )

        pending_authorization_reviews = (
            PropertyMandate.objects
            .filter(
                status=PropertyMandate.Status.UNDER_REVIEW,
            )
            .count()
        )

        published_properties = Property.objects.filter(
            status=Property.STATUS_PUBLISHED,
        ).count()

        active_partners = Partner.objects.filter(
            verification_status=Partner.STATUS_APPROVED,
            is_active=True,
        ).count()

        todays_viewings = Viewing.objects.filter(
            requested_date=today,
        ).exclude(
            status__in=[
                Viewing.Status.CANCELLED,
                Viewing.Status.REFUNDED,
            ],
        ).count()

        open_deals = Deal.objects.exclude(
            status__in=[
                Deal.Status.COMPLETED,
                Deal.Status.CANCELLED,
            ],
        ).count()

        commission_activity = CommissionAgreement.objects.filter(
            updated_at__date=today,
        ).count()

        return Response(
            {
                "pending_reviews": pending_reviews,
                "pending_authorization_reviews": (
                    pending_authorization_reviews
                ),
                "published_properties": published_properties,
                "active_partners": active_partners,
                "todays_viewings": todays_viewings,
                "open_deals": open_deals,
                "commission_activity": commission_activity,
                "generated_for_date": today,
            },
            status=status.HTTP_200_OK,
        )

class StaffOnlyAPIView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get_pending_property(self, property_id):
        property_obj = get_object_or_404(
            Property.objects
            .select_related(
                "partner",
                "partner__user",
                "partner__commission_plan",
            )
            .prefetch_related("photos", "amenities", "videos")
            .select_for_update(),
            pk=property_id,
        )

        if property_obj.status != Property.STATUS_PENDING:
            return None, Response(
                {
                    "detail": (
                        "Only properties pending verification can be "
                        "reviewed through this workflow."
                    ),
                    "property_id": property_obj.id,
                    "status": property_obj.status,
                },
                status=status.HTTP_409_CONFLICT,
            )

        return property_obj, None

    def get_pending_video(self, property_id, video_id):
        property_obj = get_object_or_404(
            Property.objects
            .select_related(
                "partner",
                "partner__user",
                "partner__commission_plan",
            )
            .prefetch_related("photos", "amenities", "videos")
            .select_for_update(),
            pk=property_id,
        )

        if property_obj.status not in {
            Property.STATUS_PENDING,
            Property.STATUS_PUBLISHED,
        }:
            return None, None, Response(
                {
                    "detail": (
                        "Videos can only be reviewed for a property "
                        "awaiting review or already published."
                    ),
                    "property_id": property_obj.id,
                    "status": property_obj.status,
                },
                status=status.HTTP_409_CONFLICT,
            )

        video = get_object_or_404(
            PropertyVideo.objects.select_for_update(),
            pk=video_id,
            property=property_obj,
        )

        if video.review_status != PropertyVideo.ReviewStatus.PENDING:
            return None, None, Response(
                {
                    "detail": (
                        "Only a walkthrough awaiting review can be "
                        "approved or returned."
                    ),
                    "video_id": video.id,
                    "review_status": video.review_status,
                },
                status=status.HTTP_409_CONFLICT,
            )

        return property_obj, video, None


class MyPartnerCapacityView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.is_staff:
            return Response(
                {
                    "detail": (
                        "Staff accounts do not have partner listing capacity."
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        if getattr(request.user, "role", None) != "partner":
            return Response(
                {
                    "detail": (
                        "Only partner accounts may access partner capacity."
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        partner = getattr(request.user, "partner_profile", None)

        if partner is None:
            return Response(
                {
                    "detail": (
                        "This account does not have a partner profile."
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            enforce_partner_operational_access(
                partner,
                operation="view_partner_capacity",
            )
        except ValidationError as exc:
            return Response(
                {"detail": _validation_error_detail(exc)},
                status=status.HTTP_403_FORBIDDEN,
            )

        return Response(
            get_partner_capacity_summary(partner),
            status=status.HTTP_200_OK,
        )


class PropertyReviewListView(StaffOnlyAPIView):
    def get(self, request):
        properties = (
            Property.objects
            .filter(
                Q(status=Property.STATUS_PENDING)
                | Q(
                    status=Property.STATUS_PUBLISHED,
                    videos__review_status=(
                        PropertyVideo.ReviewStatus.PENDING
                    ),
                )
            )
            .select_related(
                "partner",
                "partner__user",
                "partner__commission_plan",
            )
            .prefetch_related("photos", "amenities", "videos")
            .distinct()
        )

        results = [
            _review_payload(property_obj, request)
            for property_obj in properties
        ]
        results.sort(
            key=lambda item: (
                item["queue_submitted_at"],
                item["property"]["id"],
            )
        )

        return Response(
            {"count": len(results), "results": results},
            status=status.HTTP_200_OK,
        )


class PropertyReviewDetailView(StaffOnlyAPIView):
    def get(self, request, property_id):
        property_obj = get_object_or_404(
            Property.objects
            .select_related(
                "partner",
                "partner__user",
                "partner__commission_plan",
            )
            .prefetch_related("photos", "amenities", "videos"),
            pk=property_id,
        )

        return Response(
            _review_payload(property_obj, request),
            status=status.HTTP_200_OK,
        )


class VerifyCommissionReviewView(StaffOnlyAPIView):
    @transaction.atomic
    def post(self, request, property_id):
        property_obj, error_response = self.get_pending_property(property_id)
        if error_response is not None:
            return error_response

        agreement = _commission_agreement(property_obj)
        if agreement is None:
            return Response(
                {"detail": "This property does not have a commission agreement."},
                status=status.HTTP_409_CONFLICT,
            )

        agreement = CommissionAgreement.objects.select_for_update().get(pk=agreement.pk)

        if not agreement.is_verified:
            try:
                agreement.verify(verified_by=request.user)
                agreement.save()
            except ValidationError as exc:
                return Response(
                    {"detail": _validation_error_detail(exc)},
                    status=status.HTTP_409_CONFLICT,
                )

            ActivityLog.objects.create(
                actor=request.user,
                action="commission_agreement_verified",
                entity_type="CommissionAgreement",
                entity_id=str(agreement.id),
                description=(
                    f"{request.user} verified commission agreement "
                    f"{agreement.agreement_number} for {property_obj.title}."
                ),
            )

        return Response(
            _review_payload(property_obj, request),
            status=status.HTTP_200_OK,
        )


class LockCommissionReviewView(StaffOnlyAPIView):
    @transaction.atomic
    def post(self, request, property_id):
        property_obj, error_response = self.get_pending_property(property_id)
        if error_response is not None:
            return error_response

        agreement = _commission_agreement(property_obj)
        if agreement is None:
            return Response(
                {"detail": "This property does not have a commission agreement."},
                status=status.HTTP_409_CONFLICT,
            )

        agreement = CommissionAgreement.objects.select_for_update().get(pk=agreement.pk)

        if not agreement.is_locked:
            try:
                agreement.lock()
                agreement.save()
            except ValidationError as exc:
                return Response(
                    {"detail": _validation_error_detail(exc)},
                    status=status.HTTP_409_CONFLICT,
                )

            ActivityLog.objects.create(
                actor=request.user,
                action="commission_agreement_locked",
                entity_type="CommissionAgreement",
                entity_id=str(agreement.id),
                description=(
                    f"{request.user} locked commission agreement "
                    f"{agreement.agreement_number} for {property_obj.title}."
                ),
            )

        return Response(
            _review_payload(property_obj, request),
            status=status.HTTP_200_OK,
        )


class ApproveMandateReviewView(StaffOnlyAPIView):
    @transaction.atomic
    def post(self, request, property_id):
        property_obj, error_response = self.get_pending_property(property_id)
        if error_response is not None:
            return error_response

        mandate = _latest_mandate(property_obj)
        if mandate is None:
            return Response(
                {"detail": "This property does not have a digital mandate."},
                status=status.HTTP_409_CONFLICT,
            )

        mandate = (
            PropertyMandate.objects
            .select_for_update()
            .select_related(
                "owner",
                "partner",
                "partner__user",
                "commission_agreement",
            )
            .get(pk=mandate.pk)
        )

        if mandate.status != PropertyMandate.Status.APPROVED:
            try:
                mandate.approve(approved_by=request.user)
                mandate.save()
            except ValidationError as exc:
                return Response(
                    {"detail": _validation_error_detail(exc)},
                    status=status.HTTP_409_CONFLICT,
                )

            MandateEvent.objects.create(
                mandate=mandate,
                action="approved",
                actor=request.user,
                notes=(
                    "Digital property mandate approved through the Pata Hao review desk."
                ),
                metadata={
                    "declaration_version": mandate.declaration_version,
                    "commission_agreement_id": mandate.commission_agreement_id,
                },
            )

            ActivityLog.objects.create(
                actor=request.user,
                action="property_mandate_approved",
                entity_type="PropertyMandate",
                entity_id=str(mandate.id),
                description=(
                    f"{request.user} approved mandate {mandate.mandate_number} "
                    f"for {property_obj.title}."
                ),
            )

        return Response(
            _review_payload(property_obj, request),
            status=status.HTTP_200_OK,
        )


class PublishPropertyReviewView(StaffOnlyAPIView):
    @transaction.atomic
    def post(self, request, property_id):
        property_obj, error_response = self.get_pending_property(property_id)
        if error_response is not None:
            return error_response

        try:
            result = PublishingEngine.publish(property_obj)
        except ValidationError as exc:
            return Response(
                {
                    "detail": "The property cannot be published.",
                    "reasons": _validation_error_detail(exc),
                    "review": _review_payload(property_obj, request),
                },
                status=status.HTTP_409_CONFLICT,
            )

        if not result.can_publish:
            return Response(
                {
                    "detail": "The property cannot be published yet.",
                    "reasons": result.missing_requirements,
                    "review": _review_payload(property_obj, request),
                },
                status=status.HTTP_409_CONFLICT,
            )

        pending_videos = list(
            PropertyVideo.objects
            .select_for_update()
            .filter(
                property=property_obj,
                review_status=PropertyVideo.ReviewStatus.PENDING,
            )
        )

        approved_video_ids = []

        for video in pending_videos:
            video.approve(reviewed_by=request.user)
            approved_video_ids.append(video.id)
            ActivityLog.objects.create(
                actor=request.user,
                action="property_video_approved",
                entity_type="PropertyVideo",
                entity_id=str(video.id),
                description=(
                    "Approved a walkthrough video during the initial "
                    f"Flutter staff review of {property_obj.title}."
                ),
            )

        ActivityLog.objects.create(
            actor=request.user,
            action="property_approved_and_published",
            entity_type="Property",
            entity_id=str(property_obj.id),
            description=(
                f"{request.user} approved and published {property_obj.title} "
                "through the Pata Hao review desk."
            ),
        )

        return Response(
            {
                "detail": (
                    "Property and walkthrough approved and published."
                    if approved_video_ids
                    else "Property approved and published."
                ),
                "property_id": property_obj.id,
                "status": property_obj.status,
                "approved_video_ids": approved_video_ids,
                "publishing": {
                    "readiness_score": result.readiness_score,
                    "passed_checks": result.passed_checks,
                },
            },
            status=status.HTTP_200_OK,
        )


class ReturnPropertyToPartnerReviewView(StaffOnlyAPIView):
    @transaction.atomic
    def post(self, request, property_id):
        property_obj, error_response = self.get_pending_property(property_id)
        if error_response is not None:
            return error_response

        requested_reason = str(request.data.get("reason", "")).strip()

        if requested_reason:
            reason = requested_reason
        else:
            review = _review_payload(property_obj, request)
            reason = "; ".join(
                str(blocker)
                for blocker in review["blockers"]
                if str(blocker).strip()
            )

            if not reason:
                reason = "Returned by Pata Hao for additional review."

        property_obj.status = Property.STATUS_DRAFT
        property_obj.verification_return_reason = reason
        property_obj.save(
            update_fields=[
                "status",
                "verification_return_reason",
                "updated_at",
            ]
        )

        ActivityLog.objects.create(
            actor=request.user,
            action="property_returned_to_draft",
            entity_type="Property",
            entity_id=str(property_obj.id),
            description=(
                f"{request.user} returned {property_obj.title} to the partner. "
                f"Reason: {reason}"
            ),
        )

        return Response(
            {
                "detail": "Property returned to partner.",
                "property_id": property_obj.id,
                "status": property_obj.status,
                "reason": reason,
            },
            status=status.HTTP_200_OK,
        )


class ApprovePropertyVideoReviewView(StaffOnlyAPIView):
    @transaction.atomic
    def post(self, request, property_id, video_id):
        property_obj, video, error_response = self.get_pending_video(
            property_id,
            video_id,
        )

        if error_response is not None:
            return error_response

        if property_obj.status != Property.STATUS_PUBLISHED:
            return Response(
                {
                    "detail": (
                        "Approve an initial walkthrough together with "
                        "the property by using Publish Property."
                    ),
                },
                status=status.HTTP_409_CONFLICT,
            )

        try:
            replaced_video_ids = video.approve(
                reviewed_by=request.user,
            )
        except ValidationError as exc:
            return Response(
                {"detail": _validation_error_detail(exc)},
                status=status.HTTP_409_CONFLICT,
            )

        ActivityLog.objects.create(
            actor=request.user,
            action="property_video_approved",
            entity_type="PropertyVideo",
            entity_id=str(video.id),
            description=(
                f"{request.user} approved a replacement walkthrough "
                f"for {property_obj.title} through the Flutter staff "
                "review desk."
            ),
        )

        property_obj = (
            Property.objects
            .select_related(
                "partner",
                "partner__user",
                "partner__commission_plan",
            )
            .prefetch_related("photos", "amenities", "videos")
            .get(pk=property_obj.pk)
        )

        payload = _review_payload(property_obj, request)
        payload["detail"] = "Walkthrough video approved."
        payload["approved_video_id"] = video.id
        payload["replaced_video_ids"] = replaced_video_ids

        return Response(payload, status=status.HTTP_200_OK)


class ReturnPropertyVideoReviewView(StaffOnlyAPIView):
    @transaction.atomic
    def post(self, request, property_id, video_id):
        property_obj, video, error_response = self.get_pending_video(
            property_id,
            video_id,
        )

        if error_response is not None:
            return error_response

        reason = str(request.data.get("reason", "")).strip()

        if not reason:
            return Response(
                {"detail": "A video return reason is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            video.reject(
                reviewed_by=request.user,
                reason=reason,
            )
        except ValidationError as exc:
            return Response(
                {"detail": _validation_error_detail(exc)},
                status=status.HTTP_409_CONFLICT,
            )

        ActivityLog.objects.create(
            actor=request.user,
            action="property_video_returned",
            entity_type="PropertyVideo",
            entity_id=str(video.id),
            description=(
                f"{request.user} returned a walkthrough video for "
                f"{property_obj.title}. Reason: {reason}"
            ),
        )

        property_obj = (
            Property.objects
            .select_related(
                "partner",
                "partner__user",
                "partner__commission_plan",
            )
            .prefetch_related("photos", "amenities", "videos")
            .get(pk=property_obj.pk)
        )

        payload = _review_payload(property_obj, request)
        payload["detail"] = "Walkthrough video returned to the partner."
        payload["returned_video_id"] = video.id

        return Response(payload, status=status.HTTP_200_OK)

from django.core.exceptions import ValidationError
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import DealGovernanceCase
from .services import request_deal_governance_review


class PartnerDealGovernanceCaseDetailView(APIView):
    """
    Partner read-only view of one governance case assigned
    to their partner profile.
    """

    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get(self, request, case_id):
        partner = getattr(
            request.user,
            "partner_profile",
            None,
        )

        if partner is None:
            return Response(
                {
                    "detail": "A partner account is required.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        case = (
            DealGovernanceCase.objects
            .select_related(
                "deal",
                "deal__property",
                "deal__partner",
            )
            .filter(
                pk=case_id,
                partner=partner,
            )
            .first()
        )

        if case is None:
            return Response(
                {
                    "detail": "Governance case not found.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            {
                "id": case.id,
                "deal_id": case.deal_id,
                "deal_number": case.deal.deal_number,
                "property_id": case.deal.property_id,
                "property_title": case.deal.property.title,
                "status": case.status,
                "reason_code": case.reason_code,
                "title": case.title,
                "message": case.message,
                "responsible_role": case.responsible_role,
                "action_code": case.action_code,
                "action_label": case.action_label,
                "created_at": case.created_at,
                "updated_at": case.updated_at,
            },
            status=status.HTTP_200_OK,
        )


class PartnerDealGovernanceCaseListView(APIView):
    """
    Return open governance cases currently assigned to the
    authenticated partner.

    Notifications alert the partner.
    This endpoint is the source of truth for active partner work.
    """

    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get(self, request):
        partner = getattr(
            request.user,
            "partner_profile",
            None,
        )

        if partner is None:
            return Response(
                {
                    "detail": "A partner account is required.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            enforce_partner_operational_access(
                partner,
                operation="view_governance_cases",
            )
        except ValidationError as exc:
            detail = getattr(
                exc,
                "message_dict",
                None,
            )

            if detail is None:
                detail = getattr(
                    exc,
                    "messages",
                    None,
                )

            if detail is None:
                detail = str(exc)

            return Response(
                {
                    "detail": detail,
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        cases = (
            DealGovernanceCase.objects
            .select_related(
                "deal",
                "deal__property",
                "deal__partner",
            )
            .filter(
                partner=partner,
                status=DealGovernanceCase.Status.OPEN,
                responsible_role=(
                    DealGovernanceCase
                    .ResponsibleRole
                    .PARTNER
                ),
            )
            .order_by(
                "-created_at",
                "-id",
            )
        )

        results = []

        for case in cases:
            results.append(
                {
                    "id": case.id,
                    "deal_id": case.deal_id,
                    "deal_number": (
                        case.deal.deal_number
                    ),
                    "property_id": (
                        case.deal.property_id
                    ),
                    "property_title": (
                        case.deal.property.title
                    ),
                    "status": case.status,
                    "reason_code": (
                        case.reason_code
                    ),
                    "title": case.title,
                    "message": case.message,
                    "responsible_role": (
                        case.responsible_role
                    ),
                    "action_code": (
                        case.action_code
                    ),
                    "action_label": (
                        case.action_label
                    ),
                    "created_at": (
                        case.created_at
                    ),
                    "updated_at": (
                        case.updated_at
                    ),
                }
            )

        return Response(
            {
                "count": len(results),
                "results": results,
            },
            status=status.HTTP_200_OK,
        )

class PartnerRequestGovernanceReviewView(APIView):
    """
    Partner formally hands a governance block to Pata Hao
    staff for investigation.
    """

    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def post(self, request, case_id):
        try:
            case = request_deal_governance_review(
                case_id=case_id,
                actor=request.user,
            )

        except DealGovernanceCase.DoesNotExist:
            return Response(
                {
                    "detail": "Governance case not found.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        except ValidationError as exc:
            detail = getattr(
                exc,
                "messages",
                None,
            ) or str(exc)

            return Response(
                {
                    "detail": detail,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "id": case.id,
                "status": case.status,
                "responsible_role": (
                    case.responsible_role
                ),
                "action_code": case.action_code,
                "action_label": case.action_label,
                "message": (
                    "Governance review requested successfully. "
                    "The case is now awaiting Pata Hao staff."
                ),
            },
            status=status.HTTP_200_OK,
        )

class StaffDealGovernanceCaseListView(APIView):
    """
    Staff queue of open governance cases currently
    awaiting Pata Hao action.
    """

    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get(self, request):
        if not request.user.is_staff:
            return Response(
                {
                    "detail": (
                        "Only Pata Hao administrators may "
                        "access governance review cases."
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        cases = (
            DealGovernanceCase.objects
            .select_related(
                "deal",
                "deal__property",
                "deal__partner",
                "deal__partner__user",
                "partner",
            )
            .filter(
                status=DealGovernanceCase.Status.OPEN,
                responsible_role=(
                    DealGovernanceCase
                    .ResponsibleRole
                    .STAFF
                ),
            )
            .order_by(
                "-updated_at",
                "-id",
            )
        )

        results = []

        for case in cases:
            results.append(
                {
                    "id": case.id,
                    "deal_id": case.deal_id,
                    "deal_number": (
                        case.deal.deal_number
                    ),
                    "property_id": (
                        case.deal.property_id
                    ),
                    "property_title": (
                        case.deal.property.title
                    ),
                    "partner_id": (
                        case.deal.partner_id
                    ),
                    "partner_name": str(
                        case.deal.partner
                    ),
                    "status": case.status,
                    "reason_code": (
                        case.reason_code
                    ),
                    "title": case.title,
                    "message": case.message,
                    "responsible_role": (
                        case.responsible_role
                    ),
                    "action_code": (
                        case.action_code
                    ),
                    "action_label": (
                        case.action_label
                    ),
                    "created_at": (
                        case.created_at
                    ),
                    "updated_at": (
                        case.updated_at
                    ),
                }
            )

        return Response(
            {
                "count": len(results),
                "results": results,
            },
            status=status.HTTP_200_OK,
        )

class StaffDealGovernanceCaseDecisionView(APIView):
    """
    Staff decision endpoint for one open governance case.
    """

    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def post(self, request, case_id):
        if not request.user.is_staff:
            return Response(
                {
                    "detail": (
                        "Only Pata Hao administrators may "
                        "decide governance cases."
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = (
            StaffDealGovernanceDecisionSerializer(
                data=request.data,
            )
        )

        serializer.is_valid(
            raise_exception=True,
        )

        try:
            case, governance = (
                staff_decide_deal_governance_case(
                    case_id=case_id,
                    actor=request.user,
                    decision=(
                        serializer.validated_data[
                            "decision"
                        ]
                    ),
                    notes=(
                        serializer.validated_data.get(
                            "notes",
                            "",
                        )
                    ),
                )
            )

        except DealGovernanceCase.DoesNotExist:
            return Response(
                {
                    "detail": (
                        "Governance case not found."
                    ),
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        except ValidationError as exc:
            detail = getattr(
                exc,
                "message_dict",
                None,
            )

            if detail is None:
                detail = getattr(
                    exc,
                    "messages",
                    None,
                )

            if detail is None:
                detail = str(exc)

            return Response(
                {
                    "detail": detail,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "id": case.id,
                "status": case.status,
                "responsible_role": (
                    case.responsible_role
                ),
                "action_code": (
                    case.action_code
                ),
                "action_label": (
                    case.action_label
                ),
                "resolved_by": (
                    case.resolved_by_id
                ),
                "resolved_at": (
                    case.resolved_at
                ),
                "resolution_notes": (
                    case.resolution_notes
                ),
                "governance": governance,
            },
            status=status.HTTP_200_OK,
        )
