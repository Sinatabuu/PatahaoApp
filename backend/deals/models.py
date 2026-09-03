from decimal import Decimal

from django.conf import settings
from django.db import models
from uuid import uuid4
import hashlib
import secrets
from django.core.exceptions import ValidationError
from django.utils import timezone



class Deal(models.Model):

    deal_number = models.CharField(
        max_length=50,
        unique=True,
        null=True,
        blank=True,
        editable=False,
    )

    introduction = models.OneToOneField(
        "introductions.ProtectedIntroduction",
        on_delete=models.PROTECT,
        related_name="deal",
        null=True,
        blank=True,
    )

    deal_type = models.CharField(
        max_length=20,
        choices=[
            ("rental", "Rental"),
            ("sale", "Sale"),
        ],
        blank=True,
    )

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"

        AWAITING_CUSTOMER = (
            "awaiting_customer",
            "Awaiting customer confirmation",
        )

        AWAITING_OWNER = (
            "awaiting_owner",
            "Awaiting owner confirmation",
        )

        AWAITING_CONFIRMATIONS = (
            "awaiting_confirmations",
            "Awaiting customer, partner, and owner confirmations",
        )

        NEGOTIATING = "negotiating", "Negotiating"
        AGREED = "agreed", "Terms agreed"

        DOCUMENTS_PENDING = (
            "documents_pending",
            "Documents pending",
        )

        COMMISSION_DUE = (
            "commission_due",
            "Commission due",
        )

        COMMISSION_PAID = (
            "commission_paid",
            "Commission paid",
        )

        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"
        DISPUTED = "disputed", "Disputed"

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
        default=Status.DRAFT,
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

    owner_confirmed = models.BooleanField(
        default=False,
    )

    customer_confirmed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    partner_confirmed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    owner_confirmed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    agreed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    closed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    cancelled_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    cancellation_reason = models.TextField(
        blank=True,
    )

    class Meta:
        ordering = [
            "-created_at",
        ]

    def clean(self):
        errors = {}

        if self.introduction_id:
            pic = self.introduction

            if pic.customer_id != self.customer_id:
                errors["customer"] = (
                    "The deal customer must match the PIC customer."
                )

            if pic.property_id != self.property_id:
                errors["property"] = (
                    "The deal property must match the PIC property."
                )

            if pic.partner_id != self.partner_id:
                errors["partner"] = (
                    "The deal partner must match the PIC partner."
                )

            if pic.viewing_id != self.viewing_id:
                errors["viewing"] = (
                    "The deal viewing must match the PIC viewing."
                )

            if not self.pk and not pic.is_active:
                errors["introduction"] = (
                    "The PIC must be active before a deal can begin."
                )

        if self.deal_type == "rental":
            if not self.monthly_rent or self.monthly_rent <= 0:
                errors["monthly_rent"] = (
                    "A rental deal requires a monthly rent "
                    "greater than zero."
                )

            if self.sale_price is not None:
                errors["sale_price"] = (
                    "A rental deal cannot have a sale price."
                )

        if self.deal_type == "sale":
            if not self.sale_price or self.sale_price <= 0:
                errors["sale_price"] = (
                    "A sale deal requires a sale price "
                    "greater than zero."
                )

            if self.monthly_rent is not None:
                errors["monthly_rent"] = (
                    "A sale deal cannot have monthly rent."
                )

        if errors:
            raise ValidationError(errors)


    def save(self, *args, **kwargs):
        if not self.deal_number:
            self.deal_number = (
                f"PH-DEAL-{timezone.now().year}-"
                f"{uuid4().hex[:12].upper()}"
            )

        if self.pk:
            original = type(self).objects.get(pk=self.pk)

            immutable_fields = [
                "deal_number",
                "introduction_id",
                "customer_id",
                "partner_id",
                "property_id",
                "viewing_id",
                "deal_type",
            ]

            changed = []

            for field in immutable_fields:
                original_value = getattr(original, field)
                new_value = getattr(self, field)

                # Legacy records may receive an identity value once.
                # After the field has a value, it becomes immutable.
                if original_value in (None, ""):
                    continue

                if original_value != new_value:
                    changed.append(field)

            if changed:
                raise ValidationError(
                    {
                        "deal": (
                            "Core deal identity cannot be changed: "
                            + ", ".join(changed)
                        )
                    }
                )

        self.full_clean()
        super().save(*args, **kwargs)


    def confirm_customer(self):
        if self.customer_confirmed:
            return

        self.customer_confirmed = True
        self.customer_confirmed_at = timezone.now()
        self.save(
            update_fields=[
                "customer_confirmed",
                "customer_confirmed_at",
                "updated_at",
            ]
        )


    def confirm_partner(self):
        if self.partner_confirmed:
            return

        self.partner_confirmed = True
        self.partner_confirmed_at = timezone.now()
        self.save(
            update_fields=[
                "partner_confirmed",
                "partner_confirmed_at",
                "updated_at",
            ]
        )


    def confirm_owner(self):
        if self.owner_confirmed:
            return

        self.owner_confirmed = True
        self.owner_confirmed_at = timezone.now()
        self.save(
            update_fields=[
                "owner_confirmed",
                "owner_confirmed_at",
                "updated_at",
            ]
        )


    def mark_terms_agreed(self):
        if not (
            self.customer_confirmed
            and self.partner_confirmed
            and self.owner_confirmed
        ):
            raise ValidationError(
                "Customer, partner, and owner must all confirm "
                "before terms are agreed."
            )

        self.status = self.Status.AGREED
        self.agreed_at = timezone.now()
        self.save(
            update_fields=[
                "status",
                "agreed_at",
                "updated_at",
            ]
        )


    def __str__(self):
        return self.deal_number

    def __str__(self):
        return (
            f"Deal #{self.id}"
        )

