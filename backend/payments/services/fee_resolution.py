from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from core.models import ActivityLog
from notifications.models import Notification
from viewings.models import Viewing, ViewingEvent

from ..models import Payment, ViewingCredit


@transaction.atomic
def fulfill_viewing_fee_resolution(
    *,
    viewing_id,
    processed_by,
    provider_reference="",
    notes="",
):
    """
    Fulfill one customer-selected viewing fee resolution.

    Refunds require an external provider reference so Pata HAO never marks
    money as returned before staff has evidence of the provider transaction.
    Credits create one durable ledger record for the successful payment.
    """

    if processed_by is None or not processed_by.is_authenticated:
        raise ValidationError(
            "An authenticated Pata HAO administrator is required."
        )

    if not processed_by.is_staff:
        raise ValidationError(
            "Only Pata HAO staff may process viewing fee resolutions."
        )

    viewing = (
        Viewing.objects.select_for_update()
        .select_related(
            "customer",
            "property",
        )
        .get(pk=viewing_id)
    )

    payment = (
        Payment.objects.select_for_update()
        .filter(viewing=viewing)
        .first()
    )

    if not viewing.fee_resolution_choice:
        raise ValidationError(
            {
                "fee_resolution_choice": (
                    "The customer has not chosen viewing credit or a refund."
                )
            }
        )

    choice = viewing.fee_resolution_choice

    if choice not in {
        Viewing.FeeResolutionChoice.CREDIT,
        Viewing.FeeResolutionChoice.REFUND,
    }:
        raise ValidationError(
            {"fee_resolution_choice": "The fee resolution choice is invalid."}
        )

    if payment is None:
        raise ValidationError(
            {"payment": "This viewing has no payment to resolve."}
        )

    if viewing.fee_resolution_processed_at is not None:
        credit = None

        if choice == Viewing.FeeResolutionChoice.REFUND:
            if (
                viewing.status != Viewing.Status.REFUNDED
                or payment.status != Payment.Status.REFUNDED
                or not payment.refund_reference
            ):
                raise ValidationError(
                    "The recorded refund resolution is incomplete and needs "
                    "manual review."
                )

            retry_reference = str(provider_reference or "").strip()

            if (
                retry_reference
                and retry_reference != payment.refund_reference
            ):
                raise ValidationError(
                    {
                        "provider_reference": (
                            "This refund was already processed with a "
                            "different provider reference."
                        )
                    }
                )
        else:
            credit = ViewingCredit.objects.filter(
                source_payment=payment,
                source_viewing=viewing,
            ).first()

            if (
                viewing.status != Viewing.Status.CREDIT_ISSUED
                or credit is None
            ):
                raise ValidationError(
                    "The recorded credit resolution is incomplete and needs "
                    "manual review."
                )

        return {
            "viewing": viewing,
            "payment": payment,
            "credit": credit,
            "already_processed": True,
        }

    if viewing.status != Viewing.Status.SCHEDULING_FAILED:
        raise ValidationError(
            {
                "status": (
                    "Only a scheduling-failed viewing can have its fee "
                    "resolution processed."
                )
            }
        )

    if payment.status != Payment.Status.SUCCESSFUL:
        raise ValidationError(
            {
                "payment": (
                    "Only a successful viewing payment can be refunded or "
                    "converted to credit."
                )
            }
        )

    now = timezone.now()
    resolution_notes = str(notes or viewing.fee_resolution_notes).strip()
    credit = None

    if choice == Viewing.FeeResolutionChoice.REFUND:
        refund_reference = str(
            provider_reference or viewing.fee_resolution_reference
        ).strip()

        if not refund_reference:
            raise ValidationError(
                {
                    "provider_reference": (
                        "Enter the payment-provider refund reference before "
                        "marking this refund as processed."
                    )
                }
            )

        duplicate_reference = Payment.objects.filter(
            refund_reference=refund_reference,
        ).exclude(pk=payment.pk)

        if duplicate_reference.exists():
            raise ValidationError(
                {
                    "provider_reference": (
                        "This refund reference is already attached to another "
                        "payment."
                    )
                }
            )

        payment.status = Payment.Status.REFUNDED
        payment.refund_reference = refund_reference
        payment.refund_notes = resolution_notes
        payment.refunded_at = now
        payment.refunded_by = processed_by
        try:
            with transaction.atomic():
                payment.save(
                    update_fields=[
                        "status",
                        "refund_reference",
                        "refund_notes",
                        "refunded_at",
                        "refunded_by",
                        "updated_at",
                    ]
                )
        except IntegrityError as exc:
            raise ValidationError(
                {
                    "provider_reference": (
                        "This refund reference is already attached to "
                        "another payment."
                    )
                }
            ) from exc

        viewing.status = Viewing.Status.REFUNDED
        viewing.fee_resolution_reference = refund_reference
        event_type = ViewingEvent.EventType.REFUND_ISSUED
        event_notes = "The viewing fee refund was confirmed by Pata HAO staff."
        notification_title = "Viewing fee refunded"
        notification_message = (
            f"Your {payment.amount} {payment.currency} viewing fee for "
            f"{viewing.property.title} has been marked refunded. Reference: "
            f"{refund_reference}."
        )
        activity_action = "viewing_refund_processed"
    else:
        credit = ViewingCredit.objects.create(
            customer=viewing.customer,
            source_payment=payment,
            source_viewing=viewing,
            amount=payment.amount,
            remaining_amount=payment.amount,
            currency=payment.currency,
            issued_by=processed_by,
        )

        viewing.status = Viewing.Status.CREDIT_ISSUED
        viewing.fee_resolution_reference = credit.credit_reference
        event_type = ViewingEvent.EventType.CREDIT_ISSUED
        event_notes = "A transferable viewing credit was issued."
        notification_title = "Viewing credit issued"
        notification_message = (
            f"A {credit.amount} {credit.currency} viewing credit was issued "
            f"for {viewing.property.title}. Reference: "
            f"{credit.credit_reference}."
        )
        activity_action = "viewing_credit_issued"

    viewing.fee_resolution_notes = resolution_notes
    viewing.fee_resolution_processed_at = now
    viewing.fee_resolution_processed_by = processed_by
    viewing.save(
        update_fields=[
            "status",
            "fee_resolution_reference",
            "fee_resolution_notes",
            "fee_resolution_processed_at",
            "fee_resolution_processed_by",
            "updated_at",
        ]
    )

    viewing.record_event(
        event_type=event_type,
        actor=processed_by,
        notes=event_notes,
        metadata={
            "choice": choice,
            "payment_id": payment.id,
            "amount": str(payment.amount),
            "currency": payment.currency,
            "resolution_reference": viewing.fee_resolution_reference,
        },
    )

    Notification.objects.create(
        user=viewing.customer,
        title=notification_title,
        message=notification_message,
        notification_type=Notification.TYPE_PAYMENT,
    )

    ActivityLog.objects.create(
        actor=processed_by,
        action=activity_action,
        entity_type="Viewing",
        entity_id=str(viewing.pk),
        description=(
            f"Processed {choice} for viewing {viewing.pk} using reference "
            f"{viewing.fee_resolution_reference}."
        ),
    )

    return {
        "viewing": viewing,
        "payment": payment,
        "credit": credit,
        "already_processed": False,
    }
