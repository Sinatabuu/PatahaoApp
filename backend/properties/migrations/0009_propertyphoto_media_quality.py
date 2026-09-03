from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        (
            "properties",
            "0008_property_success_broadcast_until_and_more",
        ),
    ]

    operations = [
        migrations.AddField(
            model_name="propertyphoto",
            name="content_sha256",
            field=models.CharField(
                blank=True,
                db_index=True,
                editable=False,
                max_length=64,
            ),
        ),
        migrations.AddField(
            model_name="propertyphoto",
            name="file_size",
            field=models.PositiveIntegerField(
                default=0,
                editable=False,
            ),
        ),
        migrations.AddField(
            model_name="propertyphoto",
            name="image_height",
            field=models.PositiveIntegerField(
                default=0,
                editable=False,
            ),
        ),
        migrations.AddField(
            model_name="propertyphoto",
            name="image_width",
            field=models.PositiveIntegerField(
                default=0,
                editable=False,
            ),
        ),
        migrations.AddField(
            model_name="propertyphoto",
            name="quality_score",
            field=models.PositiveSmallIntegerField(
                default=100,
                editable=False,
            ),
        ),
        migrations.AddField(
            model_name="propertyphoto",
            name="quality_status",
            field=models.CharField(
                choices=[
                    (
                        "accepted",
                        "Accepted",
                    ),
                    (
                        "needs_review",
                        "Needs review",
                    ),
                ],
                db_index=True,
                default="accepted",
                editable=False,
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="propertyphoto",
            name="quality_warnings",
            field=models.JSONField(
                blank=True,
                default=list,
                editable=False,
            ),
        ),
        migrations.AddConstraint(
            model_name="propertyphoto",
            constraint=models.UniqueConstraint(
                condition=models.Q(
                    content_sha256__gt="",
                ),
                fields=(
                    "property",
                    "content_sha256",
                ),
                name="unique_property_photo_content",
            ),
        ),
    ]
