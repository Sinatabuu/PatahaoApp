from django.contrib import admin

from .models import (
    PartnerDisciplinaryAction,
    PartnerPromotionReview,
    PartnerTier,
    PartnerTierAssignment,
    PartnerReinstatement,
    PartnerViolation,
    PolicyRule,
)

@admin.register(PolicyRule)
class PolicyRuleAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "title",
        "severity",
        "recommended_action",
        "active",
        "effective_from",
    )
    list_filter = (
        "severity",
        "recommended_action",
        "active",
    )
    search_fields = (
        "code",
        "title",
        "description",
    )


@admin.register(PartnerViolation)
class PartnerViolationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "partner",
        "policy",
        "status",
        "reported_by",
        "reviewed_by",
        "reported_at",
    )
    list_filter = (
        "status",
        "policy",
    )
    search_fields = (
        "partner__display_name",
        "partner__business_name",
        "policy__code",
        "summary",
        "details",
    )
    readonly_fields = (
        "partner",
        "policy",
        "status",
        "summary",
        "details",
        "evidence_snapshot",
        "reported_by",
        "reviewed_by",
        "reported_at",
        "review_started_at",
        "decided_at",
        "decision_notes",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(
        self,
        request,
        obj=None,
    ):
        return False

    def has_delete_permission(
        self,
        request,
        obj=None,
    ):
        return False


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
        "violation",
        "partner",
        "action_type",
        "status",
        "reason",
        "decision_snapshot",
        "imposed_by",
        "starts_at",
        "ends_at",
        "created_at",
        "revoked_by",
        "revoked_at",
        "revocation_reason",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(
        self,
        request,
        obj=None,
    ):
        return False

    def has_delete_permission(
        self,
        request,
        obj=None,
    ):
        return False


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
        "partner",
        "reviewed_actions",
        "approved_by",
        "reason",
        "evidence_snapshot",
        "reinstated_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(
        self,
        request,
        obj=None,
    ):
        return False

    def has_delete_permission(
        self,
        request,
        obj=None,
    ):
        return False