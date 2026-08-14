import builtins
import hashlib
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


def mandate_upload_path(instance, filename):
    extension = filename.rsplit(".", 1)[-1].lower()

    return (
        "property_mandates/"
        f"{instance.mandate.mandate_number}/"
        f"{uuid4().hex}.{extension}"
    )


class PropertyOwner(models.Model):
    class OwnerType(models.TextChoices):
        INDIVIDUAL = "individual", "Individual"
        COMPANY = "company", "Company"
        TRUST = "trust", "Trust or estate"
        OTHER = "other", "Other"

    class VerificationStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        UNDER_REVIEW = "under_review", "Under review"
        VERIFIED = "verified", "Verified"
        REJECTED = "rejected", "Rejected"
        SUSPENDED = "suspended", "Suspended"

    owner_number = models.CharField(max_length=40, unique=True, blank=True, editable=False)
    owner_type = models.CharField(max_length=20, choices=OwnerType.choices, default=OwnerType.INDIVIDUAL)
    legal_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=30)
    email = models.EmailField(blank=True)
    national_id_number = models.CharField(max_length=80, blank=True, help_text="Private. Never expose through public APIs.")
    company_registration_number = models.CharField(max_length=100, blank=True)
    kra_pin = models.CharField(max_length=30, blank=True)
    verification_status = models.CharField(max_length=30, choices=VerificationStatus.choices, default=VerificationStatus.PENDING, db_index=True)
    verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name="verified_property_owners", null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    verification_notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_property_owners")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["legal_name"]

    def save(self, *args, **kwargs):
        if not self.owner_number:
            self.owner_number = f"PH-OWN-{uuid4().hex[:12].upper()}"
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def is_verified(self):
        return (
            self.verification_status == self.VerificationStatus.VERIFIED
            and self.verified_at is not None
            and self.verified_by_id is not None
            and self.is_active
        )

    def __str__(self):
        return f"{self.owner_number} — {self.legal_name}"