class DealEvent(models.Model):
    deal = models.ForeignKey(
        Deal,
        on_delete=models.PROTECT,
        related_name="events",
    )

    action = models.CharField(
        max_length=60,
    )

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="deal_events",
        null=True,
        blank=True,
    )

    notes = models.TextField(
        blank=True,
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = [
            "created_at",
            "id",
        ]

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError(
                "Deal events cannot be modified."
            )

        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError(
            "Deal events cannot be deleted."
        )

    def __str__(self):
        return (
            f"{self.deal.deal_number} — "
            f"{self.action} — "
            f"{self.created_at:%Y-%m-%d %H:%M}"
        )
class DealOutcome(models.Model):

    class Reporter(models.TextChoices):
        CUSTOMER = "customer", "Customer"
        PARTNER = "partner", "Partner"
        OWNER = "owner", "Owner"

    class Outcome(models.TextChoices):
        RENTED = "rented", "Customer rented property"
        PURCHASED = "purchased", "Customer bought property"
        STILL_DECIDING = "still_deciding", "Still deciding"
        DECLINED = "declined", "Declined property"
        NO_SHOW = "no_show", "Did not attend"

    deal = models.ForeignKey(
        Deal,
        on_delete=models.PROTECT,
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
        ordering = [
            "created_at",
            "id",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "deal",
                    "reporter",
                ],
                name="one_outcome_per_reporter",
            )
        ]

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError(
                "Deal outcomes cannot be modified after submission."
            )

        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError(
            "Deal outcomes cannot be deleted."
        )

    def __str__(self):
        return (
            f"{self.deal.deal_number} — "
            f"{self.get_reporter_display()} — "
            f"{self.get_outcome_display()}"
        )

