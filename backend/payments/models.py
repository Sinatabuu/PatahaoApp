from django.conf import settings
from django.db import models


class Deal(models.Model):
    DEAL_RENT = "rent"
    DEAL_SALE = "sale"

    DEAL_TYPE_CHOICES = [
        (DEAL_RENT, "Rent"),
        (DEAL_SALE, "Sale"),
    ]

    STATUS_LEAD = "lead"
    STATUS_NEGOTIATING = "negotiating"
    STATUS_PAYMENT_PENDING = "payment_pending"
    STATUS_PAID = "paid"
    STATUS_COMPLETED = "completed"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (STATUS_LEAD, "Lead"),
        (STATUS_NEGOTIATING, "Negotiating"),
        (STATUS_PAYMENT_PENDING, "Payment Pending"),
        (STATUS_PAID, "Paid"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    property = models.ForeignKey(
        "properties.Property",
        on_delete=models.CASCADE,
        related_name="deals",
    )

    viewing = models.ForeignKey(
        "viewings.Viewing",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deals",
    )

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="deals",
    )

    partner = models.ForeignKey(
        "partners.Partner",
        on_delete=models.CASCADE,
        related_name="deals",
    )

    deal_type = models.CharField(max_length=20, choices=DEAL_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=14, decimal_places=2)

    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=10.00)
    commission_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default=STATUS_LEAD)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def calculate_commission(self):
        return (self.amount * self.commission_rate) / 100

    def save(self, *args, **kwargs):
        self.commission_amount = self.calculate_commission()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.property.title} - {self.customer}"


class Payment(models.Model):
    METHOD_MPESA = "mpesa"
    METHOD_AIRTEL = "airtel"

    METHOD_CHOICES = [
        (METHOD_MPESA, "M-Pesa"),
        (METHOD_AIRTEL, "Airtel Money"),
    ]

    TYPE_COMMISSION = "commission"
    TYPE_RESERVATION = "reservation"
    TYPE_SERVICE_FEE = "service_fee"

    TYPE_CHOICES = [
        (TYPE_COMMISSION, "Commission"),
        (TYPE_RESERVATION, "Reservation"),
        (TYPE_SERVICE_FEE, "Service Fee"),
    ]

    STATUS_PENDING = "pending"
    STATUS_PAID = "paid"
    STATUS_FAILED = "failed"
    STATUS_REFUNDED = "refunded"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_PAID, "Paid"),
        (STATUS_FAILED, "Failed"),
        (STATUS_REFUNDED, "Refunded"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    deal = models.ForeignKey(
        Deal,
        on_delete=models.CASCADE,
        related_name="payments",
    )

    payer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="payments",
    )

    amount = models.DecimalField(max_digits=14, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=METHOD_CHOICES)
    payment_type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default=STATUS_PENDING)

    transaction_reference = models.CharField(max_length=100, blank=True)
    receipt_number = models.CharField(max_length=100, blank=True)

    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.payment_method} {self.amount} - {self.status}"