from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from commissions.models import CommissionAgreement
from core.models import ActivityLog
from properties.models import Property
from mandates.models import MandateEvent, PropertyMandate
from mandates.services import evaluate_property_publication
from properties.models import Property
from properties.service import PublishingEngine
from viewings.models import Viewing
from .services import (
    enforce_partner_operational_access,
    get_partner_capacity_summary,
    validate_partner_property_limit,
)
from django.utils import timezone

from deals.models import Deal
from partners.models import Partner




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


def _review_payload(property_obj):
    publishing = PublishingEngine.evaluate(property_obj)
    mandate_readiness = evaluate_property_publication(property_obj)
    capacity = _capacity_result(property_obj)
    agreement = _commission_agreement(property_obj)
    mandate = _latest_mandate(property_obj)

    photos = list(property_obj.photos.all())
    photo_count = len(photos)
    cover_photo = next((photo for photo in photos if photo.is_cover), None)

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
            "created_at": property_obj.created_at,
            "updated_at": property_obj.updated_at,
        },
        "partner": partner_data,
        "photos": {
            "count": photo_count,
            "required_for_publication": PublishingEngine.REQUIRED_PHOTO_COUNT,
            "cover_photo_id": cover_photo.id if cover_photo is not None else None,
        },
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

        pending_reviews = Property.objects.filter(
            status=Property.STATUS_PENDING,
        ).count()

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
            .prefetch_related("photos"),
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
            .filter(status=Property.STATUS_PENDING)
            .select_related(
                "partner",
                "partner__user",
                "partner__commission_plan",
            )
            .prefetch_related("photos")
            .order_by("created_at", "id")
        )

        results = [_review_payload(property_obj) for property_obj in properties]

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
            .prefetch_related("photos"),
            pk=property_id,
        )

        return Response(
            _review_payload(property_obj),
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

        return Response(_review_payload(property_obj), status=status.HTTP_200_OK)


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

        return Response(_review_payload(property_obj), status=status.HTTP_200_OK)


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

        return Response(_review_payload(property_obj), status=status.HTTP_200_OK)


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
                    "review": _review_payload(property_obj),
                },
                status=status.HTTP_409_CONFLICT,
            )

        if not result.can_publish:
            return Response(
                {
                    "detail": "The property cannot be published yet.",
                    "reasons": result.missing_requirements,
                    "review": _review_payload(property_obj),
                },
                status=status.HTTP_409_CONFLICT,
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
                "detail": "Property approved and published.",
                "property_id": property_obj.id,
                "status": property_obj.status,
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
            review = _review_payload(property_obj)
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
