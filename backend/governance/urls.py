from django.urls import path


from .views import (
    AdminOperationsSummaryView,
    ApproveMandateReviewView,
    LockCommissionReviewView,
    MyPartnerCapacityView,
    PropertyReviewDetailView,
    PropertyReviewListView,
    PartnerDealGovernanceCaseDetailView,
    PartnerDealGovernanceCaseListView,
    PartnerRequestGovernanceReviewView,
    PublishPropertyReviewView,
    ReturnPropertyToPartnerReviewView,
    VerifyCommissionReviewView,
    StaffDealGovernanceCaseListView,
    StaffDealGovernanceCaseDecisionView,
    
)
from .services import (
    enforce_partner_operational_access,
    request_deal_governance_review,
    staff_decide_deal_governance_case,
)
from .serializers import (
    StaffDealGovernanceDecisionSerializer,
)

urlpatterns = [
    path(
        "admin/operations-summary/",
        AdminOperationsSummaryView.as_view(),
        name="governance-admin-operations-summary",
    ),
    path(
        "my-capacity/",
        MyPartnerCapacityView.as_view(),
        name="governance-my-capacity",
    ),
    path(
        "property-reviews/",
        PropertyReviewListView.as_view(),
        name="governance-property-review-list",
    ),
    path(
        "property-reviews/<int:property_id>/",
        PropertyReviewDetailView.as_view(),
        name="governance-property-review-detail",
    ),
    path(
        "property-reviews/<int:property_id>/verify-commission/",
        VerifyCommissionReviewView.as_view(),
        name="governance-property-review-verify-commission",
    ),
    path(
        "property-reviews/<int:property_id>/lock-commission/",
        LockCommissionReviewView.as_view(),
        name="governance-property-review-lock-commission",
    ),
    path(
        "property-reviews/<int:property_id>/approve-mandate/",
        ApproveMandateReviewView.as_view(),
        name="governance-property-review-approve-mandate",
    ),
    path(
        "property-reviews/<int:property_id>/publish/",
        PublishPropertyReviewView.as_view(),
        name="governance-property-review-publish",
    ),
    path(
        "property-reviews/<int:property_id>/return-to-partner/",
        ReturnPropertyToPartnerReviewView.as_view(),
        name="governance-property-review-return-to-partner",
    ),
    path(
        "partner/governance-cases/<int:case_id>/",
        PartnerDealGovernanceCaseDetailView.as_view(),
        name="partner-governance-case-detail",
    ),
    path(
        "partner/governance-cases/<int:case_id>/request-review/",
        PartnerRequestGovernanceReviewView.as_view(),
        name="partner-governance-case-request-review",
    ),
    path(
        "partner/governance-cases/",
        PartnerDealGovernanceCaseListView.as_view(),
        name="partner-governance-case-list",
    ),
    path(
        "admin/governance-cases/",
        StaffDealGovernanceCaseListView.as_view(),
        name="staff-deal-governance-case-list",
    ),

    path(
        "admin/governance-cases/<int:case_id>/decision/",
        StaffDealGovernanceCaseDecisionView.as_view(),
        name="staff-deal-governance-case-decision",
    ),

]
