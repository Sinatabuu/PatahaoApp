from django.conf import settings
from django.db import models


class Partner(models.Model):
    PARTNER_TYPE_AGENT = "agent"
    PARTNER_TYPE_AGENCY = "agency"
    PARTNER_TYPE_DEVELOPER = "developer"
    PARTNER_TYPE_OWNER = "owner"

    PARTNER_TYPE_CHOICES = [
        (PARTNER_TYPE_AGENT, "Agent"),
        (PARTNER_TYPE_AGENCY, "Agency"),
        (PARTNER_TYPE_DEVELOPER, "Developer"),
        (PARTNER_TYPE_OWNER, "Owner"),
    ]

    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"
    STATUS_SUSPENDED = "suspended"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_REJECTED, "Rejected"),
        (STATUS_SUSPENDED, "Suspended"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="partner_profile",
    )

    business_name = models.CharField(max_length=255)
    partner_type = models.CharField(
        max_length=30,
        choices=PARTNER_TYPE_CHOICES,
        default=PARTNER_TYPE_AGENT,
    )

    county = models.CharField(max_length=100, blank=True)
    town = models.CharField(max_length=100, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)

    verification_status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )

    commission_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=10.00,
        help_text="Commission percentage charged by Pata Hao.",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.business_name