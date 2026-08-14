from decimal import Decimal
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from properties.models import Property


class CommissionPlan(models.Model):
    """
    Defines the percentage of the eligible commission allocation
    earned by a Pata Hao partner.

    Current business levels:
    Bronze: 20%
    Silver: 30%
    Gold: 40%
    Platinum: 50%
    """

    name = models.CharField(
        max_length=50,
        unique=True,
    )

    partner_share_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text=(
            "The partner's earning percentage. "
            "For example, enter 20.00 for Bronze."
        ),
    )

    minimum_completed_transactions = models.PositiveIntegerField(
        default=0,
        help_text=(
            "The minimum number of completed transactions normally "
            "required for this level."
        ),
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "partner_share_rate",
            "name",
        ]

    def clean(self):
        errors = {}

        if self.partner_share_rate is None:
            errors["partner_share_rate"] = (
                "The partner share rate is required."
            )
        elif self.partner_share_rate <= Decimal("0.00"):
            errors["partner_share_rate"] = (
                "The partner share rate must be greater than zero."
            )
        elif self.partner_share_rate > Decimal("100.00"):
            errors["partner_share_rate"] = (
                "The partner share rate cannot exceed 100%."
            )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.name} — "
            f"{self.partner_share_rate}% partner share"
        )


class CommissionAgreement(models.Model):
    """
    Partner-facing commission agreement for one property.

    This records what commission is payable to Pata Hao if a successful
    transaction occurs. Internal Pata Hao allocation is handled separately
    by CommissionSettlement.
    """

    class CommissionMethod(models.TextChoices):
        FIXED = "fixed", "Fixed amount"
        PERCENTAGE = "percentage", "Percentage"

    class CommissionBasis(models.TextChoices):
        FIRST_MONTH_RENT = (
            "first_month_rent",
            "First month's rent",
        )
        SALE_PRICE = (
            "sale_price",
            "Sale price",
        )
        TRANSACTION_VALUE = (
            "transaction_value",
            "Agreed transaction value",
        )

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        VERIFIED = "verified", "Verified"
        LOCKED = "locked", "Locked"
        CANCELLED = "cancelled", "Cancelled"

        # Kept temporarily for compatibility with older database rows/code.
        AWAITING_OWNER_CONFIRMATION = (
            "awaiting_owner_confirmation",
            "Awaiting owner confirmation",
        )
        OWNER_CONFIRMED = (
            "owner_confirmed",
            "Owner confirmed",
        )

    property = models.OneToOneField(
        Property,
        on_delete=models.PROTECT,
        related_name="commission_agreement",
    )

    agreement_number = models.CharField(
        max_length=40,
        unique=True,
        blank=True,
        editable=False,
    )

    owner_name = models.CharField(
        max_length=255,
    )

    owner_phone_number = models.CharField(
        max_length=30,
    )

    commission_method = models.CharField(
        max_length=20,
        choices=CommissionMethod.choices,
    )

    commission_basis = models.CharField(
        max_length=30,
        choices=CommissionBasis.choices,
        default=CommissionBasis.FIRST_MONTH_RENT,
    )

    commission_rate = models.DecimalField(
        max_digits=6,
        decimal_places=3,
        null=True,
        blank=True,
        help_text=(
            "For percentage agreements, enter the agreed rate. "
            "For example, enter 10.000 for 10%."
        ),
    )

    fixed_commission_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=(
            "The fixed commission amount. "
            "Required only for fixed agreements."
        ),
    )

    transaction_value = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        help_text=(
            "The rent, sale price, or agreed transaction value "
            "used to calculate the commission."
        ),
    )

    expected_total_commission = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        editable=False,
    )

    currency = models.CharField(
        max_length=3,
        default="KES",
    )

    status = models.CharField(
        max_length=40,
        choices=Status.choices,
        default=Status.DRAFT,
    )

    partner_accepted = models.BooleanField(
        default=False,
    )

    partner_accepted_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    accepted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="accepted_commission_agreements",
        null=True,
        blank=True,
    )

    # Legacy fields retained temporarily for existing rows/admin/tests.
    owner_confirmed = models.BooleanField(
        default=False,
    )

    owner_confirmed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    is_verified = models.BooleanField(
        default=False,
    )

    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="verified_commission_agreements",
        null=True,
        blank=True,
    )

    verified_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    is_locked = models.BooleanField(
        default=False,
    )

    locked_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_commission_agreements",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def clean(self):
        errors = {}

        if (
            self.transaction_value is None
            or self.transaction_value <= Decimal("0.00")
        ):
            errors["transaction_value"] = (
                "The transaction value must be greater than zero."
            )

        if self.commission_method == self.CommissionMethod.PERCENTAGE:
            if self.commission_rate is None:
                errors["commission_rate"] = (
                    "A commission rate is required for a percentage agreement."
                )
            elif self.commission_rate <= Decimal("0.00"):
                errors["commission_rate"] = (
                    "The commission rate must be greater than zero."
                )
            elif self.commission_rate > Decimal("100.00"):
                errors["commission_rate"] = (
                    "The commission rate cannot exceed 100%."
                )

            if self.fixed_commission_amount is not None:
                errors["fixed_commission_amount"] = (
                    "Do not enter a fixed amount for a percentage agreement."
                )

        elif self.commission_method == self.CommissionMethod.FIXED:
            if self.fixed_commission_amount is None:
                errors["fixed_commission_amount"] = (
                    "A fixed commission amount is required for a fixed agreement."
                )
            elif self.fixed_commission_amount <= Decimal("0.00"):
                errors["fixed_commission_amount"] = (
                    "The fixed commission amount must be greater than zero."
                )

            if self.commission_rate is not None:
                errors["commission_rate"] = (
                    "Do not enter a commission rate for a fixed agreement."
                )

        if self.partner_accepted:
            if self.partner_accepted_at is None:
                errors["partner_accepted_at"] = (
                    "The partner acceptance date and time are required."
                )

            if self.accepted_by is None:
                errors["accepted_by"] = (
                    "The user accepting the commission agreement is required."
                )

            if (
                self.property_id
                and self.accepted_by_id
                and self.property.partner_id
            ):
                if self.property.partner.user_id != self.accepted_by_id:
                    errors["accepted_by"] = (
                        "Only the partner assigned to this property "
                        "may accept the commission agreement."
                    )
        else:
            if self.partner_accepted_at is not None:
                errors["partner_accepted_at"] = (
                    "Partner acceptance time cannot exist before acceptance."
                )

            if self.accepted_by is not None:
                errors["accepted_by"] = (
                    "An accepting user cannot exist before partner acceptance."
                )

        # Legacy owner fields are tolerated for old records but are no longer
        # prerequisites for verification/publication.
        if self.owner_confirmed:
            if self.owner_confirmed_at is None:
                errors["owner_confirmed_at"] = (
                    "The owner confirmation date and time are required."
                )
        elif self.owner_confirmed_at is not None:
            errors["owner_confirmed_at"] = (
                "The owner confirmation time cannot be recorded "
                "before owner confirmation."
            )

        if self.is_verified:
            if not self.partner_accepted:
                errors["is_verified"] = (
                    "The agreement cannot be verified before partner acceptance."
                )

            if self.verified_by is None:
                errors["verified_by"] = (
                    "The administrator who verified the agreement is required."
                )

            if self.verified_at is None:
                errors["verified_at"] = (
                    "The verification date and time are required."
                )
        else:
            if self.verified_by is not None:
                errors["verified_by"] = (
                    "A verifier cannot be recorded before verification."
                )

            if self.verified_at is not None:
                errors["verified_at"] = (
                    "A verification time cannot be recorded before verification."
                )

        if self.is_locked:
            if not self.is_verified:
                errors["is_locked"] = (
                    "The agreement cannot be locked before verification."
                )

            if self.locked_at is None:
                errors["locked_at"] = (
                    "The locking date and time are required."
                )
        elif self.locked_at is not None:
            errors["locked_at"] = (
                "A locking time cannot be recorded before the agreement is locked."
            )

        if self.status == self.Status.VERIFIED:
            if not self.is_verified:
                errors["status"] = (
                    "Verified status requires agreement verification."
                )

        if self.status == self.Status.LOCKED:
            if not self.is_locked:
                errors["status"] = (
                    "Locked status requires the agreement to be locked."
                )

        if errors:
            raise ValidationError(errors)

    def calculate_expected_total(self):
        if self.commission_method == self.CommissionMethod.FIXED:
            amount = (
                self.fixed_commission_amount
                or Decimal("0.00")
            )
            return amount.quantize(
                Decimal("0.01")
            )

        if self.commission_method == self.CommissionMethod.PERCENTAGE:
            if (
                self.transaction_value is None
                or self.commission_rate is None
            ):
                return Decimal("0.00")

            amount = (
                self.transaction_value
                * self.commission_rate
                / Decimal("100")
            )

            return amount.quantize(
                Decimal("0.01")
            )

        return Decimal("0.00")

    def accept_by_partner(self, *, user):
        if self.is_locked:
            raise ValidationError(
                "A locked commission agreement cannot be changed."
            )

        if self.status == self.Status.CANCELLED:
            raise ValidationError(
                "A cancelled commission agreement cannot be accepted."
            )

        partner = getattr(
            self.property,
            "partner",
            None,
        )

        if partner is None or partner.user_id != user.id:
            raise ValidationError(
                "Only the partner assigned to this property "
                "may accept the commission agreement."
            )

        calculated = self.calculate_expected_total()

        if calculated <= Decimal("0.00"):
            raise ValidationError(
                "The commission amount must be greater than zero."
            )

        self.expected_total_commission = calculated
        self.partner_accepted = True
        self.partner_accepted_at = timezone.now()
        self.accepted_by = user

    def verify(self, verified_by):
        if self.is_locked:
            raise ValidationError(
                "A locked commission agreement cannot be changed."
            )

        if self.status == self.Status.CANCELLED:
            raise ValidationError(
                "A cancelled commission agreement cannot be verified."
            )

        if not self.partner_accepted:
            raise ValidationError(
                "Partner acceptance is required before verification."
            )

        if verified_by is None or not verified_by.is_staff:
            raise ValidationError(
                "A Pata Hao administrator is required to verify the agreement."
            )

        self.is_verified = True
        self.verified_by = verified_by
        self.verified_at = timezone.now()
        self.status = self.Status.VERIFIED

    def lock(self):
        if self.status == self.Status.CANCELLED:
            raise ValidationError(
                "A cancelled commission agreement cannot be locked."
            )

        if not self.partner_accepted:
            raise ValidationError(
                "Partner acceptance is required before locking."
            )

        if not self.is_verified:
            raise ValidationError(
                "The agreement must be verified before it can be locked."
            )

        if self.expected_total_commission <= Decimal("0.00"):
            raise ValidationError(
                "The commission amount must be greater than zero."
            )

        self.is_locked = True
        self.locked_at = timezone.now()
        self.status = self.Status.LOCKED

    def cancel(self):
        if self.is_locked:
            raise ValidationError(
                "A locked commission agreement cannot be cancelled."
            )

        self.status = self.Status.CANCELLED

    def is_publish_ready(self):
        return (
            self.partner_accepted
            and self.partner_accepted_at is not None
            and self.accepted_by_id is not None
            and self.is_verified
            and self.verified_by_id is not None
            and self.verified_at is not None
            and self.is_locked
            and self.locked_at is not None
            and self.status == self.Status.LOCKED
            and self.expected_total_commission > Decimal("0.00")
        )

    # Legacy compatibility helpers. These no longer participate in
    # publication readiness and can be removed in a later cleanup migration.
    def submit_for_owner_confirmation(self):
        if self.is_locked:
            raise ValidationError(
                "A locked commission agreement cannot be changed."
            )

        if self.status == self.Status.CANCELLED:
            raise ValidationError(
                "A cancelled commission agreement cannot be submitted."
            )

        self.status = self.Status.AWAITING_OWNER_CONFIRMATION

    def confirm_owner(self):
        if self.is_locked:
            raise ValidationError(
                "A locked commission agreement cannot be changed."
            )

        if self.status == self.Status.CANCELLED:
            raise ValidationError(
                "A cancelled commission agreement cannot be confirmed."
            )

        self.owner_confirmed = True
        self.owner_confirmed_at = timezone.now()
        self.status = self.Status.OWNER_CONFIRMED

    def _validate_locked_fields(self):
        if not self.pk:
            return

        original = CommissionAgreement.objects.get(
            pk=self.pk,
        )

        if not original.is_locked:
            return

        protected_fields = [
            "property_id",
            "owner_name",
            "owner_phone_number",
            "commission_method",
            "commission_basis",
            "commission_rate",
            "fixed_commission_amount",
            "transaction_value",
            "expected_total_commission",
            "currency",
            "partner_accepted",
            "partner_accepted_at",
            "accepted_by_id",
            "is_verified",
            "verified_by_id",
            "verified_at",
            "is_locked",
            "locked_at",
        ]

        for field_name in protected_fields:
            old_value = getattr(
                original,
                field_name,
            )
            new_value = getattr(
                self,
                field_name,
            )

            if old_value != new_value:
                raise ValidationError(
                    {
                        field_name: (
                            "This field cannot be changed because "
                            "the commission agreement is locked."
                        )
                    }
                )

        if self.status != original.status:
            raise ValidationError(
                {
                    "status": (
                        "The status of a locked commission agreement "
                        "cannot be changed."
                    )
                }
            )

    def save(self, *args, **kwargs):
        self._validate_locked_fields()

        if not self.agreement_number:
            self.agreement_number = (
                f"PH-CA-{uuid4().hex[:12].upper()}"
            )

        self.currency = (
            self.currency.strip().upper()
            if self.currency
            else "KES"
        )

        self.expected_total_commission = (
            self.calculate_expected_total()
        )

        self.full_clean()

        super().save(
            *args,
            **kwargs,
        )

    def __str__(self):
        return (
            f"{self.agreement_number} — "
            f"{self.property.title}"
        )

