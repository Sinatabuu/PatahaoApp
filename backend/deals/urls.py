from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AdminDealGovernanceCaseView,
    AdminDealListView,
    AdminDealOwnerConfirmationStatusView,
    DealViewSet,
    OwnerOutcomeSubmissionView,
)


router = DefaultRouter()

router.register(
    r"deals",
    DealViewSet,
    basename="deal",
)


urlpatterns = [
    path(
        "deals/owner-confirmation/",
        OwnerOutcomeSubmissionView.as_view(),
        name="owner-deal-confirmation",
    ),
    path(
        "",
        include(router.urls),
    ),
    path(
        "admin/deals/",
        AdminDealListView.as_view(),
        name="admin-deal-list",
    ),
    path(
        "admin/deals/<int:deal_id>/owner-confirmation-status/",
        AdminDealOwnerConfirmationStatusView.as_view(),
        name="admin-deal-owner-confirmation-status",
    ),
    path(
        "admin/deals/<int:deal_id>/governance-case/",
        AdminDealGovernanceCaseView.as_view(),
        name="admin-deal-governance-case",
    ),
]