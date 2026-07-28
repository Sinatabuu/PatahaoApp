from django.contrib import admin

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
        "created_at",
    )

    list_filter = (
        "status",
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
        "created_at",
        "updated_at",
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