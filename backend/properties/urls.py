from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import (
    PartnerPropertyViewSet,
    PropertyFavoriteViewSet,
    PropertyPhotoViewSet,
    PropertyViewSet,
    property_types,
)

urlpatterns = [
    path(
        "property-types/",
        property_types,
        name="property-types",
    ),
]



router = DefaultRouter()

router.register(
    r"properties",
    PropertyViewSet,
    basename="property",
)

router.register(
    r"partner/properties",
    PartnerPropertyViewSet,
    basename="partner-property",
)

router.register(
    r"partner/photos",
    PropertyPhotoViewSet,
    basename="partner-photo",
)

router.register(
    r"favorites",
    PropertyFavoriteViewSet,
    basename="favorite",
)
urlpatterns += router.urls