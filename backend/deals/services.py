from django.db import transaction

from django.core.exceptions import ValidationError

from introductions.models import ProtectedIntroduction

from .models import (
    CommissionInvoice,
    Deal,
    DealEvent,
    DealOutcome,
)
from django.utils import timezone

SUCCESS_OUTCOMES = {
    DealOutcome.Outcome.RENTED,
    DealOutcome.Outcome.PURCHASED,
}


@transaction.atomic
def evaluate_deal_outcomes(deal_id):
    """
    Compare the customer and partner outcome reports.

    This function is the central decision engine for a deal.
    It is safe to call every time an outcome is created or updated.
    """

    deal = (
        Deal.objects
        .select_for_update()
        .select_related(
            "property",
            "customer",
            "partner",
            "viewing",
        )
        .get(pk=deal_id)
    )

    customer_outcome = (
        deal.outcomes
        .filter(
            reporter=DealOutcome.Reporter.CUSTOMER,
        )
        .first()
    )

    partner_outcome = (
        deal.outcomes
        .filter(
            reporter=DealOutcome.Reporter.PARTNER,
        )
        .first()
    )

    # We cannot make a final decision until both sides report.
    if customer_outcome is None or partner_outcome is None:
        Deal.Status.DRAFT
        deal.customer_confirmed = False
        deal.partner_confirmed = False

        deal.save(
            update_fields=[
                "status",
                "customer_confirmed",
                "partner_confirmed",
                "updated_at",
            ]
        )

        return deal

    customer_answer = customer_outcome.outcome
    partner_answer = partner_outcome.outcome

    listing_type = deal.property.listing_type

    expected_success_outcome = (
        DealOutcome.Outcome.PURCHASED
        if listing_type == "sale"
        else DealOutcome.Outcome.RENTED
    )

    answers_match = customer_answer == partner_answer

    successful_match = (
        answers_match
        and customer_answer == expected_success_outcome
    )

    if successful_match:
        deal.status = Deal.Status.AGREED
        deal.customer_confirmed = True
        deal.partner_confirmed = True
        deal.customer_confirmed_at = timezone.now()
        deal.partner_confirmed_at = timezone.now()
        deal.agreed_at = timezone.now()

        deal.save(
            update_fields=[
                "status",
                "customer_confirmed",
                "partner_confirmed",
                "customer_confirmed_at",
                "partner_confirmed_at",
                "agreed_at",
                "updated_at",
            ]
        )

        DealEvent.objects.create(
            deal=deal,
            action="outcomes_matched",
            notes=(
                "Customer and partner reported a successful "
                "property transaction."
            ),
            metadata={
                "customer_outcome": customer_answer,
                "partner_outcome": partner_answer,
            },
        )

        reserve_property(deal)

        return deal

    non_deal_outcomes = {
        DealOutcome.Outcome.DECLINED,
        DealOutcome.Outcome.NO_SHOW,
    }

    if (
        answers_match
        and customer_answer in non_deal_outcomes
    ):
        deal.status = Deal.Status.CANCELLED
        deal.customer_confirmed = False
        deal.partner_confirmed = False
        deal.cancelled_at = timezone.now()
        deal.cancellation_reason = (
            "Customer and partner reported that no deal occurred."
        )

        deal.save(
            update_fields=[
                "status",
                "customer_confirmed",
                "partner_confirmed",
                "cancelled_at",
                "cancellation_reason",
                "updated_at",
            ]
        )

    if (
        answers_match
        and customer_answer
        == DealOutcome.Outcome.STILL_DECIDING
    ):
        Deal.Status.DRAFT
        deal.customer_confirmed = False
        deal.partner_confirmed = False

        deal.save(
            update_fields=[
                "status",
                "customer_confirmed",
                "partner_confirmed",
                "updated_at",
            ]
        )

        return deal

    # Any disagreement or impossible transaction becomes a dispute.
    #
    # Examples:
    # - Customer says rented, partner says declined.
    # - A rental property is reported as purchased.
    # - A sale property is reported as rented.
    deal.status = Deal.Status.DISPUTED
    deal.customer_confirmed = False
    deal.partner_confirmed = False

    deal.save(
        update_fields=[
            "status",
            "customer_confirmed",
            "partner_confirmed",
            "updated_at",
        ]
    )

    return deal


def reserve_property(deal):
    property_instance = deal.property

    if (
        property_instance.status
        != property_instance.STATUS_PUBLISHED
    ):
        return

    property_instance.status = (
        property_instance.STATUS_RESERVED
    )

    property_instance.save(
        update_fields=[
            "status",
            "updated_at",
        ]
    )


