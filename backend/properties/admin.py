from django.contrib import admin, messages
from django.db import transaction
from django.utils import timezone
from django.utils.html import format_html
from mandates.services import evaluate_property_publication
from core.models import ActivityLog

from .models import (
    Property,
    PropertyAmenity,
    PropertyPartner,
    PropertyPhoto,
    PropertyVideo,
)
from .service import PublishingEngine
from django.core.exceptions import ValidationError

class PropertyPhotoInline(admin.TabularInline):
    model = PropertyPhoto
    extra = 1
    readonly_fields = (
        "image_width",
        "image_height",
        "file_size",
        "quality_status",
        "quality_score",
        "quality_warnings",
    )


def _video_player(video, *, max_width):
    if video is None or not video.video:
        return "No walkthrough video uploaded."

    try:
        video_url = video.video.url
    except ValueError:
        return "The walkthrough video file is unavailable."

    poster_url = ""

    if video.thumbnail:
        try:
            poster_url = video.thumbnail.url
        except ValueError:
            poster_url = ""

    return format_html(
        '<div style="max-width:{}px">'
        '<video controls preload="none" poster="{}" '
        'style="display:block;width:100%;height:auto;background:#111">'
        '<source src="{}" type="video/mp4">'
        'Your browser cannot play this walkthrough video.'
        '</video>'
        '<div style="margin-top:6px">'
        '<a href="{}" target="_blank" rel="noopener">'
        'Open video in a new tab'
        '</a>'
        '</div>'
        '</div>',
        max_width,
        poster_url,
        video_url,
        video_url,
    )


class PropertyVideoPreviewMixin:
    @admin.display(description="Walkthrough preview")
    def video_preview(self, obj):
        return _video_player(obj, max_width=640)


class PropertyVideoInline(
    PropertyVideoPreviewMixin,
    admin.StackedInline,
):
    model = PropertyVideo
    extra = 0
    can_delete = False
    fields = (
        "title",
        "description",
        "video_preview",
        ("duration", "width", "height"),
        ("file_size", "video_codec", "audio_codec"),
        ("is_featured", "review_status"),
        "rejection_reason",
        ("uploaded_by", "uploaded_at"),
        ("reviewed_by", "reviewed_at"),
    )
    readonly_fields = (
        "title",
        "description",
        "video_preview",
        "duration",
        "width",
        "height",
        "file_size",
        "video_codec",
        "audio_codec",
        "is_featured",
        "uploaded_by",
        "review_status",
        "rejection_reason",
        "reviewed_by",
        "reviewed_at",
        "uploaded_at",
    )


@admin.action(description="Approve selected walkthrough videos")
def approve_property_videos(modeladmin, request, queryset):
    approved_count = 0
    replaced_count = 0
    skipped_count = 0

    for video_id in queryset.values_list("id", flat=True):
        try:
            with transaction.atomic():
                video = (
                    PropertyVideo.objects
                    .select_for_update()
                    .select_related("property")
                    .get(pk=video_id)
                )
                replaced_video_ids = video.approve(
                    reviewed_by=request.user,
                )
                ActivityLog.objects.create(
                    actor=request.user,
                    action="property_video_approved",
                    entity_type="PropertyVideo",
                    entity_id=str(video.id),
                    description=(
                        f"Approved a walkthrough video for "
                        f"{video.property.title}."
                    ),
                )
                approved_count += 1
                replaced_count += len(replaced_video_ids)
        except (PropertyVideo.DoesNotExist, ValidationError):
            skipped_count += 1

    modeladmin.message_user(
        request,
        (
            f"{approved_count} walkthrough video(s) approved; "
            f"{replaced_count} previous video(s) removed; "
            f"{skipped_count} selection(s) skipped."
        ),
        level=messages.SUCCESS,
    )


