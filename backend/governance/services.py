from decimal import Decimal

from django.db import transaction
from django.db.models import Count, Q

from django.utils import timezone

from .models import PartnerViolation, PolicyRule
from deals.models import Deal, DealOutcome

from django.core.exceptions import ValidationError

from properties.models import Property

from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import (
    PartnerDisciplinaryAction,
    PartnerPromotionReview,
    PartnerReinstatement,
    PartnerTier,
    PartnerTierAssignment,
    PartnerViolation,
    PolicyRule,
)
def get_current_tier_assignment(partner):
    """
    Return the partner's active tier assignment.

    Only one assignment should be active at a time.
    """

    return (
        PartnerTierAssignment.objects
        .select_related(
            "tier",
        )
        .filter(
            partner=partner,
            active=True,
        )
        .order_by(
            "-assigned_at",
            "-id",
        )
        .first()
    )


def get_current_tier(partner):
    """
    Return the partner's currently active tier.

    Returns None when no tier has been assigned.
    """

    assignment = get_current_tier_assignment(
        partner,
    )

    if assignment is None:
        return None

    return assignment.tier


def get_default_tier():
    """
    Return the lowest-ranked active tier.

    This should normally be Bronze.
    """

    return (
        PartnerTier.objects
        .filter(
            active=True,
        )
        .order_by(
            "rank",
            "id",
        )
        .first()
    )


def get_next_tier(current_tier):
    """
    Return the next active tier above the current tier.

    Returns None when the current tier is already the
    highest available tier.
    """

    if current_tier is None:
        return get_default_tier()

    return (
        PartnerTier.objects
        .filter(
            active=True,
            rank__gt=current_tier.rank,
        )
        .order_by(
            "rank",
            "id",
        )
        .first()
    )


def get_completed_deal_count(partner):
    """
    Count deals that reached the completed status.
    """

    return (
        Deal.objects
        .filter(
            partner=partner,
            status=Deal.Status.COMPLETED,
        )
        .count()
    )


def get_agreed_deal_count(partner):
    """
    Count deals whose three-party confirmations matched.

    An agreed deal is successful evidence, but it has not
    necessarily completed the full commission lifecycle.
    """

    return (
        Deal.objects
        .filter(
            partner=partner,
            status=Deal.Status.AGREED,
        )
        .count()
    )


def get_disputed_deal_count(partner):
    """
    Count deals currently classified as disputed.
    """

    return (
        Deal.objects
        .filter(
            partner=partner,
            status=Deal.Status.DISPUTED,
        )
        .count()
    )


def get_cancelled_deal_count(partner):
    """
    Count deals confirmed as not producing a transaction.
    """

    return (
        Deal.objects
        .filter(
            partner=partner,
            status=Deal.Status.CANCELLED,
        )
        .count()
    )


def get_three_party_confirmed_deal_count(partner):
    """
    Count deals having customer, partner, and owner evidence.

    This metric does not assume that the three outcomes matched.
    """

    return (
        Deal.objects
        .filter(
            partner=partner,
            customer_confirmed=True,
            partner_confirmed=True,
            owner_confirmed=True,
        )
        .count()
    )


def get_successful_three_party_deal_count(partner):
    """
    Count verified successful transactions.

    A qualifying deal must be agreed, completed, or have reached
    a later successful financial status.
    """

    successful_statuses = {
        Deal.Status.AGREED,
        Deal.Status.COMPLETED,
    }

    commission_paid_status = getattr(
        Deal.Status,
        "COMMISSION_PAID",
        None,
    )

    if commission_paid_status is not None:
        successful_statuses.add(
            commission_paid_status,
        )

    return (
        Deal.objects
        .filter(
            partner=partner,
            customer_confirmed=True,
            partner_confirmed=True,
            owner_confirmed=True,
            status__in=successful_statuses,
        )
        .count()
    )


