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
            "commission_agreement__accepted_by",
            "commission_agreement__verified_by",
        )
        .filter(
            property=property_obj,
            status=PropertyMandate.Status.APPROVED,
        )
        .order_by(
            "-version",
            "-approved_at",
        )
        .first()
    )


def evaluate_property_publication(property_obj):
    reasons = []

    mandate = get_current_property_mandate(
        property_obj,
    )

    if mandate is None:
        reasons.append(
            "An approved digital property mandate is required."
        )

        return PublicationReadiness(
            allowed=False,
            reasons=tuple(reasons),
            mandate=None,
        )

    if not mandate.partner_declared:
        reasons.append(
            "The partner has not accepted the digital property mandate."
        )

    if mandate.partner_declared_at is None:
        reasons.append(
            "The partner mandate acceptance time is missing."
        )

    if mandate.declared_by_id is None:
        reasons.append(
            "The partner mandate acceptance user is missing."
        )

    if not mandate.owner_authority_confirmed:
        reasons.append(
            "The partner has not confirmed authority to market this property."
        )

    if not mandate.no_cash_acknowledged:
        reasons.append(
            "The partner has not acknowledged the Pata Hao payment policy."
        )

    if not mandate.anti_circumvention_acknowledged:
        reasons.append(
            "The partner has not acknowledged the anti-circumvention rule."
        )

    agreement = mandate.commission_agreement

    if agreement is None:
        reasons.append(
            "A commission agreement is required."
        )
    else:
        if not agreement.partner_accepted:
            reasons.append(
                "The partner has not accepted the commission agreement."
            )

        if agreement.partner_accepted_at is None:
            reasons.append(
                "The commission agreement acceptance time is missing."
            )

        if agreement.accepted_by_id is None:
            reasons.append(
                "The commission agreement accepting user is missing."
            )

        if not agreement.is_verified:
            reasons.append(
                "The commission agreement has not been verified by Pata Hao."
            )

        if not agreement.is_locked:
            reasons.append(
                "The commission agreement has not been locked."
            )

        if not agreement.is_publish_ready():
            reasons.append(
                "The commission agreement is not ready for publication."
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
