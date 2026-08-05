from django.db.models.signals import post_save
from django.dispatch import receiver

from viewings.models import Viewing


@receiver(post_save, sender=Viewing)
def create_deal_when_viewing_completed(
    sender,
    instance,
    created,
    **kwargs,
):
    """
    Automatically create a deal when a viewing is completed.
    """

    if instance.status != Viewing.Status.COMPLETED:
        return

    from .services import create_deal_from_viewing

    create_deal_from_viewing(instance)