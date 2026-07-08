from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = (
        "username",
        "email",
        "phone_number",
        "full_name",
        "role",
        "is_verified",
        "trust_score",
        "is_staff",
        "is_active",
    )

    list_filter = (
        "role",
        "is_verified",
        "is_phone_verified",
        "is_email_verified",
        "is_staff",
        "is_active",
    )

    search_fields = (
        "username",
        "email",
        "phone_number",
        "full_name",
    )