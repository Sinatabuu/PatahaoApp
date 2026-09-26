from decimal import Decimal
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.functions import Lower
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
        VIEWING_CREDIT = "viewing_credit", "Pata Hao viewing credit"

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

    credit_applied_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        editable=False,
    )

    cash_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
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

    refund_reference = models.CharField(
        max_length=120,
        null=True,
        blank=True,
        unique=True,
        editable=False,
    )

    refund_notes = models.TextField(
        blank=True,
        default="",
        editable=False,
    )

    refunded_at = models.DateTimeField(
        null=True,
        blank=True,
        editable=False,
    )

    refunded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="processed_viewing_refunds",
        null=True,
        blank=True,
        editable=False,
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

        constraints = [
            models.CheckConstraint(
                condition=models.Q(credit_applied_amount__gte=Decimal("0.00")),
                name="pay_credit_applied_nonnegative",
            ),
            models.CheckConstraint(
                condition=models.Q(cash_amount__gte=Decimal("0.00")),
                name="pay_cash_amount_nonnegative",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        amount=models.F("credit_applied_amount")
                        + models.F("cash_amount")
                    )
                ),
                name="pay_amount_breakdown_matches",
            ),
            models.UniqueConstraint(
                fields=["payment_reference"],
                condition=~models.Q(payment_reference=""),
                name="payment_reference_unique",
            ),
            models.UniqueConstraint(
                Lower("provider_receipt_number"),
                condition=~models.Q(provider_receipt_number=""),
                name="pay_provider_receipt_ci_uniq",
            ),
            models.UniqueConstraint(
                fields=["checkout_request_id"],
                condition=~models.Q(checkout_request_id=""),
                name="pay_checkout_request_uniq",
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

        if (
            self._state.adding
            and self.cash_amount == Decimal("0.00")
            and self.credit_applied_amount == Decimal("0.00")
            and self.payment_method != self.PaymentMethod.VIEWING_CREDIT
        ):
            self.cash_amount = self.amount

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


class PaymentAttempt(models.Model):
    """Append-only provider-attempt history for one payment intent."""

    class Status(models.TextChoices):
        PROCESSING = "processing", "Processing"
        SUCCESSFUL = "successful", "Successful"
        FAILED = "failed", "Failed"
        REVIEW_REQUIRED = "review_required", "Review required"

    payment = models.ForeignKey(
        Payment,
        on_delete=models.PROTECT,
        related_name="attempts",
    )

    attempt_reference = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        editable=False,
    )

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.PROCESSING,
        db_index=True,
        editable=False,
    )

    merchant_request_id = models.CharField(
        max_length=150,
        blank=True,
        default="",
        db_index=True,
        editable=False,
    )

    checkout_request_id = models.CharField(
        max_length=150,
        blank=True,
        default="",
        db_index=True,
        editable=False,
    )

    provider_receipt_number = models.CharField(
        max_length=120,
        blank=True,
        default="",
        db_index=True,
        editable=False,
    )

    requested_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        editable=False,
    )

    callback_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        editable=False,
    )

    phone_number = models.CharField(
        max_length=20,
        blank=True,
        default="",
        editable=False,
    )

    provider_response_code = models.CharField(
        max_length=50,
        blank=True,
        default="",
        editable=False,
    )

    provider_response_description = models.TextField(
        blank=True,
        default="",
        editable=False,
    )

    failure_reason = models.TextField(
        blank=True,
        default="",
        editable=False,
    )

    provider_request_payload = models.JSONField(
        blank=True,
        default=dict,
        editable=False,
    )

    provider_response_payload = models.JSONField(
        blank=True,
        default=dict,
        editable=False,
    )

    provider_callback_payload = models.JSONField(
        blank=True,
        default=dict,
        editable=False,
    )

    provider_query_payload = models.JSONField(
        blank=True,
        default=dict,
        editable=False,
    )

    initiated_at = models.DateTimeField(
        default=timezone.now,
        editable=False,
    )

    callback_received_at = models.DateTimeField(
        null=True,
        blank=True,
        editable=False,
    )

    reconciled_at = models.DateTimeField(
        null=True,
        blank=True,
        editable=False,
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        editable=False,
    )

    failed_at = models.DateTimeField(
        null=True,
        blank=True,
        editable=False,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-created_at", "-id"]

        indexes = [
            models.Index(
                fields=["payment", "status", "-created_at"],
                name="payattempt_payment_status_idx",
            ),
        ]

        constraints = [
            models.UniqueConstraint(
                fields=["checkout_request_id"],
                condition=~models.Q(checkout_request_id=""),
                name="payattempt_checkout_uniq",
            ),
            models.UniqueConstraint(
                Lower("provider_receipt_number"),
                condition=~models.Q(provider_receipt_number=""),
                name="payattempt_receipt_ci_uniq",
            ),
        ]

    @staticmethod
    def generate_attempt_reference():
        year = timezone.localdate().year
        random_part = uuid.uuid4().hex[:12].upper()

        return f"PHA-{year}-{random_part}"

    def save(self, *args, **kwargs):
        if not self.attempt_reference:
            self.attempt_reference = self.generate_attempt_reference()

        self.provider_receipt_number = (
            self.provider_receipt_number.strip().upper()
        )
        self.phone_number = self.phone_number.strip()

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.attempt_reference} - {self.status}"


