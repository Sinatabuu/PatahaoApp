from django.db import transaction

from .models import (
    CommissionInvoice,
    Deal,
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
        deal.status = Deal.Status.PENDING_CONFIRMATION
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
        deal.status = Deal.Status.CONFIRMED
        deal.customer_confirmed = True
        deal.partner_confirmed = True

        deal.save(
            update_fields=[
                "status",
                "customer_confirmed",
                "partner_confirmed",
                "updated_at",
            ]
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

        deal.save(
            update_fields=[
                "status",
                "customer_confirmed",
                "partner_confirmed",
                "updated_at",
            ]
        )

        return deal

    if (
        answers_match
        and customer_answer
        == DealOutcome.Outcome.STILL_DECIDING
    ):
        deal.status = Deal.Status.PENDING_CONFIRMATION
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
    """
    Reserve a property after both parties confirm a successful deal.

    Only a published property is automatically moved to reserved.
    Rented, sold, archived, or otherwise unavailable properties
    are not overwritten.
    """

    property_instance = deal.property

    if property_instance.status != "published":
        return

    property_instance.status = "reserved"

    property_instance.save(
        update_fields=[
            "status",
            
        ]
    )


def create_deal_from_viewing(viewing):
    """
    Create a Deal for a completed viewing.

    Safe to call multiple times.
    """

    deal, created = Deal.objects.get_or_create(
        viewing=viewing,
        defaults={
            "customer": viewing.customer,
            "partner": viewing.assigned_partner,
            "property": viewing.property,
        },
    )

    return deal    


def generate_invoice_number():

    last = CommissionInvoice.objects.count() + 1

    return f"PH-COM-{last:06d}"