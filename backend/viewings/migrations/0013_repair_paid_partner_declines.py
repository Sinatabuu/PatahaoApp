from django.db import migrations
from django.utils import timezone


def repair_paid_partner_declines(apps, schema_editor):
    Viewing = apps.get_model("viewings", "Viewing")
    ViewingEvent = apps.get_model("viewings", "ViewingEvent")
    Payment = apps.get_model("payments", "Payment")
    Notification = apps.get_model("notifications", "Notification")

    successful_viewing_ids = set(
        Payment.objects.filter(
            status="successful",
            viewing_id__isnull=False,
        ).values_list("viewing_id", flat=True)
    )

    legacy_ids = set(
        Viewing.objects.filter(
            id__in=successful_viewing_ids,
            status="declined",
        ).values_list("id", flat=True)
    )

    cancelled_events = ViewingEvent.objects.filter(
        viewing_id__in=successful_viewing_ids,
        viewing__status="cancelled",
        event_type="viewing_cancelled",
    ).values_list("viewing_id", "metadata")

    for viewing_id, metadata in cancelled_events.iterator():
        if (metadata or {}).get("cancelled_by") == "partner":
            legacy_ids.add(viewing_id)

    now = timezone.now()

    for viewing in Viewing.objects.filter(id__in=legacy_ids).select_related(
        "property",
    ):
        Viewing.objects.filter(pk=viewing.pk).update(
            status="scheduling_failed",
            proposed_date=None,
            proposed_time=None,
            confirmed_date=None,
            confirmed_time=None,
            fee_resolution_choice="",
            fee_resolution_requested_at=None,
            fee_resolution_reference="",
            fee_resolution_notes="",
            fee_resolution_processed_at=None,
            fee_resolution_processed_by_id=None,
            updated_at=now,
        )

        if not ViewingEvent.objects.filter(
            viewing_id=viewing.pk,
            event_type="scheduling_failed",
            metadata__trigger="partner_declined",
        ).exists():
            prior_event = (
                ViewingEvent.objects.filter(
                    viewing_id=viewing.pk,
                    event_type="viewing_cancelled",
                )
                .order_by("-created_at", "-id")
                .first()
            )

            ViewingEvent.objects.create(
                viewing_id=viewing.pk,
                event_type="scheduling_failed",
                actor_id=(prior_event.actor_id if prior_event else None),
                notes=(
                    viewing.partner_response_message
                    or "The partner declined this paid viewing."
                ),
                metadata={
                    "trigger": "partner_declined",
                    "declined_by": "partner",
                    "repair": "0013",
                    "fee_amount": str(viewing.fee_amount),
                    "currency": "KES",
                },
            )

        Notification.objects.get_or_create(
            user_id=viewing.customer_id,
            title="Action required: choose fee resolution",
            message=(
                f"The partner declined your viewing for "
                f"{viewing.property.title}. Your KES {viewing.fee_amount:.2f} "
                "payment remains protected. Open the viewing to choose a "
                "transferable viewing credit or a full refund."
            ),
            notification_type="viewing",
            defaults={
                "action_label": "Choose credit or refund",
            },
        )


class Migration(migrations.Migration):
    dependencies = [
        ("viewings", "0012_viewing_fee_resolution_notes_and_more"),
        (
            "payments",
            "0008_paymentattempt_payment_payment_reference_unique_and_more",
        ),
        ("notifications", "0002_notification_action_label_and_more"),
    ]

    operations = [
        migrations.RunPython(
            repair_paid_partner_declines,
            migrations.RunPython.noop,
        ),
    ]
