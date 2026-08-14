from django.urls import path
from .views import CustomerRegistrationView, MeView

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
]
