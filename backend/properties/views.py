from rest_framework import viewsets, permissions
from .models import Property
from .serializers import PropertySerializer
from core.models import ActivityLog


class PropertyViewSet(viewsets.ModelViewSet):
    queryset = Property.objects.all()
    serializer_class = PropertySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        queryset = Property.objects.all()

        listing_type = self.request.query_params.get("listing_type")
        town = self.request.query_params.get("town")
        status = self.request.query_params.get("status")

        if listing_type:
            queryset = queryset.filter(listing_type=listing_type)

        if town:
            queryset = queryset.filter(town__icontains=town)

        if status:
            queryset = queryset.filter(status=status)

        return queryset

    def perform_create(self, serializer):
        property_obj = serializer.save()

        ActivityLog.objects.create(
            actor=self.request.user if self.request.user.is_authenticated else None,
            action="property_created",
            entity_type="Property",
            entity_id=str(property_obj.id),
            description=f"Property created: {property_obj.title}",
        )