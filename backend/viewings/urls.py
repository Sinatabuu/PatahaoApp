from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AdminViewingDetailView,
    AdminViewingFeeResolutionView,
    AdminViewingListView,
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
        "admin/viewings/",
        AdminViewingListView.as_view(),
        name="admin-viewing-list",
    ),
    path(
        "admin/viewings/<int:viewing_id>/",
        AdminViewingDetailView.as_view(),
        name="admin-viewing-detail",
    ),
    path(
        "admin/viewings/<int:viewing_id>/process-fee-resolution/",
        AdminViewingFeeResolutionView.as_view(),
        name="admin-viewing-process-fee-resolution",
    ),

    path(
        "viewings/<int:viewing_id>/feedback/",
        ViewingFeedbackView.as_view(),
        name="viewing-feedback",
    ),
    path("", include(router.urls)),
]
