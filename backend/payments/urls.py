from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import PaymentViewSet, mpesa_callback


router = DefaultRouter()
router.register("payments", PaymentViewSet, basename="payment")

urlpatterns = [
    path(
        "payments/mpesa/callback/",
        mpesa_callback,
        name="payment-mpesa-callback",
    ),
]

urlpatterns += router.urls