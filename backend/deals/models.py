from decimal import Decimal

from django.conf import settings
from django.db import models


class Deal(models.Model):

    class Status(models.TextChoices):

        PENDING_CONFIRMATION = (
            "pending_confirmation",
            "Pending Confirmation",
        )

        CONFIRMED = (
            "confirmed",
            "Confirmed",
        )

        COMMISSION_PENDING = (
            "commission_pending",
            "Commission Pending",
        )

        COMMISSION_PAID = (
            "commission_paid",
            "Commission Paid",
        )

        CLOSED = (
            "closed",
            "Closed",
        )

        CANCELLED = (
            "cancelled",
            "Cancelled",
        )

        DISPUTED = (
            "disputed",
            "Disputed",
        )

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="deals",
    )

    partner = models.ForeignKey(
        "partners.Partner",
        on_delete=models.PROTECT,
        related_name="deals",
    )

    property = models.ForeignKey(
        "properties.Property",
        on_delete=models.PROTECT,
        related_name="deals",
    )

    viewing = models.OneToOneField(
        "viewings.Viewing",
        on_delete=models.PROTECT,
        related_name="deal",
    )

    monthly_rent = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )

    sale_price = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
    )

    commission_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    status = models.CharField(
        max_length=40,
        choices=Status.choices,
        default=Status.PENDING_CONFIRMATION,
    )

    customer_confirmed = models.BooleanField(
        default=False,
    )

    partner_confirmed = models.BooleanField(
        default=False,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "-created_at",
        ]

    def __str__(self):
        return (
            f"Deal #{self.id}"
        )

class DealOutcome(models.Model):

    class Reporter(models.TextChoices):

        CUSTOMER = (
            "customer",
            "Customer",
        )

        PARTNER = (
            "partner",
            "Partner",
        )

    class Outcome(models.TextChoices):

        RENTED = (
            "rented",
            "Customer rented property",
        )

        PURCHASED = (
            "purchased",
            "Customer bought property",
        )

        STILL_DECIDING = (
            "still_deciding",
            "Still deciding",
        )

        DECLINED = (
            "declined",
            "Declined property",
        )

        NO_SHOW = (
            "no_show",
            "Did not attend",
        )

    deal = models.ForeignKey(
        Deal,
        on_delete=models.CASCADE,
        related_name="outcomes",
    )

    reporter = models.CharField(
        max_length=20,
        choices=Reporter.choices,
    )

    outcome = models.CharField(
        max_length=30,
        choices=Outcome.choices,
    )

    notes = models.TextField(
        blank=True,
        default="",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:

        constraints = [

            models.UniqueConstraint(
                fields=[
                    "deal",
                    "reporter",
                ],
                name="one_outcome_per_reporter",
            )

        ]

    def __str__(self):

        return (
            f"{self.deal} - {self.reporter}"
        )

class CommissionInvoice(models.Model):

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"
        CANCELLED = "cancelled", "Cancelled"
        REFUNDED = "refunded", "Refunded"

    deal = models.OneToOneField(
        Deal,
        on_delete=models.CASCADE,
        related_name="commission_invoice",
    )

    invoice_number = models.CharField(
        max_length=30,
        unique=True,
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    paid_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    def __str__(self):
        return self.invoice_number