from rest_framework.routers import DefaultRouter

from .views import (
    ViewingBookingViewSet,
    ViewingViewSet,
)


router = DefaultRouter()

router.register(
    "viewings",
    ViewingViewSet,
    basename="viewing",
)

router.register(
    "viewing-bookings",
    ViewingBookingViewSet,
    basename="viewing-booking",
)


urlpatterns = router.urls