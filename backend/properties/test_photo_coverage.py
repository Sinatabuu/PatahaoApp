from decimal import Decimal
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from rest_framework.test import APIClient

from partners.models import Partner

from .models import Property, PropertyPhoto
from .photo_coverage import (
    PHOTO_TYPE_ACCESS,
    PHOTO_TYPE_BATHROOM,
    PHOTO_TYPE_BEDROOM,
    PHOTO_TYPE_BOUNDARY,
    PHOTO_TYPE_EXTERIOR,
    PHOTO_TYPE_KITCHEN,
    PHOTO_TYPE_LIVING_AREA,
    PHOTO_TYPE_MAIN_SPACE,
    PHOTO_TYPE_OTHER,
    PHOTO_TYPE_SITE_OVERVIEW,
    evaluate_photo_coverage,
    required_photo_types_for,
)
from .serializers import (
    PartnerPropertyPhotoSerializer,
    PartnerPropertySerializer,
    PropertyPhotoUploadSerializer,
)


class PropertyPhotoCoverageRuleTests(SimpleTestCase):
    def test_residential_requirements_follow_room_counts(self):
        property_obj = SimpleNamespace(
            property_type=Property.TYPE_APARTMENT,
            bedrooms=2,
            bathrooms=1,
        )

        self.assertEqual(
            required_photo_types_for(property_obj),
            (
                PHOTO_TYPE_EXTERIOR,
                PHOTO_TYPE_LIVING_AREA,
                PHOTO_TYPE_KITCHEN,
                PHOTO_TYPE_BEDROOM,
                PHOTO_TYPE_BATHROOM,
            ),
        )

    def test_land_requirements_use_site_specific_views(self):
        property_obj = SimpleNamespace(
            property_type=Property.TYPE_LAND,
            bedrooms=0,
            bathrooms=0,
        )

        self.assertEqual(
            required_photo_types_for(property_obj),
            (
                PHOTO_TYPE_SITE_OVERVIEW,
                PHOTO_TYPE_BOUNDARY,
                PHOTO_TYPE_ACCESS,
            ),
        )

    def test_commercial_requirements_include_main_space(self):
        property_obj = SimpleNamespace(
            property_type=Property.TYPE_OFFICE,
            bedrooms=0,
            bathrooms=1,
        )

        self.assertEqual(
            required_photo_types_for(property_obj),
            (
                PHOTO_TYPE_EXTERIOR,
                PHOTO_TYPE_MAIN_SPACE,
                PHOTO_TYPE_ACCESS,
                PHOTO_TYPE_BATHROOM,
            ),
        )


