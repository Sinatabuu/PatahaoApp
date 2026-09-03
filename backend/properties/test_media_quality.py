from io import BytesIO
from tempfile import TemporaryDirectory

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import (
    SimpleUploadedFile,
)
from django.test import TestCase, override_settings
from PIL import Image, ImageDraw

from .media_quality import MAX_PHOTO_BYTES
from .models import Property, PropertyPhoto
from .serializers import (
    PartnerPropertyPhotoSerializer,
    PropertyPhotoUploadSerializer,
)


class PropertyPhotoQualityTests(TestCase):
    def setUp(self):
        self.media_directory = TemporaryDirectory()
        self.settings_override = override_settings(
            MEDIA_ROOT=self.media_directory.name,
        )
        self.settings_override.enable()

        self.property_obj = self._create_property(
            "Quality Test Property",
        )

    def tearDown(self):
        self.settings_override.disable()
        self.media_directory.cleanup()

    def _create_property(self, title):
        return Property.objects.create(
            title=title,
            property_type=Property.TYPE_APARTMENT,
            listing_type=Property.LISTING_RENT,
            price="30000.00",
            county="Nairobi",
            town="Roysambu",
            description="Media quality test property.",
            status=Property.STATUS_DRAFT,
        )

    def _photo(
        self,
        *,
        name="property.jpg",
        size=(1600, 900),
        image_format="JPEG",
        color=(90, 140, 190),
        textured=True,
    ):
        image = Image.new(
            "RGB",
            size,
            color=color,
        )

        if textured:
            draw = ImageDraw.Draw(image)

            for x_position in range(
                0,
                size[0],
                40,
            ):
                stripe_color = (
                    (30, 90, 160)
                    if (x_position // 40) % 2 == 0
                    else (210, 180, 90)
                )

                draw.rectangle(
                    (
                        x_position,
                        0,
                        min(
                            x_position + 19,
                            size[0] - 1,
                        ),
                        size[1] - 1,
                    ),
                    fill=stripe_color,
                )

        buffer = BytesIO()
        image.save(
            buffer,
            format=image_format,
            quality=90,
        )

        content_type = {
            "JPEG": "image/jpeg",
            "PNG": "image/png",
            "GIF": "image/gif",
        }[image_format]

        return SimpleUploadedFile(
            name,
            buffer.getvalue(),
            content_type=content_type,
        )

    def _serializer(
        self,
        *,
        property_obj=None,
        image=None,
    ):
        return PropertyPhotoUploadSerializer(
            data={
                "property": (
                    property_obj
                    or self.property_obj
                ).id,
                "image": image or self._photo(),
                "caption": "Front view",
            }
        )

    def test_valid_photo_persists_quality_metadata(self):
        serializer = self._serializer()

        self.assertTrue(
            serializer.is_valid(),
            serializer.errors,
        )

        photo = serializer.save()
        photo.refresh_from_db()

        self.assertEqual(
            photo.image_width,
            1600,
        )
        self.assertEqual(
            photo.image_height,
            900,
        )
        self.assertGreater(
            photo.file_size,
            0,
        )
        self.assertEqual(
            len(photo.content_sha256),
            64,
        )
        self.assertEqual(
            photo.quality_status,
            PropertyPhoto.QualityStatus.ACCEPTED,
        )
        self.assertEqual(
            photo.quality_score,
            100,
        )
        self.assertEqual(
            photo.quality_warnings,
            [],
        )
        self.assertTrue(
            photo.is_cover,
        )

    def test_small_photo_is_rejected(self):
        serializer = self._serializer(
            image=self._photo(
                size=(
                    800,
                    600,
                ),
            ),
        )

        self.assertFalse(
            serializer.is_valid(),
        )
        self.assertIn(
            "1280 x 720",
            str(
                serializer.errors["image"],
            ),
        )
        self.assertFalse(
            PropertyPhoto.objects.exists(),
        )

    def test_unsupported_image_format_is_rejected(self):
        serializer = self._serializer(
            image=self._photo(
                name="property.gif",
                image_format="GIF",
            ),
        )

        self.assertFalse(
            serializer.is_valid(),
        )
        self.assertIn(
            "JPEG, PNG, or WebP",
            str(
                serializer.errors["image"],
            ),
        )

    def test_oversized_photo_is_rejected(self):
        valid_photo = self._photo()
        content = valid_photo.read()
        padding_size = (
            MAX_PHOTO_BYTES
            - len(content)
            + 1
        )

        oversized_photo = SimpleUploadedFile(
            "oversized.jpg",
            content + (b"0" * padding_size),
            content_type="image/jpeg",
        )

        serializer = self._serializer(
            image=oversized_photo,
        )

        self.assertFalse(
            serializer.is_valid(),
        )
        self.assertIn(
            "10 MB or smaller",
            str(
                serializer.errors["image"],
            ),
        )

    def test_exact_duplicate_is_rejected_for_same_property(self):
        first = self._serializer(
            image=self._photo(),
        )

        self.assertTrue(
            first.is_valid(),
            first.errors,
        )
        first.save()

        duplicate = self._serializer(
            image=self._photo(),
        )

        self.assertFalse(
            duplicate.is_valid(),
        )
        self.assertIn(
            "already been uploaded",
            str(
                duplicate.errors["image"],
            ),
        )
        self.assertEqual(
            PropertyPhoto.objects.count(),
            1,
        )

    def test_same_photo_is_allowed_for_different_property(self):
        first = self._serializer(
            image=self._photo(),
        )
        self.assertTrue(
            first.is_valid(),
            first.errors,
        )
        first.save()

        second_property = self._create_property(
            "Second Quality Test Property",
        )

        second = self._serializer(
            property_obj=second_property,
            image=self._photo(),
        )

        self.assertTrue(
            second.is_valid(),
            second.errors,
        )
        second.save()

        self.assertEqual(
            PropertyPhoto.objects.count(),
            2,
        )

    def test_dark_photo_is_kept_with_review_warning(self):
        serializer = self._serializer(
            image=self._photo(
                color=(
                    5,
                    5,
                    5,
                ),
                textured=False,
            ),
        )

        self.assertTrue(
            serializer.is_valid(),
            serializer.errors,
        )

        photo = serializer.save()
        photo.refresh_from_db()

        self.assertEqual(
            photo.quality_status,
            PropertyPhoto.QualityStatus.NEEDS_REVIEW,
        )
        self.assertLess(
            photo.quality_score,
            100,
        )
        self.assertIn(
            "The photo may be too dark.",
            photo.quality_warnings,
        )

    def test_model_save_enforces_minimum_dimensions(self):
        with self.assertRaisesMessage(
            ValidationError,
            "1280 x 720",
        ):
            PropertyPhoto.objects.create(
                property=self.property_obj,
                image=self._photo(
                    size=(
                        640,
                        480,
                    ),
                ),
            )

    def test_partner_serializer_exposes_quality_feedback(self):
        serializer = self._serializer()
        self.assertTrue(
            serializer.is_valid(),
            serializer.errors,
        )
        photo = serializer.save()

        payload = PartnerPropertyPhotoSerializer(
            photo,
        ).data

        self.assertEqual(
            payload["image_width"],
            1600,
        )
        self.assertEqual(
            payload["image_height"],
            900,
        )
        self.assertEqual(
            payload["quality_status"],
            PropertyPhoto.QualityStatus.ACCEPTED,
        )
        self.assertIn(
            "quality_warnings",
            payload,
        )