def calculate_owner_confirmation_rate(partner):
    """
    Calculate the percentage of partner deals containing an
    immutable owner outcome.

    Only deals with at least one customer or partner submission
    are included in the denominator. Draft deals that have not
    entered confirmation are therefore excluded.
    """

    confirmation_started = (
        Deal.objects
        .filter(
            partner=partner,
        )
        .annotate(
            customer_outcomes=Count(
                "outcomes",
                filter=Q(
                    outcomes__reporter=(
                        DealOutcome.Reporter.CUSTOMER
                    )
                ),
                distinct=True,
            ),
            partner_outcomes=Count(
                "outcomes",
                filter=Q(
                    outcomes__reporter=(
                        DealOutcome.Reporter.PARTNER
                    )
                ),
                distinct=True,
            ),
            owner_outcomes=Count(
                "outcomes",
                filter=Q(
                    outcomes__reporter=(
                        DealOutcome.Reporter.OWNER
                    )
                ),
                distinct=True,
            ),
        )
        .filter(
            Q(customer_outcomes__gt=0)
            | Q(partner_outcomes__gt=0)
        )
    )

    total = confirmation_started.count()

    if total == 0:
        return Decimal("0.00")

    owner_confirmed = confirmation_started.filter(
        owner_outcomes__gt=0,
    ).count()

    percentage = (
        Decimal(owner_confirmed)
        / Decimal(total)
        * Decimal("100")
    )

    return percentage.quantize(
        Decimal("0.01"),
    )


def calculate_dispute_rate(partner):
    """
    Calculate disputed deals as a percentage of all deals that
    reached a final three-party evaluation.
    """

    evaluated_statuses = {
        Deal.Status.AGREED,
        Deal.Status.CANCELLED,
        Deal.Status.DISPUTED,
        Deal.Status.NEGOTIATING,
        Deal.Status.COMPLETED,
    }

    commission_paid_status = getattr(
        Deal.Status,
        "COMMISSION_PAID",
        None,
    )

    if commission_paid_status is not None:
        evaluated_statuses.add(
            commission_paid_status,
        )

    evaluated_deals = Deal.objects.filter(
        partner=partner,
        status__in=evaluated_statuses,
    )

    total = evaluated_deals.count()

    if total == 0:
        return Decimal("0.00")

    disputed = evaluated_deals.filter(
        status=Deal.Status.DISPUTED,
    ).count()

    percentage = (
        Decimal(disputed)
        / Decimal(total)
        * Decimal("100")
    )

    return percentage.quantize(
        Decimal("0.01"),
    )


def calculate_partner_metrics(partner):
    """
    Produce the objective evidence snapshot used for a promotion
    evaluation.

    Metrics that do not yet have a completed source subsystem are
    clearly marked as unavailable rather than given fake values.
    """
    from trust.services import (
        recalculate_partner_trust,
    )

    trust_record = recalculate_partner_trust(
        partner,
    )
    completed_deals = get_completed_deal_count(
        partner,
    )

    agreed_deals = get_agreed_deal_count(
        partner,
    )

    disputed_deals = get_disputed_deal_count(
        partner,
    )

    cancelled_deals = get_cancelled_deal_count(
        partner,
    )

    three_party_confirmed_deals = (
        get_three_party_confirmed_deal_count(
            partner,
        )
    )

    successful_three_party_deals = (
        get_successful_three_party_deal_count(
            partner,
        )
    )

    owner_confirmation_rate = (
        calculate_owner_confirmation_rate(
            partner,
        )
    )

    dispute_rate = calculate_dispute_rate(
        partner,
    )

    return {
        "completed_deals": completed_deals,
        "agreed_deals": agreed_deals,
        "successful_three_party_deals": (
            successful_three_party_deals
        ),
        "three_party_confirmed_deals": (
            three_party_confirmed_deals
        ),
        "disputed_deals": disputed_deals,
        "cancelled_deals": cancelled_deals,
        "owner_confirmation_rate": str(
            owner_confirmation_rate
        ),
        "dispute_rate": str(
            dispute_rate
        ),

        # These metrics will become real when the associated
        # governance and review subsystems are implemented.
        "trust_score": str(
            trust_record.score
        ),
        "trust_grade": trust_record.grade,
        "trust_confidence": str(
            trust_record.confidence
        ),
        "confirmed_policy_violations": (
            trust_record.confirmed_violations
        ),
        "active_suspension": (
            trust_record.active_restriction
        ),
        "gross_misconduct_confirmed": (
            trust_record.permanently_banned
        ),
        "customer_rating": str(
            trust_record.average_rating
        ),

        # Response-time evidence is not yet implemented.
        "average_response_time_hours": None,
    }


