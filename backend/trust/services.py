from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.db.models import Avg, Count, Q
from django.utils import timezone

from viewings.models import Viewing, ViewingFeedback

from .models import (
    CustomerTrustScore,
    PartnerTrustScore,
    PropertyTrustScore,
    TrustScoreHistory,
)
from deals.models import Deal
from governance.models import (
    PartnerDisciplinaryAction,
    PartnerViolation,
)

def _decimal(value, default="0.00"):
    if value is None:
        return Decimal(default)

    return Decimal(str(value))


def _percentage(value):
    value = max(
        Decimal("0.00"),
        min(Decimal("100.00"), value),
    )

    return value.quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )


def _rating_to_percentage(rating):
    return _percentage(
        _decimal(rating) * Decimal("20.00"),
    )


def _confidence(feedback_count):
    if feedback_count <= 0:
        return Decimal("0.00")

    # Confidence rises gradually and reaches 100 after 20 reviews.
    return _percentage(
        Decimal(feedback_count)
        / Decimal("20")
        * Decimal("100"),
    )


def _record_history(
    *,
    subject_type,
    subject_id,
    previous_score,
    new_score,
    viewing,
    reason,
):
    if previous_score == new_score:
        return

    TrustScoreHistory.objects.create(
        subject_type=subject_type,
        subject_id=subject_id,
        previous_score=previous_score,
        new_score=new_score,
        viewing=viewing,
        reason=reason,
    )


@transaction.atomic
def recalculate_customer_trust(customer, *, viewing=None):
    completed_viewings = Viewing.objects.filter(
        customer=customer,
        status=Viewing.Status.COMPLETED,
    ).count()

    feedback = ViewingFeedback.objects.filter(
        customer=customer,
    )

    feedback_count = feedback.count()

    attended_viewings = feedback.filter(
        attended=True,
    ).count()

    missed_viewings = feedback.filter(
        attended=False,
    ).count()

    cancelled_viewings = Viewing.objects.filter(
        customer=customer,
        status=Viewing.Status.CANCELLED,
    ).count()

    if completed_viewings == 0:
        score = Decimal("0.00")
    else:
        attendance_rate = (
            Decimal(attended_viewings)
            / Decimal(completed_viewings)
            * Decimal("100")
        )

        cancellation_penalty = min(
            Decimal(cancelled_viewings) * Decimal("5"),
            Decimal("30"),
        )

        score = _percentage(
            attendance_rate - cancellation_penalty,
        )

    record, _ = CustomerTrustScore.objects.get_or_create(
        customer=customer,
    )

    previous_score = record.score

    record.score = score
    record.confidence = _confidence(feedback_count)
    record.completed_viewings = completed_viewings
    record.feedback_count = feedback_count
    record.attended_viewings = attended_viewings
    record.missed_viewings = missed_viewings
    record.cancelled_viewings = cancelled_viewings
    record.last_calculated_at = timezone.now()

    record.save()

    _record_history(
        subject_type=TrustScoreHistory.SubjectType.CUSTOMER,
        subject_id=customer.id,
        previous_score=previous_score,
        new_score=record.score,
        viewing=viewing,
        reason="Customer trust recalculated from viewing activity.",
    )

    return record


def _partner_grade(score, *, evidence_count):
    """
    Return an explainable public trust grade.

    Partners without meaningful evidence remain unrated instead
    of receiving a misleading risk classification.
    """

    if evidence_count == 0:
        return PartnerTrustScore.Grade.UNRATED

    if score < Decimal("40.00"):
        return PartnerTrustScore.Grade.HIGH_RISK

    if score < Decimal("65.00"):
        return PartnerTrustScore.Grade.DEVELOPING

    if score < Decimal("85.00"):
        return PartnerTrustScore.Grade.GOOD

    if score < Decimal("95.00"):
        return PartnerTrustScore.Grade.TRUSTED

    return PartnerTrustScore.Grade.EXCELLENT

