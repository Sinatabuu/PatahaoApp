from rest_framework.routers import DefaultRouter

from .views import (
    PartnerPropertyViewSet,
    PropertyPhotoViewSet,
    PropertyViewSet,
)


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

urlpatterns = router.urls