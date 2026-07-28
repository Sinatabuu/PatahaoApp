from django.contrib import admin

from .models import Deal, DealOutcome


class DealOutcomeInline(admin.TabularInline):
    model = DealOutcome
    extra = 0
    readonly_fields = [
        "created_at",
    ]


@admin.register(Deal)
class DealAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "property",
        "customer",
        "partner",
        "status",
        "customer_confirmed",
        "partner_confirmed",
        "commission_amount",
        "created_at",
    ]

    list_filter = [
        "status",
        "customer_confirmed",
        "partner_confirmed",
        "property__listing_type",
        "created_at",
    ]

    search_fields = [
        "property__title",
        "customer__username",
        "customer__email",
    ]

    readonly_fields = [
        "created_at",
        "updated_at",
    ]

    autocomplete_fields = [
        "customer",
        "partner",
        "property",
        "viewing",
    ]

    inlines = [
        DealOutcomeInline,
    ]


@admin.register(DealOutcome)
class DealOutcomeAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "deal",
        "reporter",
        "outcome",
        "created_at",
    ]

    list_filter = [
        "reporter",
        "outcome",
        "created_at",
    ]

    search_fields = [
        "deal__property__title",
        "deal__customer__username",
        "notes",
    ]

    readonly_fields = [
        "created_at",
    ]

    autocomplete_fields = [
        "deal",
    ]