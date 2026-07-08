from rest_framework import viewsets, permissions
from .models import Viewing
from .serializers import ViewingSerializer
from core.models import ActivityLog


class ViewingViewSet(viewsets.ModelViewSet):
    queryset = Viewing.objects.all()
    serializer_class = ViewingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        if user.is_staff:
            return Viewing.objects.all()

        return Viewing.objects.filter(customer=user)

    def perform_create(self, serializer):
        viewing = serializer.save(customer=self.request.user)

        ActivityLog.objects.create(
            actor=self.request.user,
            action="viewing_requested",
            entity_type="Viewing",
            entity_id=str(viewing.id),
            description=f"Viewing requested for {viewing.property.title}",
        )