class PropertyMandate(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        AWAITING_PARTNER_ACCEPTANCE = "awaiting_partner_acceptance", "Awaiting partner acceptance"
        PARTNER_ACCEPTED = "partner_accepted", "Partner accepted"
        UNDER_REVIEW = "under_review", "Under review"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        EXPIRED = "expired", "Expired"
        CANCELLED = "cancelled", "Cancelled"

    class AuthorizationMethod(models.TextChoices):
        VERBAL = "verbal", "Verbal authorization"
        PHONE = "phone", "Phone authorization"
        WHATSAPP = "whatsapp", "WhatsApp or message authorization"
        WRITTEN = "written", "Written authorization"
        PROPERTY_MANAGER = "property_manager", "Property management authority"
        OWNER_SELF = "owner_self", "Partner is the owner"
        OTHER = "other", "Other"

    property = models.ForeignKey("properties.Property", on_delete=models.PROTECT, related_name="mandates")
    owner = models.ForeignKey(PropertyOwner, on_delete=models.PROTECT, related_name="mandates")
    partner = models.ForeignKey("partners.Partner", on_delete=models.PROTECT, related_name="property_mandates")
    commission_agreement = models.OneToOneField(
        "commissions.CommissionAgreement",
        on_delete=models.PROTECT,
        related_name="property_mandate",
        null=True,
        blank=True,
    )

    mandate_number = models.CharField(max_length=40, unique=True, blank=True, editable=False)
    version = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=40, choices=Status.choices, default=Status.DRAFT, db_index=True)
    authorization_method = models.CharField(max_length=30, choices=AuthorizationMethod.choices, default=AuthorizationMethod.VERBAL)
    authorization_notes = models.TextField(blank=True)
    effective_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    protection_period_days = models.PositiveIntegerField(default=180)

    owner_authority_confirmed = models.BooleanField(
        default=False,
        help_text="Partner declares that the owner/landlord/authorized representative gave authority to market this property.",
    )
    no_cash_acknowledged = models.BooleanField(
        default=False,
        help_text="Partner acknowledged Pata Hao platform payments and recorded transaction flows must not be bypassed.",
    )
    anti_circumvention_acknowledged = models.BooleanField(
        default=False,
        help_text="Partner acknowledged that Pata Hao introductions cannot knowingly be bypassed to avoid agreed commissions.",
    )
    partner_declared = models.BooleanField(default=False)
    partner_declared_at = models.DateTimeField(null=True, blank=True)
    declaration_version = models.CharField(max_length=30, default="2026.1")
    declared_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="declared_property_mandates",
        null=True,
        blank=True,
    )

    submitted_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="approved_property_mandates",
        null=True,
        blank=True,
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_property_mandates")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["property", "version"], name="unique_mandate_version_per_property"),
        ]

    def clean(self):
        errors = {}

        if self.property_id and self.partner_id and self.property.partner_id != self.partner_id:
            errors["partner"] = "The mandate partner must match the property partner."

        if (
            self.commission_agreement_id
            and self.property_id
            and self.commission_agreement.property_id != self.property_id
        ):
            errors["commission_agreement"] = "The commission agreement must belong to this property."

        if self.expiry_date and self.effective_date and self.expiry_date <= self.effective_date:
            errors["expiry_date"] = "The expiry date must be after the effective date."

        if self.partner_declared:
            if not self.owner_authority_confirmed:
                errors["owner_authority_confirmed"] = "Partner declaration requires confirmed property authority."
            if not self.no_cash_acknowledged:
                errors["no_cash_acknowledged"] = "The no-cash policy must be acknowledged."
            if not self.anti_circumvention_acknowledged:
                errors["anti_circumvention_acknowledged"] = "The anti-circumvention rule must be acknowledged."
            if self.partner_declared_at is None:
                errors["partner_declared_at"] = "The partner declaration date and time are required."
            if self.declared_by is None:
                errors["declared_by"] = "The declaring user is required."
            if self.partner_id and self.declared_by_id and self.partner.user_id != self.declared_by_id:
                errors["declared_by"] = "Only the user linked to this partner may declare this mandate."
        else:
            if self.partner_declared_at is not None:
                errors["partner_declared_at"] = "A declaration time cannot exist before partner declaration."
            if self.declared_by is not None:
                errors["declared_by"] = "A declaring user cannot exist before partner declaration."

        if self.status in {self.Status.PARTNER_ACCEPTED, self.Status.UNDER_REVIEW, self.Status.APPROVED}:
            if not self.partner_declared:
                errors["status"] = "This mandate status requires a partner declaration."

        if self.status == self.Status.APPROVED:
            if self.approved_by is None:
                errors["approved_by"] = "The approving administrator is required."
            if self.approved_at is None:
                errors["approved_at"] = "The approval date and time are required."
            if self.commission_agreement is None:
                errors["commission_agreement"] = "An accepted commission agreement is required."
            elif not self.commission_agreement.is_publish_ready():
                errors["commission_agreement"] = (
                    "The commission agreement must be accepted, verified, locked, and financially valid."
                )

        if self.status == self.Status.REJECTED and not self.rejection_reason.strip():
            errors["rejection_reason"] = "A rejection reason is required."

        if errors:
            raise ValidationError(errors)

    @builtins.property
    def has_approved_signed_document(self):
        if not self.pk:
            return False
        return self.documents.filter(
            document_type=MandateDocument.DocumentType.SIGNED_MANDATE,
            status=MandateDocument.Status.APPROVED,
            is_current=True,
        ).exists()

    @builtins.property
    def is_currently_valid(self):
        today = timezone.localdate()

        if self.status != self.Status.APPROVED:
            return False
        if self.effective_date and self.effective_date > today:
            return False
        if self.expiry_date and self.expiry_date < today:
            return False
        if not self.partner_declared:
            return False
        if not self.owner_authority_confirmed:
            return False
        if not self.no_cash_acknowledged:
            return False
        if not self.anti_circumvention_acknowledged:
            return False
        if self.commission_agreement is None:
            return False
        if not self.commission_agreement.is_publish_ready():
            return False
        return True

    def declare_by_partner(self, *, user):
        if self.status in {
            self.Status.APPROVED,
            self.Status.REJECTED,
            self.Status.EXPIRED,
            self.Status.CANCELLED,
        }:
            raise ValidationError("This mandate cannot be declared in its current status.")

        if self.partner_id is None:
            raise ValidationError("A partner is required before mandate declaration.")

        if self.partner.user_id != user.id:
            raise ValidationError("Only the partner assigned to this property may declare the mandate.")

        if not self.owner_authority_confirmed:
            raise ValidationError("Confirm your authority to market the property first.")
        if not self.no_cash_acknowledged:
            raise ValidationError("Acknowledge the Pata Hao payment policy first.")
        if not self.anti_circumvention_acknowledged:
            raise ValidationError("Acknowledge the anti-circumvention rule first.")
        if self.commission_agreement is None:
            raise ValidationError("A commission agreement is required before mandate acceptance.")
        if not self.commission_agreement.partner_accepted:
            raise ValidationError("Accept the commission agreement before accepting the mandate.")

        self.partner_declared = True
        self.partner_declared_at = timezone.now()
        self.declared_by = user
        self.status = self.Status.PARTNER_ACCEPTED

    def submit_for_review(self):
        if not self.partner_declared:
            raise ValidationError("The partner must accept the digital mandate before review.")
        if self.status in {
            self.Status.APPROVED,
            self.Status.REJECTED,
            self.Status.EXPIRED,
            self.Status.CANCELLED,
        }:
            raise ValidationError("This mandate cannot be submitted in its current status.")

        self.status = self.Status.UNDER_REVIEW
        self.submitted_at = timezone.now()

    def approve(self, *, approved_by):
        if approved_by is None or not approved_by.is_staff:
            raise ValidationError("Only a Pata Hao administrator can approve a mandate.")
        if not self.partner_declared:
            raise ValidationError("The partner must accept the mandate before approval.")
        if self.commission_agreement is None:
            raise ValidationError("A commission agreement is required before approval.")
        if not self.commission_agreement.is_publish_ready():
            raise ValidationError(
                "The commission agreement must be accepted, verified, locked, and financially valid before mandate approval."
            )

        self.status = self.Status.APPROVED
        self.approved_by = approved_by
        self.approved_at = timezone.now()
        self.rejection_reason = ""
        if self.effective_date is None:
            self.effective_date = timezone.localdate()
        self.full_clean()

    def reject(self, *, rejected_by, reason):
        if rejected_by is None or not rejected_by.is_staff:
            raise ValidationError("Only a Pata Hao administrator can reject a mandate.")
        cleaned_reason = (reason or "").strip()
        if not cleaned_reason:
            raise ValidationError("A rejection reason is required.")
        self.status = self.Status.REJECTED
        self.rejection_reason = cleaned_reason
        self.approved_by = None
        self.approved_at = None

    def save(self, *args, **kwargs):
        if not self.mandate_number:
            self.mandate_number = f"PH-MAN-{timezone.now().year}-{uuid4().hex[:10].upper()}"
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.mandate_number} — {self.property.title}"