def promotion_requirements_met(
    *,
    metrics,
    proposed_tier,
):
    """
    Evaluate the promotion requirements that are currently
    implemented.

    Missing future metrics are not silently treated as passes.
    They are reported separately in the evidence result.
    """

    completed_deals = metrics[
        "completed_deals"
    ]

    completed_deals_passed = (
        completed_deals
        >= proposed_tier.minimum_completed_deals
    )

    trust_score = metrics.get(
        "trust_score",
    )

    trust_score_available = (
        trust_score is not None
    )

    trust_score_passed = False

    active_suspension = metrics.get(
        "active_suspension",
        False,
    )

    gross_misconduct_confirmed = metrics.get(
        "gross_misconduct_confirmed",
        False,
    )

    confirmed_violations = metrics.get(
        "confirmed_policy_violations",
        0,
    )
    if active_suspension:
        blocking_reasons.append(
            "Partner has an active disciplinary restriction."
        )

    if gross_misconduct_confirmed:
        blocking_reasons.append(
            "Partner has confirmed gross misconduct."
        )

    if confirmed_violations > 0:
        blocking_reasons.append(
            (
                "Partner has "
                f"{confirmed_violations} confirmed "
                "policy violation(s)."
            )
        )

    if trust_score_available:
        trust_score_passed = (
            Decimal(str(trust_score))
            >= proposed_tier.minimum_trust_score
        )

    blocking_reasons = []

    if not completed_deals_passed:
        blocking_reasons.append(
            (
                "Completed deal requirement not met: "
                f"{completed_deals}/"
                f"{proposed_tier.minimum_completed_deals}."
            )
        )

    if (
        proposed_tier.minimum_trust_score
        > Decimal("0.00")
        and not trust_score_available
    ):
        blocking_reasons.append(
            "Trust score is not yet available."
        )

    if (
        trust_score_available
        and not trust_score_passed
    ):
        blocking_reasons.append(
            (
                "Trust score requirement not met: "
                f"{trust_score}/"
                f"{proposed_tier.minimum_trust_score}."
            )
        )

        eligible = (
            completed_deals_passed
            and (
                proposed_tier.minimum_trust_score
                == Decimal("0.00")
                or trust_score_passed
            )
            and not active_suspension
            and not gross_misconduct_confirmed
            and confirmed_violations == 0
        )

    return {
        "eligible": eligible,
        "completed_deals": {
            "actual": completed_deals,
            "required": (
                proposed_tier.minimum_completed_deals
            ),
            "passed": completed_deals_passed,
        },
        "trust_score": {
            "actual": trust_score,
            "required": str(
                proposed_tier.minimum_trust_score
            ),
            "available": trust_score_available,
            "passed": trust_score_passed,
        },
        "blocking_reasons": blocking_reasons,

        "governance_conduct": {
            "confirmed_policy_violations": (
                confirmed_violations
            ),
            "active_suspension": active_suspension,
            "gross_misconduct_confirmed": (
                gross_misconduct_confirmed
            ),
            "passed": (
                confirmed_violations == 0
                and not active_suspension
                and not gross_misconduct_confirmed
            ),
        },
    }


@transaction.atomic
def assign_default_tier(
    *,
    partner,
    assigned_by=None,
    reason=(
        "Default entry tier assigned to an "
        "approved partner."
    ),
):
    """
    Assign the entry tier when the partner has no active tier.

    Existing active assignments are never replaced by this
    helper.
    """

    existing_assignment = (
        get_current_tier_assignment(
            partner,
        )
    )

    if existing_assignment is not None:
        return existing_assignment, False

    default_tier = get_default_tier()

    if default_tier is None:
        raise ValueError(
            "No active partner tier is configured."
        )

    assignment = (
        PartnerTierAssignment.objects.create(
            partner=partner,
            tier=default_tier,
            assigned_by=assigned_by,
            reason=reason,
            active=True,
        )
    )

    return assignment, True


