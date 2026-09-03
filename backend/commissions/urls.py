from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    PartnerCommissionAgreementViewSet,
    PartnerCommissionSettlementViewSet,
    PartnerCommissionSummaryView,
    StaffCommissionParticipantPayoutView,
    StaffCommissionSettlementDetailView,
    StaffCommissionSettlementApprovalView,
    StaffCommissionReportView,
    PartnerTransactionHistoryView,
)


router = DefaultRouter()

router.register(
    r"partner/commission-agreements",
    PartnerCommissionAgreementViewSet,
    basename="partner-commission-agreement",
)

router.register(
    r"partner/commission-settlements",
    PartnerCommissionSettlementViewSet,
    basename="partner-commission-settlement",
)


urlpatterns = [
    path(
        "partner/transaction-history/",
        PartnerTransactionHistoryView.as_view(),
        name="partner-transaction-history",
    ),
    path(
        "admin/commission-report/",
        StaffCommissionReportView.as_view(),
        name="staff-commission-report",
    ),
    path(
        "admin/commission-settlements/<int:settlement_id>/approve/",
        StaffCommissionSettlementApprovalView.as_view(),
        name="staff-commission-settlement-approve",
    ),
    path(
        "admin/deals/<int:deal_id>/commission-settlement/",
        StaffCommissionSettlementDetailView.as_view(),
        name="staff-commission-settlement-detail",
    ),
    path(
        "admin/commission-participants/<int:participant_id>/payout/",
        StaffCommissionParticipantPayoutView.as_view(),
        name="staff-commission-participant-payout",
    ),
    path(
        "partner/commission-summary/",
        PartnerCommissionSummaryView.as_view(),
        name="partner-commission-summary",
    ),
]

urlpatterns += router.urls