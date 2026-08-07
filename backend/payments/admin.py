import uuid

from django.conf import settings
from django.contrib import admin, messages
from django.db import transaction
from django.utils import timezone
from .views import _complete_payment

from .models import Payment


@admin.action(description="DEV ONLY: Mark selected payments successful")
def mark_payments_successful(modeladmin, request, queryset):
    if not settings.DEBUG:
        modeladmin.message_user(
            request,
            "Development payment simulation is disabled outside DEBUG mode.",
            level=messages.ERROR,
        )
        return

    successful_count = 0
    skipped_count = 0

    payments = queryset.select_related("viewing")

    for payment in payments:
        if payment.status == Payment.Status.SUCCESSFUL:
            skipped_count += 1
            continue

        if payment.viewing is None:
            skipped_count += 1
            continue

        with transaction.atomic():
            now = timezone.now()
            mock_reference = uuid.uuid4().hex[:10].upper()

            payment.provider_response_code = "0"
            payment.provider_response_description = (
                "Development payment simulation completed successfully."
            )
            payment.callback_received_at = now
            payment.provider_callback_payload = {
                "development_simulation": True,
                "simulated_by_user_id": request.user.pk,
                "simulated_at": now.isoformat(),
            }

            payment.save(
                update_fields=[
                    "provider_response_code",
                    "provider_response_description",
                    "callback_received_at",
                    "provider_callback_payload",
                    "updated_at",
                ]
            )

            _complete_payment(
                payment,
                payment.viewing,
                provider_receipt=f"TEST{mock_reference}",
                transaction_date=now,
                actor=request.user,
            )

            successful_count += 1

    if successful_count:
        modeladmin.message_user(
            request,
            (
                f"{successful_count} payment(s) marked successful. "
                "Their viewings are now awaiting partner response."
            ),
            level=messages.SUCCESS,
        )

    if skipped_count:
        modeladmin.message_user(
            request,
            (
                f"{skipped_count} payment(s) skipped because they were already "
                "successful or had no linked viewing."
            ),
            level=messages.WARNING,
        )


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "payment_reference",
        "viewing",
        "payer",
        "purpose",
        "amount",
        "currency",
        "payment_method",
        "status",
        "receipt_number",
        "paid_at",
        "created_at",
    )

    list_filter = (
        "status",
        "payment_method",
        "purpose",
        "currency",
    )

    search_fields = (
        "payment_reference",
        "receipt_number",
        "provider_transaction_id",
        "provider_receipt_number",
        "phone_number",
        "payer__email",
        "payer__username",
    )

    readonly_fields = (
        "payment_reference",
        "receipt_number",
        "paid_at",
        "created_at",
        "updated_at",
    )

    actions = (
        mark_payments_successful,
    )

    def get_actions(self, request):
        actions = super().get_actions(request)

        if not settings.DEBUG:
            actions.pop("mark_payments_successful", None)

        return actions