@transaction.atomic
def evaluate_partner_for_promotion(partner):
    """
    Evaluate a partner against the next configured tier and save
    the exact evidence used for the decision.

    This service never promotes the partner automatically.
    """

    current_assignment = (
        get_current_tier_assignment(
            partner,
        )
    )

    if current_assignment is None:
        current_assignment, _created = (
            assign_default_tier(
                partner=partner,
            )
        )

    current_tier = current_assignment.tier

    proposed_tier = get_next_tier(
        current_tier,
    )

    if proposed_tier is None:
        return None

    metrics = calculate_partner_metrics(
        partner,
    )

    requirements = (
        promotion_requirements_met(
            metrics=metrics,
            proposed_tier=proposed_tier,
        )
    )

    snapshot = {
        "partner_id": partner.id,
        "current_tier": {
            "id": current_tier.id,
            "code": current_tier.code,
            "name": current_tier.name,
            "rank": current_tier.rank,
            "property_limit": (
                current_tier.property_limit
            ),
        },
        "proposed_tier": {
            "id": proposed_tier.id,
            "code": proposed_tier.code,
            "name": proposed_tier.name,
            "rank": proposed_tier.rank,
            "property_limit": (
                proposed_tier.property_limit
            ),
        },
        "metrics": metrics,
        "requirements": requirements,
    }

    decision = (
        PartnerPromotionReview.Decision.ELIGIBLE
        if requirements["eligible"]
        else (
            PartnerPromotionReview
            .Decision
            .NOT_ELIGIBLE
        )
    )

    review = PartnerPromotionReview.objects.create(
        partner=partner,
        current_tier=current_tier,
        proposed_tier=proposed_tier,
        trust_score=Decimal("0.00"),
        completed_deals=metrics[
            "completed_deals"
        ],
        violations=0,
        decision=decision,
        metrics_snapshot=snapshot,
        notes=(
            "Automatic evidence-based promotion "
            "evaluation."
        ),
    )

    return review

def get_partner_property_limit(partner):
    """
    Return the active published-property limit for a partner.

    Partners without an assignment are automatically placed
    into the default entry tier.
    """

    assignment = get_current_tier_assignment(
        partner,
    )

    if assignment is None:
        assignment, _created = assign_default_tier(
            partner=partner,
        )

    return assignment.tier.property_limit


def get_active_published_property_count(
    partner,
    *,
    exclude_property_id=None,
):
    """
    Count the partner's currently published properties.

    The property being published can be excluded when updating
    an existing record.
    """

    queryset = Property.objects.filter(
        partner=partner,
        status=Property.STATUS_PUBLISHED,
    )

    if exclude_property_id is not None:
        queryset = queryset.exclude(
            pk=exclude_property_id,
        )

    return queryset.count()


def validate_partner_property_limit(property_obj):
    """
    Prevent a partner from publishing beyond the limit defined
    by their current governance tier.
    """

    partner = property_obj.partner

    if partner is None:
        raise ValidationError(
            {
                "partner": (
                    "A partner is required before a property "
                    "can be published."
                ),
            }
        )

    enforce_partner_operational_access(
        partner,
        operation="publish_property",
    )

    property_limit = get_partner_property_limit(
        partner,
    )

    active_count = get_active_published_property_count(
        partner,
        exclude_property_id=property_obj.pk,
    )

    if active_count >= property_limit:
        current_tier = get_current_tier(
            partner,
        )

        raise ValidationError(
            {
                "status": (
                    f"{current_tier.name} partners may publish "
                    f"up to {property_limit} active properties. "
                    f"This partner currently has {active_count} "
                    "published properties."
                ),
            }
        )

    current_tier = get_current_tier(
        partner,
    )

    return {
        "allowed": True,
        "tier": {
            "id": current_tier.id,
            "code": current_tier.code,
            "name": current_tier.name,
            "rank": current_tier.rank,
        },
        "property_limit": property_limit,
        "published_count": active_count,
        "remaining_slots": (
            property_limit - active_count
        ),
    }

def get_partner_capacity_summary(partner):
    """
    Return the partner's current tier and published-property
    capacity.

    Partners without an active tier assignment are automatically
    assigned the default entry tier.
    """

    assignment = get_current_tier_assignment(
        partner,
    )

    if assignment is None:
        assignment, _created = assign_default_tier(
            partner=partner,
        )

    tier = assignment.tier

    published_properties = (
        get_active_published_property_count(
            partner,
        )
    )

    property_limit = tier.property_limit

    remaining_property_slots = max(
        property_limit - published_properties,
        0,
    )

    return {
        "partner_id": partner.id,
        "tier": {
            "id": tier.id,
            "code": tier.code,
            "name": tier.name,
            "rank": tier.rank,
        },
        "property_capacity": {
            "property_limit": property_limit,
            "published_properties": published_properties,
            "remaining_property_slots": (
                remaining_property_slots
            ),
            "limit_reached": (
                published_properties >= property_limit
            ),
            "usage_percentage": (
                round(
                    (
                        published_properties
                        / property_limit
                        * 100
                    ),
                    2,
                )
                if property_limit > 0
                else 0
            ),
        },
    }

