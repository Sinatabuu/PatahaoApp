from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.db import transaction

from mandates.models import (
    MandateDocument,
    MandateEvent,
    PropertyMandate,
)


@dataclass(frozen=True)
class PublicationReadiness:
    allowed: bool
    reasons: tuple[str, ...]
    mandate: PropertyMandate | None = None



@transaction.atomic
def supersede_mandate_document(
    *,
    document_id,
    actor,
    file,
    notes="",
):
    """
    Replace current mandate evidence without altering its history.

    The existing document remains permanently intact and becomes
    non-current. A new document row is created as the current
    evidence and the transition is recorded in MandateEvent.
    """

    if actor is None or not actor.is_authenticated:
        raise ValidationError(
            "An authenticated user is required to replace mandate evidence."
        )

    if not actor.is_staff:
        raise ValidationError(
            "Only a Pata Hao administrator may supersede mandate evidence."
        )

    if file is None:
        raise ValidationError(
            "A replacement evidence file is required."
        )

    current_document = (
        MandateDocument.objects
        .select_for_update()
        .select_related(
            "mandate",
        )
        .get(
            pk=document_id,
        )
    )

    if not current_document.is_current:
        raise ValidationError(
            "Only the current mandate document may be superseded."
        )

    old_document_id = current_document.id
    old_file_hash = current_document.file_hash

    current_document.is_current = False
    current_document.save(
        update_fields=[
            "is_current",
        ],
    )

    new_document = MandateDocument.objects.create(
        mandate=current_document.mandate,
        document_type=current_document.document_type,
        file=file,
        status=MandateDocument.Status.UPLOADED,
        is_current=True,
        uploaded_by=actor,
    )

    MandateEvent.objects.create(
        mandate=current_document.mandate,
        action="document_superseded",
        actor=actor,
        notes=(notes or "").strip(),
        metadata={
            "document_type": current_document.document_type,
            "old_document_id": old_document_id,
            "old_file_hash": old_file_hash,
            "new_document_id": new_document.id,
            "new_file_hash": new_document.file_hash,
        },
    )

    return new_document

@transaction.atomic
def reject_mandate_document(
    *,
    document_id,
    actor,
    reason,
):
    """
    Reject current mandate evidence and record the decision atomically.
    """

    if actor is None or not actor.is_authenticated:
        raise ValidationError(
            "An authenticated user is required to reject mandate evidence."
        )

    if not actor.is_staff:
        raise ValidationError(
            "Only a Pata Hao administrator may reject mandate evidence."
        )

    cleaned_reason = (reason or "").strip()

    if not cleaned_reason:
        raise ValidationError(
            "A document rejection reason is required."
        )

    document = (
        MandateDocument.objects
        .select_for_update()
        .select_related(
            "mandate",
        )
        .get(
            pk=document_id,
        )
    )

    previous_status = document.status

    document.reject(
        reviewed_by=actor,
        reason=cleaned_reason,
    )

    MandateEvent.objects.create(
        mandate=document.mandate,
        action="document_rejected",
        actor=actor,
        notes=cleaned_reason,
        metadata={
            "document_id": document.id,
            "file_hash": document.file_hash,
            "document_type": document.document_type,
            "previous_status": previous_status,
            "new_status": document.status,
            "is_current": document.is_current,
        },
    )

    return document


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



