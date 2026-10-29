from io import BytesIO
from tempfile import TemporaryDirectory

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image

from properties.models import Property
from properties.serializers import PropertyPhotoUploadSerializer


class PhotoUploadIntegrationTests(TestCase):

    def test_upload_generates_both_optimized_variants(self):
        property_obj = Property.objects.create(
            title="Optimization Test Property",
            property_type="apartment",
            listing_type="rent",
            price=15000,
            county="Nairobi",
            town="Roysambu",
            description="Temporary property for image testing.",
        )

        source = BytesIO()
        Image.new("RGB", (1800, 1200), "lightblue").save(
            source,
            format="JPEG",
        )
        original_bytes = source.getvalue()

        uploaded = SimpleUploadedFile(
            "property.jpg",
            original_bytes,
            content_type="image/jpeg",
        )

        with TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                serializer = PropertyPhotoUploadSerializer(
                    data={
                        "property": property_obj.pk,
                        "image": uploaded,
                        "caption": "Test photograph",
                    }
                )

                self.assertTrue(
                    serializer.is_valid(),
                    serializer.errors,
                )

                photo = serializer.save()

                self.assertTrue(photo.pk)
                self.assertTrue(photo.image)
                self.assertTrue(photo.thumbnail_image)
                self.assertTrue(photo.listing_image)

                for field_name, expected_size in (
                    ("thumbnail_image", (360, 240)),
                    ("listing_image", (900, 600)),
                ):
                    field = getattr(photo, field_name)

                    self.assertTrue(field.storage.exists(field.name))

                    with field.open("rb") as stored:
                        with Image.open(stored) as image:
                            self.assertEqual(image.size, expected_size)

                with photo.image.open("rb") as original:
                    self.assertEqual(original.read(), original_bytes)

                photo.refresh_from_db()

                self.assertTrue(photo.thumbnail_image.name)
                self.assertTrue(photo.listing_image.name)

    def test_database_failure_cleans_up_generated_variants(self):
        from unittest.mock import patch

        from django.db import DatabaseError
        from properties.models import PropertyPhoto

        property_obj = Property.objects.create(
            title="Database Failure Test",
            property_type="apartment",
            listing_type="rent",
            price=15000,
            county="Nairobi",
            town="Roysambu",
            description="Testing cleanup after database failure.",
        )

        source = BytesIO()
        Image.new("RGB", (1800, 1200), "lightblue").save(
            source, format="JPEG"
        )

        uploaded = SimpleUploadedFile(
            "failure.jpg",
            source.getvalue(),
            content_type="image/jpeg",
        )

        with TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                serializer = PropertyPhotoUploadSerializer(
                    data={
                        "property": property_obj.pk,
                        "image": uploaded,
                    }
                )
                self.assertTrue(serializer.is_valid(), serializer.errors)

                original_save = PropertyPhoto.save

                def fail_variant_database_save(instance, *args, **kwargs):
                    if kwargs.get("update_fields") == [
                        "thumbnail_image",
                        "listing_image",
                    ]:
                        raise DatabaseError("Simulated database failure")
                    return original_save(instance, *args, **kwargs)

                with patch.object(
                    PropertyPhoto,
                    "save",
                    fail_variant_database_save,
                ):
                    with self.assertRaisesRegex(
                        DatabaseError,
                        "Simulated database failure",
                    ):
                        serializer.save()

                from pathlib import Path

                thumbnail_dir = (
                    Path(media_root) / "property_photos" / "thumbnails"
                )
                listing_dir = (
                    Path(media_root) / "property_photos" / "listings"
                )

                for directory in (thumbnail_dir, listing_dir):
                    if directory.exists():
                        self.assertEqual(
                            list(directory.iterdir()),
                            [],
                            f"Orphaned optimized images in {directory}",
                        )


class NewPhotoFailureCleanupTests(TestCase):

    def test_variant_failure_removes_original_and_database_record(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from unittest.mock import patch

        from django.core.files.uploadedfile import SimpleUploadedFile
        from django.test import override_settings
        from PIL import Image
        from io import BytesIO

        from properties.models import Property, PropertyPhoto
        from properties.serializers import PropertyPhotoUploadSerializer

        property_obj = Property.objects.create(
            title="Upload Cleanup Test",
            property_type="apartment",
            listing_type="rent",
            price=15000,
            county="Nairobi",
            town="Roysambu",
            description="Testing failed upload cleanup.",
        )

        image_bytes = BytesIO()
        Image.new("RGB", (1800, 1200), "blue").save(
            image_bytes,
            format="JPEG",
        )

        uploaded = SimpleUploadedFile(
            "failed_upload.jpg",
            image_bytes.getvalue(),
            content_type="image/jpeg",
        )

        with TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                serializer = PropertyPhotoUploadSerializer(
                    data={
                        "property": property_obj.pk,
                        "image": uploaded,
                    }
                )

                self.assertTrue(
                    serializer.is_valid(),
                    serializer.errors,
                )

                with patch(
                    "properties.serializers.generate_photo_variants",
                    side_effect=OSError(
                        "Simulated thumbnail generation failure"
                    ),
                ):
                    with self.assertRaisesRegex(
                        OSError,
                        "Simulated thumbnail generation failure",
                    ):
                        serializer.save()

                self.assertFalse(
                    PropertyPhoto.objects.filter(
                        property=property_obj,
                    ).exists()
                )

                remaining_files = [
                    path
                    for path in Path(media_root).rglob("*")
                    if path.is_file()
                ]

                self.assertEqual(
                    remaining_files,
                    [],
                    "Failed upload left orphaned image files.",
                )
