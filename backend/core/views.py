from rest_framework import viewsets, permissions
from .models import ActivityLog
from .serializers import ActivityLogSerializer


class ActivityLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ActivityLogSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        return ActivityLog.objects.all()
