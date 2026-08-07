from django.contrib import admin

from .models import (
    PartnerDisciplinaryAction,
    PartnerPromotionReview,
    PartnerTier,
    PartnerTierAssignment,
    PartnerViolation,
    PartnerReinstatement,
    PolicyRule,
)

@admin.register(PartnerTier)
class PartnerTierAdmin(admin.ModelAdmin):
    list_display = (
        "rank",
        "name",
        "property_limit",
        "minimum_completed_deals",
        "minimum_trust_score",
        "active",
    )

    ordering = (
        "rank",
    )


@admin.register(PartnerTierAssignment)
class PartnerTierAssignmentAdmin(admin.ModelAdmin):
    list_display = (
        "partner",
        "tier",
        "active",
        "assigned_at",
        "ended_at",
    )

    list_filter = (
        "tier",
        "active",
    )

    search_fields = (
        "partner__display_name",
        "partner__business_name",
    )


@admin.register(PartnerPromotionReview)
class PartnerPromotionReviewAdmin(admin.ModelAdmin):
    list_display = (
        "partner",
        "current_tier",
        "proposed_tier",
        "completed_deals",
        "trust_score",
        "decision",
        "reviewed_at",
    )

    list_filter = (
        "decision",
    )

    search_fields = (
        "partner__display_name",
        "partner__business_name",
    )
@admin.register(PartnerDisciplinaryAction)
class PartnerDisciplinaryActionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "partner",
        "action_type",
        "status",
        "starts_at",
        "ends_at",
        "imposed_by",
    )

    list_filter = (
        "action_type",
        "status",
    )

    search_fields = (
        "partner__display_name",
        "partner__business_name",
        "violation__policy__code",
        "violation__summary",
        "reason",
    )

    readonly_fields = (
        "created_at",
        "revoked_at",
    )

    autocomplete_fields = (
        "partner",
        "imposed_by",
        "revoked_by",
    )

    raw_id_fields = (
        "violation",
    )

@admin.register(PartnerReinstatement)
class PartnerReinstatementAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "partner",
        "approved_by",
        "reinstated_at",
    )

    search_fields = (
        "partner__display_name",
        "partner__business_name",
        "reason",
    )

    readonly_fields = (
        "reinstated_at",
    )

    autocomplete_fields = (
        "partner",
        "approved_by",
    )

    filter_horizontal = (
        "reviewed_actions",
    )