def evaluate_sale_mandate_evidence(mandate):
    """
    Return the missing evidence required before a sale property
    may be published.

    The database evidence is authoritative. Staff or Flutter
    cannot satisfy these requirements with manual booleans.
    """

    reasons = []

    if not mandate.owner.is_verified:
        reasons.append(
            "The property owner must be verified before a sale property "
            "can be published."
        )

    approved_current_document_types = set(
        mandate.documents.filter(
            status=MandateDocument.Status.APPROVED,
            is_current=True,
        ).values_list(
            "document_type",
            flat=True,
        )
    )

    required_documents = {
        MandateDocument.DocumentType.OWNER_ID:
            "Approved owner identification is required for a sale property.",
        MandateDocument.DocumentType.OWNERSHIP_PROOF:
            "Approved ownership proof is required for a sale property.",
        MandateDocument.DocumentType.SIGNED_MANDATE:
            "An approved signed sale mandate is required for a sale property.",
    }

    for document_type, reason in required_documents.items():
        if document_type not in approved_current_document_types:
            reasons.append(reason)

    return tuple(reasons)


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

    if property_obj.listing_type == property_obj.LISTING_SALE:
        reasons.extend(
            evaluate_sale_mandate_evidence(
                mandate,
            )
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



def get_sale_mandate_pack_status(mandate):
    """
    Build the read-only partner-facing three-step Sale Pack status.

    Private file paths are deliberately excluded.
    """

    property_obj = mandate.property

    sale_pack_required = (
        property_obj.listing_type
        == property_obj.LISTING_SALE
    )

    required_steps = (
        (
            "owner_identity",
            "Owner identity",
            MandateDocument.DocumentType.OWNER_ID,
        ),
        (
            "ownership_proof",
            "Ownership proof",
            MandateDocument.DocumentType.OWNERSHIP_PROOF,
        ),
        (
            "sale_authority",
            "Signed sale authority",
            MandateDocument.DocumentType.SIGNED_MANDATE,
        ),
    )

    current_documents = {
        document.document_type: document
        for document in mandate.documents.filter(
            document_type__in=[
                document_type
                for _key, _label, document_type
                in required_steps
            ],
            is_current=True,
        )
    }

    agreement = mandate.commission_agreement

    commission_ready = bool(
        agreement is not None
        and agreement.is_publish_ready()
    )

    steps = []

    if sale_pack_required:
        for key, label, document_type in required_steps:
            document = current_documents.get(
                document_type,
            )

            document_approved = bool(
                document is not None
                and document.status
                == MandateDocument.Status.APPROVED
            )

            checks = {
                "document_approved": document_approved,
            }

            if key == "owner_identity":
                checks["owner_verified"] = (
                    mandate.owner.is_verified
                )

            if key == "sale_authority":
                checks["partner_declared"] = (
                    mandate.partner_declared
                )
                checks["commission_agreement_ready"] = (
                    commission_ready
                )

            document_data = None

            if document is not None:
                document_data = {
                    "id": document.id,
                    "document_type": document.document_type,
                    "document_type_display": (
                        document.get_document_type_display()
                    ),
                    "original_filename": (
                        document.original_filename
                    ),
                    "file_hash": document.file_hash,
                    "file_size": document.file_size,
                    "status": document.status,
                    "status_display": (
                        document.get_status_display()
                    ),
                    "is_current": document.is_current,
                    "rejection_reason": (
                        document.rejection_reason
                    ),
                    "uploaded_at": document.uploaded_at,
                    "reviewed_at": document.reviewed_at,
                }

            steps.append(
                {
                    "key": key,
                    "label": label,
                    "completed": all(
                        checks.values(),
                    ),
                    "checks": checks,
                    "document": document_data,
                }
            )

    completed_steps = sum(
        1
        for step in steps
        if step["completed"]
    )

    readiness = evaluate_property_publication(
        property_obj,
    )

    return {
        "mandate_id": mandate.id,
        "mandate_number": mandate.mandate_number,
        "property_id": property_obj.id,
        "property_title": property_obj.title,
        "listing_type": property_obj.listing_type,
        "sale_pack_required": sale_pack_required,
        "completed_steps": completed_steps,
        "total_steps": len(steps),
        "pack_complete": (
            completed_steps == len(steps)
            if sale_pack_required
            else None
        ),
        "publication_allowed": readiness.allowed,
        "blocking_reasons": list(
            readiness.reasons,
        ),
        "administrative_review": {
            "mandate_status": mandate.status,
            "mandate_status_display": (
                mandate.get_status_display()
            ),
            "mandate_currently_valid": (
                mandate.is_currently_valid
            ),
        },
        "steps": steps,
    }



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
