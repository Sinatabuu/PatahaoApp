from django.urls import path

from .views import (
    ApproveMandateReviewView,
    LockCommissionReviewView,
    MyPartnerCapacityView,
    PropertyReviewDetailView,
    PropertyReviewListView,
    PublishPropertyReviewView,
    ReturnPropertyToPartnerReviewView,
    VerifyCommissionReviewView,
)


urlpatterns = [
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
]