class CommissionSettlement(models.Model):
    """
    Records how the commission from a completed deal will be distributed.

    The CommissionAgreement records what the property owner agreed to pay.

    The CommissionSettlement records how that commission is shared between
    Pata Hao, partners, agents, and other eligible participants.
    """

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ALLOCATION_PENDING = (
            "allocation_pending",
            "Allocation pending",
        )
        ALLOCATED = "allocated", "Allocated"
        APPROVED = "approved", "Approved"
        PARTIALLY_PAID = "partially_paid", "Partially paid"
        PAID = "paid", "Paid"
        DISPUTED = "disputed", "Disputed"
        CANCELLED = "cancelled", "Cancelled"

    deal = models.OneToOneField(
        "deals.Deal",
        on_delete=models.PROTECT,
        related_name="commission_settlement",
    )

    agreement = models.ForeignKey(
        CommissionAgreement,
        on_delete=models.PROTECT,
        related_name="settlements",
    )

    gross_commission_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        help_text=(
            "The complete commission available for allocation. "
            "This is normally copied from the locked commission agreement."
        ),
    )

    allocated_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        editable=False,
    )

    unallocated_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        editable=False,
    )

    currency = models.CharField(
        max_length=3,
        default="KES",
    )

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.DRAFT,
    )

    notes = models.TextField(
        blank=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_commission_settlements",
    )

    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="approved_commission_settlements",
        null=True,
        blank=True,
    )

    approved_at = models.DateTimeField(
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

    def clean(self):
        errors = {}

        if (
            self.gross_commission_amount is None
            or self.gross_commission_amount <= Decimal("0.00")
        ):
            errors["gross_commission_amount"] = (
                "The gross commission amount must be greater than zero."
            )

        if self.agreement_id and not self.agreement.is_locked:
            errors["agreement"] = (
                "A commission settlement requires a locked "
                "commission agreement."
            )

        if self.deal_id and self.agreement_id:
            if self.deal.property_id != self.agreement.property_id:
                errors["agreement"] = (
                    "The commission agreement must belong to the same "
                    "property as the deal."
                )

        if self.status == self.Status.APPROVED:
            if self.approved_by is None:
                errors["approved_by"] = (
                    "The approving administrator is required."
                )

            if self.approved_at is None:
                errors["approved_at"] = (
                    "The approval date and time are required."
                )

            if self.unallocated_amount != Decimal("0.00"):
                errors["status"] = (
                    "The settlement cannot be approved until the entire "
                    "commission has been allocated."
                )

        if errors:
            raise ValidationError(errors)

    def recalculate_allocations(self):
        """
        Recalculate the total amount allocated across all participants.
        """

        if not self.pk:
            self.allocated_amount = Decimal("0.00")
            self.unallocated_amount = self.gross_commission_amount
            return

        total = self.participants.aggregate(
            total=models.Sum("amount")
        )["total"] or Decimal("0.00")

        self.allocated_amount = total.quantize(Decimal("0.01"))

        self.unallocated_amount = (
            self.gross_commission_amount - self.allocated_amount
        ).quantize(Decimal("0.01"))

    def approve(self, approved_by):
        """
        Approve a fully allocated commission settlement.
        """

        self.recalculate_allocations()

        if self.unallocated_amount != Decimal("0.00"):
            raise ValidationError(
                "The entire commission must be allocated before approval."
            )

        if approved_by is None:
            raise ValidationError(
                "The approving administrator is required."
            )

        self.approved_by = approved_by
        self.approved_at = timezone.now()
        self.status = self.Status.APPROVED

    def save(self, *args, **kwargs):
        self.currency = self.currency.strip().upper()

        if self.gross_commission_amount is not None:
            self.gross_commission_amount = (
                self.gross_commission_amount.quantize(
                    Decimal("0.01")
                )
            )

        if not self.pk:
            self.allocated_amount = Decimal("0.00")
            self.unallocated_amount = (
                self.gross_commission_amount or Decimal("0.00")
            )

        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"Settlement #{self.pk or 'new'} — "
            f"{self.deal}"
        )