@transaction.atomic
def create_deal_from_pic(
    *,
    introduction,
    actor,
    monthly_rent=None,
    sale_price=None,
):
    if actor is None:
        raise ValidationError(
            "An authenticated actor is required."
        )

    if not introduction.is_active:
        raise ValidationError(
            "Only an active PIC can create a deal."
        )

    existing = Deal.objects.filter(
        introduction=introduction,
    ).first()

    if existing is not None:
        return existing, False

    listing_type = introduction.listing_type_snapshot

    if listing_type in {"rent", "rental"}:
        deal_type = "rental"
    elif listing_type == "sale":
        deal_type = "sale"
    else:
        raise ValidationError(
            "The PIC listing type must be rental or sale."
        )

    if deal_type == "rental":
        if monthly_rent is None:
            monthly_rent = (
                introduction.property_price_snapshot
            )

        if monthly_rent <= 0:
            raise ValidationError(
                "Monthly rent must be greater than zero."
            )

        sale_price = None

    if deal_type == "sale":
        if sale_price is None:
            sale_price = (
                introduction.property_price_snapshot
            )

        if sale_price <= 0:
            raise ValidationError(
                "Sale price must be greater than zero."
            )

        monthly_rent = None

    legacy_deal = Deal.objects.filter(
        viewing=introduction.viewing,
    ).first()

    if legacy_deal is not None:
        legacy_deal.introduction = introduction
        legacy_deal.deal_type = deal_type
        legacy_deal.customer = introduction.customer
        legacy_deal.partner = introduction.partner
        legacy_deal.property = introduction.property
        legacy_deal.commission_amount = (
            introduction.expected_commission_snapshot
        )
        legacy_deal.status = Deal.Status.DRAFT

        if deal_type == "rental":
            legacy_deal.monthly_rent = monthly_rent
            legacy_deal.sale_price = None
        else:
            legacy_deal.sale_price = sale_price
            legacy_deal.monthly_rent = None

        legacy_deal.save(
            update_fields=[
                "introduction",
                "deal_type",
                "customer",
                "partner",
                "property",
                "monthly_rent",
                "sale_price",
                "commission_amount",
                "status",
                "updated_at",
            ]
        )

        DealEvent.objects.create(
            deal=legacy_deal,
            action="legacy_deal_linked_to_pic",
            actor=actor,
            notes=(
                "Existing deal linked to Property Introduction "
                f"Certificate {introduction.certificate_number}."
            ),
            metadata={
                "pic_id": introduction.id,
                "certificate_number": (
                    introduction.certificate_number
                ),
            },
        )

        introduction.transition_status(
            new_status=(
                ProtectedIntroduction.Status.CONVERTED_TO_DEAL
            ),
            actor=actor,
            notes=(
                f"PIC linked to existing deal "
                f"{legacy_deal.deal_number}."
            ),
            metadata={
                "deal_id": legacy_deal.id,
                "deal_number": legacy_deal.deal_number,
            },
        )

        return legacy_deal, False

    deal = Deal.objects.create(
        introduction=introduction,
        customer=introduction.customer,
        partner=introduction.partner,
        property=introduction.property,
        viewing=introduction.viewing,
        deal_type=deal_type,
        monthly_rent=monthly_rent,
        sale_price=sale_price,
        commission_amount=(
            introduction.expected_commission_snapshot
        ),
        status=Deal.Status.DRAFT,
    )

    DealEvent.objects.create(
        deal=deal,
        action="deal_created",
        actor=actor,
        notes=(
            "Deal created from Property Introduction "
            f"Certificate {introduction.certificate_number}."
        ),
        metadata={
            "pic_id": introduction.id,
            "certificate_number": (
                introduction.certificate_number
            ),
            "deal_type": deal_type,
        },
    )

    introduction.transition_status(
        new_status=(
            ProtectedIntroduction.Status.CONVERTED_TO_DEAL
        ),
        actor=actor,
        notes=(
            f"PIC converted to deal {deal.deal_number}."
        ),
        metadata={
            "deal_id": deal.id,
            "deal_number": deal.deal_number,
        },
    )

    return deal, True


def generate_invoice_number():

    last = CommissionInvoice.objects.count() + 1

    return f"PH-COM-{last:06d}"

def create_deal_from_viewing(viewing, actor=None):
    try:
        introduction = viewing.property_introduction_certificate
    except ProtectedIntroduction.DoesNotExist as error:
        raise ValidationError(
            "A Property Introduction Certificate is required "
            "before creating a deal."
        ) from error

    return create_deal_from_pic(
        introduction=introduction,
        actor=actor,
    )