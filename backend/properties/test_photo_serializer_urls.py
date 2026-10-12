from django.test import SimpleTestCase

from properties.models import PropertyPhoto
from properties.serializers import PropertyPhotoSerializer


class PhotoSerializerURLTests(SimpleTestCase):

    def test_photo_with_variants(self):
        photo = PropertyPhoto(
            image="property_photos/original.jpg",
            thumbnail_image="property_photos/thumbnails/small.jpg",
            listing_image="property_photos/listings/medium.jpg",
            is_cover=True,
        )

        data = PropertyPhotoSerializer(photo).data

        self.assertIn("original.jpg", data["image_url"])
        self.assertIn("small.jpg", data["thumbnail_url"])
        self.assertIn("medium.jpg", data["listing_image_url"])
        self.assertTrue(data["is_cover"])

    def test_legacy_photo_without_variants(self):
        photo = PropertyPhoto(
            image="property_photos/legacy.jpg",
            is_cover=True,
        )

        data = PropertyPhotoSerializer(photo).data

        self.assertIn("legacy.jpg", data["image_url"])
        self.assertIsNone(data["thumbnail_url"])
        self.assertIsNone(data["listing_image_url"])