class ViewingCredit(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        CONSUMED = "consumed", "Consumed"
        VOID = "void", "Void"

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="viewing_credits",
    )

    source_payment = models.OneToOneField(
        Payment,
        on_delete=models.PROTECT,
        related_name="viewing_credit",
    )

    source_viewing = models.OneToOneField(
        "viewings.Viewing",
        on_delete=models.PROTECT,
        related_name="issued_credit",
    )

    credit_reference = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        editable=False,
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        editable=False,
    )

    remaining_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        editable=False,
    )

    currency = models.CharField(
        max_length=3,
        default="KES",
        editable=False,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
        editable=False,
    )

    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="issued_viewing_credits",
    )

    issued_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-issued_at", "-id"]

        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=Decimal("0.00")),
                name="viewcredit_amount_positive",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(remaining_amount__gte=Decimal("0.00"))
                    & models.Q(remaining_amount__lte=models.F("amount"))
                ),
                name="viewcredit_remaining_valid",
            ),
        ]

    @staticmethod
    def generate_credit_reference():
        year = timezone.localdate().year
        random_part = uuid.uuid4().hex[:10].upper()

        return f"PHC-{year}-{random_part}"

    def save(self, *args, **kwargs):
        if not self.credit_reference:
            self.credit_reference = self.generate_credit_reference()

        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.credit_reference} - "
            f"{self.remaining_amount} {self.currency}"
        )


class ViewingCreditRedemption(models.Model):
    credit = models.ForeignKey(
        ViewingCredit,
        on_delete=models.PROTECT,
        related_name="redemptions",
    )

    payment = models.ForeignKey(
        Payment,
        on_delete=models.PROTECT,
        related_name="credit_redemptions",
    )

    viewing = models.ForeignKey(
        "viewings.Viewing",
        on_delete=models.PROTECT,
        related_name="credit_redemptions",
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        editable=False,
    )

    redemption_reference = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        editable=False,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=Decimal("0.00")),
                name="viewcredit_redemption_positive",
            ),
            models.UniqueConstraint(
                fields=["credit", "payment"],
                name="viewcredit_once_per_payment",
            ),
        ]

    @staticmethod
    def generate_redemption_reference():
        year = timezone.localdate().year
        random_part = uuid.uuid4().hex[:10].upper()

        return f"PHCR-{year}-{random_part}"

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValidationError(
                "Viewing credit redemption records are immutable."
            )

        if not self.redemption_reference:
            self.redemption_reference = self.generate_redemption_reference()

        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError(
            "Viewing credit redemption records cannot be deleted."
        )

    def __str__(self):
        return (
            f"{self.redemption_reference} - "
            f"{self.amount} {self.credit.currency}"
        )
