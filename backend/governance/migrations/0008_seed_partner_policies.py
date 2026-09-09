from datetime import date

from django.db import migrations


POLICIES = [
    (
        "POL-001",
        "Verified owner authority required",
        (
            "A partner may list or transact on a property only "
            "when valid owner authority and an approved mandate "
            "are recorded in Pata Hao."
        ),
        "serious",
        "long_suspension",
    ),
    (
        "POL-002",
        "False or misleading listings prohibited",
        (
            "A partner must not publish fabricated, materially "
            "misleading, unavailable, or incorrectly represented "
            "property listings."
        ),
        "serious",
        "long_suspension",
    ),
    (
        "POL-003",
        "Duplicate listing abuse prohibited",
        (
            "A partner must not repeatedly publish duplicate "
            "listings to manipulate visibility or search ranking."
        ),
        "moderate",
        "short_suspension",
    ),
    (
        "POL-004",
        "Professional conduct required",
        (
            "Partners must treat customers, owners, staff, and "
            "other partners respectfully and professionally."
        ),
        "moderate",
        "short_suspension",
    ),
    (
        "POL-005",
        "Viewing obligations must be honored",
        (
            "Partners must attend or properly manage confirmed "
            "viewings and must communicate unavoidable changes."
        ),
        "moderate",
        "short_suspension",
    ),
    (
        "POL-006",
        "Outside-platform transactions prohibited",
        (
            "A partner must not complete, receive payment for, "
            "or conceal a transaction outside Pata Hao after a "
            "customer or property introduction has been protected "
            "by the platform."
        ),
        "gross_misconduct",
        "permanent_ban",
    ),
    (
        "POL-007",
        "Document falsification prohibited",
        (
            "Forging, altering, fabricating, or knowingly using "
            "false owner, mandate, identity, property, viewing, "
            "payment, or transaction evidence is prohibited."
        ),
        "gross_misconduct",
        "permanent_ban",
    ),
]


def seed_partner_policies(apps, schema_editor):
    PolicyRule = apps.get_model(
        "governance",
        "PolicyRule",
    )

    for (
        code,
        title,
        description,
        severity,
        recommended_action,
    ) in POLICIES:
        PolicyRule.objects.update_or_create(
            code=code,
            defaults={
                "title": title,
                "description": description,
                "severity": severity,
                "recommended_action": recommended_action,
                "effective_from": date(2026, 9, 9),
                "active": True,
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        (
            "governance",
            "0007_partnertier_commission_share_rate",
        ),
    ]

    operations = [
        migrations.RunPython(
            seed_partner_policies,
            migrations.RunPython.noop,
        ),
    ]