class MandateDocument(models.Model):
    class DocumentType(models.TextChoices):
        SIGNED_MANDATE = "signed_mandate", "Signed property mandate"
        OWNER_ID = "owner_id", "Owner identification"
        OWNERSHIP_PROOF = "ownership_proof", "Ownership proof"
        AUTHORITY_LETTER = "authority_letter", "Authority letter"
        COMPANY_RESOLUTION = "company_resolution", "Company resolution"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        UPLOADED = "uploaded", "Uploaded"
        UNDER_REVIEW = "under_review", "Under review"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    mandate = models.ForeignKey(PropertyMandate, on_delete=models.PROTECT, related_name="documents")
    document_type = models.CharField(max_length=30, choices=DocumentType.choices)
    file = models.FileField(upload_to=mandate_upload_path)
    original_filename = models.CharField(max_length=255, blank=True)
    file_hash = models.CharField(max_length=64, blank=True, editable=False, db_index=True)
    file_size = models.PositiveBigIntegerField(default=0, editable=False)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.UPLOADED, db_index=True)
    is_current = models.BooleanField(default=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="uploaded_mandate_documents")
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name="reviewed_mandate_documents", null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["mandate", "document_type"],
                condition=models.Q(is_current=True),
                name="one_current_document_per_mandate_type",
            ),
        ]

    def calculate_hash(self):
        digest = hashlib.sha256()
        self.file.open("rb")
        try:
            for chunk in self.file.chunks():
                digest.update(chunk)
        finally:
            self.file.close()
        return digest.hexdigest()

    def clean(self):
        errors = {}
        if self.status == self.Status.APPROVED:
            if self.reviewed_by is None:
                errors["reviewed_by"] = "The reviewing administrator is required."
            if self.reviewed_at is None:
                errors["reviewed_at"] = "The review date and time are required."
        if self.status == self.Status.REJECTED and not self.rejection_reason.strip():
            errors["rejection_reason"] = "A rejection reason is required."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        if is_new:
            self.original_filename = self.original_filename or self.file.name.rsplit("/", 1)[-1]
            self.file_size = self.file.size
        self.full_clean()
        super().save(*args, **kwargs)
        if is_new and not self.file_hash:
            self.file_hash = self.calculate_hash()
            type(self).objects.filter(pk=self.pk).update(file_hash=self.file_hash)

    def approve(self, *, reviewed_by):
        if reviewed_by is None or not reviewed_by.is_staff:
            raise ValidationError("Only a Pata Hao administrator can approve documents.")
        self.status = self.Status.APPROVED
        self.reviewed_by = reviewed_by
        self.reviewed_at = timezone.now()
        self.rejection_reason = ""
        self.save()

    def __str__(self):
        return f"{self.mandate.mandate_number} — {self.get_document_type_display()}"


class MandateEvent(models.Model):
    mandate = models.ForeignKey(PropertyMandate, on_delete=models.PROTECT, related_name="events")
    action = models.CharField(max_length=60)
    notes = models.TextField(blank=True)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name="mandate_events", null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.mandate.mandate_number}: {self.action}"