@transaction.atomic
def report_partner_violation(
    *,
    partner,
    policy,
    summary,
    details="",
    evidence_snapshot=None,
    reported_by=None,
):
    """
    Create a new alleged policy violation.

    Reporting does not suspend or punish the partner.
    """

    if not isinstance(policy, PolicyRule):
        raise ValidationError(
            {"policy": "A valid policy rule is required."}
        )

    if not policy.active:
        raise ValidationError(
            {"policy": "This policy rule is inactive."}
        )

    cleaned_summary = (summary or "").strip()

    if not cleaned_summary:
        raise ValidationError(
            {"summary": "A violation summary is required."}
        )

    violation = PartnerViolation.objects.create(
        partner=partner,
        policy=policy,
        status=PartnerViolation.Status.REPORTED,
        summary=cleaned_summary,
        details=(details or "").strip(),
        evidence_snapshot=evidence_snapshot or {},
        reported_by=reported_by,
    )

    return violation

@transaction.atomic
def start_violation_review(
    *,
    violation,
    reviewer,
):
    """
    Move a reported violation into formal review.
    """

    if violation.status != PartnerViolation.Status.REPORTED:
        raise ValidationError(
            {
                "status": (
                    "Only reported violations may enter review."
                )
            }
        )

    if reviewer is None or not reviewer.is_authenticated:
        raise ValidationError(
            {"reviewed_by": "An authenticated reviewer is required."}
        )

    if not reviewer.is_staff:
        raise ValidationError(
            {"reviewed_by": "Only staff may review violations."}
        )

    violation.status = PartnerViolation.Status.UNDER_REVIEW
    violation.reviewed_by = reviewer
    violation.review_started_at = timezone.now()

    violation.save(
        update_fields=[
            "status",
            "reviewed_by",
            "review_started_at",
        ]
    )

    return violation

@transaction.atomic
def request_partner_response(
    *,
    violation,
    reviewer,
    notes="",
):
    """
    Pause the review while the partner is asked to respond.
    """

    if violation.status != PartnerViolation.Status.UNDER_REVIEW:
        raise ValidationError(
            {
                "status": (
                    "A partner response may be requested only "
                    "during review."
                )
            }
        )

    if reviewer is None or not reviewer.is_staff:
        raise ValidationError(
            {"reviewed_by": "Only staff may request a response."}
        )

    violation.status = PartnerViolation.Status.AWAITING_RESPONSE
    violation.reviewed_by = reviewer

    if notes:
        violation.decision_notes = notes.strip()

    violation.save(
        update_fields=[
            "status",
            "reviewed_by",
            "decision_notes",
        ]
    )

    return violation

@transaction.atomic
def dismiss_partner_violation(
    *,
    violation,
    reviewer,
    decision_notes,
):
    """
    Dismiss an allegation when the evidence does not support it.
    """

    allowed_statuses = {
        PartnerViolation.Status.UNDER_REVIEW,
        PartnerViolation.Status.AWAITING_RESPONSE,
    }

    if violation.status not in allowed_statuses:
        raise ValidationError(
            {
                "status": (
                    "Only a reviewed violation may be dismissed."
                )
            }
        )

    if reviewer is None or not reviewer.is_staff:
        raise ValidationError(
            {"reviewed_by": "Only staff may dismiss violations."}
        )

    cleaned_notes = (decision_notes or "").strip()

    if not cleaned_notes:
        raise ValidationError(
            {"decision_notes": "Dismissal reasons are required."}
        )

    violation.status = PartnerViolation.Status.DISMISSED
    violation.reviewed_by = reviewer
    violation.decided_at = timezone.now()
    violation.decision_notes = cleaned_notes

    violation.save(
        update_fields=[
            "status",
            "reviewed_by",
            "decided_at",
            "decision_notes",
        ]
    )

    return violation

