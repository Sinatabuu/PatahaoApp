from django.contrib import admin

from .models import (
    CustomerTrustScore,
    PartnerTrustScore,
    PropertyTrustScore,
    TrustScoreHistory,
)


@admin.register(PartnerTrustScore)
class PartnerTrustScoreAdmin(admin.ModelAdmin):
    list_display = (
        "partner",
        "score",
        "grade",
        "confidence",
        "average_rating",
        "successful_deals",
        "confirmed_violations",
        "active_restriction",
        "last_calculated_at",
    )

    list_filter = (
        "grade",
        "active_restriction",
        "permanently_banned",
    )

    search_fields = (
        "partner__display_name",
        "partner__business_name",
        "partner__partner_code",
    )

    readonly_fields = (
        "calculation_snapshot",
        "last_calculated_at",
        "created_at",
        "updated_at",
    )


@admin.register(CustomerTrustScore)
class CustomerTrustScoreAdmin(admin.ModelAdmin):
    list_display = (
        "customer",
        "score",
        "confidence",
        "completed_viewings",
        "feedback_count",
        "last_calculated_at",
    )


@admin.register(PropertyTrustScore)
class PropertyTrustScoreAdmin(admin.ModelAdmin):
    list_display = (
        "property",
        "score",
        "confidence",
        "average_rating",
        "feedback_count",
        "last_calculated_at",
    )


@admin.register(TrustScoreHistory)
class TrustScoreHistoryAdmin(admin.ModelAdmin):
    list_display = (
        "subject_type",
        "subject_id",
        "previous_score",
        "new_score",
        "reason",
        "created_at",
    )

    list_filter = (
        "subject_type",
    )

    search_fields = (
        "reason",
    )

    readonly_fields = (
        "created_at",
    )