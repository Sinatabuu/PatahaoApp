from django.contrib import admin

from .models import (
    IntroductionEvent,
    ProtectedIntroduction,
)


class IntroductionEventInline(admin.TabularInline):
    model = IntroductionEvent
    extra = 0
    can_delete = False

    fields = [
        "action",
        "notes",
        "actor",
        "metadata",
        "created_at",
    ]

    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(ProtectedIntroduction)
class ProtectedIntroductionAdmin(admin.ModelAdmin):
    list_display = [
        "certificate_number",
        "customer",
        "property",
        "partner",
        "status",
        "protected_from",
        "protected_until",
        "is_active",
    ]

    list_filter = [
        "status",
        "protected_from",
        "protected_until",
    ]

    search_fields = [
        "certificate_number",
        "customer__username",
        "customer_name_snapshot",
        "property__title",
        "property_title_snapshot",
        "owner_name_snapshot",
        "partner_name_snapshot",
        "mandate_number_snapshot",
        "commission_agreement_number_snapshot",
        "viewing_payment_reference",
    ]

    readonly_fields = [
        field.name
        for field in ProtectedIntroduction._meta.fields
    ]

    inlines = [
        IntroductionEventInline,
    ]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return request.user.is_staff


@admin.register(IntroductionEvent)
class IntroductionEventAdmin(admin.ModelAdmin):
    list_display = [
        "introduction",
        "action",
        "actor",
        "created_at",
    ]

    list_filter = [
        "action",
        "created_at",
    ]

    search_fields = [
        "introduction__certificate_number",
        "action",
        "notes",
    ]

    readonly_fields = [
        "introduction",
        "action",
        "notes",
        "actor",
        "metadata",
        "created_at",
    ]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False