from django.db import models
from django.conf import settings

class PartnerTier(models.Model):
    """
    Defines a promotion tier.

    The system promotes partners into these tiers
    automatically when every rule is satisfied.
    """

    code = models.CharField(
        max_length=30,
        unique=True,
    )

    name = models.CharField(
        max_length=100,
    )

    description = models.TextField(
        blank=True,
    )

    rank = models.PositiveIntegerField(
        unique=True,
    )

    property_limit = models.PositiveIntegerField()

    minimum_completed_deals = models.PositiveIntegerField(
        default=0,
    )

    minimum_trust_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
    )
    commission_share_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=(
            "Percentage of an eligible Pata Hao commission "
            "allocated to a partner in this tier."
        ),
    )

    active = models.BooleanField(
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
            "rank",
        ]

    def __str__(self):
        return self.name


class PartnerTierAssignment(models.Model):
    """
    Records every tier assignment.

    History is never overwritten.
    A new assignment is created whenever a partner
    is promoted or demoted.
    """

    partner = models.ForeignKey(
        "partners.Partner",
        on_delete=models.PROTECT,
        related_name="tier_history",
    )

    tier = models.ForeignKey(
        PartnerTier,
        on_delete=models.PROTECT,
        related_name="assignments",
    )

    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="partner_tier_assignments",
        null=True,
        blank=True,
    )

    reason = models.TextField(
        blank=True,
    )

    active = models.BooleanField(
        default=True,
    )

    assigned_at = models.DateTimeField(
        auto_now_add=True,
    )

    ended_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = [
            "-assigned_at",
        ]

    def __str__(self):
        return (
            f"{self.partner.display_name} → {self.tier.name}"
        )
class PartnerPromotionReview(models.Model):
    """
    Snapshot of a promotion evaluation.

    The system creates these automatically.
    """

    class Decision(models.TextChoices):
        ELIGIBLE = "eligible", "Eligible"
        NOT_ELIGIBLE = "not_eligible", "Not Eligible"
        PROMOTED = "promoted", "Promoted"
        REJECTED = "rejected", "Rejected"

    partner = models.ForeignKey(
        "partners.Partner",
        on_delete=models.PROTECT,
    )

    current_tier = models.ForeignKey(
        PartnerTier,
        on_delete=models.PROTECT,
        related_name="+",
    )

    proposed_tier = models.ForeignKey(
        PartnerTier,
        on_delete=models.PROTECT,
        related_name="+",
    )

    trust_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
    )

    completed_deals = models.PositiveIntegerField()

    violations = models.PositiveIntegerField()

    decision = models.CharField(
        max_length=20,
        choices=Decision.choices,
    )

    metrics_snapshot = models.JSONField(
        default=dict,
        blank=True,
    )

    notes = models.TextField(
        blank=True,
    )

    reviewed_at = models.DateTimeField(
        auto_now_add=True,
    )

class PolicyRule(models.Model):
    """
    Defines an official Pata Hao partner policy.

    Policy records are retained so disciplinary decisions can
    always identify the exact rule that applied.
    """

    class Severity(models.TextChoices):
        MINOR = "minor", "Minor"
        MODERATE = "moderate", "Moderate"
        SERIOUS = "serious", "Serious"
        GROSS_MISCONDUCT = (
            "gross_misconduct",
            "Gross misconduct",
        )

    class RecommendedAction(models.TextChoices):
        WARNING = "warning", "Warning"
        SHORT_SUSPENSION = (
            "short_suspension",
            "Short suspension",
        )
        LONG_SUSPENSION = (
            "long_suspension",
            "Long suspension",
        )
        PERMANENT_BAN = (
            "permanent_ban",
            "Permanent ban",
        )

    code = models.CharField(
        max_length=30,
        unique=True,
    )

    title = models.CharField(
        max_length=200,
    )

    description = models.TextField()

    severity = models.CharField(
        max_length=30,
        choices=Severity.choices,
    )

    recommended_action = models.CharField(
        max_length=30,
        choices=RecommendedAction.choices,
    )

    effective_from = models.DateField()

    active = models.BooleanField(
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
            "code",
        ]

    def __str__(self):
        return f"{self.code} — {self.title}"

class PartnerViolation(models.Model):
    """
    Records an alleged or confirmed partner-policy violation.

    Creating a violation does not itself punish the partner.
    Evidence must be reviewed before a final disciplinary
    decision is applied.
    """

    class Status(models.TextChoices):
        REPORTED = "reported", "Reported"
        UNDER_REVIEW = "under_review", "Under review"
        AWAITING_RESPONSE = (
            "awaiting_response",
            "Awaiting partner response",
        )
        DISMISSED = "dismissed", "Dismissed"
        CONFIRMED = "confirmed", "Confirmed"

    partner = models.ForeignKey(
        "partners.Partner",
        on_delete=models.PROTECT,
        related_name="governance_violations",
    )

    policy = models.ForeignKey(
        PolicyRule,
        on_delete=models.PROTECT,
        related_name="violations",
    )

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.REPORTED,
    )

    summary = models.CharField(
        max_length=255,
    )

    details = models.TextField(
        blank=True,
    )

    evidence_snapshot = models.JSONField(
        default=dict,
        blank=True,
    )

    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="reported_partner_violations",
        null=True,
        blank=True,
    )

    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="reviewed_partner_violations",
        null=True,
        blank=True,
    )

    reported_at = models.DateTimeField(
        auto_now_add=True,
    )

    review_started_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    decided_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    decision_notes = models.TextField(
        blank=True,
    )

    class Meta:
        ordering = [
            "-reported_at",
            "-id",
        ]

        indexes = [
            models.Index(
                fields=[
                    "partner",
                    "status",
                ],
            ),
            models.Index(
                fields=[
                    "policy",
                    "status",
                ],
            ),
        ]

    def __str__(self):
        return (
            f"{self.partner} — "
            f"{self.policy.code} — "
            f"{self.get_status_display()}"
        )

