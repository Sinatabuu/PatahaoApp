from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from payments.models import Payment
from introductions.models import ProtectedIntroduction
from mandates.models import PropertyMandate
from governance.services import (
    enforce_partner_operational_access,
)
from .models import (
    CommissionInvoice,
    Deal,
    DealEvent,
    DealOutcome,
    OwnerConfirmationToken,
)


SUCCESS_OUTCOMES = {
    DealOutcome.Outcome.RENTED,
    DealOutcome.Outcome.PURCHASED,
}


@transaction.atomic
def evaluate_deal_outcomes(deal_id):
    """
    Evaluate immutable customer, partner, and owner confirmations.

    Rules:
    - Fewer than three submissions: await remaining confirmations.
    - Three matching successful submissions: agree the deal.
    - Three matching non-deal submissions: cancel the deal.
    - Three still-deciding submissions: keep negotiating.
    - Any disagreement or impossible result: dispute the deal.
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
        .prefetch_related(
            "outcomes",
        )
        .get(pk=deal_id)
    )

    outcomes_by_reporter = {
        outcome.reporter: outcome
        for outcome in deal.outcomes.all()
    }

    required_reporters = {
        DealOutcome.Reporter.CUSTOMER,
        DealOutcome.Reporter.PARTNER,
        DealOutcome.Reporter.OWNER,
    }

    submitted_reporters = set(
        outcomes_by_reporter.keys()
    )

    missing_reporters = (
        required_reporters - submitted_reporters
    )

    if missing_reporters:
        deal.status = Deal.Status.AWAITING_CONFIRMATIONS

        deal.customer_confirmed = (
            DealOutcome.Reporter.CUSTOMER
            in submitted_reporters
        )

        deal.partner_confirmed = (
            DealOutcome.Reporter.PARTNER
            in submitted_reporters
        )

        deal.owner_confirmed = (
            DealOutcome.Reporter.OWNER
            in submitted_reporters
        )

        deal.save(
            update_fields=[
                "status",
                "customer_confirmed",
                "partner_confirmed",
                "owner_confirmed",
                "updated_at",
            ]
        )

        return deal

    customer_outcome = outcomes_by_reporter[
        DealOutcome.Reporter.CUSTOMER
    ]

    partner_outcome = outcomes_by_reporter[
        DealOutcome.Reporter.PARTNER
    ]

    owner_outcome = outcomes_by_reporter[
        DealOutcome.Reporter.OWNER
    ]

    customer_answer = customer_outcome.outcome
    partner_answer = partner_outcome.outcome
    owner_answer = owner_outcome.outcome

    answers = {
        customer_answer,
        partner_answer,
        owner_answer,
    }

    expected_success_outcome = (
        DealOutcome.Outcome.PURCHASED
        if deal.property.listing_type == "sale"
        else DealOutcome.Outcome.RENTED
    )

    metadata = {
        "customer_outcome": customer_answer,
        "partner_outcome": partner_answer,
        "owner_outcome": owner_answer,
    }

    now = timezone.now()

    deal.customer_confirmed = True
    deal.partner_confirmed = True
    deal.owner_confirmed = True

    deal.customer_confirmed_at = (
        deal.customer_confirmed_at
        or customer_outcome.created_at
        or now
    )

    deal.partner_confirmed_at = (
        deal.partner_confirmed_at
        or partner_outcome.created_at
        or now
    )

    deal.owner_confirmed_at = (
        deal.owner_confirmed_at
        or owner_outcome.created_at
        or now
    )

    confirmation_fields = [
        "customer_confirmed",
        "partner_confirmed",
        "owner_confirmed",
        "customer_confirmed_at",
        "partner_confirmed_at",
        "owner_confirmed_at",
    ]

    # All three parties confirm the correct successful transaction.
    if answers == {expected_success_outcome}:
        deal.status = Deal.Status.AGREED
        deal.agreed_at = deal.agreed_at or now

        deal.save(
            update_fields=[
                *confirmation_fields,
                "status",
                "agreed_at",
                "updated_at",
            ]
        )

        DealEvent.objects.get_or_create(
            deal=deal,
            action="three_party_confirmation_matched",
            defaults={
                "notes": (
                    "Customer, partner, and owner confirmed "
                    "the same successful property transaction."
                ),
                "metadata": metadata,
            },
        )

        reserve_property(deal)

        return deal

    non_deal_outcomes = {
        DealOutcome.Outcome.DECLINED,
        DealOutcome.Outcome.NO_SHOW,
    }

    # All three agree that no transaction occurred.
    if (
        len(answers) == 1
        and customer_answer in non_deal_outcomes
    ):
        deal.status = Deal.Status.CANCELLED
        deal.cancelled_at = deal.cancelled_at or now
        deal.cancellation_reason = (
            "Customer, partner, and owner confirmed "
            "that no property transaction occurred."
        )

        deal.save(
            update_fields=[
                *confirmation_fields,
                "status",
                "cancelled_at",
                "cancellation_reason",
                "updated_at",
            ]
        )

        DealEvent.objects.get_or_create(
            deal=deal,
            action="three_party_no_deal_confirmed",
            defaults={
                "notes": deal.cancellation_reason,
                "metadata": metadata,
            },
        )

        return deal

    # All three report that the customer is still deciding.
    if answers == {
        DealOutcome.Outcome.STILL_DECIDING
    }:
        deal.status = Deal.Status.NEGOTIATING

        deal.save(
            update_fields=[
                *confirmation_fields,
                "status",
                "updated_at",
            ]
        )

        DealEvent.objects.get_or_create(
            deal=deal,
            action="three_party_still_deciding",
            defaults={
                "notes": (
                    "Customer, partner, and owner reported "
                    "that the transaction is still being considered."
                ),
                "metadata": metadata,
            },
        )

        return deal

    # Any disagreement or listing-incompatible result is disputed.
    deal.status = Deal.Status.DISPUTED

    deal.save(
        update_fields=[
            *confirmation_fields,
            "status",
            "updated_at",
        ]
    )

    DealEvent.objects.get_or_create(
        deal=deal,
        action="three_party_confirmation_disputed",
        defaults={
            "notes": (
                "The customer, partner, and owner confirmations "
                "did not produce a valid matching transaction."
            ),
            "metadata": {
                **metadata,
                "expected_success_outcome": (
                    expected_success_outcome
                ),
            },
        },
    )

    return deal


@transaction.atomic
def issue_owner_confirmation_token(
    *,
    deal_id,
    actor,
    validity_hours=48,
):
    """
    Issue a single-use owner confirmation token.

    Only staff or the deal's approved partner may issue it.
    Older unused tokens for the deal are revoked.
    """

    if actor is None or not actor.is_authenticated:
        raise ValidationError(
            "An authenticated actor is required."
        )

    deal = (
        Deal.objects
        .select_for_update()
        .select_related(
            "property",
            "partner",
            "partner__user",
        )
        .get(pk=deal_id)
    )

    actor_partner = getattr(
        actor,
        "partner_profile",
        None,
    )

    is_assigned_partner = (
        actor_partner is not None
        and actor_partner.pk == deal.partner_id
    )

    if not actor.is_staff and not is_assigned_partner:
        raise ValidationError(
            "Only Pata Hao staff or the assigned partner "
            "may issue owner confirmation."
        )
    if is_assigned_partner:
        enforce_partner_operational_access(
            actor_partner,
            operation="issue_owner_confirmation",
        )

    if deal.status in {
        Deal.Status.AGREED,
        Deal.Status.CANCELLED,
        Deal.Status.COMPLETED,
        Deal.Status.COMMISSION_PAID,
    }:
        raise ValidationError(
            "Owner confirmation cannot be issued "
            "for this deal status."
        )

    if DealOutcome.objects.filter(
        deal=deal,
        reporter=DealOutcome.Reporter.OWNER,
    ).exists():
        raise ValidationError(
            "The owner has already submitted a confirmation."
        )

    mandate = (
        PropertyMandate.objects
        .select_for_update()
        .select_related(
            "owner",
            "property",
            "partner",
            "commission_agreement",
        )
        .filter(
            property=deal.property,
            partner=deal.partner,
            status=PropertyMandate.Status.APPROVED,
        )
        .order_by(
            "-version",
            "-created_at",
        )
        .first()
    )

    if mandate is None:
        raise ValidationError(
            "No approved property mandate was found "
            "for this deal."
        )

    if not mandate.is_currently_valid:
        raise ValidationError(
            "The property mandate is not currently valid."
        )

    owner = mandate.owner

    if not owner.is_verified:
        raise ValidationError(
            "The property owner is not verified."
        )

    if not owner.phone_number and not owner.email:
        raise ValidationError(
            "The verified owner has no delivery contact."
        )

    now = timezone.now()

    existing_tokens = (
        OwnerConfirmationToken.objects
        .select_for_update()
        .filter(
            deal=deal,
            used_at__isnull=True,
            revoked_at__isnull=True,
        )
    )

    for existing_token in existing_tokens:
        existing_token.revoked_at = now
        existing_token.save(
            update_fields=[
                "revoked_at",
            ]
        )

    token_record, raw_token = (
        OwnerConfirmationToken.issue(
            deal=deal,
            owner=owner,
            mandate=mandate,
            created_by=actor,
            expires_at=(
                now
                + timedelta(
                    hours=validity_hours,
                )
            ),
        )
    )

    DealEvent.objects.create(
        deal=deal,
        action="owner_confirmation_token_issued",
        actor=actor,
        notes=(
            "A single-use owner confirmation token was issued "
            "to the verified property owner."
        ),
        metadata={
            "owner_number": owner.owner_number,
            "mandate_number": mandate.mandate_number,
            "expires_at": (
                token_record.expires_at.isoformat()
            ),
            "delivery_phone_available": bool(
                owner.phone_number
            ),
            "delivery_email_available": bool(
                owner.email
            ),
        },
    )

    return token_record, raw_token


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
def submit_owner_outcome(
    *,
    raw_token,
    outcome,
    notes="",
):
    """
    Validate and consume a single-use owner token, create immutable
    owner confirmation evidence, and evaluate the deal.
    """

    if not raw_token:
        raise ValidationError(
            "The owner confirmation token is required."
        )

    token_hash = OwnerConfirmationToken.hash_token(
        raw_token,
    )

    token_record = (
        OwnerConfirmationToken.objects
        .select_for_update()
        .select_related(
            "deal",
            "deal__property",
            "deal__partner",
            "owner",
            "mandate",
            "mandate__owner",
            "mandate__property",
            "mandate__partner",
            "mandate__commission_agreement",
        )
        .filter(
            token_hash=token_hash,
        )
        .first()
    )

    if token_record is None:
        raise ValidationError(
            "The owner confirmation token is invalid."
        )

    if not token_record.is_usable:
        raise ValidationError(
            "This owner confirmation token is expired, "
            "used, or revoked."
        )

    deal = (
        Deal.objects
        .select_for_update()
        .select_related(
            "property",
            "partner",
        )
        .get(pk=token_record.deal_id)
    )

    mandate = token_record.mandate
    owner = token_record.owner

    if mandate.property_id != deal.property_id:
        raise ValidationError(
            "The mandate does not belong to the deal property."
        )

    if mandate.partner_id != deal.partner_id:
        raise ValidationError(
            "The mandate does not belong to "
            "the assigned deal partner."
        )

    if mandate.owner_id != owner.id:
        raise ValidationError(
            "The confirmation owner does not match "
            "the mandate owner."
        )

    if not mandate.is_currently_valid:
        raise ValidationError(
            "The property mandate is no longer valid."
        )

    if not owner.is_verified:
        raise ValidationError(
            "The property owner is no longer verified."
        )

    existing_owner_outcome = (
        DealOutcome.objects
        .filter(
            deal=deal,
            reporter=DealOutcome.Reporter.OWNER,
        )
        .first()
    )

    if existing_owner_outcome is not None:
        raise ValidationError(
            "The owner confirmation has already been submitted."
        )

    valid_outcomes = {
        value
        for value, _label
        in DealOutcome.Outcome.choices
    }

    if outcome not in valid_outcomes:
        raise ValidationError(
            {
                "outcome": (
                    "The submitted owner outcome is invalid."
                )
            }
        )

    cleaned_notes = (notes or "").strip()

    if len(cleaned_notes) > 2000:
        raise ValidationError(
            {
                "notes": (
                    "Notes cannot exceed 2,000 characters."
                )
            }
        )

    owner_outcome = DealOutcome.objects.create(
        deal=deal,
        reporter=DealOutcome.Reporter.OWNER,
        outcome=outcome,
        notes=cleaned_notes,
    )

    token_record.mark_used()

    DealEvent.objects.create(
        deal=deal,
        action="owner_confirmation_submitted",
        actor=None,
        notes=(
            "The verified property owner submitted "
            "a deal outcome using a single-use confirmation token."
        ),
        metadata={
            "owner_number": owner.owner_number,
            "mandate_number": mandate.mandate_number,
            "outcome_id": owner_outcome.id,
            "outcome": owner_outcome.outcome,
            "token_id": token_record.id,
        },
    )

    evaluated_deal = evaluate_deal_outcomes(
        deal.id,
    )

    return owner_outcome, evaluated_deal


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
    actor_partner = getattr(
        actor,
        "partner_profile",
        None,
    )

    is_assigned_partner = (
        actor_partner is not None
        and actor_partner.pk == introduction.partner_id
    )

    if not actor.is_staff and not is_assigned_partner:
        raise ValidationError(
            "Only Pata Hao staff or the assigned partner "
            "may convert this PIC into a deal."
        )

    if is_assigned_partner:
        enforce_partner_operational_access(
            actor_partner,
            operation="convert_pic_to_deal",
        )

    if not introduction.is_active:
        raise ValidationError(
            "Only an active PIC can create a deal."
        )

    existing = (
        Deal.objects
        .filter(
            introduction=introduction,
        )
        .first()
    )

    if existing is not None:
        return existing, False

    listing_type = (
        introduction.listing_type_snapshot
    )

    if listing_type in {
        "rent",
        "rental",
    }:
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

    else:
        if sale_price is None:
            sale_price = (
                introduction.property_price_snapshot
            )

        if sale_price <= 0:
            raise ValidationError(
                "Sale price must be greater than zero."
            )

        monthly_rent = None

    legacy_deal = (
        Deal.objects
        .filter(
            viewing=introduction.viewing,
        )
        .first()
    )

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
                "PIC linked to existing deal "
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


def create_deal_from_viewing(
    viewing,
    actor=None,
):
    try:
        introduction = (
            viewing.property_introduction_certificate
        )

    except ProtectedIntroduction.DoesNotExist as error:
        raise ValidationError(
            "A Property Introduction Certificate is required "
            "before creating a deal."
        ) from error

    return create_deal_from_pic(
        introduction=introduction,
        actor=actor,
    )


def build_deal_timeline(deal):
    """
    Build a normalized chronological timeline from existing evidence.

    No timeline records are created, changed, or deleted here.
    """

    timeline = []

    def add_item(
        *,
        timestamp,
        event_type,
        title,
        description="",
        actor=None,
        source,
        source_id=None,
        metadata=None,
    ):
        if timestamp is None:
            return

        timeline.append(
            {
                "timestamp": timestamp,
                "event_type": event_type,
                "title": title,
                "description": description or "",
                "actor": actor,
                "source": source,
                "source_id": source_id,
                "metadata": metadata or {},
            }
        )

    add_item(
        timestamp=deal.created_at,
        event_type="deal_created",
        title="Deal created",
        description=(
            f"Deal {deal.deal_number} was created "
            f"for {deal.property.title}."
        ),
        source="deal",
        source_id=deal.id,
        metadata={
            "deal_number": deal.deal_number,
            "deal_type": deal.deal_type,
            "property_id": deal.property_id,
            "viewing_id": deal.viewing_id,
        },
    )

    viewing = deal.viewing

    viewing_partner_name = None

    if viewing.assigned_partner is not None:
        viewing_partner_name = (
            viewing.assigned_partner.display_name
            or viewing.assigned_partner.business_name
            or viewing.assigned_partner.user
            .get_full_name()
            .strip()
            or viewing.assigned_partner.user.email
            or viewing.assigned_partner.user.username
        )

    add_item(
        timestamp=viewing.created_at,
        event_type="viewing_requested",
        title="Viewing requested",
        description=(
            f"A viewing was requested for "
            f"{viewing.property.title}."
        ),
        actor=(
            viewing.customer.get_full_name().strip()
            or viewing.customer.email
            or viewing.customer.username
        ),
        source="viewing",
        source_id=viewing.id,
        metadata={
            "viewing_id": viewing.id,
            "property_id": viewing.property_id,
            "property_title": viewing.property.title,
            "customer_id": viewing.customer_id,
            "assigned_partner_id": (
                viewing.assigned_partner_id
            ),
            "assigned_partner_name": (
                viewing_partner_name
            ),
            "requested_date": (
                viewing.requested_date.isoformat()
            ),
            "requested_time": (
                viewing.requested_time.isoformat()
            ),
            "fee_amount": str(viewing.fee_amount),
            "status": viewing.status,
            "status_label": viewing.get_status_display(),
            "customer_message": viewing.customer_message,
        },
    )

    add_item(
        timestamp=viewing.partner_responded_at,
        event_type="viewing_partner_responded",
        title="Partner responded to viewing",
        description=(
            viewing.partner_response_message
            or "The assigned partner responded to the viewing request."
        ),
        actor=viewing_partner_name,
        source="viewing",
        source_id=viewing.id,
        metadata={
            "status": viewing.status,
            "status_label": viewing.get_status_display(),
            "proposed_date": (
                viewing.proposed_date.isoformat()
                if viewing.proposed_date
                else None
            ),
            "proposed_time": (
                viewing.proposed_time.isoformat()
                if viewing.proposed_time
                else None
            ),
            "confirmed_date": (
                viewing.confirmed_date.isoformat()
                if viewing.confirmed_date
                else None
            ),
            "confirmed_time": (
                viewing.confirmed_time.isoformat()
                if viewing.confirmed_time
                else None
            ),
        },
    )

    for viewing_event in (
        viewing.events
        .all()
        .order_by(
            "created_at",
            "id",
        )
    ):
        viewing_event_actor = None

        if viewing_event.actor is not None:
            viewing_event_actor = (
                viewing_event.actor.get_full_name().strip()
                or viewing_event.actor.email
                or viewing_event.actor.username
            )

        add_item(
            timestamp=viewing_event.created_at,
            event_type=viewing_event.event_type,
            title=(
                "Viewing "
                + viewing_event.get_event_type_display()
            ),
            description=viewing_event.notes,
            actor=viewing_event_actor,
            source="viewing_event",
            source_id=viewing_event.id,
            metadata={
                "viewing_id": viewing.id,
                "event_type": viewing_event.event_type,
                "event_type_label": (
                    viewing_event.get_event_type_display()
                ),
                **(viewing_event.metadata or {}),
            },
        )

    add_item(
        timestamp=viewing.completed_at,
        event_type="viewing_completed",
        title="Viewing completed",
        description=(
            f"The viewing of {viewing.property.title} "
            "was completed."
        ),
        source="viewing",
        source_id=viewing.id,
        metadata={
            "viewing_id": viewing.id,
            "status": viewing.status,
            "status_label": viewing.get_status_display(),
            "payment_reference": (
                viewing.payment_reference
            ),
        },
    )

    try:
        payment = viewing.payment
    except Payment.DoesNotExist:
        payment = None

    if payment is not None:
        payer_name = (
            payment.payer.get_full_name().strip()
            or payment.payer.email
            or payment.payer.username
        )

        add_item(
            timestamp=payment.created_at,
            event_type="viewing_payment_created",
            title="Viewing payment created",
            description=(
                "A viewing-fee payment record was created."
            ),
            actor=payer_name,
            source="payment",
            source_id=payment.id,
            metadata={
                "payment_reference": (
                    payment.payment_reference
                ),
                "viewing_id": payment.viewing_id,
                "payer_id": payment.payer_id,
                "amount": str(payment.amount),
                "currency": payment.currency,
                "payment_method": (
                    payment.payment_method
                ),
                "payment_method_label": (
                    payment.get_payment_method_display()
                ),
                "purpose": payment.purpose,
                "status": payment.status,
                "status_label": (
                    payment.get_status_display()
                ),
            },
        )

        add_item(
            timestamp=payment.initiated_at,
            event_type="viewing_payment_initiated",
            title="Viewing payment initiated",
            description=(
                "The viewing-fee payment request was "
                "submitted to the payment provider."
            ),
            actor=payer_name,
            source="payment",
            source_id=payment.id,
            metadata={
                "payment_reference": (
                    payment.payment_reference
                ),
                "payment_method": (
                    payment.payment_method
                ),
                "merchant_request_id": (
                    payment.merchant_request_id
                ),
                "checkout_request_id": (
                    payment.checkout_request_id
                ),
                "provider_response_code": (
                    payment.provider_response_code
                ),
                "provider_response_description": (
                    payment.provider_response_description
                ),
            },
        )

        add_item(
            timestamp=payment.callback_received_at,
            event_type="viewing_payment_callback_received",
            title="Payment provider callback received",
            description=(
                "Pata Hao received the payment provider's "
                "transaction result."
            ),
            source="payment",
            source_id=payment.id,
            metadata={
                "payment_reference": (
                    payment.payment_reference
                ),
                "provider_transaction_id": (
                    payment.provider_transaction_id
                ),
                "provider_receipt_number": (
                    payment.provider_receipt_number
                ),
                "provider_response_code": (
                    payment.provider_response_code
                ),
            },
        )

        add_item(
            timestamp=payment.paid_at,
            event_type="viewing_fee_paid",
            title="Viewing fee paid",
            description=(
                f"The customer paid {payment.currency} "
                f"{payment.amount} for the viewing."
            ),
            actor=payer_name,
            source="payment",
            source_id=payment.id,
            metadata={
                "payment_reference": (
                    payment.payment_reference
                ),
                "receipt_number": (
                    payment.receipt_number
                ),
                "provider_receipt_number": (
                    payment.provider_receipt_number
                ),
                "provider_transaction_id": (
                    payment.provider_transaction_id
                ),
                "amount": str(payment.amount),
                "currency": payment.currency,
                "payment_method": (
                    payment.payment_method
                ),
                "status": payment.status,
            },
        )

        add_item(
            timestamp=payment.failed_at,
            event_type="viewing_payment_failed",
            title="Viewing payment failed",
            description=(
                payment.failure_reason
                or "The viewing-fee payment failed."
            ),
            actor=payer_name,
            source="payment",
            source_id=payment.id,
            metadata={
                "payment_reference": (
                    payment.payment_reference
                ),
                "provider_response_code": (
                    payment.provider_response_code
                ),
                "provider_response_description": (
                    payment.provider_response_description
                ),
                "status": payment.status,
            },
        )

    introduction = getattr(
        deal,
        "introduction",
        None,
    )

    if introduction is not None:
        mandate = introduction.mandate
        commission_agreement = (
            introduction.commission_agreement
        )

        mandate_created_by = mandate.created_by
        mandate_creator_name = None

        if mandate_created_by is not None:
            mandate_creator_name = (
                mandate_created_by.get_full_name().strip()
                or mandate_created_by.email
                or mandate_created_by.username
            )

        add_item(
            timestamp=mandate.created_at,
            event_type="property_mandate_created",
            title="Property mandate created",
            description=(
                f"Property mandate {mandate.mandate_number} "
                f"was created for {deal.property.title}."
            ),
            actor=mandate_creator_name,
            source="property_mandate",
            source_id=mandate.id,
            metadata={
                "mandate_number": mandate.mandate_number,
                "version": mandate.version,
                "status": mandate.status,
                "status_label": mandate.get_status_display(),
                "owner_number": mandate.owner.owner_number,
                "owner_name": mandate.owner.legal_name,
                "partner_id": mandate.partner_id,
                "effective_date": (
                    mandate.effective_date.isoformat()
                    if mandate.effective_date
                    else None
                ),
                "expiry_date": (
                    mandate.expiry_date.isoformat()
                    if mandate.expiry_date
                    else None
                ),
                "protection_period_days": (
                    mandate.protection_period_days
                ),
            },
        )

        mandate_approver_name = None

        if mandate.approved_by is not None:
            mandate_approver_name = (
                mandate.approved_by.get_full_name().strip()
                or mandate.approved_by.email
                or mandate.approved_by.username
            )

        add_item(
            timestamp=mandate.approved_at,
            event_type="property_mandate_approved",
            title="Property mandate approved",
            description=(
                f"Property mandate {mandate.mandate_number} "
                "was approved for property operations."
            ),
            actor=mandate_approver_name,
            source="property_mandate",
            source_id=mandate.id,
            metadata={
                "mandate_number": mandate.mandate_number,
                "status": mandate.status,
                "owner_authority_confirmed": (
                    mandate.owner_authority_confirmed
                ),
                "no_cash_acknowledged": (
                    mandate.no_cash_acknowledged
                ),
                "anti_circumvention_acknowledged": (
                    mandate.anti_circumvention_acknowledged
                ),
            },
        )

        for mandate_event in (
            mandate.events
            .all()
            .order_by(
                "created_at",
                "id",
            )
        ):
            mandate_event_actor = None

            if mandate_event.actor is not None:
                mandate_event_actor = (
                    mandate_event.actor.get_full_name().strip()
                    or mandate_event.actor.email
                    or mandate_event.actor.username
                )

            add_item(
                timestamp=mandate_event.created_at,
                event_type=(
                    f"mandate_{mandate_event.action}"
                ),
                title=(
                    "Mandate "
                    + mandate_event.action
                    .replace("_", " ")
                    .title()
                ),
                description=mandate_event.notes,
                actor=mandate_event_actor,
                source="mandate_event",
                source_id=mandate_event.id,
                metadata={
                    "mandate_id": mandate.id,
                    "mandate_number": mandate.mandate_number,
                    **(mandate_event.metadata or {}),
                },
            )

        add_item(
            timestamp=commission_agreement.created_at,
            event_type="commission_agreement_created",
            title="Commission agreement created",
            description=(
                "The property commission agreement was created "
                "before publication and customer introduction."
            ),
            source="commission_agreement",
            source_id=commission_agreement.id,
            metadata={
                "agreement_number": (
                    commission_agreement.agreement_number
                ),
                "status": commission_agreement.status,
                "status_label": (
                    commission_agreement.get_status_display()
                ),
                "commission_method": (
                    commission_agreement.commission_method
                ),
                "expected_total_commission": str(
                    commission_agreement.expected_total_commission
                ),
                "currency": commission_agreement.currency,
            },
        )

        add_item(
            timestamp=commission_agreement.owner_confirmed_at,
            event_type="commission_agreement_owner_confirmed",
            title="Commission agreement confirmed by owner",
            description=(
                "The property owner confirmed the commission "
                "agreement."
            ),
            source="commission_agreement",
            source_id=commission_agreement.id,
            metadata={
                "agreement_number": (
                    commission_agreement.agreement_number
                ),
                "status": commission_agreement.status,
            },
        )

        verifier_name = None

        if commission_agreement.verified_by is not None:
            verifier_name = (
                commission_agreement.verified_by
                .get_full_name()
                .strip()
                or commission_agreement.verified_by.email
                or commission_agreement.verified_by.username
            )

        add_item(
            timestamp=commission_agreement.verified_at,
            event_type="commission_agreement_verified",
            title="Commission agreement verified",
            description=(
                "A Pata Hao administrator verified the commission "
                "agreement."
            ),
            actor=verifier_name,
            source="commission_agreement",
            source_id=commission_agreement.id,
            metadata={
                "agreement_number": (
                    commission_agreement.agreement_number
                ),
                "status": commission_agreement.status,
            },
        )

        add_item(
            timestamp=commission_agreement.locked_at,
            event_type="commission_agreement_locked",
            title="Commission agreement locked",
            description=(
                "The commission terms were locked against "
                "financial alteration."
            ),
            source="commission_agreement",
            source_id=commission_agreement.id,
            metadata={
                "agreement_number": (
                    commission_agreement.agreement_number
                ),
                "expected_total_commission": str(
                    commission_agreement.expected_total_commission
                ),
                "currency": commission_agreement.currency,
            },
        )

        add_item(
            timestamp=introduction.created_at,
            event_type="pic_issued",
            title="Property Introduction Certificate issued",
            description=(
                f"PIC {introduction.certificate_number} protected "
                "the customer introduction to this property."
            ),
            source="protected_introduction",
            source_id=introduction.id,
            metadata={
                "certificate_number": (
                    introduction.certificate_number
                ),
                "status": introduction.status,
                "status_label": (
                    introduction.get_status_display()
                ),
                "customer_name": (
                    introduction.customer_name_snapshot
                ),
                "property_title": (
                    introduction.property_title_snapshot
                ),
                "listing_type": (
                    introduction.listing_type_snapshot
                ),
                "property_price": str(
                    introduction.property_price_snapshot
                ),
                "owner_name": (
                    introduction.owner_name_snapshot
                ),
                "partner_name": (
                    introduction.partner_name_snapshot
                ),
                "mandate_number": (
                    introduction.mandate_number_snapshot
                ),
                "commission_agreement_number": (
                    introduction
                    .commission_agreement_number_snapshot
                ),
                "expected_commission": str(
                    introduction.expected_commission_snapshot
                ),
                "currency": (
                    introduction.currency_snapshot
                ),
                "viewing_fee": str(
                    introduction.viewing_fee_snapshot
                ),
                "viewing_payment_reference": (
                    introduction.viewing_payment_reference
                ),
                "protected_from": (
                    introduction.protected_from.isoformat()
                ),
                "protected_until": (
                    introduction.protected_until.isoformat()
                ),
            },
        )

        for introduction_event in (
            introduction.events
            .all()
            .order_by(
                "created_at",
                "id",
            )
        ):
            introduction_event_actor = None

            if introduction_event.actor is not None:
                introduction_event_actor = (
                    introduction_event.actor
                    .get_full_name()
                    .strip()
                    or introduction_event.actor.email
                    or introduction_event.actor.username
                )

            add_item(
                timestamp=introduction_event.created_at,
                event_type=(
                    f"pic_{introduction_event.action}"
                ),
                title=(
                    "PIC "
                    + introduction_event.action
                    .replace("_", " ")
                    .title()
                ),
                description=introduction_event.notes,
                actor=introduction_event_actor,
                source="introduction_event",
                source_id=introduction_event.id,
                metadata={
                    "pic_id": introduction.id,
                    "certificate_number": (
                        introduction.certificate_number
                    ),
                    **(introduction_event.metadata or {}),
                },
            )

    for outcome in deal.outcomes.all():
        reporter_name = (
            outcome.get_reporter_display()
        )

        outcome_name = (
            outcome.get_outcome_display()
        )

        add_item(
            timestamp=outcome.created_at,
            event_type=(
                f"{outcome.reporter}_outcome_submitted"
            ),
            title=(
                f"{reporter_name} confirmation submitted"
            ),
            description=(
                outcome.notes
                or (
                    f"{reporter_name} reported: "
                    f"{outcome_name}."
                )
            ),
            source="deal_outcome",
            source_id=outcome.id,
            metadata={
                "reporter": outcome.reporter,
                "reporter_label": reporter_name,
                "outcome": outcome.outcome,
                "outcome_label": outcome_name,
            },
        )

    for token in (
        deal.owner_confirmation_tokens
        .all()
        .order_by("created_at", "id")
    ):
        created_by = token.created_by
        actor_name = None

        if created_by is not None:
            actor_name = (
                created_by.get_full_name().strip()
                or created_by.email
                or created_by.username
            )

        add_item(
            timestamp=token.created_at,
            event_type=(
                "owner_confirmation_token_issued"
            ),
            title="Owner confirmation issued",
            description=(
                "A single-use owner confirmation token "
                "was issued."
            ),
            actor=actor_name,
            source="owner_confirmation_token",
            source_id=token.id,
            metadata={
                "owner_number": (
                    token.owner.owner_number
                ),
                "mandate_number": (
                    token.mandate.mandate_number
                ),
                "expires_at": (
                    token.expires_at.isoformat()
                ),
            },
        )

        add_item(
            timestamp=token.revoked_at,
            event_type=(
                "owner_confirmation_token_revoked"
            ),
            title="Owner confirmation token revoked",
            description=(
                "A previous unused owner confirmation "
                "token was revoked."
            ),
            source="owner_confirmation_token",
            source_id=token.id,
            metadata={
                "owner_number": (
                    token.owner.owner_number
                ),
            },
        )

        add_item(
            timestamp=token.used_at,
            event_type=(
                "owner_confirmation_token_used"
            ),
            title="Owner confirmation token used",
            description=(
                "The owner confirmation token was "
                "successfully consumed."
            ),
            source="owner_confirmation_token",
            source_id=token.id,
            metadata={
                "owner_number": (
                    token.owner.owner_number
                ),
            },
        )

    represented_event_actions = {
        "owner_confirmation_token_issued",
        "owner_confirmation_submitted",
    }

    terminal_event_actions = {
        "three_party_confirmation_matched",
        "three_party_no_deal_confirmed",
        "three_party_still_deciding",
        "three_party_confirmation_disputed",
    }

    seen_terminal_actions = set()

    for event in (
        deal.events
        .all()
        .order_by("created_at", "id")
    ):
        # Token and owner-outcome records provide richer representations.
        if event.action in represented_event_actions:
            continue

        # Preserve immutable history in the database, but normalize
        # historical duplicate terminal events in the API presentation.
        if event.action in terminal_event_actions:
            if event.action in seen_terminal_actions:
                continue

            seen_terminal_actions.add(
                event.action,
            )

        actor_name = None

        if event.actor is not None:
            actor_name = (
                event.actor.get_full_name().strip()
                or event.actor.email
                or event.actor.username
            )

        add_item(
            timestamp=event.created_at,
            event_type=event.action,
            title=(
                event.action
                .replace("_", " ")
                .title()
            ),
            description=event.notes,
            actor=actor_name,
            source="deal_event",
            source_id=event.id,
            metadata=event.metadata,
        )

    add_item(
        timestamp=deal.agreed_at,
        event_type="deal_agreed",
        title="Deal agreed",
        description=(
            "Customer, partner, and owner confirmations "
            "produced a verified matching transaction."
        ),
        source="deal",
        source_id=deal.id,
        metadata={
            "status": Deal.Status.AGREED,
        },
    )

    add_item(
        timestamp=deal.cancelled_at,
        event_type="deal_cancelled",
        title="Deal cancelled",
        description=deal.cancellation_reason,
        source="deal",
        source_id=deal.id,
        metadata={
            "status": Deal.Status.CANCELLED,
        },
    )

    add_item(
        timestamp=deal.completed_at,
        event_type="deal_completed",
        title="Deal completed",
        description=(
            "The property transaction was completed."
        ),
        source="deal",
        source_id=deal.id,
        metadata={
            "status": Deal.Status.COMPLETED,
        },
    )

    
    timeline.sort(
        key=lambda item: (
            item["timestamp"],
            item["source"],
            item["source_id"] or 0,
        )
    )

    return timeline