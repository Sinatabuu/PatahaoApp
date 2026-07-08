from django.contrib import admin
from .models import Partner


@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    list_display = (
        "business_name",
        "user",
        "partner_type",
        "county",
        "town",
        "verification_status",
        "commission_rate",
        "created_at",
    )

    list_filter = (
        "partner_type",
        "verification_status",
        "county",
    )

    search_fields = (
        "business_name",
        "user__username",
        "user__email",
        "phone_number",
    )