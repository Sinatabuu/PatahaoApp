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

from .models import PartnerApplication


@admin.register(PartnerApplication)
class PartnerApplicationAdmin(admin.ModelAdmin):
    list_display = ('reference', 'full_name', 'county', 'operating_area', 'status', 'office_appointment', 'created_at')
    list_filter = ('status', 'county', 'training_availability', 'partner_type')
    search_fields = ('reference', 'full_name', 'phone_number', 'email')
    readonly_fields = ('reference', 'submission_key', 'consent_version', 'created_at', 'updated_at')
    fieldsets = (
        ('Application', {'fields': ('reference', 'full_name', 'phone_number', 'email', 'county', 'operating_area', 'partner_type', 'experience', 'training_availability')}),
        ('Office screening', {'fields': ('status', 'office_appointment'), 'description': 'Verify originals and keep sensitive identity records in the locked physical file identified by this application reference. This screen does not activate partner accounts.'}),
        ('Submission record', {'fields': ('submission_key', 'consent_version', 'created_at', 'updated_at')}),
    )

    def has_add_permission(self, request):
        return False
