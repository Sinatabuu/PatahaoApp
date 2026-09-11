from django.contrib import admin, messages
from django.core.exceptions import ValidationError

from payments.services import fulfill_viewing_fee_resolution

from .models import Viewing
from .models import ViewingBooking, ViewingBookingItem

@admin.register(Viewing)
class ViewingAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "customer",
        "property",
        "requested_date",
        "requested_time",
        "fee_amount",
        "status",
        "reschedule_decline_count",
        "fee_resolution_choice",
        "fee_resolution_reference",
        "fee_resolution_processed_at",
        "created_at",
    )

    list_filter = (
        "status",
        "fee_resolution_choice",
        "requested_date",
        "created_at",
    )

    search_fields = (
        "customer__username",
        "customer__email",
        "payment_reference",
    )

    readonly_fields = (
        "fee_amount",
        "reschedule_decline_count",
        "fee_resolution_choice",
        "fee_resolution_requested_at",
        "fee_resolution_processed_at",
        "fee_resolution_processed_by",
        "created_at",
        "updated_at",
    )

    actions = (
        "process_selected_fee_resolutions",
    )

    def get_readonly_fields(self, request, obj=None):
        fields = tuple(super().get_readonly_fields(request, obj))

        if obj and obj.fee_resolution_processed_at:
            fields += (
                "fee_resolution_reference",
                "fee_resolution_notes",
            )

        return fields

    @admin.action(
        description="Process selected customer fee resolutions"
    )
    def process_selected_fee_resolutions(
        self,
        request,
        queryset,
    ):
        processed_count = 0
        already_processed_count = 0
        failed_count = 0

        for viewing in queryset:
            try:
                result = fulfill_viewing_fee_resolution(
                    viewing_id=viewing.pk,
                    processed_by=request.user,
                    provider_reference=(
                        viewing.fee_resolution_reference
                    ),
                    notes=viewing.fee_resolution_notes,
                )

                if result["already_processed"]:
                    already_processed_count += 1
                else:
                    processed_count += 1

            except ValidationError as exc:
                failed_count += 1
                self.message_user(
                    request,
                    f"Viewing {viewing.pk} was not processed: {exc}",
                    level=messages.ERROR,
                )

        if processed_count:
            self.message_user(
                request,
                f"{processed_count} fee resolution(s) processed.",
                level=messages.SUCCESS,
            )

        if already_processed_count:
            self.message_user(
                request,
                (
                    f"{already_processed_count} fee resolution(s) were "
                    "already processed and were not duplicated."
                ),
                level=messages.WARNING,
            )

        if failed_count:
            self.message_user(
                request,
                (
                    f"{failed_count} fee resolution(s) need correction "
                    "before processing."
                ),
                level=messages.ERROR,
            )


class ViewingBookingItemInline(admin.TabularInline):
    model = ViewingBookingItem
    extra = 0


@admin.register(ViewingBooking)
class ViewingBookingAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "customer",
        "booking_type",
        "viewing_date",
        "total_amount",
        "status",
        "assigned_partner",
        "created_at",
    )

    list_filter = (
        "booking_type",
        "status",
        "viewing_date",
    )

    readonly_fields = (
        "total_amount",
        "payment_reference",
        "created_at",
        "updated_at",
    )

    inlines = [ViewingBookingItemInline]
