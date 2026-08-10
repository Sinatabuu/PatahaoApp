from django.shortcuts import get_object_or_404

from rest_framework import permissions, status, viewsets
from rest_framework.response import Response

from .models import Property, PropertyFavorite
from .serializers import PropertySerializer


class PropertyFavoriteViewSet(viewsets.ModelViewSet):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    http_method_names = [
        "get",
        "post",
        "delete",
        "head",
        "options",
    ]

    def get_queryset(self):
        return (
            PropertyFavorite.objects
            .select_related(
                "property",
                "property__partner",
            )
            .filter(
                customer=self.request.user,
            )
            .order_by("-created_at")
        )

    def list(self, request, *args, **kwargs):
        favorites = self.get_queryset()

        data = []

        for favorite in favorites:
            data.append(
                {
                    "id": favorite.id,
                    "customer": favorite.customer_id,
                    "property": favorite.property_id,
                    "property_details": PropertySerializer(
                        favorite.property,
                        context={
                            "request": request,
                        },
                    ).data,
                    "created_at": favorite.created_at,
                }
            )

        return Response(data)

    def create(self, request, *args, **kwargs):
        property_id = request.data.get("property")

        if not property_id:
            return Response(
                {
                    "property": [
                        "A property is required.",
                    ],
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        property_obj = get_object_or_404(
            Property,
            pk=property_id,
            status=Property.STATUS_PUBLISHED,
        )

        favorite, created = PropertyFavorite.objects.get_or_create(
            customer=request.user,
            property=property_obj,
        )

        response_status = (
            status.HTTP_201_CREATED
            if created
            else status.HTTP_200_OK
        )

        return Response(
            {
                "id": favorite.id,
                "customer": favorite.customer_id,
                "property": favorite.property_id,
                "property_details": PropertySerializer(
                    property_obj,
                    context={
                        "request": request,
                    },
                ).data,
                "created_at": favorite.created_at,
            },
            status=response_status,
        )

    def destroy(self, request, *args, **kwargs):
        favorite = get_object_or_404(
            self.get_queryset(),
            pk=kwargs["pk"],
        )

        favorite.delete()

        return Response(
            status=status.HTTP_204_NO_CONTENT,
        )
