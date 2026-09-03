from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


class Property(models.Model):
    TYPE_APARTMENT = "apartment"
    TYPE_HOUSE = "house"
    TYPE_LAND = "land"
    TYPE_OFFICE = "office"
    TYPE_SHOP = "shop"
    TYPE_WAREHOUSE = "warehouse"

    PROPERTY_TYPE_CHOICES = [
        (TYPE_APARTMENT, "Apartment"),
        (TYPE_HOUSE, "House"),
        (TYPE_LAND, "Land"),
        (TYPE_OFFICE, "Office"),
        (TYPE_SHOP, "Shop"),
        (TYPE_WAREHOUSE, "Warehouse"),
    ]

    LISTING_RENT = "rent"
    LISTING_SALE = "sale"

    LISTING_TYPE_CHOICES = [
        (LISTING_RENT, "Rent"),
        (LISTING_SALE, "Sale"),
    ]

    RENT_SUCCESS_BROADCAST_DAYS = 15
    SALE_SUCCESS_BROADCAST_DAYS = 30

    STATUS_DRAFT = "draft"
    STATUS_PENDING = "pending"
    STATUS_PUBLISHED = "published"
    STATUS_RESERVED = "reserved"
    STATUS_RENTED = "rented"
    STATUS_SOLD = "sold"
    STATUS_ARCHIVED = "archived"

    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_PENDING, "Pending Verification"),
        (STATUS_PUBLISHED, "Published"),
        (STATUS_RESERVED, "Reserved"),
        (STATUS_RENTED, "Rented"),
        (STATUS_SOLD, "Sold"),
        (STATUS_ARCHIVED, "Archived"),
    ]

    TRUST_BADGE_CHOICES = [
        ("none", "None"),
        ("bronze", "Bronze"),
        ("silver", "Silver"),
        ("gold", "Gold"),
    ]

    partner = models.ForeignKey(
        "partners.Partner",
        on_delete=models.PROTECT,
        related_name="properties",
        null=True,
        blank=True,
    )

    title = models.CharField(max_length=255)

    property_type = models.CharField(
        max_length=30,
        choices=PROPERTY_TYPE_CHOICES,
    )

    listing_type = models.CharField(
        max_length=20,
        choices=LISTING_TYPE_CHOICES,
    )

    price = models.DecimalField(
        max_digits=14,
        decimal_places=2,
    )

    county = models.CharField(max_length=100)
    town = models.CharField(max_length=100)
    estate = models.CharField(max_length=100, blank=True)
    address = models.CharField(max_length=255, blank=True)

    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
    )

    longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
    )

    def save(self, *args, **kwargs):
            is_being_published = False

            if self.status == self.STATUS_PUBLISHED:
                if self.pk is None:
                    is_being_published = True
                else:
                    previous_status = (
                        type(self)
                        .objects
                        .filter(pk=self.pk)
                        .values_list("status", flat=True)
                        .first()
                    )

                    is_being_published = (
                        previous_status != self.STATUS_PUBLISHED
                    )

            if is_being_published:
                from governance.services import (
                    validate_partner_property_limit,
                )
                from mandates.services import (
                    validate_property_publication,
                )

                validate_partner_property_limit(
                    self,
                )

                validate_property_publication(
                    self,
                )

            self.full_clean()
            super().save(*args, **kwargs)

    bedrooms = models.PositiveIntegerField(default=0)
    bathrooms = models.PositiveIntegerField(default=0)

    description = models.TextField()

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT,
    )

    trust_badge = models.CharField(
        max_length=20,
        choices=TRUST_BADGE_CHOICES,
        default="none",
    )
    verification_return_reason = models.TextField(
        blank=True,
        help_text=(
            "Reason a pending property was returned "
            "to the partner for changes."
        ),
    )

    transaction_completed_at = models.DateTimeField(
        null=True,
        blank=True,
        editable=False,
    )

    success_broadcast_until = models.DateTimeField(
        null=True,
        blank=True,
        editable=False,
        db_index=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    @property
    def is_available(self):
        return self.status == self.STATUS_PUBLISHED

    @property
    def is_success_broadcast_active(self):
        return (
            self.status
            in {
                self.STATUS_RENTED,
                self.STATUS_SOLD,
            }
            and self.success_broadcast_until is not None
            and self.success_broadcast_until > timezone.now()
        )

    @property
    def success_badge(self):
        if not self.is_success_broadcast_active:
            return ""

        if self.status == self.STATUS_SOLD:
            return "Sold Through Pata Hao"

        return "Rented Through Pata Hao"

    def mark_transaction_completed(
        self,
        *,
        completed_at=None,
    ):
        completed_at = completed_at or timezone.now()

        if self.listing_type == self.LISTING_SALE:
            completed_status = self.STATUS_SOLD
            broadcast_days = (
                self.SALE_SUCCESS_BROADCAST_DAYS
            )

        elif self.listing_type == self.LISTING_RENT:
            completed_status = self.STATUS_RENTED
            broadcast_days = (
                self.RENT_SUCCESS_BROADCAST_DAYS
            )

        else:
            raise ValueError(
                "Unsupported property listing type."
            )

        self.status = completed_status
        self.transaction_completed_at = completed_at
        self.success_broadcast_until = (
            completed_at
            + timedelta(
                days=broadcast_days,
            )
        )

        self.save(
            update_fields=[
                "status",
                "transaction_completed_at",
                "success_broadcast_until",
                "updated_at",
            ]
        )

        return broadcast_days


class PropertyFavorite(models.Model):
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="property_favorites",
    )

    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name="favorites",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = [
            "-created_at",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "customer",
                    "property",
                ],
                name=(
                    "unique_property_favorite_per_customer"
                ),
            ),
        ]

    def __str__(self):
        return (
            f"{self.customer} saved "
            f"{self.property.title}"
        )


class PropertyPhoto(models.Model):
    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name="photos",
    )

    image = models.ImageField(
        upload_to="property_photos/",
    )

    caption = models.CharField(
        max_length=255,
        blank=True,
    )

    is_cover = models.BooleanField(default=False)

    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_cover", "uploaded_at"]

    def __str__(self):
        return f"Photo for {self.property.title}"

class PropertyPartner(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACTIVE = "active", "Active"
        SUSPENDED = "suspended", "Suspended"
        REMOVED = "removed", "Removed"

    class Role(models.TextChoices):
        SOURCE = "source", "Source partner"
        PARTICIPATING = "participating", "Participating partner"

    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name="partner_participations",
    )

    partner = models.ForeignKey(
        "partners.Partner",
        on_delete=models.PROTECT,
        related_name="property_participations",
    )

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.PARTICIPATING,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )

    joined_at = models.DateTimeField(
        auto_now_add=True,
    )

    verified_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["property_id", "partner_id"]
        constraints = [
            models.UniqueConstraint(
                fields=["property", "partner"],
                name="unique_partner_per_property",
            ),
        ]

    def __str__(self):
        return (
            f"{self.property.title} — "
            f"{self.partner} ({self.role})"
        )

class PropertyVideo(models.Model):
    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name="videos",
    )

    video = models.FileField(
        upload_to="property_videos/",
    )

    thumbnail = models.ImageField(
        upload_to="property_video_thumbnails/",
        null=True,
        blank=True,
    )

    title = models.CharField(
        max_length=255,
        blank=True,
    )

    description = models.TextField(blank=True)

    duration = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Duration in seconds",
    )

    is_featured = models.BooleanField(default=False)

    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_featured", "-uploaded_at"]

    def __str__(self):
        return self.title or f"Video for {self.property.title}"