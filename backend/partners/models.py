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
    STATUS_UNDER_REVIEW = "under_review"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"
    STATUS_SUSPENDED = "suspended"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_UNDER_REVIEW, "Under Review"),
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

    display_name = models.CharField(
        max_length=150,
        blank=True,
        help_text="Public name shown to customers.",
    )

    partner_type = models.CharField(
        max_length=30,
        choices=PARTNER_TYPE_CHOICES,
        default=PARTNER_TYPE_AGENT,
    )

    partner_code = models.CharField(
        max_length=30,
        unique=True,
        blank=True,
        null=True,
        help_text="Unique public Pata Hao partner reference.",
    )

    profile_photo = models.ImageField(
        upload_to="partner_profiles/",
        blank=True,
        null=True,
    )

    bio = models.TextField(
        blank=True,
        help_text="Short public description shown on the partner profile.",
    )

    county = models.CharField(max_length=100, blank=True)
    town = models.CharField(max_length=100, blank=True)

    service_area = models.CharField(
        max_length=255,
        blank=True,
        help_text="Estate, neighborhood, town, or territory served.",
    )

    phone_number = models.CharField(max_length=20, blank=True)

    public_phone_number = models.CharField(
        max_length=20,
        blank=True,
        help_text="Optional number that may be shown after booking confirmation.",
    )

    national_id_number = models.CharField(
        max_length=50,
        blank=True,
        help_text="Private verification information. Never expose publicly.",
    )

    business_registration_number = models.CharField(
        max_length=100,
        blank=True,
    )

    verification_status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )

    verification_notes = models.TextField(
        blank=True,
        help_text="Private admin verification notes.",
    )

    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="verified_partners",
        null=True,
        blank=True,
    )

    verified_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    commission_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=10.00,
        help_text="Legacy commission percentage.",
    )

    commission_plan = models.ForeignKey(
        "commissions.CommissionPlan",
        on_delete=models.PROTECT,
        related_name="partners",
        null=True,
        blank=True,
        help_text="The partner's current Pata Hao earning level.",
    )

    is_active = models.BooleanField(default=True)

    accepts_viewing_requests = models.BooleanField(
        default=True,
        help_text="Controls whether customers can request viewings.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["business_name"]

    def __str__(self):
        return self.display_name or self.business_name

    @property
    def is_verified(self):
        return (
            self.verification_status == self.STATUS_APPROVED
            and self.is_active
        )