@transaction.atomic
def recalculate_partner_trust(
    partner,
    *,
    viewing=None,
):
    """
    Recalculate partner trust from verified platform evidence.

    Components:
    - Customer rating: 35%
    - Viewing completion: 20%
    - Owner confirmation: 15%
    - Successful deal evidence: 20%
    - Low dispute rate: 10%

    Confirmed violations apply deductions.
    Active restrictions apply a hard score cap.
    A permanent ban forces the score to zero.
    """

    assigned_viewings = Viewing.objects.filter(
        assigned_partner=partner,
    )

    completed_viewings = assigned_viewings.filter(
        status=Viewing.Status.COMPLETED,
    ).count()

    accepted_viewings = assigned_viewings.filter(
        status__in=[
            Viewing.Status.CONFIRMED,
            Viewing.Status.COMPLETED,
        ],
    ).count()

    declined_viewings = assigned_viewings.filter(
        status=Viewing.Status.DECLINED,
    ).count()

    rescheduled_viewings = assigned_viewings.filter(
        status=Viewing.Status.RESCHEDULE_PROPOSED,
    ).count()

    resolved_viewings = (
        completed_viewings
        + declined_viewings
    )

    if resolved_viewings > 0:
        viewing_completion_rate = _percentage(
            Decimal(completed_viewings)
            / Decimal(resolved_viewings)
            * Decimal("100")
        )
    else:
        viewing_completion_rate = Decimal("0.00")

    feedback = ViewingFeedback.objects.filter(
        viewing__assigned_partner=partner,
    )

    feedback_summary = feedback.aggregate(
        average_rating=Avg("partner_rating"),
        feedback_count=Count("id"),
    )

    average_rating = _decimal(
        feedback_summary["average_rating"],
    )

    feedback_count = (
        feedback_summary["feedback_count"]
        or 0
    )

    rating_score = _rating_to_percentage(
        average_rating,
    )

    partner_deals = Deal.objects.filter(
        partner=partner,
    )

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

    evaluated_statuses = {
        Deal.Status.AGREED,
        Deal.Status.CANCELLED,
        Deal.Status.DISPUTED,
        Deal.Status.NEGOTIATING,
        Deal.Status.COMPLETED,
    }

    if commission_paid_status is not None:
        evaluated_statuses.add(
            commission_paid_status,
        )

    successful_deals = partner_deals.filter(
        status__in=successful_statuses,
        customer_confirmed=True,
        partner_confirmed=True,
        owner_confirmed=True,
    ).count()

    evaluated_deals = partner_deals.filter(
        status__in=evaluated_statuses,
    ).count()

    disputed_deals = partner_deals.filter(
        status=Deal.Status.DISPUTED,
    ).count()

    confirmation_started_deals = partner_deals.filter(
        Q(customer_confirmed=True)
        | Q(partner_confirmed=True)
    )

    confirmation_started_count = (
        confirmation_started_deals.count()
    )

    owner_confirmed_count = (
        confirmation_started_deals
        .filter(
            owner_confirmed=True,
        )
        .count()
    )

    if confirmation_started_count > 0:
        owner_confirmation_rate = _percentage(
            Decimal(owner_confirmed_count)
            / Decimal(confirmation_started_count)
            * Decimal("100")
        )
    else:
        owner_confirmation_rate = Decimal("0.00")

    if evaluated_deals > 0:
        dispute_rate = _percentage(
            Decimal(disputed_deals)
            / Decimal(evaluated_deals)
            * Decimal("100")
        )
    else:
        dispute_rate = Decimal("0.00")

    if evaluated_deals > 0:
        dispute_health_score = _percentage(
            Decimal("100.00") - dispute_rate
        )
    else:
        dispute_health_score = Decimal("0.00")

    # Successful transaction evidence reaches full component
    # credit after twenty verified successful deals.
    successful_deal_score = _percentage(
        min(
            Decimal(successful_deals)
            / Decimal("20")
            * Decimal("100"),
            Decimal("100"),
        )
    )

    components = {
        "customer_rating": {
            "score": str(rating_score),
            "weight": "35.00",
        },
        "viewing_completion": {
            "score": str(viewing_completion_rate),
            "weight": "20.00",
        },
        "owner_confirmation": {
            "score": str(owner_confirmation_rate),
            "weight": "15.00",
        },
        "successful_deals": {
            "score": str(successful_deal_score),
            "weight": "20.00",
        },
        "dispute_health": {
            "score": str(dispute_health_score),
            "weight": "10.00",
        },
    }

    base_score = _percentage(
        rating_score * Decimal("0.35")
        + viewing_completion_rate * Decimal("0.20")
        + owner_confirmation_rate * Decimal("0.15")
        + successful_deal_score * Decimal("0.20")
        + dispute_health_score * Decimal("0.10")
    )

    confirmed_violation_queryset = (
        PartnerViolation.objects
        .select_related(
            "policy",
        )
        .filter(
            partner=partner,
            status=PartnerViolation.Status.CONFIRMED,
        )
    )

    confirmed_violations = (
        confirmed_violation_queryset.count()
    )

    violation_penalties = {
        "minor": Decimal("3.00"),
        "moderate": Decimal("8.00"),
        "serious": Decimal("20.00"),
        "gross_misconduct": Decimal("50.00"),
    }

    violation_breakdown = []
    total_violation_penalty = Decimal("0.00")

    for violation in confirmed_violation_queryset:
        penalty = violation_penalties.get(
            violation.policy.severity,
            Decimal("0.00"),
        )

        total_violation_penalty += penalty

        violation_breakdown.append(
            {
                "violation_id": violation.id,
                "policy_code": violation.policy.code,
                "severity": violation.policy.severity,
                "penalty": str(penalty),
            }
        )

    total_violation_penalty = min(
        total_violation_penalty,
        Decimal("100.00"),
    )

    active_restrictive_types = {
        (
            PartnerDisciplinaryAction
            .ActionType
            .SHORT_SUSPENSION
        ),
        (
            PartnerDisciplinaryAction
            .ActionType
            .LONG_SUSPENSION
        ),
        (
            PartnerDisciplinaryAction
            .ActionType
            .PERMANENT_BAN
        ),
    }

    active_actions = (
        PartnerDisciplinaryAction.objects
        .filter(
            partner=partner,
            status=(
                PartnerDisciplinaryAction
                .Status
                .ACTIVE
            ),
            action_type__in=active_restrictive_types,
        )
    )

    active_restriction = active_actions.exists()

    permanently_banned = active_actions.filter(
        action_type=(
            PartnerDisciplinaryAction
            .ActionType
            .PERMANENT_BAN
        ),
    ).exists()

    score_after_penalties = _percentage(
        base_score - total_violation_penalty
    )

    blocking_reasons = []

    if permanently_banned:
        final_score = Decimal("0.00")

        blocking_reasons.append(
            "Partner has an active permanent ban."
        )

    elif active_restriction:
        final_score = min(
            score_after_penalties,
            Decimal("20.00"),
        )

        blocking_reasons.append(
            "Partner has an active disciplinary restriction."
        )

    else:
        final_score = score_after_penalties

    final_score = _percentage(
        final_score,
    )

    evidence_count = (
        feedback_count
        + resolved_viewings
        + evaluated_deals
    )

    if evidence_count == 0:
        final_score = Decimal("0.00")
        confidence = Decimal("0.00")
        grade = PartnerTrustScore.Grade.UNRATED

    else:
        confidence = _percentage(
            min(
                Decimal(evidence_count)
                / Decimal("30")
                * Decimal("100"),
                Decimal("100"),
            )
        )

    grade = _partner_grade(
        final_score,
        evidence_count=evidence_count,
    )

    snapshot = {
        "version": "partner_trust_v1",
        "partner_id": partner.id,
        "metrics": {
            "average_rating": str(
                average_rating.quantize(
                    Decimal("0.01"),
                    rounding=ROUND_HALF_UP,
                )
            ),
            "feedback_count": feedback_count,
            "completed_viewings": completed_viewings,
            "accepted_viewings": accepted_viewings,
            "declined_viewings": declined_viewings,
            "rescheduled_viewings": rescheduled_viewings,
            "resolved_viewings": resolved_viewings,
            "viewing_completion_rate": str(
                viewing_completion_rate
            ),
            "successful_deals": successful_deals,
            "evaluated_deals": evaluated_deals,
            "disputed_deals": disputed_deals,
            "owner_confirmation_rate": str(
                owner_confirmation_rate
            ),
            "dispute_rate": str(
                dispute_rate
            ),
            "confirmed_violations": (
                confirmed_violations
            ),
            "active_restriction": active_restriction,
            "permanently_banned": permanently_banned,
        },
        "components": components,
        "penalties": {
            "confirmed_violations": (
                violation_breakdown
            ),
            "total_violation_penalty": str(
                total_violation_penalty
            ),
        },
        "calculation": {
            "base_score": str(base_score),
            "score_after_penalties": str(
                score_after_penalties
            ),
            "final_score": str(final_score),
            "confidence": str(confidence),
            "grade": grade,
        },
        "blocking_reasons": blocking_reasons,
        "calculated_at": timezone.now().isoformat(),
    }

    record, _created = (
        PartnerTrustScore.objects.get_or_create(
            partner=partner,
        )
    )

    previous_score = record.score

    record.score = final_score
    record.confidence = confidence
    record.grade = grade

    record.completed_viewings = completed_viewings
    record.feedback_count = feedback_count
    record.average_rating = average_rating.quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )

    record.accepted_viewings = accepted_viewings
    record.declined_viewings = declined_viewings
    record.rescheduled_viewings = rescheduled_viewings
    record.viewing_completion_rate = (
        viewing_completion_rate
    )

    record.successful_deals = successful_deals
    record.evaluated_deals = evaluated_deals
    record.disputed_deals = disputed_deals
    record.owner_confirmation_rate = (
        owner_confirmation_rate
    )
    record.dispute_rate = dispute_rate

    record.confirmed_violations = (
        confirmed_violations
    )
    record.active_restriction = active_restriction
    record.permanently_banned = permanently_banned

    record.calculation_snapshot = snapshot
    record.last_calculated_at = timezone.now()

    record.save()

    _record_history(
        subject_type=TrustScoreHistory.SubjectType.PARTNER,
        subject_id=partner.id,
        previous_score=previous_score,
        new_score=record.score,
        viewing=viewing,
        reason=(
            "Partner trust recalculated from ratings, viewings, "
            "verified deals, disputes, owner confirmations, and "
            "governance history."
        ),
    )

    return record


