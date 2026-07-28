from decimal import Decimal
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


STANDARD_VIEWING_FEE = Decimal("400.00")


class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        SUCCESSFUL = "successful", "Successful"
        FAILED = "failed", "Failed"
        EXPIRED = "expired", "Expired"
        CANCELLED = "cancelled", "Cancelled"
        REFUNDED = "refunded", "Refunded"

    class PaymentMethod(models.TextChoices):
        # Retained for compatibility with historical database records.
        MOBILE_MONEY = "mobile_money", "Mobile money"
        MPESA = "mpesa", "M-Pesa"
        AIRTEL_MONEY = "airtel_money", "Airtel Money"

    viewing = models.OneToOneField(
        "viewings.Viewing",
        on_delete=models.PROTECT,
        related_name="payment",
        null=True,
        blank=True,
    )

    payer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="payments",
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=STANDARD_VIEWING_FEE,
        editable=False,
    )

    currency = models.CharField(
        max_length=3,
        default="KES",
        editable=False,
    )

    phone_number = models.CharField(
        max_length=20,
        blank=True,
        default="",
    )

    payment_method = models.CharField(
        max_length=30,
        choices=PaymentMethod.choices,
        default=PaymentMethod.MPESA,
    )

    purpose = models.CharField(
        max_length=50,
        default="viewing_fee",
        editable=False,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )

    payment_reference = models.CharField(
        max_length=100,
        blank=True,
        default="",
        db_index=True,
        editable=False,
    )

    provider_transaction_id = models.CharField(
        max_length=120,
        blank=True,
        default="",
        db_index=True,
    )

    provider_receipt_number = models.CharField(
        max_length=120,
        blank=True,
        default="",
        db_index=True,
    )

    receipt_number = models.CharField(
        max_length=100,
        blank=True,
        default="",
        db_index=True,
        editable=False,
    )

    merchant_request_id = models.CharField(
        max_length=150,
        blank=True,
        default="",
        db_index=True,
    )

    checkout_request_id = models.CharField(
        max_length=150,
        blank=True,
        default="",
        db_index=True,
    )

    provider_response_code = models.CharField(
        max_length=50,
        blank=True,
        default="",
    )

    provider_response_description = models.TextField(
        blank=True,
        default="",
    )

    failure_reason = models.TextField(
        blank=True,
        default="",
    )

    provider_request_payload = models.JSONField(
        blank=True,
        default=dict,
    )

    provider_callback_payload = models.JSONField(
        blank=True,
        default=dict,
    )

    initiated_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    callback_received_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    paid_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    failed_at = models.DateTimeField(
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
        ordering = ["-created_at"]

        indexes = [
            models.Index(
                fields=["payer", "status", "-created_at"],
                name="payment_payer_status_idx",
            ),
            models.Index(
                fields=["payment_method", "status", "-created_at"],
                name="payment_provider_status_idx",
            ),
            models.Index(
                fields=["checkout_request_id", "status"],
                name="payment_checkout_status_idx",
            ),
        ]

    @staticmethod
    def generate_payment_reference():
        year = timezone.localdate().year
        random_part = uuid.uuid4().hex[:10].upper()

        return f"PH-{year}-{random_part}"

    @staticmethod
    def generate_receipt_number():
        year = timezone.localdate().year
        random_part = uuid.uuid4().hex[:10].upper()

        return f"PHR-{year}-{random_part}"

    def save(self, *args, **kwargs):
        if not self.payment_reference:
            self.payment_reference = (
                self.generate_payment_reference()
            )

        super().save(*args, **kwargs)

    @property
    def provider(self):
        """Compatibility alias used by API responses."""
        return self.payment_method

    def __str__(self):
        reference = (
            self.payment_reference
            or f"Payment #{self.pk}"
        )

        return (
            f"{reference} - "
            f"{self.amount} {self.currency}"
        )