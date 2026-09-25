from django.contrib import admin
from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "user",
        "notification_type",
        "viewing",
        "requires_action",
        "is_read",
        "created_at",
    )

    list_filter = (
        "notification_type",
        "requires_action",
        "is_read",
        "created_at",
    )

    search_fields = (
        "title",
        "message",
        "user__email",
        "user__username",
    )
