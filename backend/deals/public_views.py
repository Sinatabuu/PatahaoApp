from django.core.exceptions import ValidationError
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from .models import (
    Deal,
    DealOutcome,
    OwnerConfirmationToken,
)
from .services import submit_owner_outcome


def _get_token_record(raw_token):
    if not raw_token:
        return None

    token_hash = OwnerConfirmationToken.hash_token(
        raw_token,
    )

    token_record = (
        OwnerConfirmationToken.objects
        .select_related(
            "deal",
            "deal__property",
            "owner",
            "mandate",
        )
        .filter(
            token_hash=token_hash,
        )
        .first()
    )

    if (
        token_record is None
        or not token_record.is_usable
    ):
        return None

    return token_record


def _error_message(error):
    messages = getattr(
        error,
        "messages",
        None,
    )

    if messages:
        return " ".join(
            str(message)
            for message in messages
        )

    return str(error)


def _secure_render(
    request,
    context,
    *,
    status_code=200,
):
    response = render(
        request,
        "deals/owner_confirmation.html",
        context,
        status=status_code,
    )

    response["Cache-Control"] = (
        "max-age=0, no-cache, no-store, "
        "must-revalidate, private"
    )
    response["Pragma"] = "no-cache"
    response["Expires"] = "0"
    response["Referrer-Policy"] = "same-origin"
    response["X-Robots-Tag"] = "noindex, nofollow"

    return response


def _outcome_choices(deal):
    if deal.deal_type == "sale":
        success_outcome = (
            DealOutcome.Outcome.PURCHASED
        )
    else:
        success_outcome = (
            DealOutcome.Outcome.RENTED
        )

    labels = dict(
        DealOutcome.Outcome.choices
    )

    return [
        (
            success_outcome,
            labels[success_outcome],
        ),
        (
            DealOutcome.Outcome.STILL_DECIDING,
            labels[
                DealOutcome.Outcome.STILL_DECIDING
            ],
        ),
        (
            DealOutcome.Outcome.DECLINED,
            "Customer did not proceed",
        ),
    ]


@never_cache
@require_http_methods([
    "GET",
    "POST",
])
def owner_confirmation_page(
    request,
    token,
):
    token_record = _get_token_record(
        token,
    )

    if token_record is None:
        return _secure_render(
            request,
            {
                "invalid_link": True,
            },
            status_code=400,
        )

    deal = token_record.deal
    owner = token_record.owner
    choices = _outcome_choices(
        deal,
    )

    context = {
        "invalid_link": False,
        "submitted": False,
        "deal": deal,
        "owner": owner,
        "expires_at": token_record.expires_at,
        "outcome_choices": choices,
        "selected_outcome": "",
        "notes": "",
        "error_message": "",
    }

    if request.method == "GET":
        return _secure_render(
            request,
            context,
        )

    selected_outcome = (
        request.POST.get(
            "outcome",
            "",
        )
        or ""
    ).strip()

    notes = (
        request.POST.get(
            "notes",
            "",
        )
        or ""
    ).strip()

    context["selected_outcome"] = (
        selected_outcome
    )
    context["notes"] = notes

    allowed_outcomes = {
        value
        for value, _label in choices
    }

    if selected_outcome not in allowed_outcomes:
        context["error_message"] = (
            "Select one property outcome."
        )

        return _secure_render(
            request,
            context,
            status_code=400,
        )

    if len(notes) > 2000:
        context["error_message"] = (
            "Notes cannot exceed 2,000 characters."
        )

        return _secure_render(
            request,
            context,
            status_code=400,
        )

    try:
        submitted_outcome, evaluated_deal = (
            submit_owner_outcome(
                raw_token=token,
                outcome=selected_outcome,
                notes=notes,
            )
        )

    except ValidationError as error:
        context["error_message"] = (
            _error_message(error)
        )

        return _secure_render(
            request,
            context,
            status_code=400,
        )

    context.update(
        {
            "submitted": True,
            "submitted_outcome_label": dict(
                DealOutcome.Outcome.choices
            ).get(
                submitted_outcome.outcome,
                submitted_outcome.outcome,
            ),
            "deal_status_label": dict(
                Deal.Status.choices
            ).get(
                evaluated_deal.status,
                evaluated_deal.status,
            ),
        }
    )

    return _secure_render(
        request,
        context,
    )