@transaction.atomic
def confirm_partner_violation(
    *,
    violation,
    reviewer,
    decision_notes,
):
    """
    Confirm a violation after evidence review.

    This records the finding only. The disciplinary action will
    be created by the next service layer.
    """

    allowed_statuses = {
        PartnerViolation.Status.UNDER_REVIEW,
        PartnerViolation.Status.AWAITING_RESPONSE,
    }

    if violation.status not in allowed_statuses:
        raise ValidationError(
            {
                "status": (
                    "Only a reviewed violation may be confirmed."
                )
            }
        )

    if reviewer is None or not reviewer.is_staff:
        raise ValidationError(
            {"reviewed_by": "Only staff may confirm violations."}
        )

    cleaned_notes = (decision_notes or "").strip()

    if not cleaned_notes:
        raise ValidationError(
            {"decision_notes": "Decision reasons are required."}
        )

    violation.status = PartnerViolation.Status.CONFIRMED
    violation.reviewed_by = reviewer
    violation.decided_at = timezone.now()
    violation.decision_notes = cleaned_notes

    violation.save(
        update_fields=[
            "status",
            "reviewed_by",
            "decided_at",
            "decision_notes",
        ]
    )

    return violation

@transaction.atomic
def impose_disciplinary_action(
    *,
    violation,
    action_type,
    imposed_by,
    reason,
    duration_days=None,
    override_reason="",
):
    """
    Impose a formal consequence after a confirmed violation.
    """

    if violation.status != PartnerViolation.Status.CONFIRMED:
        raise ValidationError(
            {
                "violation": (
                    "A disciplinary action may be imposed only "
                    "after the violation is confirmed."
                )
            }
        )

    if imposed_by is None or not imposed_by.is_authenticated:
        raise ValidationError(
            {
                "imposed_by": (
                    "An authenticated staff member is required."
                )
            }
        )

    if not imposed_by.is_staff:
        raise ValidationError(
            {
                "imposed_by": (
                    "Only staff may impose disciplinary actions."
                )
            }
        )

    valid_action_types = {
        value
        for value, _label in (
            PartnerDisciplinaryAction.ActionType.choices
        )
    }

    if action_type not in valid_action_types:
        raise ValidationError(
            {
                "action_type": (
                    "The disciplinary action type is invalid."
                )
            }
        )

    cleaned_reason = (reason or "").strip()

    if not cleaned_reason:
        raise ValidationError(
            {
                "reason": (
                    "A disciplinary decision reason is required."
                )
            }
        )

    recommended_action = violation.policy.recommended_action
    cleaned_override_reason = (override_reason or "").strip()

    if (
        action_type != recommended_action
        and not cleaned_override_reason
    ):
        raise ValidationError(
            {
                "override_reason": (
                    "A documented override reason is required "
                    "when the imposed action differs from the "
                    "policy recommendation."
                )
            }
        )

    suspension_actions = {
        PartnerDisciplinaryAction.ActionType.SHORT_SUSPENSION,
        PartnerDisciplinaryAction.ActionType.LONG_SUSPENSION,
    }

    if (
        action_type in suspension_actions
        and (
            duration_days is None
            or duration_days <= 0
        )
    ):
        raise ValidationError(
            {
                "duration_days": (
                    "A positive suspension duration is required."
                )
            }
        )

    if (
        action_type
        == PartnerDisciplinaryAction.ActionType.PERMANENT_BAN
        and duration_days is not None
    ):
        raise ValidationError(
            {
                "duration_days": (
                    "A permanent ban cannot have an expiry."
                )
            }
        )

    now = timezone.now()
    ends_at = None

    if action_type in suspension_actions:
        ends_at = now + timedelta(days=duration_days)

    partner = violation.partner

    decision_snapshot = {
        "violation_id": violation.id,
        "partner_id": partner.id,
        "policy": {
            "id": violation.policy_id,
            "code": violation.policy.code,
            "title": violation.policy.title,
            "severity": violation.policy.severity,
            "recommended_action": recommended_action,
        },
        "violation": {
            "status": violation.status,
            "summary": violation.summary,
            "details": violation.details,
            "evidence_snapshot": violation.evidence_snapshot,
            "decision_notes": violation.decision_notes,
            "decided_at": (
                violation.decided_at.isoformat()
                if violation.decided_at
                else None
            ),
        },
        "disciplinary_decision": {
            "action_type": action_type,
            "reason": cleaned_reason,
            "duration_days": duration_days,
            "override_reason": cleaned_override_reason,
            "imposed_by_id": imposed_by.id,
            "imposed_at": now.isoformat(),
        },
    }

    action = PartnerDisciplinaryAction.objects.create(
        violation=violation,
        partner=partner,
        action_type=action_type,
        status=PartnerDisciplinaryAction.Status.ACTIVE,
        reason=cleaned_reason,
        decision_snapshot=decision_snapshot,
        imposed_by=imposed_by,
        starts_at=now,
        ends_at=ends_at,
    )

    if action.is_restrictive and partner.is_active:
        partner.is_active = False
        partner.save(
            update_fields=[
                "is_active",
            ]
        )

    return action


