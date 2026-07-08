from django.contrib import admin
from .models import ActivityLog


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = (
        "actor",
        "action",
        "entity_type",
        "entity_id",
        "created_at",
    )

    list_filter = (
        "action",
        "entity_type",
        "created_at",
    )

    search_fields = (
        "actor__email",
        "actor__username",
        "action",
        "entity_type",
        "entity_id",
        "description",
    )
