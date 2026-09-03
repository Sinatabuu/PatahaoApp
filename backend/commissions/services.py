from decimal import Decimal, ROUND_HALF_UP

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone

from governance.services import get_current_tier

from .models import (
    CommissionSettlement,
    CommissionSettlementParticipant,
    CommissionSettlementPayment,
)


@transaction.atomic
def allocate_commission_settlement(
    settlement_id,
):
    """
    Allocate one commission settlement using the partner's
    current authoritative governance tier.

    Current MVP allocation:
    - Listing partner receives the tier commission share.
    - Pata Hao receives the remainder.

    Allocation amounts become the financial snapshot for this
    settlement. Later partner promotions must not alter them.

    The operation is idempotent:
    - a correctly allocated settlement is returned unchanged;
    - partial/conflicting allocations are rejected.
    """

    settlement = (
        CommissionSettlement.objects
        .select_for_update()
        .select_related(
            "deal",
            "deal__partner",
            "agreement",
        )
        .get(pk=settlement_id)
    )

    deal = settlement.deal
    partner = deal.partner

    if partner is None:
        raise ValidationError(
            {
                "partner": (
                    "The deal does not have an assigned partner."
                )
            }
        )

    if settlement.status not in {
        CommissionSettlement.Status.ALLOCATION_PENDING,
        CommissionSettlement.Status.ALLOCATED,
    }:
        raise ValidationError(
            {
                "settlement": (
                    "This commission settlement can no longer "
                    "be allocated."
                )
            }
        )

    tier = get_current_tier(
        partner,
    )

    if tier is None:
        raise ValidationError(
            {
                "tier": (
                    "The partner does not have an active "
                    "governance tier."
                )
            }
        )

    share_rate = tier.commission_share_rate

    if share_rate is None:
        raise ValidationError(
            {
                "tier": (
                    f"The {tier.name} tier does not have a "
                    "commission share configured."
                )
            }
        )

    if (
        share_rate <= Decimal("0.00")
        or share_rate > Decimal("100.00")
    ):
        raise ValidationError(
            {
                "tier": (
                    "The partner commission share must be "
                    "greater than 0% and no more than 100%."
                )
            }
        )

    gross = settlement.gross_commission_amount

    partner_amount = (
        gross
        * share_rate
        / Decimal("100")
    ).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )

    # Use the remainder rather than a second percentage calculation.
    # This guarantees that allocations total the gross amount exactly.
    platform_amount = (
        gross - partner_amount
    ).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )

    existing = list(
        settlement.participants
        .select_for_update()
        .order_by("id")
    )

    #
    # No allocation exists yet: create the financial snapshot.
    #
    if not existing:
        CommissionSettlementParticipant.objects.create(
            settlement=settlement,
            participant_type=(
                CommissionSettlementParticipant
                .ParticipantType
                .LISTING_PARTNER
            ),
            partner=partner,
            amount=partner_amount,
            is_platform_share=False,
            notes=(
                f"Listing partner allocation using "
                f"{tier.name} tier at "
                f"{share_rate:.2f}%."
            ),
        )

        CommissionSettlementParticipant.objects.create(
            settlement=settlement,
            participant_type=(
                CommissionSettlementParticipant
                .ParticipantType
                .PATA_HAO
            ),
            participant_name="Pata Hao",
            amount=platform_amount,
            is_platform_share=True,
            notes=(
                "Pata Hao platform share after the "
                f"{tier.name} partner allocation."
            ),
        )

        settlement.refresh_from_db()

        return settlement

    #
    # Existing allocations must be exactly the expected two records.
    # We never silently overwrite financial allocations.
    #
    if len(existing) != 2:
        raise ValidationError(
            {
                "settlement": (
                    "This settlement already contains a partial "
                    "or non-standard allocation and requires review."
                )
            }
        )

    partner_share = next(
        (
            participant
            for participant in existing
            if (
                participant.participant_type
                == CommissionSettlementParticipant
                .ParticipantType
                .LISTING_PARTNER
                and participant.partner_id == partner.id
                and not participant.is_platform_share
            )
        ),
        None,
    )

    platform_share = next(
        (
            participant
            for participant in existing
            if (
                participant.participant_type
                == CommissionSettlementParticipant
                .ParticipantType
                .PATA_HAO
                and participant.is_platform_share
            )
        ),
        None,
    )

    if (
        partner_share is None
        or platform_share is None
    ):
        raise ValidationError(
            {
                "settlement": (
                    "The existing commission allocation does not "
                    "match the expected partner/platform structure."
                )
            }
        )

    if partner_share.amount != partner_amount:
        raise ValidationError(
            {
                "settlement": (
                    "The existing partner allocation does not "
                    "match the expected tier snapshot."
                )
            }
        )

    if platform_share.amount != platform_amount:
        raise ValidationError(
            {
                "settlement": (
                    "The existing Pata Hao allocation does not "
                    "match the expected platform share."
                )
            }
        )

    settlement.refresh_from_db()

    return settlement