class PartnerDisciplinaryAction(models.Model):
    """
    Records a formal consequence imposed after a confirmed
    partner-policy violation.

    A violation records what was proven.
    This model records the consequence imposed.
    """

    class ActionType(models.TextChoices):
        WARNING = "warning", "Formal warning"

        SHORT_SUSPENSION = (
            "short_suspension",
            "Short suspension",
        )

        LONG_SUSPENSION = (
            "long_suspension",
            "Long suspension",
        )

        PERMANENT_BAN = (
            "permanent_ban",
            "Permanent ban",
        )

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        EXPIRED = "expired", "Expired"
        REVOKED = "revoked", "Revoked"

    violation = models.ForeignKey(
        PartnerViolation,
        on_delete=models.PROTECT,
        related_name="disciplinary_actions",
    )

    partner = models.ForeignKey(
        "partners.Partner",
        on_delete=models.PROTECT,
        related_name="disciplinary_actions",
    )

    action_type = models.CharField(
        max_length=30,
        choices=ActionType.choices,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )

    reason = models.TextField()

    decision_snapshot = models.JSONField(
        default=dict,
        blank=True,
    )

    imposed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="imposed_partner_disciplinary_actions",
    )

    starts_at = models.DateTimeField()

    ends_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    revoked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="revoked_partner_disciplinary_actions",
        null=True,
        blank=True,
    )

    revoked_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    revocation_reason = models.TextField(
        blank=True,
    )

    class Meta:
        ordering = [
            "-starts_at",
            "-id",
        ]

        indexes = [
            models.Index(
                fields=[
                    "partner",
                    "status",
                ],
            ),
            models.Index(
                fields=[
                    "action_type",
                    "status",
                ],
            ),
        ]

    @property
    def is_restrictive(self):
        return self.action_type in {
            self.ActionType.SHORT_SUSPENSION,
            self.ActionType.LONG_SUSPENSION,
            self.ActionType.PERMANENT_BAN,
        }

    @property
    def is_permanent(self):
        return (
            self.action_type
            == self.ActionType.PERMANENT_BAN
        )

    def __str__(self):
        return (
            f"{self.partner} — "
            f"{self.get_action_type_display()} — "
            f"{self.get_status_display()}"
        )

class PartnerReinstatement(models.Model):
    """
    Records a deliberate staff decision to restore a suspended
    partner's operational access.

    Expiry or revocation of a disciplinary action never restores
    access automatically.
    """

    partner = models.ForeignKey(
        "partners.Partner",
        on_delete=models.PROTECT,
        related_name="reinstatements",
    )

    reviewed_actions = models.ManyToManyField(
        PartnerDisciplinaryAction,
        related_name="reinstatements",
        blank=True,
    )

    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="approved_partner_reinstatements",
    )

    reason = models.TextField()

    evidence_snapshot = models.JSONField(
        default=dict,
        blank=True,
    )

    reinstated_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = [
            "-reinstated_at",
            "-id",
        ]

    def __str__(self):
        return (
            f"{self.partner} reinstated "
            f"{self.reinstated_at:%Y-%m-%d %H:%M}"
        )

class DealGovernanceCase(models.Model):
    """
    Operational governance case raised when a deal cannot
    safely progress.

    This model answers:
    - What is blocking the deal?
    - Whose action is required?
    - What action is required?
    - Has the issue been resolved?

    A governance case is not automatically a policy violation.
    """

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        RESOLVED = "resolved", "Resolved"
        DISMISSED = "dismissed", "Dismissed"

    class ResponsibleRole(models.TextChoices):
        PARTNER = "partner", "Partner"
        STAFF = "staff", "Pata Hao staff"
        OWNER = "owner", "Property owner"
        CUSTOMER = "customer", "Customer"

    deal = models.ForeignKey(
        "deals.Deal",
        on_delete=models.PROTECT,
        related_name="governance_cases",
    )

    partner = models.ForeignKey(
        "partners.Partner",
        on_delete=models.PROTECT,
        related_name="deal_governance_cases",
        null=True,
        blank=True,
    )

    reason_code = models.CharField(
        max_length=80,
        db_index=True,
    )

    title = models.CharField(
        max_length=255,
    )

    message = models.TextField()

    responsible_role = models.CharField(
        max_length=20,
        choices=ResponsibleRole.choices,
        db_index=True,
    )

    action_code = models.CharField(
        max_length=80,
    )

    action_label = models.CharField(
        max_length=160,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
        db_index=True,
    )

    context_snapshot = models.JSONField(
        default=dict,
        blank=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_deal_governance_cases",
        null=True,
        blank=True,
    )

    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="resolved_deal_governance_cases",
        null=True,
        blank=True,
    )

    resolution_notes = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = [
            "-created_at",
            "-id",
        ]

        indexes = [
            models.Index(
                fields=[
                    "status",
                    "responsible_role",
                    "-created_at",
                ],
            ),
            models.Index(
                fields=[
                    "deal",
                    "status",
                ],
            ),
            models.Index(
                fields=[
                    "partner",
                    "status",
                ],
            ),
        ]

    def __str__(self):
        return (
            f"{self.deal.deal_number} — "
            f"{self.reason_code} — "
            f"{self.get_status_display()}"
        )