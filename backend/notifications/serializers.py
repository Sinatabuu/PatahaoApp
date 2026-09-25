from rest_framework import serializers

from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    notification_type_label = serializers.CharField(
        source="get_notification_type_display",
        read_only=True,
    )

    class Meta:
        model = Notification
        fields = [
            "id",
            "title",
            "message",
            "notification_type",
            "notification_type_label",
            "governance_case",
            "viewing",
            "action_label",
            "requires_action",
            "is_read",
            "created_at",
        ]

        read_only_fields = [
            "id",
            "title",
            "message",
            "notification_type",
            "notification_type_label",
            "governance_case",
            "viewing",
            "action_label",
            "requires_action",
            "created_at",
        ]
