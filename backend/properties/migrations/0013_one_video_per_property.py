from django.db import migrations, models, transaction


def enforce_one_video_workflow(apps, schema_editor):
    PropertyVideo = apps.get_model("properties", "PropertyVideo")
    database_alias = schema_editor.connection.alias
    videos = PropertyVideo.objects.using(database_alias)
    property_ids = list(
        videos.order_by()
        .values_list("property_id", flat=True)
        .distinct()
    )

    for property_id in property_ids:
        property_videos = list(
            videos.filter(property_id=property_id)
            .order_by("-is_featured", "-uploaded_at", "-id")
        )
        approved = [
            video
            for video in property_videos
            if video.review_status == "approved"
        ]
        pending = [
            video
            for video in property_videos
            if video.review_status == "pending"
        ]
        rejected = [
            video
            for video in property_videos
            if video.review_status == "rejected"
        ]

        approved_video = approved[0] if approved else None
        pending_video = pending[0] if pending else None
        rejected_video = (
            rejected[0]
            if rejected and pending_video is None
            else None
        )
        kept_videos = [
            video
            for video in (
                approved_video,
                pending_video,
                rejected_video,
            )
            if video is not None
        ]
        kept_ids = {video.id for video in kept_videos}

        videos.filter(property_id=property_id).update(
            is_featured=False,
        )

        current_video = (
            approved_video
            or pending_video
            or rejected_video
        )

        if current_video is not None:
            videos.filter(pk=current_video.pk).update(
                is_featured=True,
            )

        for video in property_videos:
            if video.id in kept_ids:
                continue

            stored_files = []

            for field_name in ("video", "thumbnail"):
                field_file = getattr(video, field_name)

                if field_file and field_file.name:
                    stored_files.append(
                        (field_file.storage, field_file.name)
                    )

            videos.filter(pk=video.pk).delete()

            for storage, name in stored_files:
                transaction.on_commit(
                    lambda storage=storage, name=name: storage.delete(name),
                    using=database_alias,
                )


class Migration(migrations.Migration):

    dependencies = [
        ("properties", "0012_propertyvideo_audio_codec_and_more"),
    ]

    operations = [
        migrations.RunPython(
            enforce_one_video_workflow,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.AddConstraint(
            model_name="propertyvideo",
            constraint=models.UniqueConstraint(
                condition=models.Q(review_status="approved"),
                fields=("property",),
                name="unique_approved_video_per_property",
            ),
        ),
        migrations.AddConstraint(
            model_name="propertyvideo",
            constraint=models.UniqueConstraint(
                condition=models.Q(review_status="pending"),
                fields=("property",),
                name="unique_pending_video_per_property",
            ),
        ),
    ]
