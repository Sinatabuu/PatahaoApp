from django.contrib import admin
from django.utils import timezone

from .models import (
    MandateDocument,
    MandateEvent,
    PropertyMandate,
    PropertyOwner,
)


@admin.register(PropertyOwner)
class PropertyOwnerAdmin(admin.ModelAdmin):
    list_display = [
        "owner_number",
        "legal_name",
        "owner_type",
        "phone_number",
        "verification_status",
        "is_active",
        "verified_at",
    ]

    list_filter = [
        "owner_type",
        "verification_status",
        "is_active",
    ]

    search_fields = [
        "owner_number",
        "legal_name",
        "phone_number",
        "email",
        "national_id_number",
        "company_registration_number",
        "kra_pin",
    ]

    readonly_fields = [
        "owner_number",
        "verified_by",
        "verified_at",
        "created_at",
        "updated_at",
    ]

    actions = [
        "verify_selected_owners",
    ]

    @admin.action(
        description="Verify selected property owners",
    )
    def verify_selected_owners(
        self,
        request,
        queryset,
    ):
        updated = 0

        for owner in queryset:
            owner.verification_status = (
                PropertyOwner.VerificationStatus.VERIFIED
            )
            owner.verified_by = request.user
            owner.verified_at = timezone.now()
            owner.save()

            updated += 1

        self.message_user(
            request,
            f"{updated} property owner(s) verified.",
        )


class MandateDocumentInline(admin.TabularInline):
    model = MandateDocument
    extra = 0

    fields = [
        "document_type",
        "file",
        "status",
        "is_current",
        "file_hash",
        "file_size",
        "uploaded_by",
        "reviewed_by",
        "reviewed_at",
        "rejection_reason",
    ]

    readonly_fields = [
        "file_hash",
        "file_size",
        "uploaded_by",
        "reviewed_by",
        "reviewed_at",
    ]


class MandateEventInline(admin.TabularInline):
    model = MandateEvent
    extra = 0

    fields = [
        "action",
        "notes",
        "actor",
        "metadata",
        "created_at",
    ]

    readonly_fields = [
        "action",
        "notes",
        "actor",
        "metadata",
        "created_at",
    ]

    can_delete = False


