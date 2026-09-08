from decimal import Decimal

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from governance.models import PartnerTier
from partners.models import Partner

from .models import Property, PropertyAmenity


class PropertyAmenitiesTests(APITestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(
            username="amenities_admin",
            email="amenities-admin@example.com",
            password="test-pass-123",
            role=User.ROLE_ADMIN,
            is_staff=True,
        )
        self.partner_user = User.objects.create_user(
            username="amenities_partner",
            email="amenities-partner@example.com",
            password="test-pass-123",
            role=User.ROLE_PARTNER,
        )
        self.partner = Partner.objects.create(
            user=self.partner_user,
            business_name="Amenities Partner",
            verification_status=Partner.STATUS_APPROVED,
            verified_by=self.admin_user,
            verified_at=timezone.now(),
        )
        self.partner_tier = PartnerTier.objects.create(
            code="amenities-test",
            name="Amenities Test Tier",
            rank=901,
            property_limit=20,
            minimum_completed_deals=0,
            minimum_trust_score=Decimal("0.00"),
            active=True,
        )
        self.property_obj = Property.objects.create(
            partner=self.partner,
            title="Amenities Test Home",
            property_type=Property.TYPE_HOUSE,
            listing_type=Property.LISTING_RENT,
            price=Decimal("35000.00"),
            county="Nairobi",
            town="Roysambu",
            estate="Roysambu",
            address="Test address",
            bedrooms=2,
            bathrooms=1,
            description="A rental property with useful amenities.",
            status=Property.STATUS_DRAFT,
        )
        self.security = PropertyAmenity.objects.create(
            name="24-hour Security Test",
            slug="test-security",
            icon="security",
            display_order=1010,
        )
        self.parking = PropertyAmenity.objects.create(
            name="Parking Test",
            slug="test-parking",
            icon="local_parking",
            display_order=1020,
        )
        self.client.force_authenticate(
            user=self.partner_user,
        )

    def test_partner_can_load_active_amenity_options(self):
        response = self.client.get(
            "/api/partner/properties/amenity-options/",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        slugs = {
            item["slug"]
            for item in response.data
        }

        self.assertIn(self.security.slug, slugs)
        self.assertIn(self.parking.slug, slugs)

    def test_source_partner_can_save_optional_amenities(self):
        response = self.client.patch(
            (
                "/api/partner/properties/"
                f"{self.property_obj.id}/amenities/"
            ),
            {
                "amenities": [
                    self.security.slug,
                    self.parking.slug,
                ],
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            {
                item["slug"]
                for item in response.data["amenities"]
            },
            {
                self.security.slug,
                self.parking.slug,
            },
        )

        self.assertEqual(
            set(
                self.property_obj.amenities.values_list(
                    "slug",
                    flat=True,
                )
            ),
            {
                self.security.slug,
                self.parking.slug,
            },
        )

    def test_empty_amenities_are_allowed(self):
        self.property_obj.amenities.add(
            self.security,
        )

        response = self.client.patch(
            (
                "/api/partner/properties/"
                f"{self.property_obj.id}/amenities/"
            ),
            {
                "amenities": [],
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertFalse(
            self.property_obj.amenities.exists(),
        )

    def test_partner_cannot_change_another_property(self):
        other_user = User.objects.create_user(
            username="other_amenities_partner",
            email="other-amenities-partner@example.com",
            password="test-pass-123",
            role=User.ROLE_PARTNER,
        )
        other_partner = Partner.objects.create(
            user=other_user,
            business_name="Other Amenities Partner",
            verification_status=Partner.STATUS_APPROVED,
            verified_by=self.admin_user,
            verified_at=timezone.now(),
        )
        other_property = Property.objects.create(
            partner=other_partner,
            title="Another Partner Home",
            property_type=Property.TYPE_HOUSE,
            listing_type=Property.LISTING_RENT,
            price=Decimal("40000.00"),
            county="Nairobi",
            town="Roysambu",
            description="Another partner property.",
            status=Property.STATUS_DRAFT,
        )

        response = self.client.patch(
            (
                "/api/partner/properties/"
                f"{other_property.id}/amenities/"
            ),
            {
                "amenities": [
                    self.security.slug,
                ],
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertFalse(
            other_property.amenities.exists(),
        )

    def test_unknown_amenity_is_rejected(self):
        response = self.client.patch(
            (
                "/api/partner/properties/"
                f"{self.property_obj.id}/amenities/"
            ),
            {
                "amenities": [
                    "not-a-real-amenity",
                ],
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertFalse(
            self.property_obj.amenities.exists(),
        )

    def test_staff_property_review_includes_selected_amenities(self):
        self.property_obj.amenities.add(
            self.security,
            self.parking,
        )
        self.property_obj.status = Property.STATUS_PENDING
        self.property_obj.save(
            update_fields=["status", "updated_at"],
        )
        self.client.force_authenticate(
            user=self.admin_user,
        )

        response = self.client.get(
            f"/api/property-reviews/{self.property_obj.id}/",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            {
                item["slug"]
                for item in response.data["property"]["amenities"]
            },
            {
                self.security.slug,
                self.parking.slug,
            },
        )
