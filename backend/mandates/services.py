from dataclasses import dataclass

from django.core.exceptions import ValidationError

from mandates.models import PropertyMandate


@dataclass(frozen=True)
class PublicationReadiness:
    allowed: bool
    reasons: tuple[str, ...]
    mandate: PropertyMandate | None = None


def get_current_property_mandate(property_obj):
    return (
        PropertyMandate.objects
        .select_related(
            "owner",
            "partner",
            "commission_agreement",
        )
        .prefetch_related("documents")
        .filter(
            property=property_obj,
            status=PropertyMandate.Status.APPROVED,
        )
        .order_by("-version", "-approved_at")
        .first()
    )


def evaluate_property_publication(property_obj):
    reasons = []

    mandate = get_current_property_mandate(property_obj)

    if mandate is None:
        reasons.append(
            "An approved property mandate is required."
        )

        return PublicationReadiness(
            allowed=False,
            reasons=tuple(reasons),
            mandate=None,
        )

    if not mandate.owner.is_verified:
        reasons.append(
            "The property owner has not been verified."
        )

    if not mandate.owner_authority_confirmed:
        reasons.append(
            "The owner's authority over this property "
            "has not been confirmed."
        )

    if not mandate.has_approved_signed_document:
        reasons.append(
            "An approved signed property mandate is required."
        )

    if not mandate.no_cash_acknowledged:
        reasons.append(
            "The owner has not acknowledged the no-cash policy."
        )

    if not mandate.anti_circumvention_acknowledged:
        reasons.append(
            "The owner has not acknowledged the "
            "anti-circumvention rule."
        )

    if not mandate.commission_agreement.is_publish_ready():
        reasons.append(
            "The commission agreement is not confirmed, "
            "verified, and locked."
        )

    if not mandate.is_currently_valid:
        reasons.append(
            "The property mandate is not currently valid."
        )

    return PublicationReadiness(
        allowed=not reasons,
        reasons=tuple(reasons),
        mandate=mandate,
    )


def validate_property_publication(property_obj):
    readiness = evaluate_property_publication(
        property_obj,
    )

    if not readiness.allowed:
        raise ValidationError(
            {
                "status": list(readiness.reasons),
            }
        )

    return readiness