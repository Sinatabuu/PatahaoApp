from decimal import Decimal

from django.conf import settings
from django.core.validators import (
    MaxValueValidator,
    MinValueValidator,
)
from django.db import models


class TrustScoreBase(models.Model):
    score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[
            MinValueValidator(Decimal("0.00")),
            MaxValueValidator(Decimal("100.00")),
        ],
    )

    confidence = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[
            MinValueValidator(Decimal("0.00")),
            MaxValueValidator(Decimal("100.00")),
        ],
    )

    completed_viewings = models.PositiveIntegerField(
        default=0,
    )

    feedback_count = models.PositiveIntegerField(
        default=0,
    )

    last_calculated_at = models.DateTimeField(
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
        abstract = True


class CustomerTrustScore(TrustScoreBase):
    customer = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="customer_trust_score",
    )

    attended_viewings = models.PositiveIntegerField(
        default=0,
    )

    missed_viewings = models.PositiveIntegerField(
        default=0,
    )

    cancelled_viewings = models.PositiveIntegerField(
        default=0,
    )

    def __str__(self):
        return (
            f"Customer trust: {self.customer} "
            f"({self.score})"
        )


class PartnerTrustScore(TrustScoreBase):
    partner = models.OneToOneField(
        "partners.Partner",
        on_delete=models.CASCADE,
        related_name="trust_score_record",
    )

    average_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[
            MinValueValidator(Decimal("0.00")),
            MaxValueValidator(Decimal("5.00")),
        ],
    )

    accepted_viewings = models.PositiveIntegerField(
        default=0,
    )

    declined_viewings = models.PositiveIntegerField(
        default=0,
    )

    rescheduled_viewings = models.PositiveIntegerField(
        default=0,
    )

    def __str__(self):
        return (
            f"Partner trust: {self.partner} "
            f"({self.score})"
        )


class PropertyTrustScore(TrustScoreBase):
    property = models.OneToOneField(
        "properties.Property",
        on_delete=models.CASCADE,
        related_name="trust_score_record",
    )

    average_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[
            MinValueValidator(Decimal("0.00")),
            MaxValueValidator(Decimal("5.00")),
        ],
    )

    accurate_feedback_count = models.PositiveIntegerField(
        default=0,
    )

    partially_accurate_feedback_count = (
        models.PositiveIntegerField(
            default=0,
        )
    )

    inaccurate_feedback_count = models.PositiveIntegerField(
        default=0,
    )

    def __str__(self):
        return (
            f"Property trust: {self.property} "
            f"({self.score})"
        )


class TrustScoreHistory(models.Model):
    class SubjectType(models.TextChoices):
        CUSTOMER = "customer", "Customer"
        PARTNER = "partner", "Partner"
        PROPERTY = "property", "Property"

    subject_type = models.CharField(
        max_length=20,
        choices=SubjectType.choices,
    )

    subject_id = models.PositiveIntegerField()

    previous_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    new_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    reason = models.CharField(
        max_length=255,
        blank=True,
    )

    viewing = models.ForeignKey(
        "viewings.Viewing",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="trust_score_changes",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = [
            "-created_at",
        ]

        indexes = [
            models.Index(
                fields=[
                    "subject_type",
                    "subject_id",
                ],
            ),
        ]

    def __str__(self):
        return (
            f"{self.subject_type} #{self.subject_id}: "
            f"{self.previous_score} → {self.new_score}"
        )