from decimal import Decimal

from django.core.management.base import BaseCommand

from governance.models import PartnerTier


class Command(BaseCommand):
    help = (
        "Create or update the default "
        "Pata Hao partner tiers."
    )

    TIERS = [
        {
            "code": "bronze",
            "name": "Bronze",
            "description": (
                "Entry level partner."
            ),
            "rank": 1,
            "property_limit": 20,
            "minimum_completed_deals": 0,
            "minimum_trust_score": Decimal("0.00"),
        },
        {
            "code": "silver",
            "name": "Silver",
            "description": (
                "Trusted growing partner."
            ),
            "rank": 2,
            "property_limit": 50,
            "minimum_completed_deals": 50,
            "minimum_trust_score": Decimal("90.00"),
        },
        {
            "code": "gold",
            "name": "Gold",
            "description": (
                "High-performing partner."
            ),
            "rank": 3,
            "property_limit": 100,
            "minimum_completed_deals": 150,
            "minimum_trust_score": Decimal("93.00"),
        },
        {
            "code": "platinum",
            "name": "Platinum",
            "description": (
                "Elite partner."
            ),
            "rank": 4,
            "property_limit": 250,
            "minimum_completed_deals": 400,
            "minimum_trust_score": Decimal("96.00"),
        },
        {
            "code": "diamond",
            "name": "Diamond",
            "description": (
                "Top-tier partner."
            ),
            "rank": 5,
            "property_limit": 999999,
            "minimum_completed_deals": 1000,
            "minimum_trust_score": Decimal("98.00"),
        },
    ]

    def handle(self, *args, **options):
        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "Seeding Partner Tiers..."
            )
        )

        for tier in self.TIERS:
            obj, created = (
                PartnerTier.objects.update_or_create(
                    code=tier["code"],
                    defaults=tier,
                )
            )

            if created:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ Created {obj.name}"
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"• Updated {obj.name}"
                    )
                )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "Partner tiers seeded successfully."
            )
        )