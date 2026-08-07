import builtins
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class ProtectedIntroduction(models.Model):
    """
    Property Introduction Certificate (PIC).

    Permanent commercial evidence that Pata Hao introduced
    a customer to a property under an approved mandate and
    locked commission agreement.
    """

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        CONVERTED_TO_DEAL = (
            "converted_to_deal",
            "Converted to deal",
        )
        EXPIRED = "expired", "Expired"
        DISPUTED = "disputed", "Disputed"
        CANCELLED = "cancelled", "Cancelled"

    certificate_number = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        editable=False,
    )

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="property_introduction_certificates",
    )

    property = models.ForeignKey(
        "properties.Property",
        on_delete=models.PROTECT,
        related_name="property_introduction_certificates",
    )

    partner = models.ForeignKey(
        "partners.Partner",
        on_delete=models.PROTECT,
        related_name="property_introduction_certificates",
    )

    viewing = models.OneToOneField(
        "viewings.Viewing",
        on_delete=models.PROTECT,
        related_name="property_introduction_certificate",
    )

    mandate = models.ForeignKey(
        "mandates.PropertyMandate",
        on_delete=models.PROTECT,
        related_name="property_introduction_certificates",
    )

    commission_agreement = models.ForeignKey(
        "commissions.CommissionAgreement",
        on_delete=models.PROTECT,
        related_name="property_introduction_certificates",
    )

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
    )

    protected_from = models.DateTimeField(
        default=timezone.now,
    )

    protected_until = models.DateTimeField()

    protection_period_days = models.PositiveIntegerField()

    # Immutable snapshots preserve the original commercial facts.
    customer_name_snapshot = models.CharField(
        max_length=255,
        blank=True,
    )

    property_title_snapshot = models.CharField(
        max_length=255,
    )

    listing_type_snapshot = models.CharField(
        max_length=30,
    )

    property_price_snapshot = models.DecimalField(
        max_digits=14,
        decimal_places=2,
    )

    owner_name_snapshot = models.CharField(
        max_length=255,
    )

    partner_name_snapshot = models.CharField(
        max_length=255,
    )

    mandate_number_snapshot = models.CharField(
        max_length=50,
    )

    commission_agreement_number_snapshot = models.CharField(
        max_length=50,
    )

    commission_method_snapshot = models.CharField(
        max_length=20,
    )

    commission_rate_snapshot = models.DecimalField(
        max_digits=6,
        decimal_places=3,
        null=True,
        blank=True,
    )

    fixed_commission_snapshot = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
    )

    expected_commission_snapshot = models.DecimalField(
        max_digits=14,
        decimal_places=2,
    )

    currency_snapshot = models.CharField(
        max_length=3,
        default="KES",
    )

    viewing_fee_snapshot = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    viewing_payment_reference = models.CharField(
        max_length=120,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "customer",
                    "property",
                ],
                condition=models.Q(
                    status__in=[
                        "active",
                        "converted_to_deal",
                        "disputed",
                    ],
                ),
                name="one_active_pic_per_customer_property",
            ),
        ]

    def clean(self):
        errors = {}

        if self.viewing_id:
            if self.viewing.customer_id != self.customer_id:
                errors["customer"] = (
                    "PIC customer must match the viewing customer."
                )

            if self.viewing.property_id != self.property_id:
                errors["property"] = (
                    "PIC property must match the viewing property."
                )

            if self.viewing.status != self.viewing.Status.COMPLETED:
                errors["viewing"] = (
                    "A PIC can only be created after the viewing "
                    "has been completed."
                )

            if self.viewing.assigned_partner_id is None:
                errors["partner"] = (
                    "A completed viewing must have an assigned partner "
                    "before a PIC can be created."
                )

        if self.viewing_id and self.partner_id:
            if self.viewing.assigned_partner_id != self.partner_id:
                errors["partner"] = (
                    "PIC partner must match the partner assigned "
                    "to the viewing."
                )

        if self.mandate_id:
            if self.mandate.property_id != self.property_id:
                errors["mandate"] = (
                    "The mandate must belong to this property."
                )

            if not self.mandate.is_currently_valid:
                errors["mandate"] = (
                    "A valid approved property mandate is required."
                )

        if self.commission_agreement_id:
            if (
                self.commission_agreement.property_id
                != self.property_id
            ):
                errors["commission_agreement"] = (
                    "The commission agreement must belong "
                    "to this property."
                )

            if not self.commission_agreement.is_publish_ready():
                errors["commission_agreement"] = (
                    "The commission agreement must be locked "
                    "and publish-ready."
                )

        if (
            self.protected_until
            and self.protected_from
            and self.protected_until <= self.protected_from
        ):
            errors["protected_until"] = (
                "Protection must end after it begins."
            )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self.pk:
            original = type(self)._base_manager.get(
                pk=self.pk,
            )

            immutable_fields = [
                "certificate_number",
                "customer_id",
                "property_id",
                "partner_id",
                "viewing_id",
                "mandate_id",
                "commission_agreement_id",
                "protected_from",
                "protected_until",
                "protection_period_days",
                "customer_name_snapshot",
                "property_title_snapshot",
                "listing_type_snapshot",
                "property_price_snapshot",
                "owner_name_snapshot",
                "partner_name_snapshot",
                "mandate_number_snapshot",
                "commission_agreement_number_snapshot",
                "commission_method_snapshot",
                "commission_rate_snapshot",
                "fixed_commission_snapshot",
                "expected_commission_snapshot",
                "currency_snapshot",
                "viewing_fee_snapshot",
                "viewing_payment_reference",
                "created_at",
            ]

            changed_fields = [
                field
                for field in immutable_fields
                if getattr(original, field)
                != getattr(self, field)
            ]

            if changed_fields:
                raise ValidationError(
                    {
                        "protected_introduction": (
                            "PIC evidence cannot be changed after "
                            "creation. Attempted fields: "
                            + ", ".join(changed_fields)
                        )
                    }
                )

            allowed_status_transitions = {
                self.Status.ACTIVE: {
                    self.Status.CONVERTED_TO_DEAL,
                    self.Status.EXPIRED,
                    self.Status.DISPUTED,
                    self.Status.CANCELLED,
                },
                self.Status.DISPUTED: {
                    self.Status.ACTIVE,
                    self.Status.CONVERTED_TO_DEAL,
                    self.Status.CANCELLED,
                },
                self.Status.CONVERTED_TO_DEAL: set(),
                self.Status.EXPIRED: set(),
                self.Status.CANCELLED: set(),
            }

            if self.status != original.status:
                permitted = allowed_status_transitions.get(
                    original.status,
                    set(),
                )

                if self.status not in permitted:
                    raise ValidationError(
                        {
                            "status": (
                                "PIC status cannot move from "
                                f"{original.status} "
                                f"to {self.status}."
                            )
                        }
                    )

        if not self.certificate_number:
            self.certificate_number = (
                f"PIC-{timezone.now().year}-"
                f"{uuid4().hex[:12].upper()}"
            )

        self.full_clean()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError(
            "Property Introduction Certificates are permanent "
            "commercial records and cannot be deleted."
    )

    def transition_status(
        self,
        *,
        new_status,
        actor,
        notes="",
        metadata=None,
    ):
        if actor is None:
            raise ValidationError(
                "An authenticated actor is required."
            )

        previous_status = self.status
        self.status = new_status
        self.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        IntroductionEvent.objects.create(
            introduction=self,
            action="status_changed",
            actor=actor,
            notes=notes,
            metadata={
                "previous_status": previous_status,
                "new_status": new_status,
                **(metadata or {}),
            },
        )   

    @builtins.property
    def is_active(self):
        return (
            self.status == self.Status.ACTIVE
            and self.protected_until > timezone.now()
        )

    def __str__(self):
        return self.certificate_number


class IntroductionEvent(models.Model):
    introduction = models.ForeignKey(
        ProtectedIntroduction,
        on_delete=models.PROTECT,
        related_name="events",
    )

    action = models.CharField(
        max_length=60,
    )

    notes = models.TextField(
        blank=True,
    )

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="property_introduction_events",
        null=True,
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
        ordering = ["created_at"]

    def __str__(self):
        return (
            f"{self.introduction.certificate_number}: "
            f"{self.action}"
        )

class ProtectedIntroductionQuerySet(models.QuerySet):
    def delete(self):
        raise ValidationError(
            "Property Introduction Certificates cannot be deleted."
        )

    def update(self, **kwargs):
        raise ValidationError(
            "PIC records cannot be modified through bulk updates."
        )