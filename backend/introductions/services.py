from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from mandates.models import PropertyMandate

from .models import (
    IntroductionEvent,
    ProtectedIntroduction,
)


@transaction.atomic
def create_property_introduction_certificate(
    *,
    viewing,
    actor=None,
):
    if viewing.status != viewing.Status.COMPLETED:
        raise ValidationError(
            "A PIC can only be created after a completed viewing."
        )

    if not viewing.payment_reference:
        raise ValidationError(
            "A verified viewing payment reference is required."
        )

    property_obj = viewing.property
    partner = property_obj.partner

    mandate = (
        PropertyMandate.objects
        .select_related(
            "owner",
            "commission_agreement",
        )
        .filter(
            property=property_obj,
            status=PropertyMandate.Status.APPROVED,
        )
        .order_by("-version", "-approved_at")
        .first()
    )

    if mandate is None or not mandate.is_currently_valid:
        raise ValidationError(
            "The property does not have a valid approved mandate."
        )

    agreement = mandate.commission_agreement

    existing = ProtectedIntroduction.objects.filter(
        customer=viewing.customer,
        property=property_obj,
        status__in=[
            ProtectedIntroduction.Status.ACTIVE,
            ProtectedIntroduction.Status.CONVERTED_TO_DEAL,
            ProtectedIntroduction.Status.DISPUTED,
        ],
    ).first()

    if existing is not None:
        return existing, False

    protected_from = timezone.now()
    protected_until = protected_from + timedelta(
        days=mandate.protection_period_days,
    )

    customer_name = viewing.customer.get_full_name().strip()

    introduction = ProtectedIntroduction.objects.create(
        customer=viewing.customer,
        property=property_obj,
        partner=partner,
        viewing=viewing,
        mandate=mandate,
        commission_agreement=agreement,
        protected_from=protected_from,
        protected_until=protected_until,
        protection_period_days=mandate.protection_period_days,
        customer_name_snapshot=(
            customer_name
            or viewing.customer.get_username()
        ),
        property_title_snapshot=property_obj.title,
        listing_type_snapshot=property_obj.listing_type,
        property_price_snapshot=property_obj.price,
        owner_name_snapshot=mandate.owner.legal_name,
        partner_name_snapshot=str(partner),
        mandate_number_snapshot=mandate.mandate_number,
        commission_agreement_number_snapshot=(
            agreement.agreement_number
        ),
        commission_method_snapshot=agreement.commission_method,
        commission_rate_snapshot=agreement.commission_rate,
        fixed_commission_snapshot=(
            agreement.fixed_commission_amount
        ),
        expected_commission_snapshot=(
            agreement.expected_total_commission
        ),
        currency_snapshot=agreement.currency,
        viewing_fee_snapshot=viewing.fee_amount,
        viewing_payment_reference=viewing.payment_reference,
    )

    IntroductionEvent.objects.create(
        introduction=introduction,
        action="certificate_created",
        actor=actor,
        notes=(
            "Property Introduction Certificate created "
            "from a completed paid viewing."
        ),
        metadata={
            "viewing_id": viewing.id,
            "property_id": property_obj.id,
            "customer_id": viewing.customer_id,
            "partner_id": partner.id,
            "mandate_id": mandate.id,
            "commission_agreement_id": agreement.id,
        },
    )

    return introduction, True
