from django.contrib import admin, messages
from django.utils import timezone
from mandates.services import evaluate_property_publication
from core.models import ActivityLog

from .models import (
    Property,
    PropertyPartner,
    PropertyPhoto,
    PropertyVideo,
)
from .service import PublishingEngine
from django.core.exceptions import ValidationError

class PropertyPhotoInline(admin.TabularInline):
    model = PropertyPhoto
    extra = 1


class PropertyVideoInline(admin.TabularInline):
    model = PropertyVideo
    extra = 1

@admin.action(
    description="Approve selected partner participation requests"
)
def approve_property_participations(
    modeladmin,
    request,
    queryset,
):
    approved_count = 0
    skipped_count = 0

    for participation in queryset.select_related(
        "property",
        "partner",
    ):
        if participation.status != PropertyPartner.Status.PENDING:
            skipped_count += 1
            continue

        participation.status = PropertyPartner.Status.ACTIVE
        participation.verified_at = timezone.now()
        participation.save(
            update_fields=[
                "status",
                "verified_at",
                "updated_at",
            ]
        )

        ActivityLog.objects.create(
            actor=request.user,
            action="property_participation_approved",
            entity_type="PropertyPartner",
            entity_id=str(participation.id),
            description=(
                f"Approved {participation.partner} "
                f"to participate in "
                f"{participation.property.title}"
            ),
        )

        approved_count += 1

    if approved_count:
        modeladmin.message_user(
            request,
            (
                f"{approved_count} participation request(s) "
                "approved."
            ),
            level=messages.SUCCESS,
        )

    if skipped_count:
        modeladmin.message_user(
            request,
            (
                f"{skipped_count} record(s) skipped because "
                "they were not pending."
            ),
            level=messages.WARNING,
        )


@admin.action(
    description="Reject/remove selected participation requests"
)
def remove_property_participations(
    modeladmin,
    request,
    queryset,
):
    removed_count = 0
    skipped_count = 0

    for participation in queryset.select_related(
        "property",
        "partner",
    ):
        if participation.status not in {
            PropertyPartner.Status.PENDING,
            PropertyPartner.Status.ACTIVE,
            PropertyPartner.Status.SUSPENDED,
        }:
            skipped_count += 1
            continue

        participation.status = PropertyPartner.Status.REMOVED
        participation.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        ActivityLog.objects.create(
            actor=request.user,
            action="property_participation_removed",
            entity_type="PropertyPartner",
            entity_id=str(participation.id),
            description=(
                f"Removed {participation.partner} "
                f"from participation in "
                f"{participation.property.title}"
            ),
        )

        removed_count += 1

    if removed_count:
        modeladmin.message_user(
            request,
            (
                f"{removed_count} participation record(s) "
                "removed."
            ),
            level=messages.SUCCESS,
        )

    if skipped_count:
        modeladmin.message_user(
            request,
            (
                f"{skipped_count} record(s) skipped."
            ),
            level=messages.WARNING,
        )


@admin.action(
    description="Suspend selected active participations"
)
def suspend_property_participations(
    modeladmin,
    request,
    queryset,
):
    suspended_count = 0
    skipped_count = 0

    for participation in queryset.select_related(
        "property",
        "partner",
    ):
        if participation.status != PropertyPartner.Status.ACTIVE:
            skipped_count += 1
            continue

        participation.status = PropertyPartner.Status.SUSPENDED
        participation.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        ActivityLog.objects.create(
            actor=request.user,
            action="property_participation_suspended",
            entity_type="PropertyPartner",
            entity_id=str(participation.id),
            description=(
                f"Suspended {participation.partner} "
                f"from participation in "
                f"{participation.property.title}"
            ),
        )

        suspended_count += 1

    if suspended_count:
        modeladmin.message_user(
            request,
            (
                f"{suspended_count} participation record(s) "
                "suspended."
            ),
            level=messages.SUCCESS,
        )

    if skipped_count:
        modeladmin.message_user(
            request,
            (
                f"{skipped_count} record(s) skipped because "
                "they were not active."
            ),
            level=messages.WARNING,
      )

@admin.action(
    description="Approve and publish selected pending properties"
)
def approve_and_publish_properties(
    modeladmin,
    request,
    queryset,
):
    published_count = 0
    skipped_count = 0
    blocked_count = 0

    for property_obj in queryset.select_related(
        "partner",
    ).prefetch_related(
        "photos",
    ):
        if property_obj.status != Property.STATUS_PENDING:
            skipped_count += 1
            continue

        try:
            result = PublishingEngine.publish(
                property_obj,
            )
        except ValidationError as exc:
            blocked_count += 1

            if hasattr(exc, "message_dict"):
                messages_list = []

                for field_messages in exc.message_dict.values():
                    messages_list.extend(field_messages)

                reason = "; ".join(
                    str(message)
                    for message in messages_list
                )
            else:
                reason = "; ".join(
                    str(message)
                    for message in exc.messages
                )

            modeladmin.message_user(
                request,
                (
                    f'{property_obj.title} was not published. '
                    f'{reason}'
                ),
                level=messages.WARNING,
            )

            continue

        if not result.can_publish:
            blocked_count += 1

            requirements = "; ".join(
                result.missing_requirements
            )

            modeladmin.message_user(
                request,
                (
                    f'{property_obj.title} was not published. '
                    f'Missing: {requirements}'
                ),
                level=messages.WARNING,
            )

            continue

        ActivityLog.objects.create(
            actor=request.user,
            action="property_approved_and_published",
            entity_type="Property",
            entity_id=str(property_obj.id),
            description=(
                f"{request.user} approved and published "
                f"{property_obj.title}."
            ),
        )

        published_count += 1

    if published_count:
        modeladmin.message_user(
            request,
            (
                f"{published_count} property/properties "
                "approved and published."
            ),
            level=messages.SUCCESS,
        )

    if skipped_count:
        modeladmin.message_user(
            request,
            (
                f"{skipped_count} property/properties skipped "
                "because they were not pending verification."
            ),
            level=messages.WARNING,
        )

    if blocked_count:
        modeladmin.message_user(
            request,
            (
                f"{blocked_count} pending property/properties "
                "failed publishing readiness checks."
            ),
            level=messages.WARNING,
        )


