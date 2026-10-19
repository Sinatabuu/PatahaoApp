from django.urls import path
from .recruitment import apply, application_status
from .training_portal import TrainingCohortListView, TrainingCohortDetailView, TrainingEnrollmentDetailView, TrainingDecisionView
from .staff_reports import StaffRecruitmentReportsView, StaffRecruitmentReportExportView
from .staff_portal import PortalLoginView, PortalMeView, StaffApplicationListView, StaffApplicationDetailView

from .views import (
    AdminPartnerDetailView,
    AdminPartnerDisciplinaryActionView,
    AdminPartnerListView,
    AdminPartnerReinstatementView,
    PartnerConfirmViewingView,
    PartnerDashboardView,
    PartnerDeclineViewingView,
    PartnerPropertiesView,
    PartnerRescheduleViewingView,
    PartnerTodayViewingsView,
    PartnerViewingsView,
    partner_viewing_arrived,
    partner_viewing_complete,
    partner_viewing_en_route,
    partner_viewing_start,
)


urlpatterns = [
    path("staff/onboarding/training/cohorts/", TrainingCohortListView.as_view(), name="training-cohort-list"),
    path("staff/onboarding/training/cohorts/<int:pk>/", TrainingCohortDetailView.as_view(), name="training-cohort-detail"),
    path("staff/onboarding/training/enrollments/<int:pk>/", TrainingEnrollmentDetailView.as_view(), name="training-enrollment-detail"),
    path("staff/onboarding/training/enrollments/<int:pk>/decision/", TrainingDecisionView.as_view(), name="training-enrollment-decision"),
    path("staff/onboarding/reports/", StaffRecruitmentReportsView.as_view(), name="staff-onboarding-reports"),
    path("staff/onboarding/reports/export/", StaffRecruitmentReportExportView.as_view(), name="staff-onboarding-report-export"),
    path("staff/onboarding/login/", PortalLoginView.as_view(), name="staff-onboarding-login"),
    path("staff/onboarding/me/", PortalMeView.as_view(), name="staff-onboarding-me"),
    path("staff/onboarding/applications/", StaffApplicationListView.as_view(), name="staff-onboarding-applications"),
    path("staff/onboarding/applications/<int:pk>/", StaffApplicationDetailView.as_view(), name="staff-onboarding-detail"),
    path("partner-applications/", apply, name="partner-application"),
    path("partner-applications/status/", application_status, name="partner-application-status"),
    path(
        "partners/dashboard/",
        PartnerDashboardView.as_view(),
        name="partner-dashboard",
    ),
    path(
        "partners/properties/",
        PartnerPropertiesView.as_view(),
        name="partner-properties",
    ),
    path(
        "partners/viewings/",
        PartnerViewingsView.as_view(),
        name="partner-viewings",
    ),
    path(
        "partners/viewings/today/",
        PartnerTodayViewingsView.as_view(),
        name="partner-viewings-today",
    ),
    path(
        "partners/viewings/<int:viewing_id>/confirm/",
        PartnerConfirmViewingView.as_view(),
        name="partner-viewing-confirm",
    ),
    path(
        "partners/viewings/<int:viewing_id>/reschedule/",
        PartnerRescheduleViewingView.as_view(),
        name="partner-viewing-reschedule",
    ),
    path(
        "partners/viewings/<int:viewing_id>/decline/",
        PartnerDeclineViewingView.as_view(),
        name="partner-viewing-decline",
    ),
    path(
        "partners/viewings/<int:viewing_id>/en-route/",
        partner_viewing_en_route,
        name="partner-viewing-en-route",
    ),
    path(
        "partners/viewings/<int:viewing_id>/arrived/",
        partner_viewing_arrived,
        name="partner-viewing-arrived",
    ),
    path(
        "partners/viewings/<int:viewing_id>/start/",
        partner_viewing_start,
        name="partner-viewing-start",
    ),
    path(
        "partners/viewings/<int:viewing_id>/complete/",
        partner_viewing_complete,
        name="partner-viewing-complete",
    ),
    path(
        "admin/partners/",
        AdminPartnerListView.as_view(),
        name="admin-partner-list",
    ),
    path(
        "admin/partners/<int:partner_id>/",
        AdminPartnerDetailView.as_view(),
        name="admin-partner-detail",
    ),
    path(
        "admin/partners/<int:partner_id>/disciplinary-action/",
        AdminPartnerDisciplinaryActionView.as_view(),
        name="admin-partner-disciplinary-action",
    ),
    path(
        "admin/partners/<int:partner_id>/reinstate/",
        AdminPartnerReinstatementView.as_view(),
        name="admin-partner-reinstate",
    ),
]