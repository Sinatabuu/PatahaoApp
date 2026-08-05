from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
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
]