class OwnerConfirmationToken(models.Model):
    deal = models.ForeignKey(
        Deal,
        on_delete=models.PROTECT,
        related_name="owner_confirmation_tokens",
    )

    owner = models.ForeignKey(
        "mandates.PropertyOwner",
        on_delete=models.PROTECT,
        related_name="deal_confirmation_tokens",
    )

    mandate = models.ForeignKey(
        "mandates.PropertyMandate",
        on_delete=models.PROTECT,
        related_name="deal_confirmation_tokens",
    )

    token_hash = models.CharField(
        max_length=64,
        unique=True,
        editable=False,
    )

    expires_at = models.DateTimeField()

    used_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    revoked_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_owner_confirmation_tokens",
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
                    "deal",
                    "expires_at",
                ],
            ),
        ]

    @classmethod
    def hash_token(cls, raw_token):
        return hashlib.sha256(
            raw_token.encode("utf-8")
        ).hexdigest()

    @classmethod
    def issue(
        cls,
        *,
        deal,
        owner,
        mandate,
        created_by,
        expires_at,
    ):
        raw_token = secrets.token_urlsafe(48)

        token = cls.objects.create(
            deal=deal,
            owner=owner,
            mandate=mandate,
            token_hash=cls.hash_token(raw_token),
            expires_at=expires_at,
            created_by=created_by,
        )

        return token, raw_token

    @property
    def is_usable(self):
        now = timezone.now()

        return (
            self.used_at is None
            and self.revoked_at is None
            and self.expires_at > now
        )

    def mark_used(self):
        if not self.is_usable:
            raise ValidationError(
                "This owner confirmation token is no longer valid."
            )

        self.used_at = timezone.now()
        self.save(
            update_fields=[
                "used_at",
            ]
        )

    def revoke(self):
        if self.used_at is not None:
            raise ValidationError(
                "A used owner confirmation token cannot be revoked."
            )

        if self.revoked_at is None:
            self.revoked_at = timezone.now()
            self.save(
                update_fields=[
                    "revoked_at",
                ]
            )

    def __str__(self):
        return (
            f"{self.deal.deal_number} — "
            f"{self.owner.owner_number}"
        )