@transaction.atomic
def recalculate_property_trust(property_obj, *, viewing=None):
    feedback = ViewingFeedback.objects.filter(
        viewing__property=property_obj,
    )

    summary = feedback.aggregate(
        average_rating=Avg("property_rating"),
        feedback_count=Count("id"),
        accurate=Count(
            "id",
            filter=Q(
                property_accuracy=(
                    ViewingFeedback.PropertyAccuracy.YES
                )
            ),
        ),
        partially_accurate=Count(
            "id",
            filter=Q(
                property_accuracy=(
                    ViewingFeedback.PropertyAccuracy.PARTIALLY
                )
            ),
        ),
        inaccurate=Count(
            "id",
            filter=Q(
                property_accuracy=(
                    ViewingFeedback.PropertyAccuracy.NO
                )
            ),
        ),
    )

    average_rating = _decimal(
        summary["average_rating"],
    )

    feedback_count = summary["feedback_count"] or 0
    accurate = summary["accurate"] or 0
    partially_accurate = (
        summary["partially_accurate"] or 0
    )
    inaccurate = summary["inaccurate"] or 0

    rating_score = _rating_to_percentage(
        average_rating,
    )

    if feedback_count > 0:
        accuracy_score = (
            (
                Decimal(accurate)
                + Decimal(partially_accurate)
                * Decimal("0.50")
            )
            / Decimal(feedback_count)
            * Decimal("100")
        )
    else:
        accuracy_score = Decimal("0.00")

    score = _percentage(
        rating_score * Decimal("0.60")
        + accuracy_score * Decimal("0.40"),
    )

    completed_viewings = Viewing.objects.filter(
        property=property_obj,
        status=Viewing.Status.COMPLETED,
    ).count()

    record, _ = PropertyTrustScore.objects.get_or_create(
        property=property_obj,
    )

    previous_score = record.score

    record.score = score
    record.confidence = _confidence(feedback_count)
    record.completed_viewings = completed_viewings
    record.feedback_count = feedback_count
    record.average_rating = average_rating.quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )
    record.accurate_feedback_count = accurate
    record.partially_accurate_feedback_count = (
        partially_accurate
    )
    record.inaccurate_feedback_count = inaccurate
    record.last_calculated_at = timezone.now()

    record.save()

    _record_history(
        subject_type=TrustScoreHistory.SubjectType.PROPERTY,
        subject_id=property_obj.id,
        previous_score=previous_score,
        new_score=record.score,
        viewing=viewing,
        reason="Property trust recalculated from viewing feedback.",
    )

    return record


@transaction.atomic
def recalculate_trust_from_feedback(feedback):
    viewing = feedback.viewing

    customer_score = recalculate_customer_trust(
        feedback.customer,
        viewing=viewing,
    )

    partner_score = None

    if viewing.assigned_partner_id is not None:
        partner_score = recalculate_partner_trust(
            viewing.assigned_partner,
            viewing=viewing,
        )

    property_score = recalculate_property_trust(
        viewing.property,
        viewing=viewing,
    )

    return {
        "customer": customer_score,
        "partner": partner_score,
        "property": property_score,
    }
