from rest_framework import serializers
from .models import ActivityLog


class ActivityLogSerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(source="actor.full_name", read_only=True)
    actor_email = serializers.EmailField(source="actor.email", read_only=True)

    class Meta:
        model = ActivityLog
        fields = [
            "id",
            "actor",
            "actor_name",
            "actor_email",
            "action",
            "entity_type",
            "entity_id",
            "description",
            "created_at",
        ]