def get_active_disciplinary_actions(partner):
    """
    Return active disciplinary actions for a partner.
    """

    return (
        PartnerDisciplinaryAction.objects
        .select_related(
            "violation",
            "violation__policy",
            "imposed_by",
        )
        .filter(
            partner=partner,
            status=PartnerDisciplinaryAction.Status.ACTIVE,
        )
        .order_by(
            "-starts_at",
            "-id",
        )
    )


def get_partner_restriction_summary(partner):
    """
    Return active governance restrictions affecting a partner.
    """

    actions = list(
        get_active_disciplinary_actions(partner)
    )

    restrictive_actions = [
        action
        for action in actions
        if action.is_restrictive
    ]

    permanent_ban = next(
        (
            action
            for action in restrictive_actions
            if action.is_permanent
        ),
        None,
    )

    return {
        "partner_id": partner.id,
        "restricted": bool(restrictive_actions),
        "permanently_banned": permanent_ban is not None,
        "active_action_count": len(actions),
        "active_restrictive_action_count": len(
            restrictive_actions
        ),
        "actions": [
            {
                "id": action.id,
                "violation_id": action.violation_id,
                "policy_code": (
                    action.violation.policy.code
                ),
                "action_type": action.action_type,
                "action_type_label": (
                    action.get_action_type_display()
                ),
                "starts_at": action.starts_at.isoformat(),
                "ends_at": (
                    action.ends_at.isoformat()
                    if action.ends_at
                    else None
                ),
                "reason": action.reason,
            }
            for action in actions
        ],
    }

def enforce_partner_operational_access(
    partner,
    *,
    operation,
):
    """
    Enforce the central governance restrictions for a partner.

    Every sensitive partner operation should call this service
    rather than implementing separate suspension or ban logic.
    """

    if partner is None:
        raise ValidationError(
            {
                "partner": (
                    "A valid partner profile is required."
                ),
                "operation": operation,
            }
        )

    restriction_summary = (
        get_partner_restriction_summary(
            partner,
        )
    )

    if restriction_summary["permanently_banned"]:
        raise ValidationError(
            {
                "partner": (
                    "This partner has been permanently banned "
                    "from Pata Hao."
                ),
                "operation": operation,
                "restriction_type": "permanent_ban",
            }
        )

    if restriction_summary["restricted"]:
        active_actions = ", ".join(
            action["action_type"]
            for action in restriction_summary["actions"]
        )

        raise ValidationError(
            {
                "partner": (
                    "This partner is currently suspended "
                    "from Pata Hao operations."
                ),
                "operation": operation,
                "restriction_type": (
                    active_actions
                    or "active_restriction"
                ),
            }
        )

    if not partner.is_active:
        raise ValidationError(
            {
                "partner": (
                    "This partner profile is inactive."
                ),
                "operation": operation,
            }
        )

    if (
        partner.verification_status
        != partner.STATUS_APPROVED
    ):
        raise ValidationError(
            {
                "partner": (
                    "The partner profile must be approved before "
                    "performing this operation."
                ),
                "operation": operation,
            }
        )

    return {
        "allowed": True,
        "operation": operation,
        "partner_id": partner.id,
        "restriction": restriction_summary,
    }

@transaction.atomic
def revoke_disciplinary_action(
    *,
    action,
    revoked_by,
    reason,
):
    """
    Revoke an active disciplinary action.
    """

    if action.status != PartnerDisciplinaryAction.Status.ACTIVE:
        raise ValidationError(
            {
                "status": (
                    "Only an active disciplinary action may "
                    "be revoked."
                )
            }
        )

    if revoked_by is None or not revoked_by.is_authenticated:
        raise ValidationError(
            {
                "revoked_by": (
                    "An authenticated staff member is required."
                )
            }
        )

    if not revoked_by.is_staff:
        raise ValidationError(
            {
                "revoked_by": (
                    "Only staff may revoke disciplinary actions."
                )
            }
        )

    cleaned_reason = (reason or "").strip()

    if not cleaned_reason:
        raise ValidationError(
            {
                "revocation_reason": (
                    "A revocation reason is required."
                )
            }
        )

    action.status = PartnerDisciplinaryAction.Status.REVOKED
    action.revoked_by = revoked_by
    action.revoked_at = timezone.now()
    action.revocation_reason = cleaned_reason

    action.save(
        update_fields=[
            "status",
            "revoked_by",
            "revoked_at",
            "revocation_reason",
        ]
    )

    return action

