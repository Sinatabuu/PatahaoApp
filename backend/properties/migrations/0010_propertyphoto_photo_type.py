from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        (
            "properties",
            "0009_propertyphoto_media_quality",
        ),
    ]

    operations = [
        migrations.AddField(
            model_name="propertyphoto",
            name="photo_type",
            field=models.CharField(
                choices=[
                    ("exterior", "Exterior"),
                    ("living_area", "Living area"),
                    ("bedroom", "Bedroom"),
                    ("kitchen", "Kitchen"),
                    ("bathroom", "Bathroom"),
                    ("site_overview", "Site overview"),
                    ("boundary", "Boundary"),
                    ("access", "Access or entrance"),
                    (
                        "main_space",
                        "Main commercial space",
                    ),
                    ("amenity", "Amenity"),
                    ("other", "Other"),
                ],
                db_index=True,
                default="other",
                max_length=30,
            ),
        ),
    ]
