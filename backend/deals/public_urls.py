from django.urls import path

from .public_views import (
    owner_confirmation_page,
)


urlpatterns = [
    path(
        "owner-confirmation/<str:token>/",
        owner_confirmation_page,
        name="owner-confirmation-page",
    ),
]
