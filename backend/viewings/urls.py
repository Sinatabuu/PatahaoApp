from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ViewingBookingViewSet,
    ViewingFeedbackView,
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

urlpatterns = [
    path(
        "viewings/<int:viewing_id>/feedback/",
        ViewingFeedbackView.as_view(),
        name="viewing-feedback",
    ),
    path("", include(router.urls)),
]