@admin.action(
    description="Return selected pending properties to draft"
)
def return_properties_to_draft(
    modeladmin,
    request,
    queryset,
):
    returned_count = 0
    skipped_count = 0

    for property_obj in queryset:
            if property_obj.status != Property.STATUS_PENDING:
                skipped_count += 1
                continue

            blockers = []

            publishing_result = PublishingEngine.evaluate(
                property_obj,
            )

            blockers.extend(
                publishing_result.missing_requirements
            )

            mandate_result = evaluate_property_publication(
                property_obj,
            )

            blockers.extend(
                mandate_result.reasons
            )

            if blockers:
                reason = "; ".join(blockers)
            else:
                reason = (
                    "Returned by Pata Hao for additional review."
                )

            property_obj.status = Property.STATUS_DRAFT
            property_obj.verification_return_reason = reason

            property_obj.save(
                update_fields=[
                    "status",
                    "verification_return_reason",
                    "updated_at",
                ]
            )

            ActivityLog.objects.create(
                actor=request.user,
                action="property_returned_to_draft",
                entity_type="Property",
                entity_id=str(property_obj.id),
                description=(
                    f"{request.user} returned "
                    f"{property_obj.title} to draft. "
                    f"Reason: {reason}"
                ),
            )

            returned_count += 1

    if returned_count:
        modeladmin.message_user(
            request,
            (
                f"{returned_count} property/properties "
                "returned to draft."
            ),
            level=messages.SUCCESS,
        )

    if skipped_count:
        modeladmin.message_user(
            request,
            (
                f"{skipped_count} property/properties skipped "
                "because they were not pending."
            ),
            level=messages.WARNING,
        )


@admin.register(PropertyPartner)
class PropertyPartnerAdmin(admin.ModelAdmin):
    list_display = (
        "property",
        "partner",
        "role",
        "status",
        "joined_at",
        "verified_at",
        "updated_at",
    )

    list_filter = (
        "status",
        "role",
        "property__county",
        "property__town",
    )

    search_fields = (
        "property__title",
        "partner__business_name",
        "partner__user__username",
        "property__town",
        "property__estate",
    )

    readonly_fields = (
        "joined_at",
        "verified_at",
        "created_at",
        "updated_at",
    )

    actions = (
        approve_property_participations,
        remove_property_participations,
        suspend_property_participations,
    )

@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "partner",
        "property_type",
        "listing_type",
        "price",
        "town",
        "status",
        "publication_readiness",
        "publication_blockers",
        "trust_badge",
        "created_at",
    )

    list_filter = (
        "property_type",
        "listing_type",
        "status",
        "trust_badge",
        "county",
        "town",
    )
    readonly_fields = (
        "status",
    )
    search_fields = (
        "title",
        "description",
        "partner__business_name",
        "county",
        "town",
        "estate",
    )
    actions = (
        approve_and_publish_properties,
        return_properties_to_draft,
    )

    fieldsets = (
        (
            "Property ownership",
            {
                "fields": (
                    "partner",
                )
            },
        ),
        (
            "Listing details",
            {
                "fields": (
                    "title",
                    "property_type",
                    "listing_type",
                    "price",
                    "description",
                )
            },
        ),
        (
            "Location",
            {
                "fields": (
                    "county",
                    "town",
                    "estate",
                    "address",
                    "latitude",
                    "longitude",
                )
            },
        ),
        (
            "Property features",
            {
                "fields": (
                    "bedrooms",
                    "bathrooms",
                )
            },
        ),
        (
            "Availability and trust",
            {
                "fields": (
                    "status",
                    "trust_badge",
                )
            },
        ),
    )

    inlines = [
        PropertyPhotoInline,
        PropertyVideoInline,
    ]

    @admin.display(
    description="Readiness",
    )
    def publication_readiness(self, obj):
        if obj.status != Property.STATUS_PENDING:
            return "Not pending"

        publishing_result = PublishingEngine.evaluate(obj)

        if not publishing_result.can_publish:
            return "Needs attention"

        mandate_result = evaluate_property_publication(obj)

        if not mandate_result.allowed:
            return "Needs attention"

        return "Ready"


    @admin.display(
        description="Blockers",
    )
    def publication_blockers(self, obj):
        if obj.status != Property.STATUS_PENDING:
            return ""

        blockers = []

        publishing_result = PublishingEngine.evaluate(obj)

        blockers.extend(
            publishing_result.missing_requirements
        )

        mandate_result = evaluate_property_publication(obj)

        blockers.extend(
            mandate_result.reasons
        )

        if not blockers:
            return "Ready to publish"

        return "; ".join(blockers)


@admin.register(PropertyPhoto)
class PropertyPhotoAdmin(admin.ModelAdmin):
    list_display = (
        "property",
        "caption",
        "is_cover",
        "uploaded_at",
    )

    list_filter = (
        "is_cover",
    )


@admin.register(PropertyVideo)
class PropertyVideoAdmin(admin.ModelAdmin):
    list_display = (
        "property",
        "title",
        "duration",
        "is_featured",
        "uploaded_at",
    )

    list_filter = (
        "is_featured",
    )

    search_fields = (
        "title",
        "property__title",
    )