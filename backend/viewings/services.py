from django.db import transaction
from django.utils import timezone

from core.models import ActivityLog
from notifications.models import Notification

from .models import Viewing, ViewingEvent


@transaction.atomic
def send_partner_decline_to_fee_resolution(
    *,
    viewing,
    actor,
    reason,
    partner=None,
):
    """End scheduling safely when a partner declines a paid viewing.

    The successful payment stays untouched. The customer, rather than the
    partner, chooses whether Pata HAO should issue transferable viewing credit
    or process a full refund.
    """

    responded_at = timezone.now()

    if partner is not None:
        viewing.assigned_partner = partner

    viewing.status = Viewing.Status.SCHEDULING_FAILED
    viewing.partner_response_message = reason
    viewing.partner_responded_at = responded_at
    viewing.proposed_date = None
    viewing.proposed_time = None
    viewing.confirmed_date = None
    viewing.confirmed_time = None

    # A direct partner decline starts a new, unresolved fee-resolution step.
    viewing.fee_resolution_choice = ""
    viewing.fee_resolution_requested_at = None
    viewing.fee_resolution_reference = ""
    viewing.fee_resolution_notes = ""
    viewing.fee_resolution_processed_at = None
    viewing.fee_resolution_processed_by = None

    viewing.save(
        update_fields=[
            "assigned_partner",
            "status",
            "partner_response_message",
            "partner_responded_at",
            "proposed_date",
            "proposed_time",
            "confirmed_date",
            "confirmed_time",
            "fee_resolution_choice",
            "fee_resolution_requested_at",
            "fee_resolution_reference",
            "fee_resolution_notes",
            "fee_resolution_processed_at",
            "fee_resolution_processed_by",
            "updated_at",
        ]
    )

    viewing.record_event(
        event_type=ViewingEvent.EventType.SCHEDULING_FAILED,
        actor=actor,
        notes=reason,
        metadata={
            "trigger": "partner_declined",
            "declined_by": "partner",
            "fee_amount": str(viewing.fee_amount),
            "currency": "KES",
        },
    )

    Notification.objects.create(
        user=viewing.customer,
        title="Action required: choose fee resolution",
        message=(
            f"The partner declined your viewing for "
            f"{viewing.property.title}. Your KES {viewing.fee_amount:.2f} "
            "payment remains protected. Open the viewing to choose a "
            "transferable viewing credit or a full refund."
        ),
        notification_type=Notification.TYPE_VIEWING,
        action_label="Choose credit or refund",
    )

    ActivityLog.objects.create(
        actor=actor,
        action="viewing_partner_declined",
        entity_type="Viewing",
        entity_id=str(viewing.pk),
        description=(
            f"Partner declined viewing for {viewing.property.title}; "
            "the paid fee now requires customer resolution."
        ),
    )

    return viewing
