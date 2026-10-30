from django.urls import path
from .operations_portal import OperationsListView, OperationsDetailView, OperationsScanView

from rest_framework.routers import DefaultRouter
from .views import ActivityLogViewSet

router = DefaultRouter()
router.register(r"activity-logs", ActivityLogViewSet, basename="activity-log")

urlpatterns = [
    path('staff/onboarding/operations/', OperationsListView.as_view()),
    path('staff/onboarding/operations/scan/', OperationsScanView.as_view()),
    path('staff/onboarding/operations/<int:pk>/', OperationsDetailView.as_view()),
] + router.urls
