from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLE_ADMIN = "admin"
    ROLE_PARTNER = "partner"
    ROLE_CUSTOMER = "customer"

    ROLE_CHOICES = [
        (ROLE_ADMIN, "Admin"),
        (ROLE_PARTNER, "Partner"),
        (ROLE_CUSTOMER, "Customer"),
    ]

    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20, unique=True, null=True, blank=True)
    full_name = models.CharField(max_length=255, blank=True)

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_CUSTOMER)

    is_phone_verified = models.BooleanField(default=False)
    is_email_verified = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)

    trust_score = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.full_name or self.username or self.email


class PasswordResetChallenge(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="password_reset_challenges",
    )
    code_digest = models.CharField(max_length=64)
    request_ip = models.GenericIPAddressField(null=True, blank=True)
    failed_attempts = models.PositiveSmallIntegerField(default=0)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(
                fields=("user", "used_at", "created_at"),
                name="acct_reset_active_idx",
            ),
        ]

    def __str__(self):
        return f"Password reset for user {self.user_id}"