@admin.register(PropertyMandate)
class PropertyMandateAdmin(admin.ModelAdmin):
    list_display = [
        "mandate_number",
        "property",
        "owner",
        "partner",
        "status",
        "version",
        "partner_declared",
        "authorization_method",
        "no_cash_acknowledged",
        "anti_circumvention_acknowledged",
        "approved_at",
    ]

    list_filter = [
        "status",
        "partner_declared",
        "authorization_method",
        "no_cash_acknowledged",
        "anti_circumvention_acknowledged",
        "owner_authority_confirmed",
        "effective_date",
        "expiry_date",
    ]

    search_fields = [
        "mandate_number",
        "property__title",
        "owner__legal_name",
        "owner__owner_number",
        "partner__business_name",
        "commission_agreement__agreement_number",
        "declared_by__username",
    ]

    readonly_fields = [
        "mandate_number",
        "partner_declared_at",
        "declared_by",
        "submitted_at",
        "approved_by",
        "approved_at",
        "created_at",
        "updated_at",
    ]

    fieldsets = [
        (
            "Property mandate",
            {
                "fields": [
                    "mandate_number",
                    "property",
                    "owner",
                    "partner",
                    "commission_agreement",
                    "version",
                    "status",
                ]
            },
        ),
        (
            "Partner authority",
            {
                "fields": [
                    "authorization_method",
                    "authorization_notes",
                    "owner_authority_confirmed",
                ]
            },
        ),
        (
            "Pata Hao terms",
            {
                "fields": [
                    "no_cash_acknowledged",
                    "anti_circumvention_acknowledged",
                    "partner_declared",
                    "partner_declared_at",
                    "declaration_version",
                    "declared_by",
                ]
            },
        ),
        (
            "Validity",
            {
                "fields": [
                    "effective_date",
                    "expiry_date",
                    "protection_period_days",
                ]
            },
        ),
        (
            "Review",
            {
                "fields": [
                    "submitted_at",
                    "approved_by",
                    "approved_at",
                    "rejection_reason",
                ]
            },
        ),
        (
            "Audit",
            {
                "fields": [
                    "created_by",
                    "created_at",
                    "updated_at",
                ]
            },
        ),
    ]

    inlines = [
        MandateDocumentInline,
        MandateEventInline,
    ]

    actions = [
        "submit_selected_for_review",
        "approve_selected_mandates",
    ]

    @admin.action(
        description="Submit selected mandates for review",
    )
    def submit_selected_for_review(
        self,
        request,
        queryset,
    ):
        updated = 0
        failed = []

        for mandate in queryset:
            try:
                mandate.submit_for_review()
                mandate.save()

                MandateEvent.objects.create(
                    mandate=mandate,
                    action="submitted_for_review",
                    actor=request.user,
                    notes=(
                        "Digital property mandate submitted "
                        "for Pata Hao review."
                    ),
                    metadata={
                        "declaration_version": (
                            mandate.declaration_version
                        ),
                    },
                )

                updated += 1

            except Exception as error:
                failed.append(
                    f"{mandate.mandate_number}: {error}"
                )

        if updated:
            self.message_user(
                request,
                f"{updated} mandate(s) submitted for review.",
            )

        for message in failed:
            self.message_user(
                request,
                message,
                level="error",
            )

    @admin.action(
        description="Approve selected mandates",
    )
    def approve_selected_mandates(
        self,
        request,
        queryset,
    ):
        approved = 0
        failed = []

        for mandate in queryset:
            try:
                mandate.approve(
                    approved_by=request.user,
                )
                mandate.save()

                MandateEvent.objects.create(
                    mandate=mandate,
                    action="approved",
                    actor=request.user,
                    notes=(
                        "Digital property mandate approved "
                        "by Pata Hao."
                    ),
                    metadata={
                        "declaration_version": (
                            mandate.declaration_version
                        ),
                        "commission_agreement_id": (
                            mandate.commission_agreement_id
                        ),
                    },
                )

                approved += 1

            except Exception as error:
                failed.append(
                    f"{mandate.mandate_number}: {error}"
                )

        if approved:
            self.message_user(
                request,
                f"{approved} mandate(s) approved.",
            )

        for message in failed:
            self.message_user(
                request,
                message,
                level="error",
            )


@admin.register(MandateDocument)
class MandateDocumentAdmin(admin.ModelAdmin):
    list_display = [
        "mandate",
        "document_type",
        "status",
        "is_current",
        "original_filename",
        "file_hash",
        "uploaded_at",
        "reviewed_at",
    ]

    list_filter = [
        "document_type",
        "status",
        "is_current",
    ]

    search_fields = [
        "mandate__mandate_number",
        "mandate__property__title",
        "mandate__owner__legal_name",
        "original_filename",
        "file_hash",
    ]

    readonly_fields = [
        "file_hash",
        "file_size",
        "uploaded_at",
        "reviewed_by",
        "reviewed_at",
    ]

    actions = [
        "approve_selected_documents",
    ]

    @admin.action(
        description="Approve selected mandate documents",
    )
    def approve_selected_documents(
        self,
        request,
        queryset,
    ):
        approved = 0

        for document in queryset:
            document.approve(
                reviewed_by=request.user,
            )

            MandateEvent.objects.create(
                mandate=document.mandate,
                action="document_approved",
                actor=request.user,
                notes=(
                    f"{document.get_document_type_display()} "
                    "approved as supporting evidence."
                ),
                metadata={
                    "document_id": document.id,
                    "file_hash": document.file_hash,
                },
            )

            approved += 1

        self.message_user(
            request,
            f"{approved} document(s) approved.",
        )


@admin.register(MandateEvent)
class MandateEventAdmin(admin.ModelAdmin):
    list_display = [
        "mandate",
        "action",
        "actor",
        "created_at",
    ]

    list_filter = [
        "action",
        "created_at",
    ]

    search_fields = [
        "mandate__mandate_number",
        "action",
        "notes",
    ]

    readonly_fields = [
        "mandate",
        "action",
        "notes",
        "actor",
        "metadata",
        "created_at",
    ]

    def has_add_permission(
        self,
        request,
    ):
        return False

    def has_delete_permission(
        self,
        request,
        obj=None,
    ):
        return False
