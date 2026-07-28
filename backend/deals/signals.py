from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import DealOutcome
from .services import evaluate_deal_outcomes
from viewings.models import Viewing
from django.db.models.signals import post_save


@receiver(
    post_save,
    sender=DealOutcome,
)
def evaluate_outcomes_after_save(
    sender,
    instance,
    created,
    **kwargs,
):
    """
    Re-evaluate the deal whenever an outcome is submitted
    or corrected.
    """

    evaluate_deal_outcomes(
        instance.deal_id,
    )


@receiver(
    post_delete,
    sender=DealOutcome,
)
def evaluate_outcomes_after_delete(
    sender,
    instance,
    **kwargs,
):
    """
    Return the deal to pending confirmation if one side's
    report is removed.
    """

    evaluate_deal_outcomes(
        instance.deal_id,
    )
@receiver(post_save, sender=Viewing)
def create_deal_when_viewing_completed(
    sender,
    instance,
    created,
    **kwargs,
):
    """
    Automatically create a Deal when
    a viewing is completed.
    """

    if instance.status != Viewing.Status.COMPLETED:
        return

    from .services import create_deal_from_viewing

    create_deal_from_viewing(instance)    