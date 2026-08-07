from django.urls import path

from .views import MyPartnerCapacityView


urlpatterns = [
    path(
        "my-capacity/",
        MyPartnerCapacityView.as_view(),
        name="governance-my-capacity",
    ),
]