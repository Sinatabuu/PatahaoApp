import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0002_notification_action_label_and_more"),
        ("viewings", "0013_repair_paid_partner_declines"),
    ]

    operations = [
        migrations.AddField(
            model_name="notification",
            name="requires_action",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="notification",
            name="viewing",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="notifications",
                to="viewings.viewing",
            ),
        ),
    ]
