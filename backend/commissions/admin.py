from django.contrib import admin, messages
from django.core.exceptions import ValidationError

from .models import (
    CommissionAgreement,
    CommissionPlan,
    CommissionSettlement,
    CommissionSettlementParticipant,
)


@admin.register(CommissionPlan)
class CommissionPlanAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "partner_share_rate",
        "minimum_completed_transactions",
        "is_active",
        "updated_at",
    ]

    list_filter = [
        "is_active",
    ]

    search_fields = [
        "name",
    ]

    ordering = [
        "partner_share_rate",
    ]


@admin.register(CommissionAgreement)
class CommissionAgreementAdmin(admin.ModelAdmin):
    readonly_fields = [
        "agreement_number",
        "expected_total_commission",
        "status",
        "owner_confirmed",
        "owner_confirmed_at",
        "is_verified",
        "verified_by",
        "verified_at",
        "is_locked",
        "locked_at",
        "created_by",
        "created_at",
        "updated_at",
    ]

    list_filter = [
        "commission_method",
        "status",
        "owner_confirmed",
        "is_verified",
        "is_locked",
        "currency",
    ]

    search_fields = [
        "agreement_number",
        "property__title",
        "owner_name",
        "owner_phone_number",
    ]

    raw_id_fields = [
        "property",
    ]

    actions = [
        "submit_selected_for_owner_confirmation",
        "confirm_selected_by_owner",
        "verify_selected_agreements",
        "lock_selected_agreements",
    ]

    def save_model(
        self,
        request,
        obj,
        form,
        change,
    ):
        if not obj.pk:
            obj.created_by = request.user
            obj.status = CommissionAgreement.Status.DRAFT
            obj.owner_confirmed = False
            obj.owner_confirmed_at = None
            obj.is_verified = False
            obj.verified_by = None
            obj.verified_at = None
            obj.is_locked = False
            obj.locked_at = None

        super().save_model(
            request,
            obj,
            form,
            change,
        )
    @admin.display(
        boolean=True,
        description="Publish ready",
    )
    def publish_ready(self, obj):
        return obj.is_publish_ready()

    @admin.action(
        description="Submit selected agreements for owner confirmation"
    )
    def submit_selected_for_owner_confirmation(
        self,
        request,
        queryset,
    ):
        success_count = 0

        for agreement in queryset:
            try:
                agreement.submit_for_owner_confirmation()
                agreement.save()
                success_count += 1

            except ValidationError as error:
                self.message_user(
                    request,
                    (
                        f"{agreement.agreement_number} could not be "
                        f"submitted: {error}"
                    ),
                    level=messages.ERROR,
                )

        if success_count:
            self.message_user(
                request,
                (
                    f"{success_count} agreement(s) submitted for "
                    "owner confirmation."
                ),
                level=messages.SUCCESS,
            )

    @admin.action(
        description="Record owner confirmation for selected agreements"
    )
    def confirm_selected_by_owner(
        self,
        request,
        queryset,
    ):
        success_count = 0

        for agreement in queryset:
            try:
                agreement.confirm_owner()
                agreement.save()
                success_count += 1

            except ValidationError as error:
                self.message_user(
                    request,
                    (
                        f"{agreement.agreement_number} could not be "
                        f"confirmed: {error}"
                    ),
                    level=messages.ERROR,
                )

        if success_count:
            self.message_user(
                request,
                (
                    "Owner confirmation recorded for "
                    f"{success_count} agreement(s)."
                ),
                level=messages.SUCCESS,
            )

    @admin.action(
        description="Verify selected commission agreements"
    )
    def verify_selected_agreements(
        self,
        request,
        queryset,
    ):
        success_count = 0

        for agreement in queryset:
            try:
                agreement.verify(request.user)
                agreement.save()
                success_count += 1

            except ValidationError as error:
                self.message_user(
                    request,
                    (
                        f"{agreement.agreement_number} could not be "
                        f"verified: {error}"
                    ),
                    level=messages.ERROR,
                )

        if success_count:
            self.message_user(
                request,
                (
                    f"{success_count} agreement(s) verified "
                    "successfully."
                ),
                level=messages.SUCCESS,
            )

    @admin.action(
        description="Lock selected commission agreements"
    )
    def lock_selected_agreements(
        self,
        request,
        queryset,
    ):
        success_count = 0

        for agreement in queryset:
            try:
                agreement.lock()
                agreement.save()
                success_count += 1

            except ValidationError as error:
                self.message_user(
                    request,
                    (
                        f"{agreement.agreement_number} could not be "
                        f"locked: {error}"
                    ),
                    level=messages.ERROR,
                )

        if success_count:
            self.message_user(
                request,
                (
                    f"{success_count} agreement(s) locked "
                    "successfully."
                ),
                level=messages.SUCCESS,
            )


class CommissionSettlementParticipantInline(admin.TabularInline):
    model = CommissionSettlementParticipant

    extra = 1

    fields = [
        "participant_type",
        "partner",
        "participant_name",
        "amount",
        "percentage_of_total",
        "is_platform_share",
        "notes",
    ]

    readonly_fields = [
        "percentage_of_total",
    ]

    raw_id_fields = [
        "partner",
    ]


@admin.register(CommissionSettlement)
class CommissionSettlementAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "deal",
        "agreement",
        "gross_commission_amount",
        "allocated_amount",
        "unallocated_amount",
        "currency",
        "status",
        "approved_by",
        "created_at",
    ]

    list_filter = [
        "status",
        "currency",
        "created_at",
    ]

    search_fields = [
        "agreement__agreement_number",
        "agreement__owner_name",
        "deal__property__title",
    ]

    readonly_fields = [
        "allocated_amount",
        "unallocated_amount",
        "created_by",
        "approved_by",
        "approved_at",
        "created_at",
        "updated_at",
    ]

    raw_id_fields = [
        "deal",
        "agreement",
        
    ]

    inlines = [
        CommissionSettlementParticipantInline,
    ]

    actions = [
        "approve_selected_settlements",
    ]

    def save_model(
        self,
        request,
        obj,
        form,
        change,
    ):
        if not obj.pk:
            obj.created_by = request.user

        super().save_model(
            request,
            obj,
            form,
            change,
        )

    @admin.action(
        description="Approve selected commission settlements"
    )
    def approve_selected_settlements(
        self,
        request,
        queryset,
    ):
        approved_count = 0

        for settlement in queryset:
            try:
                settlement.approve(request.user)
                settlement.save()
                approved_count += 1

            except ValidationError as error:
                self.message_user(
                    request,
                    (
                        f"Settlement #{settlement.pk} was not "
                        f"approved: {error}"
                    ),
                    level=messages.ERROR,
                )

        if approved_count:
            self.message_user(
                request,
                (
                    f"{approved_count} settlement(s) approved "
                    "successfully."
                ),
                level=messages.SUCCESS,
            )


@admin.register(CommissionSettlementParticipant)
class CommissionSettlementParticipantAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "settlement",
        "participant_type",
        "partner",
        "participant_name",
        "amount",
        "percentage_of_total",
        "is_platform_share",
        "created_at",
    ]

    list_filter = [
        "participant_type",
        "is_platform_share",
        "created_at",
    ]

    search_fields = [
        "participant_name",
        "settlement__agreement__agreement_number",
        "settlement__deal__property__title",
    ]

    raw_id_fields = [
        "settlement",
        "partner",
    ]

    readonly_fields = [
        "percentage_of_total",
        "created_at",
        "updated_at",
    ]