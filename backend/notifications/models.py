from django.conf import settings
from django.db import models


class Notification(models.Model):
    TYPE_VIEWING = "viewing"
    TYPE_PAYMENT = "payment"
    TYPE_DEAL = "deal"
    TYPE_SYSTEM = "system"

    TYPE_CHOICES = [
        (TYPE_VIEWING, "Viewing"),
        (TYPE_PAYMENT, "Payment"),
        (TYPE_DEAL, "Deal"),
        (TYPE_SYSTEM, "System"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )

    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(
        max_length=30,
        choices=TYPE_CHOICES,
        default=TYPE_SYSTEM,
    )

    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
