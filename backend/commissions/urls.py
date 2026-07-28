from django.urls import path

from rest_framework.routers import DefaultRouter

from .views import (
    PartnerCommissionSettlementViewSet,
    PartnerCommissionSummaryView,
)


router = DefaultRouter()

router.register(
    r"partner/commission-settlements",
    PartnerCommissionSettlementViewSet,
    basename="partner-commission-settlement",
)


urlpatterns = [
    path(
        "partner/commission-summary/",
        PartnerCommissionSummaryView.as_view(),
        name="partner-commission-summary",
    ),
]

urlpatterns += router.urls
