from django.contrib import admin
from .models import Deal, Payment


@admin.register(Deal)
class DealAdmin(admin.ModelAdmin):
    list_display = (
        "property",
        "customer",
        "partner",
        "deal_type",
        "amount",
        "commission_rate",
        "commission_amount",
        "status",
        "created_at",
    )

    list_filter = ("deal_type", "status", "partner")
    search_fields = ("property__title", "customer__email", "partner__business_name")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "deal",
        "payer",
        "amount",
        "payment_method",
        "payment_type",
        "status",
        "transaction_reference",
        "created_at",
    )

    list_filter = ("payment_method", "payment_type", "status")
    search_fields = ("transaction_reference", "receipt_number", "payer__email")