class CommissionSettlementParticipant(models.Model):
    """
    Records one participant's share of a commission settlement.
    """

    class ParticipantType(models.TextChoices):
        PATA_HAO = "pata_hao", "Pata Hao"
        LISTING_PARTNER = (
            "listing_partner",
            "Listing partner",
        )
        CUSTOMER_AGENT = (
            "customer_agent",
            "Customer agent",
        )
        SELLER_AGENT = (
            "seller_agent",
            "Seller agent",
        )
        REFERRAL_AGENT = (
            "referral_agent",
            "Referral agent",
        )
        PROPERTY_OWNER = (
            "property_owner",
            "Property owner",
        )
        OTHER = "other", "Other"

    settlement = models.ForeignKey(
        CommissionSettlement,
        on_delete=models.CASCADE,
        related_name="participants",
    )

    participant_type = models.CharField(
        max_length=30,
        choices=ParticipantType.choices,
    )

    partner = models.ForeignKey(
        "partners.Partner",
        on_delete=models.SET_NULL,
        related_name="commission_settlement_shares",
        null=True,
        blank=True,
    )

    participant_name = models.CharField(
        max_length=255,
        blank=True,
        help_text=(
            "Use this for an external agent or participant who does "
            "not have a Pata Hao partner account."
        ),
    )

    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
    )

    percentage_of_total = models.DecimalField(
        max_digits=7,
        decimal_places=4,
        default=Decimal("0.0000"),
        editable=False,
    )

    is_platform_share = models.BooleanField(
        default=False,
        help_text="Select this when the allocation belongs to Pata Hao.",
    )

    notes = models.TextField(
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
            "settlement",
            "participant_type",
            "participant_name",
        ]

    def clean(self):
        errors = {}

        if self.amount is None or self.amount <= Decimal("0.00"):
            errors["amount"] = (
                "The participant amount must be greater than zero."
            )

        if not self.partner_id and not self.participant_name.strip():
            if self.participant_type != self.ParticipantType.PATA_HAO:
                errors["participant_name"] = (
                    "Select a partner or enter the participant's name."
                )

        if (
            self.participant_type == self.ParticipantType.PATA_HAO
            and not self.is_platform_share
        ):
            errors["is_platform_share"] = (
                "A Pata Hao allocation must be marked as a platform share."
            )

        if (
            self.participant_type != self.ParticipantType.PATA_HAO
            and self.is_platform_share
        ):
            errors["is_platform_share"] = (
                "Only a Pata Hao allocation can be marked as a "
                "platform share."
            )

        if self.settlement_id and self.amount:
            existing_total = (
                self.settlement.participants.exclude(
                    pk=self.pk
                ).aggregate(
                    total=models.Sum("amount")
                )["total"]
                or Decimal("0.00")
            )

            proposed_total = existing_total + self.amount

            if proposed_total > self.settlement.gross_commission_amount:
                errors["amount"] = (
                    "This allocation would exceed the gross commission "
                    "available for the settlement."
                )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.amount = self.amount.quantize(Decimal("0.01"))

        if (
            self.settlement_id
            and self.settlement.gross_commission_amount
            > Decimal("0.00")
        ):
            self.percentage_of_total = (
                self.amount
                / self.settlement.gross_commission_amount
                * Decimal("100")
            ).quantize(Decimal("0.0001"))

        self.full_clean()
        super().save(*args, **kwargs)

        self.settlement.recalculate_allocations()

        CommissionSettlement.objects.filter(
            pk=self.settlement_id
        ).update(
            allocated_amount=self.settlement.allocated_amount,
            unallocated_amount=self.settlement.unallocated_amount,
            status=(
                CommissionSettlement.Status.ALLOCATED
                if self.settlement.unallocated_amount == Decimal("0.00")
                else CommissionSettlement.Status.ALLOCATION_PENDING
            ),
        )

    def delete(self, *args, **kwargs):
        settlement_id = self.settlement_id

        result = super().delete(*args, **kwargs)

        settlement = CommissionSettlement.objects.get(
            pk=settlement_id
        )

        settlement.recalculate_allocations()

        CommissionSettlement.objects.filter(
            pk=settlement_id
        ).update(
            allocated_amount=settlement.allocated_amount,
            unallocated_amount=settlement.unallocated_amount,
            status=(
                CommissionSettlement.Status.ALLOCATED
                if settlement.unallocated_amount == Decimal("0.00")
                else CommissionSettlement.Status.ALLOCATION_PENDING
            ),
        )

        return result

    def __str__(self):
        name = (
            self.partner
            or self.participant_name
            or self.get_participant_type_display()
        )

        return (
            f"{name} — "
            f"{self.settlement.currency} {self.amount}"
        )