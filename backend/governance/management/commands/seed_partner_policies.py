from datetime import date

from django.core.management.base import BaseCommand

from governance.models import PolicyRule


class Command(BaseCommand):
    help = "Create or update default Pata Hao partner policies."

    POLICIES = [
        {
            "code": "POL-001",
            "title": "Verified owner authority required",
            "description": (
                "A partner may list or transact on a property only "
                "when valid owner authority and an approved mandate "
                "are recorded in Pata Hao."
            ),
            "severity": PolicyRule.Severity.SERIOUS,
            "recommended_action": (
                PolicyRule.RecommendedAction.LONG_SUSPENSION
            ),
        },
        {
            "code": "POL-002",
            "title": "False or misleading listings prohibited",
            "description": (
                "A partner must not publish fabricated, materially "
                "misleading, unavailable, or incorrectly represented "
                "property listings."
            ),
            "severity": PolicyRule.Severity.SERIOUS,
            "recommended_action": (
                PolicyRule.RecommendedAction.LONG_SUSPENSION
            ),
        },
        {
            "code": "POL-003",
            "title": "Duplicate listing abuse prohibited",
            "description": (
                "A partner must not repeatedly publish duplicate "
                "listings to manipulate visibility or search ranking."
            ),
            "severity": PolicyRule.Severity.MODERATE,
            "recommended_action": (
                PolicyRule.RecommendedAction.SHORT_SUSPENSION
            ),
        },
        {
            "code": "POL-004",
            "title": "Professional conduct required",
            "description": (
                "Partners must treat customers, owners, staff, and "
                "other partners respectfully and professionally."
            ),
            "severity": PolicyRule.Severity.MODERATE,
            "recommended_action": (
                PolicyRule.RecommendedAction.SHORT_SUSPENSION
            ),
        },
        {
            "code": "POL-005",
            "title": "Viewing obligations must be honored",
            "description": (
                "Partners must attend or properly manage confirmed "
                "viewings and must communicate unavoidable changes."
            ),
            "severity": PolicyRule.Severity.MODERATE,
            "recommended_action": (
                PolicyRule.RecommendedAction.SHORT_SUSPENSION
            ),
        },
        {
            "code": "POL-006",
            "title": "Outside-platform transactions prohibited",
            "description": (
                "A partner must not complete, receive payment for, "
                "or conceal a transaction outside Pata Hao after a "
                "customer or property introduction has been protected "
                "by the platform."
            ),
            "severity": (
                PolicyRule.Severity.GROSS_MISCONDUCT
            ),
            "recommended_action": (
                PolicyRule.RecommendedAction.PERMANENT_BAN
            ),
        },
        {
            "code": "POL-007",
            "title": "Document falsification prohibited",
            "description": (
                "Forging, altering, fabricating, or knowingly using "
                "false owner, mandate, identity, property, viewing, "
                "payment, or transaction evidence is prohibited."
            ),
            "severity": (
                PolicyRule.Severity.GROSS_MISCONDUCT
            ),
            "recommended_action": (
                PolicyRule.RecommendedAction.PERMANENT_BAN
            ),
        },
    ]

    def handle(self, *args, **options):
        effective_from = date.today()

        for policy_data in self.POLICIES:
            policy, created = PolicyRule.objects.update_or_create(
                code=policy_data["code"],
                defaults={
                    **policy_data,
                    "effective_from": effective_from,
                    "active": True,
                },
            )

            action = "Created" if created else "Updated"

            self.stdout.write(
                self.style.SUCCESS(
                    f"{action} {policy.code}: {policy.title}"
                )
            )

        self.stdout.write(
            self.style.SUCCESS(
                "Partner policies seeded successfully."
            )
        )