@transaction.atomic
def expire_disciplinary_action(
    *,
    action,
):
    """
    Mark a temporary disciplinary action as expired.

    Expiry never reactivates the partner.
    """

    if (
        action.status
        != PartnerDisciplinaryAction.Status.ACTIVE
    ):
        raise ValidationError(
            {
                "status": (
                    "Only an active disciplinary action may "
                    "be marked expired."
                )
            }
        )

    if action.is_permanent:
        raise ValidationError(
            {
                "action_type": (
                    "A permanent ban cannot expire."
                )
            }
        )

    if action.ends_at is None:
        raise ValidationError(
            {
                "ends_at": (
                    "This disciplinary action has no expiry date."
                )
            }
        )

    if action.ends_at > timezone.now():
        raise ValidationError(
            {
                "ends_at": (
                    "This disciplinary action has not yet expired."
                )
            }
        )

    action.status = (
        PartnerDisciplinaryAction.Status.EXPIRED
    )

    action.save(
        update_fields=[
            "status",
        ]
    )

    # Deliberately do not set partner.is_active = True.
    return action

@transaction.atomic
def reinstate_partner(
    *,
    partner,
    approved_by,
    reason,
):
    """
    Restore a partner only after every restrictive action has
    been resolved.

    Reinstatement is a separate auditable decision.
    """

    if approved_by is None or not approved_by.is_authenticated:
        raise ValidationError(
            {
                "approved_by": (
                    "An authenticated staff member is required."
                )
            }
        )

    if not approved_by.is_staff:
        raise ValidationError(
            {
                "approved_by": (
                    "Only staff may reinstate a partner."
                )
            }
        )

    cleaned_reason = (reason or "").strip()

    if not cleaned_reason:
        raise ValidationError(
            {
                "reason": (
                    "A reinstatement reason is required."
                )
            }
        )

    active_actions = list(
        get_active_disciplinary_actions(
            partner,
        )
    )

    active_restrictive_actions = [
        action
        for action in active_actions
        if action.is_restrictive
    ]

    if active_restrictive_actions:
        raise ValidationError(
            {
                "disciplinary_actions": (
                    "The partner still has active restrictive "
                    "disciplinary actions."
                )
            }
        )

    permanent_ban_history = (
        PartnerDisciplinaryAction.objects
        .filter(
            partner=partner,
            action_type=(
                PartnerDisciplinaryAction
                .ActionType
                .PERMANENT_BAN
            ),
        )
        .exclude(
            status=(
                PartnerDisciplinaryAction
                .Status
                .REVOKED
            ),
        )
        .exists()
    )

    if permanent_ban_history:
        raise ValidationError(
            {
                "partner": (
                    "A permanent ban must be formally revoked "
                    "before reinstatement."
                )
            }
        )

    reviewed_actions = list(
        PartnerDisciplinaryAction.objects
        .filter(
            partner=partner,
        )
        .order_by(
            "starts_at",
            "id",
        )
    )

    snapshot = {
        "partner_id": partner.id,
        "partner_was_active": partner.is_active,
        "reviewed_action_ids": [
            action.id
            for action in reviewed_actions
        ],
        "actions": [
            {
                "id": action.id,
                "action_type": action.action_type,
                "status": action.status,
                "starts_at": action.starts_at.isoformat(),
                "ends_at": (
                    action.ends_at.isoformat()
                    if action.ends_at
                    else None
                ),
                "revoked_at": (
                    action.revoked_at.isoformat()
                    if action.revoked_at
                    else None
                ),
            }
            for action in reviewed_actions
        ],
        "approved_by_id": approved_by.id,
        "reason": cleaned_reason,
        "decision_time": timezone.now().isoformat(),
    }

    reinstatement = PartnerReinstatement.objects.create(
        partner=partner,
        approved_by=approved_by,
        reason=cleaned_reason,
        evidence_snapshot=snapshot,
    )

    reinstatement.reviewed_actions.set(
        reviewed_actions,
    )

    if not partner.is_active:
        partner.is_active = True

        partner.save(
            update_fields=[
                "is_active",
            ]
        )

    return reinstatement