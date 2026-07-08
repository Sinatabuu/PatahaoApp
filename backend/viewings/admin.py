from django.contrib import admin
from .models import Viewing


@admin.register(Viewing)
class ViewingAdmin(admin.ModelAdmin):
    list_display = (
        "property",
        "customer",
        "partner",
        "preferred_date",
        "preferred_time",
        "status",
        "created_at",
    )

    list_filter = (
        "status",
        "preferred_date",
        "partner",
    )

    search_fields = (
        "property__title",
        "customer__username",
        "customer__email",
        "partner__business_name",
    )