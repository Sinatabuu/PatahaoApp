from django.contrib import admin

from .models import (
    CommissionInvoice,
    CommissionReceipt,
    Deal,
    DealOutcome,
)


class DealOutcomeInline(admin.TabularInline):
    model = DealOutcome
    extra = 0
    readonly_fields = [
        "created_at",
    ]


@admin.register(Deal)
class DealAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "property",
        "customer",
        "partner",
        "status",
        "customer_confirmed",
        "partner_confirmed",
        "commission_amount",
        "commission_invoice_status",
        "commission_received",
        "commission_outstanding",
        "completed_at",
        "closed_at",
        "created_at",
    ]

    list_filter = [
        "status",
        "customer_confirmed",
        "partner_confirmed",
        "property__listing_type",
        "created_at",
    ]

    search_fields = [
        "property__title",
        "customer__username",
        "customer__email",
    ]

    readonly_fields = [
        "commission_invoice_status",
        "commission_received",
        "commission_outstanding",
        "completed_at",
        "closed_at",
        "created_at",
        "updated_at",
    ]

    autocomplete_fields = [
        "customer",
        "partner",
        "property",
        "viewing",
    ]

    inlines = [
        DealOutcomeInline,
    ]

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related(
                "property",
                "customer",
                "partner",
                "commission_invoice",
            )
            .prefetch_related(
                "commission_invoice__receipts",
            )
        )

    @admin.display(
        description="Invoice status",
    )
    def commission_invoice_status(self, obj):
        try:
            return obj.commission_invoice.get_status_display()
        except CommissionInvoice.DoesNotExist:
            return "—"

    @admin.display(
        description="Commission received",
    )
    def commission_received(self, obj):
        try:
            invoice = obj.commission_invoice
        except CommissionInvoice.DoesNotExist:
            return "—"

        total = sum(
            (
                receipt.amount
                for receipt in invoice.receipts.all()
            ),
            0,
        )

        return f"{invoice.currency} {total:,.2f}"

    @admin.display(
        description="Commission outstanding",
    )
    def commission_outstanding(self, obj):
        try:
            invoice = obj.commission_invoice
        except CommissionInvoice.DoesNotExist:
            return "—"

        received = sum(
            (
                receipt.amount
                for receipt in invoice.receipts.all()
            ),
            0,
        )

        outstanding = invoice.amount - received

        return f"{invoice.currency} {outstanding:,.2f}"


@admin.register(DealOutcome)
class DealOutcomeAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "deal",
        "reporter",
        "outcome",
        "created_at",
    ]

    list_filter = [
        "reporter",
        "outcome",
        "created_at",
    ]

    search_fields = [
        "deal__property__title",
        "deal__customer__username",
        "notes",
    ]

    readonly_fields = [
        "created_at",
    ]

    autocomplete_fields = [
        "deal",
    ]

@admin.register(CommissionInvoice)
class CommissionInvoiceAdmin(admin.ModelAdmin):
    """
    Read-only administrative view of commission receivables.
    """

    list_display = [
        "invoice_number",
        "deal",
        "owner_legal_name_snapshot",
        "amount",
        "currency",
        "status",
        "issued_at",
        "paid_at",
    ]

    list_filter = [
        "status",
        "currency",
        "issued_at",
        "paid_at",
    ]

    search_fields = [
        "invoice_number",
        "owner_number_snapshot",
        "owner_legal_name_snapshot",
        "agreement_number_snapshot",
        "deal__property__title",
    ]

    readonly_fields = [
        "deal",
        "settlement",
        "agreement",
        "owner",
        "invoice_number",
        "owner_number_snapshot",
        "owner_legal_name_snapshot",
        "owner_phone_number_snapshot",
        "owner_email_snapshot",
        "agreement_number_snapshot",
        "amount",
        "currency",
        "status",
        "issued_at",
        "paid_at",
        "created_by",
        "created_at",
        "updated_at",
    ]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return True

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(CommissionReceipt)
class CommissionReceiptAdmin(admin.ModelAdmin):
    """
    Read-only administrative view of immutable commission
    receipt evidence.
    """

    list_display = [
        "id",
        "invoice",
        "amount",
        "currency",
        "payment_method",
        "payment_reference",
        "received_at",
        "recorded_by",
    ]

    list_filter = [
        "payment_method",
        "currency",
        "received_at",
        "created_at",
    ]

    search_fields = [
        "payment_reference",
        "invoice__invoice_number",
        "invoice__owner_legal_name_snapshot",
        "invoice__deal__property__title",
    ]

    readonly_fields = [
        "invoice",
        "amount",
        "currency",
        "payment_method",
        "payment_reference",
        "received_at",
        "notes",
        "recorded_by",
        "created_at",
    ]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return True

    def has_delete_permission(self, request, obj=None):
        return False
