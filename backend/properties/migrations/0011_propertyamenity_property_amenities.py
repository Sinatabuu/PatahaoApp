from django.db import migrations, models


DEFAULT_AMENITIES = [
    ("24-hour Security", "security", "security", 10),
    ("Parking", "parking", "local_parking", 20),
    ("Reliable Water Supply", "water-supply", "water_drop", 30),
    ("Backup Power", "backup-power", "electric_bolt", 40),
    ("Wi-Fi Ready", "wifi-ready", "wifi", 50),
    ("Furnished", "furnished", "chair", 60),
    ("Balcony", "balcony", "balcony", 70),
    ("Lift or Elevator", "lift", "elevator", 80),
    ("Swimming Pool", "swimming-pool", "pool", 90),
    ("Gym", "gym", "fitness_center", 100),
    ("Garden", "garden", "yard", 110),
    ("Pet Friendly", "pet-friendly", "pets", 120),
    ("Gated Community", "gated-community", "fence", 130),
    ("CCTV", "cctv", "videocam", 140),
    ("Borehole", "borehole", "water", 150),
]


def seed_default_amenities(apps, schema_editor):
    PropertyAmenity = apps.get_model(
        "properties",
        "PropertyAmenity",
    )

    for name, slug, icon, display_order in DEFAULT_AMENITIES:
        PropertyAmenity.objects.update_or_create(
            slug=slug,
            defaults={
                "name": name,
                "icon": icon,
                "display_order": display_order,
                "is_active": True,
            },
        )


def remove_default_amenities(apps, schema_editor):
    PropertyAmenity = apps.get_model(
        "properties",
        "PropertyAmenity",
    )
    PropertyAmenity.objects.filter(
        slug__in=[
            slug
            for _name, slug, _icon, _order
            in DEFAULT_AMENITIES
        ],
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        (
            "properties",
            "0010_propertyphoto_photo_type",
        ),
    ]

    operations = [
        migrations.CreateModel(
            name="PropertyAmenity",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "name",
                    models.CharField(max_length=100),
                ),
                (
                    "slug",
                    models.SlugField(
                        max_length=100,
                        unique=True,
                    ),
                ),
                (
                    "icon",
                    models.CharField(
                        blank=True,
                        max_length=50,
                    ),
                ),
                (
                    "display_order",
                    models.PositiveSmallIntegerField(
                        default=0,
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(default=True),
                ),
            ],
            options={
                "verbose_name_plural": "property amenities",
                "ordering": [
                    "display_order",
                    "name",
                ],
            },
        ),
        migrations.AddField(
            model_name="property",
            name="amenities",
            field=models.ManyToManyField(
                blank=True,
                related_name="properties",
                to="properties.propertyamenity",
            ),
        ),
        migrations.RunPython(
            seed_default_amenities,
            remove_default_amenities,
        ),
    ]
