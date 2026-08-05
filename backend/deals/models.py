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