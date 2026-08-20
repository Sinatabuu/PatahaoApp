from rest_framework import serializers

from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            "id",
            "title",
            "message",
            "notification_type",
            "governance_case",
            "action_label",
            "is_read",
            "created_at",
        ]

        read_only_fields = [
            "id",
            "title",
            "message",
            "notification_type",
            "governance_case",
            "action_label",
            "created_at",
        ]