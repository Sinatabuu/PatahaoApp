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


@transaction.atomic
def recalculate_partner_trust(partner, *, viewing=None):
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

    feedback_count = feedback_summary["feedback_count"] or 0

    rating_score = _rating_to_percentage(
        average_rating,
    )

    total_resolved = (
        completed_viewings
        + declined_viewings
    )

    if total_resolved > 0:
        completion_rate = (
            Decimal(completed_viewings)
            / Decimal(total_resolved)
            * Decimal("100")
        )
    else:
        completion_rate = Decimal("0.00")

    score = _percentage(
        rating_score * Decimal("0.70")
        + completion_rate * Decimal("0.30"),
    )

    record, _ = PartnerTrustScore.objects.get_or_create(
        partner=partner,
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
    record.accepted_viewings = accepted_viewings
    record.declined_viewings = declined_viewings
    record.rescheduled_viewings = rescheduled_viewings
    record.last_calculated_at = timezone.now()

    record.save()

    _record_history(
        subject_type=TrustScoreHistory.SubjectType.PARTNER,
        subject_id=partner.id,
        previous_score=previous_score,
        new_score=record.score,
        viewing=viewing,
        reason="Partner trust recalculated from customer feedback.",
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
