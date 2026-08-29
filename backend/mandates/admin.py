from django import forms
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.http import Http404
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils import timezone

from .models import (
    MandateDocument,
    MandateEvent,
    PropertyMandate,
    PropertyOwner,
)
from .services import (
    reject_mandate_document,
    supersede_mandate_document,
)


class SupersedeMandateDocumentForm(forms.Form):
    replacement_file = forms.FileField(
        label="Replacement evidence file",
        help_text=(
            "The existing evidence will remain permanently preserved. "
            "This upload becomes the new current document and must be "
            "reviewed again before it can satisfy publication rules."
        ),
    )

    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "rows": 4,
            }
        ),
        help_text="Optional reason or context for replacing the evidence.",
    )


class RejectMandateDocumentForm(forms.Form):
    reason = forms.CharField(
        label="Rejection reason",
        widget=forms.Textarea(
            attrs={
                "rows": 5,
            }
        ),
        help_text=(
            "Explain specifically why this evidence cannot be accepted. "
            "The reason becomes part of the immutable mandate audit trail."
        ),
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

    can_delete = False

    def has_add_permission(
        self,
        request,
        obj=None,
    ):
        return False


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

    def get_urls(self):
        urls = super().get_urls()

        custom_urls = [
            path(
                "<path:object_id>/supersede/",
                self.admin_site.admin_view(
                    self.supersede_document_view,
                ),
                name=(
                    "mandates_mandatedocument_supersede"
                ),
            ),
            path(
                "<path:object_id>/reject/",
                self.admin_site.admin_view(
                    self.reject_document_view,
                ),
                name=(
                    "mandates_mandatedocument_reject"
                ),
            ),
        ]

        return custom_urls + urls

    def supersede_document_view(
        self,
        request,
        object_id,
    ):
        document = self.get_object(
            request,
            object_id,
        )

        if document is None:
            raise Http404(
                "Mandate document not found."
            )

        if not self.has_change_permission(
            request,
            document,
        ):
            raise PermissionDenied

        change_url = reverse(
            "admin:mandates_mandatedocument_change",
            args=[
                document.pk,
            ],
        )

        if not document.is_current:
            self.message_user(
                request,
                (
                    "This evidence is historical and is no longer "
                    "current. Only current evidence can be superseded."
                ),
                level=messages.ERROR,
            )

            return redirect(
                change_url,
            )

        if request.method == "POST":
            form = SupersedeMandateDocumentForm(
                request.POST,
                request.FILES,
            )

            if form.is_valid():
                try:
                    new_document = supersede_mandate_document(
                        document_id=document.pk,
                        actor=request.user,
                        file=form.cleaned_data[
                            "replacement_file"
                        ],
                        notes=form.cleaned_data[
                            "notes"
                        ],
                    )

                except ValidationError as error:
                    form.add_error(
                        None,
                        error,
                    )

                else:
                    self.message_user(
                        request,
                        (
                            "Evidence superseded successfully. "
                            "The replacement is now current but "
                            "must be reviewed and approved."
                        ),
                        level=messages.SUCCESS,
                    )

                    return redirect(
                        reverse(
                            (
                                "admin:"
                                "mandates_mandatedocument_change"
                            ),
                            args=[
                                new_document.pk,
                            ],
                        )
                    )

        else:
            form = SupersedeMandateDocumentForm()

        context = {
            **self.admin_site.each_context(
                request,
            ),
            "title": "Supersede mandate evidence",
            "opts": self.model._meta,
            "original": document,
            "document": document,
            "form": form,
            "media": self.media + form.media,
        }

        return TemplateResponse(
            request,
            (
                "admin/mandates/"
                "mandatedocument/supersede.html"
            ),
            context,
        )

    def reject_document_view(
        self,
        request,
        object_id,
    ):
        document = self.get_object(
            request,
            object_id,
        )

        if document is None:
            raise Http404(
                "Mandate document not found."
            )

        if not self.has_change_permission(
            request,
            document,
        ):
            raise PermissionDenied

        change_url = reverse(
            "admin:mandates_mandatedocument_change",
            args=[
                document.pk,
            ],
        )

        if not document.is_current:
            self.message_user(
                request,
                (
                    "This evidence is historical and cannot be rejected. "
                    "Only current evidence may be reviewed."
                ),
                level=messages.ERROR,
            )

            return redirect(
                change_url,
            )

        if document.status == MandateDocument.Status.REJECTED:
            self.message_user(
                request,
                "This evidence has already been rejected.",
                level=messages.INFO,
            )

            return redirect(
                change_url,
            )

        if request.method == "POST":
            form = RejectMandateDocumentForm(
                request.POST,
            )

            if form.is_valid():
                try:
                    reject_mandate_document(
                        document_id=document.pk,
                        actor=request.user,
                        reason=form.cleaned_data[
                            "reason"
                        ],
                    )

                except ValidationError as error:
                    form.add_error(
                        None,
                        error,
                    )

                else:
                    self.message_user(
                        request,
                        (
                            "Evidence rejected successfully. "
                            "The reason was added to the immutable "
                            "mandate audit trail."
                        ),
                        level=messages.SUCCESS,
                    )

                    return redirect(
                        change_url,
                    )

        else:
            form = RejectMandateDocumentForm()

        context = {
            **self.admin_site.each_context(
                request,
            ),
            "title": "Reject mandate evidence",
            "opts": self.model._meta,
            "original": document,
            "document": document,
            "form": form,
            "media": self.media + form.media,
        }

        return TemplateResponse(
            request,
            (
                "admin/mandates/"
                "mandatedocument/reject.html"
            ),
            context,
        )

    def get_readonly_fields(
        self,
        request,
        obj=None,
    ):
        readonly = [
            "file_hash",
            "file_size",
            "uploaded_at",
            "reviewed_by",
            "reviewed_at",
            "status",
            "is_current",
            "rejection_reason",
            "supersede_evidence",
            "reject_evidence",
        ]

        if obj is not None:
            readonly.extend(
                [
                    "mandate",
                    "document_type",
                    "file",
                    "original_filename",
                    "uploaded_by",
                ]
            )

        return readonly

    @admin.display(
        description="Evidence replacement",
    )
    def supersede_evidence(
        self,
        obj,
    ):
        if obj is None:
            return "Available after upload."

        if not obj.is_current:
            return "Historical evidence — replacement not permitted."

        url = reverse(
            "admin:mandates_mandatedocument_supersede",
            args=[
                obj.pk,
            ],
        )

        from django.utils.html import format_html

        return format_html(
            '<a class="button" href="{}">Supersede evidence</a>',
            url,
        )

    @admin.display(
        description="Evidence rejection",
    )
    def reject_evidence(
        self,
        obj,
    ):
        if obj is None:
            return "Available after upload."

        if not obj.is_current:
            return "Historical evidence — rejection not permitted."

        if obj.status == MandateDocument.Status.REJECTED:
            return "Already rejected — reason recorded."

        url = reverse(
            "admin:mandates_mandatedocument_reject",
            args=[
                obj.pk,
            ],
        )

        from django.utils.html import format_html

        return format_html(
            '<a class="button" href="{}">Reject evidence</a>',
            url,
        )

    def save_model(
        self,
        request,
        obj,
        form,
        change,
    ):
        if not change and obj.uploaded_by_id is None:
            obj.uploaded_by = request.user

        super().save_model(
            request,
            obj,
            form,
            change,
        )

    @admin.action(
        description="Approve selected mandate documents",
    )
    def approve_selected_documents(
        self,
        request,
        queryset,
    ):
        approved = 0
        skipped = 0
        already_approved = 0

        for selected_document in queryset:
            with transaction.atomic():
                document = (
                    MandateDocument.objects
                    .select_for_update()
                    .select_related("mandate")
                    .get(pk=selected_document.pk)
                )

                if not document.is_current:
                    skipped += 1
                    continue

                if document.status == MandateDocument.Status.APPROVED:
                    already_approved += 1
                    continue

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
                        "is_current": document.is_current,
                    },
                )

            approved += 1

        if approved:
            self.message_user(
                request,
                f"{approved} document(s) approved.",
                level=messages.SUCCESS,
            )

        if skipped:
            self.message_user(
                request,
                (
                    f"{skipped} historical document(s) skipped. "
                    "Only current evidence may be approved."
                ),
                level=messages.WARNING,
            )

        if already_approved:
            self.message_user(
                request,
                (
                    f"{already_approved} already-approved document(s) "
                    "skipped. No duplicate approval event was created."
                ),
                level=messages.INFO,
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
