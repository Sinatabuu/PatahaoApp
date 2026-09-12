from django.urls import path
from .views import (
    CustomerRegistrationView,
    MeView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
)

urlpatterns = [
    path(
        "auth/register/",
        CustomerRegistrationView.as_view(),
        name="auth_register",
    ),
    path(
        "auth/me/",
        MeView.as_view(),
        name="auth_me",
    ),
    path(
        "auth/password-reset/request/",
        PasswordResetRequestView.as_view(),
        name="auth_password_reset_request",
    ),
    path(
        "auth/password-reset/confirm/",
        PasswordResetConfirmView.as_view(),
        name="auth_password_reset_confirm",
    ),
]