@admin.action(description="Return selected videos for replacement")
def return_property_videos(modeladmin, request, queryset):
    returned_count = 0
    skipped_count = 0
    reason = (
        "The walkthrough does not meet Pata Hao's listing standards. "
        "Please replace it with a clear, accurate video."
    )

    for video_id in queryset.values_list("id", flat=True):
        try:
            with transaction.atomic():
                video = (
                    PropertyVideo.objects
                    .select_for_update()
                    .select_related("property")
                    .get(pk=video_id)
                )
                video.reject(
                    reviewed_by=request.user,
                    reason=reason,
                )
                ActivityLog.objects.create(
                    actor=request.user,
                    action="property_video_returned",
                    entity_type="PropertyVideo",
                    entity_id=str(video.id),
                    description=(
                        f"Returned a walkthrough video for "
                        f"{video.property.title}."
                    ),
                )
                returned_count += 1
        except (PropertyVideo.DoesNotExist, ValidationError):
            skipped_count += 1

    modeladmin.message_user(
        request,
        (
            f"{returned_count} walkthrough video(s) returned; "
            f"{skipped_count} selection(s) skipped."
        ),
        level=messages.WARNING,
    )

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
    description=(
        "Approve and publish properties with pending walkthrough videos"
    )
)
def approve_and_publish_properties(
    modeladmin,
    request,
    queryset,
):
    published_count = 0
    approved_video_count = 0
    skipped_count = 0
    blocked_count = 0

    for property_obj in queryset.select_related(
        "partner",
    ):
        if property_obj.status != Property.STATUS_PENDING:
            skipped_count += 1
            continue

        try:
            with transaction.atomic():
                locked_property = (
                    Property.objects
                    .select_for_update()
                    .select_related("partner")
                    .get(pk=property_obj.pk)
                )

                if locked_property.status != Property.STATUS_PENDING:
                    skipped_count += 1
                    continue

                result = PublishingEngine.publish(
                    locked_property,
                )

                if not result.can_publish:
                    blocked_count += 1

                    requirements = "; ".join(
                        result.missing_requirements
                    )

                    modeladmin.message_user(
                        request,
                        (
                            f'{locked_property.title} was not published. '
                            f'Missing: {requirements}'
                        ),
                        level=messages.WARNING,
                    )

                    continue

                pending_videos = list(
                    PropertyVideo.objects
                    .select_for_update()
                    .filter(
                        property=locked_property,
                        review_status=(
                            PropertyVideo.ReviewStatus.PENDING
                        ),
                    )
                )

                for video in pending_videos:
                    video.approve(reviewed_by=request.user)
                    ActivityLog.objects.create(
                        actor=request.user,
                        action="property_video_approved",
                        entity_type="PropertyVideo",
                        entity_id=str(video.id),
                        description=(
                            "Approved a walkthrough video during the "
                            f"initial review of {locked_property.title}."
                        ),
                    )

                ActivityLog.objects.create(
                    actor=request.user,
                    action="property_approved_and_published",
                    entity_type="Property",
                    entity_id=str(locked_property.id),
                    description=(
                        f"{request.user} approved and published "
                        f"{locked_property.title}."
                    ),
                )

                published_count += 1
                approved_video_count += len(pending_videos)
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

    if published_count:
        modeladmin.message_user(
            request,
            (
                f"{published_count} property/properties "
                "approved and published; "
                f"{approved_video_count} pending walkthrough "
                "video(s) approved."
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


@admin.register(PropertyAmenity)
class PropertyAmenityAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "slug",
        "display_order",
        "is_active",
    )
    list_editable = (
        "display_order",
        "is_active",
    )
    search_fields = (
        "name",
        "slug",
    )
    prepopulated_fields = {
        "slug": ("name",),
    }


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
        "transaction_completed_at",
        "success_broadcast_until",
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
                    "amenities",
                )
            },
        ),
        (
            "Availability and trust",
            {
                "fields": (
                    "status",
                    "trust_badge",
                    "transaction_completed_at",
                    "success_broadcast_until",
                )
            },
        ),
    )

    filter_horizontal = (
        "amenities",
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
        "photo_type",
        "is_cover",
        "quality_status",
        "quality_score",
        "image_width",
        "image_height",
        "uploaded_at",
    )

    list_filter = (
        "photo_type",
        "is_cover",
        "quality_status",
    )

    readonly_fields = (
        "image_width",
        "image_height",
        "file_size",
        "content_sha256",
        "quality_status",
        "quality_score",
        "quality_warnings",
    )


@admin.register(PropertyVideo)
class PropertyVideoAdmin(
    PropertyVideoPreviewMixin,
    admin.ModelAdmin,
):
    list_display = (
        "property",
        "title",
        "review_preview",
        "duration",
        "resolution",
        "is_featured",
        "review_status",
        "uploaded_at",
    )

    list_filter = (
        "is_featured",
        "review_status",
    )

    search_fields = (
        "title",
        "property__title",
    )

    readonly_fields = (
        "property",
        "video_preview",
        "video",
        "thumbnail",
        "duration",
        "width",
        "height",
        "file_size",
        "content_sha256",
        "video_codec",
        "audio_codec",
        "uploaded_by",
        "is_featured",
        "review_status",
        "reviewed_by",
        "reviewed_at",
        "uploaded_at",
    )

    fieldsets = (
        (
            "Review walkthrough",
            {
                "fields": (
                    "property",
                    "title",
                    "description",
                    "video_preview",
                    "is_featured",
                    "review_status",
                    "rejection_reason",
                )
            },
        ),
        (
            "Verified media metadata",
            {
                "fields": (
                    "video",
                    "thumbnail",
                    ("duration", "width", "height"),
                    ("file_size", "video_codec", "audio_codec"),
                    "content_sha256",
                )
            },
        ),
        (
            "Audit information",
            {
                "fields": (
                    ("uploaded_by", "uploaded_at"),
                    ("reviewed_by", "reviewed_at"),
                )
            },
        ),
    )

    actions = (
        approve_property_videos,
        return_property_videos,
    )

    list_per_page = 25

    @admin.display(description="Preview")
    def review_preview(self, obj):
        return _video_player(obj, max_width=300)

    @admin.display(description="Resolution")
    def resolution(self, obj):
        if not obj.width or not obj.height:
            return "Not analyzed"

        return f"{obj.width} × {obj.height}"
