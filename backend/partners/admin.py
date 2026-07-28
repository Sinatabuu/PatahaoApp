from django.contrib import admin

from .models import Partner


@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    list_display = (
        "business_name",
        "partner_type",
        "partner_code",
        "county",
        "town",
        "verification_status",
        "is_active",
        "accepts_viewing_requests",
        "created_at",
    )

    list_filter = (
        "partner_type",
        "verification_status",
        "is_active",
        "accepts_viewing_requests",
        "county",
    )

    search_fields = (
        "business_name",
        "display_name",
        "partner_code",
        "phone_number",
        "user__username",
        "user__email",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )