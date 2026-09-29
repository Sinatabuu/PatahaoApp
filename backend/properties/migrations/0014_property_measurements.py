from decimal import Decimal

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("properties", "0013_one_video_per_property"),
    ]

    operations = [
        migrations.AddField(
            model_name="property",
            name="floor_area",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="Indoor or built-up floor area.",
                max_digits=12,
                null=True,
                validators=[
                    django.core.validators.MinValueValidator(
                        Decimal("0.01")
                    )
                ],
            ),
        ),
        migrations.AddField(
            model_name="property",
            name="floor_area_unit",
            field=models.CharField(
                choices=[
                    ("sq_ft", "Square feet"),
                    ("sq_m", "Square metres"),
                    ("acres", "Acres"),
                    ("hectares", "Hectares"),
                ],
                default="sq_ft",
                max_length=12,
            ),
        ),
        migrations.AddField(
            model_name="property",
            name="land_area",
            field=models.DecimalField(
                blank=True,
                decimal_places=4,
                help_text="Plot or land area.",
                max_digits=12,
                null=True,
                validators=[
                    django.core.validators.MinValueValidator(
                        Decimal("0.0001")
                    )
                ],
            ),
        ),
        migrations.AddField(
            model_name="property",
            name="land_area_unit",
            field=models.CharField(
                choices=[
                    ("sq_ft", "Square feet"),
                    ("sq_m", "Square metres"),
                    ("acres", "Acres"),
                    ("hectares", "Hectares"),
                ],
                default="acres",
                max_length=12,
            ),
        ),
    ]