@transaction.atomic
def record_commission_payment(
    *,
    participant_id,
    actor,
    amount,
    payment_method,
    payment_reference,
    paid_at=None,
    notes="",
):
    """
    Record immutable payout evidence against one approved
    commission settlement participant allocation.

    Rules:
    - Only authenticated Pata Hao staff may record payouts.
    - The participant must belong to an approved or partially
      paid settlement.
    - Participant payments may never exceed the approved allocation.
    - Settlement status is derived from total non-platform payout evidence.
    """

    if actor is None or not actor.is_authenticated:
        raise ValidationError(
            "An authenticated Pata Hao administrator is required."
        )

    if not actor.is_staff:
        raise ValidationError(
            "Only Pata Hao staff may record commission payouts."
        )

    participant = (
        CommissionSettlementParticipant.objects
        .select_for_update()
        .select_related(
            "settlement",
            "settlement__deal",
            "partner",
        )
        .get(pk=participant_id)
    )

    settlement = (
        CommissionSettlement.objects
        .select_for_update()
        .get(pk=participant.settlement_id)
    )

    if participant.is_platform_share:
        raise ValidationError(
            {
                "participant": (
                    "Pata Hao platform revenue is retained revenue "
                    "and must not be recorded as a payout to itself."
                )
            }
        )

    if settlement.status not in {
        CommissionSettlement.Status.APPROVED,
        CommissionSettlement.Status.PARTIALLY_PAID,
    }:
        raise ValidationError(
            {
                "settlement": (
                    "Commission payouts may only be recorded "
                    "against an approved settlement."
                )
            }
        )

    payment = CommissionSettlementPayment.objects.create(
        participant=participant,
        amount=amount,
        currency=settlement.currency,
        payment_method=payment_method,
        payment_reference=payment_reference,
        paid_at=(
            paid_at
            or timezone.now()
        ),
        notes=notes,
        recorded_by=actor,
    )

    payable_participants = (
        settlement.participants
        .filter(
            is_platform_share=False,
        )
    )

    total_payable = (
        payable_participants.aggregate(
            total=models.Sum("amount")
        )["total"]
        or Decimal("0.00")
    ).quantize(
        Decimal("0.01")
    )

    total_paid = (
        CommissionSettlementPayment.objects
        .filter(
            participant__settlement=settlement,
            participant__is_platform_share=False,
        )
        .aggregate(
            total=models.Sum("amount")
        )["total"]
        or Decimal("0.00")
    ).quantize(
        Decimal("0.01")
    )

    if total_paid < total_payable:
        settlement.status = (
            CommissionSettlement.Status.PARTIALLY_PAID
        )

    elif total_paid == total_payable:
        settlement.status = (
            CommissionSettlement.Status.PAID
        )

    else:
        raise ValidationError(
            {
                "amount": (
                    "Recorded commission payouts cannot exceed "
                    "the approved non-platform allocations."
                )
            }
        )

    settlement.save(
        update_fields=[
            "status",
            "updated_at",
        ]
    )

    return payment, settlement


@transaction.atomic
def pay_commission_participant_outstanding(
    *,
    participant_id,
    actor,
    payment_method,
    payment_reference,
    paid_at=None,
    notes="",
):
    """
    Pay the full backend-calculated outstanding entitlement for one
    non-platform commission settlement participant.

    The caller never supplies the payout amount.

    Financial authority:
    - approved participant allocation determines entitlement;
    - immutable previous payment evidence determines amount already paid;
    - the backend derives the exact outstanding amount;
    - platform retained revenue can never be paid through this operation.
    """

    if actor is None or not actor.is_authenticated:
        raise ValidationError(
            "An authenticated Pata Hao administrator is required."
        )

    if not actor.is_staff:
        raise ValidationError(
            "Only Pata Hao staff may authorize commission payouts."
        )

    participant = (
        CommissionSettlementParticipant.objects
        .select_for_update()
        .select_related(
            "settlement",
            "settlement__deal",
            "partner",
        )
        .get(pk=participant_id)
    )

    settlement = (
        CommissionSettlement.objects
        .select_for_update()
        .get(pk=participant.settlement_id)
    )

    if participant.is_platform_share:
        raise ValidationError(
            {
                "participant": (
                    "Pata Hao platform revenue is retained revenue "
                    "and cannot be paid out to itself."
                )
            }
        )

    if settlement.status not in {
        CommissionSettlement.Status.APPROVED,
        CommissionSettlement.Status.PARTIALLY_PAID,
    }:
        raise ValidationError(
            {
                "settlement": (
                    "Commission payouts may only be authorized "
                    "against an approved settlement."
                )
            }
        )

    already_paid = (
        participant.payments.aggregate(
            total=models.Sum("amount")
        )["total"]
        or Decimal("0.00")
    ).quantize(
        Decimal("0.01")
    )

    entitlement = participant.amount.quantize(
        Decimal("0.01")
    )

    outstanding = (
        entitlement - already_paid
    ).quantize(
        Decimal("0.01")
    )

    if outstanding <= Decimal("0.00"):
        raise ValidationError(
            {
                "participant": (
                    "This participant has no outstanding "
                    "commission entitlement."
                )
            }
        )

    payment, settlement = record_commission_payment(
        participant_id=participant.id,
        actor=actor,
        amount=outstanding,
        payment_method=payment_method,
        payment_reference=payment_reference,
        paid_at=paid_at,
        notes=notes,
    )

    return payment, settlement


@transaction.atomic
def approve_commission_settlement(
    *,
    settlement_id,
    actor,
):
    """
    Approve a fully allocated commission settlement.

    No financial amount, percentage, recipient, or allocation may be
    supplied by the caller. Approval freezes the backend-calculated
    settlement snapshot for payout.
    """

    if actor is None or not actor.is_authenticated:
        raise ValidationError(
            "An authenticated Pata Hao administrator is required."
        )

    if not actor.is_staff:
        raise ValidationError(
            "Only Pata Hao staff may approve commission settlements."
        )

    settlement = (
        CommissionSettlement.objects
        .select_for_update()
        .prefetch_related(
            "participants",
        )
        .get(pk=settlement_id)
    )

    if settlement.status == CommissionSettlement.Status.APPROVED:
        return settlement, False

    if settlement.status != CommissionSettlement.Status.ALLOCATED:
        raise ValidationError(
            {
                "status": (
                    "Only a fully allocated commission settlement "
                    "may be approved."
                )
            }
        )

    settlement.approve(
        approved_by=actor,
    )

    settlement.save()

    return settlement, True