class CommissionInvoice(models.Model):
    """
    Accounts-receivable evidence for commission owed to Pata Hao.

    The locked CommissionAgreement establishes the obligation.
    The CommissionSettlement records how the gross commission is
    economically allocated.

    This invoice records who owes Pata Hao, how much is owed, and
    the historical owner/agreement identity that applied when the
    receivable was issued.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PARTIALLY_PAID = "partially_paid", "Partially paid"
        PAID = "paid", "Paid"
        CANCELLED = "cancelled", "Cancelled"
        REFUNDED = "refunded", "Refunded"

    deal = models.OneToOneField(
        Deal,
        on_delete=models.PROTECT,
        related_name="commission_invoice",
    )

    settlement = models.OneToOneField(
        "commissions.CommissionSettlement",
        on_delete=models.PROTECT,
        related_name="commission_invoice",
        null=True,
        blank=True,
    )

    agreement = models.ForeignKey(
        "commissions.CommissionAgreement",
        on_delete=models.PROTECT,
        related_name="commission_invoices",
        null=True,
        blank=True,
    )

    owner = models.ForeignKey(
        "mandates.PropertyOwner",
        on_delete=models.PROTECT,
        related_name="commission_invoices",
        null=True,
        blank=True,
    )

    invoice_number = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        editable=False,
    )

    owner_number_snapshot = models.CharField(
        max_length=40,
        blank=True,
        editable=False,
    )

    owner_legal_name_snapshot = models.CharField(
        max_length=255,
        blank=True,
        editable=False,
    )

    owner_phone_number_snapshot = models.CharField(
        max_length=30,
        blank=True,
        editable=False,
    )

    owner_email_snapshot = models.EmailField(
        blank=True,
        editable=False,
    )

    agreement_number_snapshot = models.CharField(
        max_length=50,
        blank=True,
        editable=False,
    )

    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
    )

    currency = models.CharField(
        max_length=3,
        default="KES",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )

    issued_at = models.DateTimeField(
        default=timezone.now,
    )

    paid_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_commission_invoices",
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
        ordering = [
            "-issued_at",
            "-id",
        ]

    def clean(self):
        errors = {}

        if self.settlement_id is None:
            errors["settlement"] = (
                "A commission settlement is required."
            )

        if self.agreement_id is None:
            errors["agreement"] = (
                "A locked commission agreement is required."
            )

        if self.owner_id is None:
            errors["owner"] = (
                "The liable property owner is required."
            )

        if self.created_by_id is None:
            errors["created_by"] = (
                "The administrator issuing the invoice is required."
            )

        if self.amount is None or self.amount <= Decimal("0.00"):
            errors["amount"] = (
                "The commission invoice amount must be greater than zero."
            )

        if self.agreement_id:
            if self.agreement.property_id != self.deal.property_id:
                errors["agreement"] = (
                    "The invoice agreement must belong to the "
                    "same property as the deal."
                )

            if not self.agreement.is_locked:
                errors["agreement"] = (
                    "The commission agreement must be locked "
                    "before an invoice can be issued."
                )

        if self.settlement_id:
            if self.settlement.deal_id != self.deal_id:
                errors["settlement"] = (
                    "The commission settlement must belong to "
                    "the same deal as the invoice."
                )

            if (
                self.agreement_id
                and self.settlement.agreement_id != self.agreement_id
            ):
                errors["settlement"] = (
                    "The settlement and invoice must use the "
                    "same commission agreement."
                )

            if (
                self.amount is not None
                and self.settlement.gross_commission_amount != self.amount
            ):
                errors["amount"] = (
                    "The invoice amount must equal the gross "
                    "commission settlement amount."
                )

            if (
                self.currency
                and self.settlement.currency
                and self.currency.strip().upper()
                != self.settlement.currency.strip().upper()
            ):
                errors["currency"] = (
                    "The invoice currency must match the "
                    "commission settlement currency."
                )

        if self.status == self.Status.PAID:
            if self.paid_at is None:
                errors["paid_at"] = (
                    "A paid commission invoice requires a payment time."
                )

        elif self.paid_at is not None:
            errors["paid_at"] = (
                "A payment time cannot exist unless the invoice is paid."
            )

        if errors:
            raise ValidationError(errors)

    def _validate_immutable_receivable(self):
        if not self.pk:
            return

        original = CommissionInvoice.objects.get(
            pk=self.pk,
        )

        protected_fields = [
            "deal_id",
            "settlement_id",
            "agreement_id",
            "owner_id",
            "invoice_number",
            "owner_number_snapshot",
            "owner_legal_name_snapshot",
            "owner_phone_number_snapshot",
            "owner_email_snapshot",
            "agreement_number_snapshot",
            "amount",
            "currency",
            "issued_at",
            "created_by_id",
        ]

        changed_fields = [
            field
            for field in protected_fields
            if getattr(original, field) != getattr(self, field)
        ]

        if changed_fields:
            raise ValidationError(
                {
                    "commission_invoice": (
                        "Issued commission receivable evidence "
                        "cannot be changed. Attempted fields: "
                        + ", ".join(changed_fields)
                    )
                }
            )

    def save(self, *args, **kwargs):
        self._validate_immutable_receivable()

        if not self.invoice_number:
            self.invoice_number = (
                f"PH-COM-{timezone.now().year}-"
                f"{uuid4().hex[:12].upper()}"
            )

        if self.owner_id and not self.pk:
            self.owner_number_snapshot = self.owner.owner_number
            self.owner_legal_name_snapshot = self.owner.legal_name
            self.owner_phone_number_snapshot = self.owner.phone_number
            self.owner_email_snapshot = self.owner.email or ""

        if self.agreement_id and not self.pk:
            self.agreement_number_snapshot = (
                self.agreement.agreement_number
            )

        if self.amount is not None:
            self.amount = self.amount.quantize(
                Decimal("0.01")
            )

        self.currency = self.currency.strip().upper()

        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.invoice_number



class CommissionReceipt(models.Model):
    """
    Immutable evidence of commission money received by Pata Hao
    against a CommissionInvoice.

    Multiple receipts may exist for one invoice so partial payments
    remain preserved as individual financial events.
    """

    class PaymentMethod(models.TextChoices):
        MPESA = "mpesa", "M-Pesa"
        AIRTEL_MONEY = "airtel_money", "Airtel Money"
        BANK_TRANSFER = "bank_transfer", "Bank transfer"
        CASH = "cash", "Cash"
        OTHER = "other", "Other"

    invoice = models.ForeignKey(
        CommissionInvoice,
        on_delete=models.PROTECT,
        related_name="receipts",
    )

    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
    )

    currency = models.CharField(
        max_length=3,
        default="KES",
    )

    payment_method = models.CharField(
        max_length=30,
        choices=PaymentMethod.choices,
    )

    payment_reference = models.CharField(
        max_length=150,
        db_index=True,
    )

    received_at = models.DateTimeField()

    notes = models.TextField(
        blank=True,
    )

    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="recorded_commission_receipts",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = [
            "invoice",
            "received_at",
            "id",
        ]

    def clean(self):
        errors = {}

        if self.amount is None or self.amount <= Decimal("0.00"):
            errors["amount"] = (
                "The received amount must be greater than zero."
            )

        if not self.payment_reference.strip():
            errors["payment_reference"] = (
                "A payment reference is required."
            )

        if self.invoice_id:
            if self.invoice.status in {
                CommissionInvoice.Status.CANCELLED,
                CommissionInvoice.Status.REFUNDED,
            }:
                errors["invoice"] = (
                    "Commission cannot be received against a "
                    "cancelled or refunded invoice."
                )

            existing_received = (
                self.invoice.receipts
                .exclude(pk=self.pk)
                .aggregate(
                    total=models.Sum("amount")
                )["total"]
                or Decimal("0.00")
            )

            if self.amount is not None:
                proposed_received = existing_received + self.amount

                if proposed_received > self.invoice.amount:
                    errors["amount"] = (
                        "This receipt would exceed the commission "
                        "invoice amount."
                    )

            if (
                self.currency
                and self.invoice.currency
                and self.currency.strip().upper()
                != self.invoice.currency.strip().upper()
            ):
                errors["currency"] = (
                    "The receipt currency must match the "
                    "commission invoice currency."
                )

        if errors:
            raise ValidationError(errors)

    def _validate_immutable(self):
        if not self.pk:
            return

        original = CommissionReceipt.objects.get(
            pk=self.pk,
        )

        protected_fields = [
            "invoice_id",
            "amount",
            "currency",
            "payment_method",
            "payment_reference",
            "received_at",
            "notes",
            "recorded_by_id",
        ]

        changed_fields = [
            field
            for field in protected_fields
            if getattr(original, field) != getattr(self, field)
        ]

        if changed_fields:
            raise ValidationError(
                {
                    "commission_receipt": (
                        "Commission receipt evidence is immutable. "
                        "Attempted fields: "
                        + ", ".join(changed_fields)
                    )
                }
            )

    def save(self, *args, **kwargs):
        self._validate_immutable()

        if self.amount is not None:
            self.amount = self.amount.quantize(
                Decimal("0.01")
            )

        self.currency = self.currency.strip().upper()
        self.payment_reference = self.payment_reference.strip()

        self.full_clean()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.pk:
            raise ValidationError(
                {
                    "commission_receipt": (
                        "Commission receipt evidence cannot be deleted."
                    )
                }
            )

        return super().delete(*args, **kwargs)

    def __str__(self):
        return (
            f"Commission receipt #{self.pk or 'new'} — "
            f"{self.currency} {self.amount}"
        )