class PropertyPhotoCoverageSubmissionTests(TestCase):
    def setUp(self):
        user_model = get_user_model()

        self.user = user_model.objects.create_user(
            username="coverage-partner",
            password="test-password",
        )

        self.partner = Partner.objects.create(
            user=self.user,
            business_name="Coverage Homes",
            verification_status=Partner.STATUS_APPROVED,
            is_active=True,
        )

        self.property_obj = Property.objects.create(
            partner=self.partner,
            title="Coverage Test Home",
            property_type=Property.TYPE_APARTMENT,
            listing_type=Property.LISTING_RENT,
            price=Decimal("35000.00"),
            county="Nairobi",
            town="Roysambu",
            estate="Garden Estate",
            address="Coverage Road",
            latitude=Decimal("-1.218000"),
            longitude=Decimal("36.886000"),
            bedrooms=2,
            bathrooms=1,
            description=(
                "A complete residential property used to "
                "test photo coverage."
            ),
            status=Property.STATUS_DRAFT,
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def _add_photos(self, photo_types):
        photos = []

        for index, photo_type in enumerate(photo_types):
            photos.append(
                PropertyPhoto(
                    property=self.property_obj,
                    image=(
                        "property_photos/"
                        f"coverage-{index}.jpg"
                    ),
                    caption=f"Coverage photo {index + 1}",
                    photo_type=photo_type,
                    is_cover=index == 0,
                    image_width=1600,
                    image_height=900,
                    file_size=250000,
                    quality_status=(
                        PropertyPhoto.QualityStatus.ACCEPTED
                    ),
                    quality_score=100,
                )
            )

        PropertyPhoto.objects.bulk_create(photos)

    def _submit(self):
        return self.client.post(
            (
                "/api/partner/properties/"
                f"{self.property_obj.id}/"
                "submit-verification/"
            ),
            {},
            format="json",
        )

    def test_fewer_than_five_photos_cannot_be_submitted(self):
        self._add_photos(
            [
                PHOTO_TYPE_EXTERIOR,
                PHOTO_TYPE_LIVING_AREA,
                PHOTO_TYPE_KITCHEN,
                PHOTO_TYPE_BEDROOM,
            ]
        )

        response = self._submit()

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["photo_count"], 4)
        self.assertEqual(
            response.data["minimum_photo_count"],
            5,
        )
        self.assertFalse(response.data["complete"])

    def test_random_angles_do_not_satisfy_coverage(self):
        self._add_photos(
            [
                PHOTO_TYPE_OTHER,
                PHOTO_TYPE_OTHER,
                PHOTO_TYPE_OTHER,
                PHOTO_TYPE_OTHER,
                PHOTO_TYPE_OTHER,
            ]
        )

        response = self._submit()

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            set(response.data["missing_photo_types"]),
            {
                PHOTO_TYPE_EXTERIOR,
                PHOTO_TYPE_LIVING_AREA,
                PHOTO_TYPE_KITCHEN,
                PHOTO_TYPE_BEDROOM,
                PHOTO_TYPE_BATHROOM,
            },
        )

    def test_complete_residential_coverage_can_be_submitted(self):
        self._add_photos(
            [
                PHOTO_TYPE_EXTERIOR,
                PHOTO_TYPE_LIVING_AREA,
                PHOTO_TYPE_KITCHEN,
                PHOTO_TYPE_BEDROOM,
                PHOTO_TYPE_BATHROOM,
            ]
        )

        response = self._submit()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            response.data["photo_coverage"]["complete"],
        )

        self.property_obj.refresh_from_db()

        self.assertEqual(
            self.property_obj.status,
            Property.STATUS_PENDING,
        )

    def test_partner_photo_serializer_exposes_photo_type(self):
        self._add_photos([PHOTO_TYPE_EXTERIOR])

        photo = PropertyPhoto.objects.get()

        payload = PartnerPropertyPhotoSerializer(photo).data

        self.assertEqual(
            payload["photo_type"],
            PHOTO_TYPE_EXTERIOR,
        )

    def test_partner_property_serializer_exposes_coverage(self):
        self._add_photos([PHOTO_TYPE_EXTERIOR])

        payload = PartnerPropertySerializer(
            self.property_obj,
        ).data

        self.assertEqual(
            payload["photo_coverage"]["photo_count"],
            1,
        )
        self.assertIn(
            PHOTO_TYPE_KITCHEN,
            payload["photo_coverage"][
                "missing_photo_types"
            ],
        )
        self.assertEqual(
            payload["photos"][0]["photo_type"],
            PHOTO_TYPE_EXTERIOR,
        )

    def test_upload_serializer_rejects_unknown_photo_type(self):
        self._add_photos([PHOTO_TYPE_EXTERIOR])

        photo = PropertyPhoto.objects.get()

        serializer = PropertyPhotoUploadSerializer(
            instance=photo,
            data={
                "photo_type": "random_angle",
            },
            partial=True,
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("photo_type", serializer.errors)

    def test_coverage_payload_contains_human_labels(self):
        property_obj = SimpleNamespace(
            property_type=Property.TYPE_LAND,
            bedrooms=0,
            bathrooms=0,
        )

        coverage = evaluate_photo_coverage(
            property_obj,
            [],
        )

        self.assertEqual(
            coverage["missing_photo_labels"],
            [
                "Site overview",
                "Boundary",
                "Access or entrance",
            ],
        )
