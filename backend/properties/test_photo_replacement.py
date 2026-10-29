from pathlib import Path
from io import BytesIO
from tempfile import TemporaryDirectory

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image

from properties.models import Property
from properties.serializers import PropertyPhotoUploadSerializer


class PhotoReplacementTests(TestCase):

    def make_upload(self, filename, color):
        buffer = BytesIO()
        Image.new("RGB", (1800, 1200), color).save(
            buffer, format="JPEG"
        )
        return SimpleUploadedFile(
            filename,
            buffer.getvalue(),
            content_type="image/jpeg",
        )

    def test_replacement_regenerates_optimized_images(self):
        property_obj = Property.objects.create(
            title="Replacement Test Property",
            property_type="apartment",
            listing_type="rent",
            price=15000,
            county="Nairobi",
            town="Roysambu",
            description="Testing photograph replacement.",
        )

        with TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                create_serializer = PropertyPhotoUploadSerializer(
                    data={
                        "property": property_obj.pk,
                        "image": self.make_upload(
                            "original.jpg", "blue"
                        ),
                    }
                )
                self.assertTrue(
                    create_serializer.is_valid(),
                    create_serializer.errors,
                )
                photo = create_serializer.save()

                old_hash = photo.content_sha256
                old_thumbnail = photo.thumbnail_image.name
                old_listing = photo.listing_image.name

                replace_serializer = PropertyPhotoUploadSerializer(
                    photo,
                    data={
                        "image": self.make_upload(
                            "replacement.jpg", "red"
                        ),
                    },
                    partial=True,
                )
                self.assertTrue(
                    replace_serializer.is_valid(),
                    replace_serializer.errors,
                )

                updated = replace_serializer.save()
                updated.refresh_from_db()

                self.assertNotEqual(
                    updated.content_sha256,
                    old_hash,
                )
                self.assertNotEqual(
                    updated.thumbnail_image.name,
                    old_thumbnail,
                )
                self.assertNotEqual(
                    updated.listing_image.name,
                    old_listing,
                )

                for field_name in (
                    "thumbnail_image",
                    "listing_image",
                ):
                    field = getattr(updated, field_name)
                    self.assertTrue(
                        field.storage.exists(field.name)
                    )

    def test_failed_replacement_preserves_existing_images(self):
        from unittest.mock import patch

        property_obj = Property.objects.create(
            title="Failed Replacement Test",
            property_type="apartment",
            listing_type="rent",
            price=15000,
            county="Nairobi",
            town="Roysambu",
            description="Testing failed photograph replacement.",
        )

        with TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                create_serializer = PropertyPhotoUploadSerializer(
                    data={
                        "property": property_obj.pk,
                        "image": self.make_upload(
                            "safe_original.jpg", "blue"
                        ),
                    }
                )
                self.assertTrue(
                    create_serializer.is_valid(),
                    create_serializer.errors,
                )
                photo = create_serializer.save()

                original_name = photo.image.name
                original_hash = photo.content_sha256
                thumbnail_name = photo.thumbnail_image.name
                listing_name = photo.listing_image.name

                replacement = PropertyPhotoUploadSerializer(
                    photo,
                    data={
                        "image": self.make_upload(
                            "unsafe_replacement.jpg", "red"
                        ),
                    },
                    partial=True,
                )
                self.assertTrue(
                    replacement.is_valid(),
                    replacement.errors,
                )

                with patch(
                    "properties.serializers.prepare_replacement_variants",
                    side_effect=OSError(
                        "Simulated replacement preparation failure"
                    ),
                    create=True,
                ):
                    with self.assertRaisesRegex(
                        OSError,
                        "Simulated replacement preparation failure",
                    ):
                        replacement.save()

                photo.refresh_from_db()

                self.assertEqual(photo.image.name, original_name)
                self.assertEqual(photo.content_sha256, original_hash)
                self.assertEqual(
                    photo.thumbnail_image.name,
                    thumbnail_name,
                )
                self.assertEqual(
                    photo.listing_image.name,
                    listing_name,
                )

                for field_name in (
                    "image",
                    "thumbnail_image",
                    "listing_image",
                ):
                    field = getattr(photo, field_name)
                    self.assertTrue(field.storage.exists(field.name))

    def test_storage_failure_preserves_existing_images(self):
        from unittest.mock import patch

        property_obj = Property.objects.create(
            title="Storage Failure Test",
            property_type="apartment",
            listing_type="rent",
            price=15000,
            county="Nairobi",
            town="Roysambu",
            description="Testing replacement storage failure.",
        )

        with TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                serializer = PropertyPhotoUploadSerializer(
                    data={
                        "property": property_obj.pk,
                        "image": self.make_upload(
                            "storage_original.jpg", "blue"
                        ),
                    }
                )
                self.assertTrue(serializer.is_valid(), serializer.errors)
                photo = serializer.save()

                original_names = {
                    name: getattr(photo, name).name
                    for name in (
                        "image",
                        "thumbnail_image",
                        "listing_image",
                    )
                }
                original_hash = photo.content_sha256

                replacement = PropertyPhotoUploadSerializer(
                    photo,
                    data={
                        "image": self.make_upload(
                            "storage_replacement.jpg", "red"
                        ),
                    },
                    partial=True,
                )
                self.assertTrue(
                    replacement.is_valid(),
                    replacement.errors,
                )

                storage = photo.listing_image.storage
                real_save = storage.save

                def fail_listing_save(name, content, *args, **kwargs):
                    if "property_photos/listings/" in name:
                        raise OSError("Simulated listing storage failure")
                    return real_save(name, content, *args, **kwargs)

                with patch.object(
                    storage,
                    "save",
                    side_effect=fail_listing_save,
                ):
                    with self.assertRaisesRegex(
                        OSError,
                        "Simulated listing storage failure",
                    ):
                        replacement.save()

                photo.refresh_from_db()

                self.assertEqual(photo.content_sha256, original_hash)

                remaining_files = {
                    str(path.relative_to(media_root)).replace("\\", "/")
                    for path in Path(media_root).rglob("*")
                    if path.is_file()
                }

                self.assertEqual(
                    remaining_files,
                    set(original_names.values()),
                    "Failed replacement left orphaned files in storage.",
                )

                for name, original in original_names.items():
                    field = getattr(photo, name)
                    self.assertEqual(field.name, original)
                    self.assertTrue(field.storage.exists(original))

    def test_database_failure_preserves_existing_images(self):
        from unittest.mock import patch

        property_obj = Property.objects.create(
            title="Database Failure Test",
            property_type="apartment",
            listing_type="rent",
            price=15000,
            county="Nairobi",
            town="Roysambu",
            description="Testing database failure protection.",
        )

        with TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                serializer = PropertyPhotoUploadSerializer(
                    data={
                        "property": property_obj.pk,
                        "image": self.make_upload(
                            "database_original.jpg", "blue"
                        ),
                    }
                )
                self.assertTrue(serializer.is_valid(), serializer.errors)
                photo = serializer.save()

                original_names = {
                    name: getattr(photo, name).name
                    for name in (
                        "image",
                        "thumbnail_image",
                        "listing_image",
                    )
                }
                original_hash = photo.content_sha256

                replacement = PropertyPhotoUploadSerializer(
                    photo,
                    data={
                        "image": self.make_upload(
                            "database_replacement.jpg", "red"
                        ),
                    },
                    partial=True,
                )
                self.assertTrue(
                    replacement.is_valid(),
                    replacement.errors,
                )

                from properties.models import PropertyPhoto

                with patch.object(
                    PropertyPhoto,
                    "save",
                    side_effect=OSError(
                        "Simulated database save failure"
                    ),
                ):
                    with self.assertRaisesRegex(
                        OSError,
                        "Simulated database save failure",
                    ):
                        replacement.save()

                photo.refresh_from_db()

                self.assertEqual(photo.content_sha256, original_hash)

                for name, original in original_names.items():
                    field = getattr(photo, name)
                    self.assertEqual(field.name, original)
                    self.assertTrue(field.storage.exists(original))

                remaining_files = {
                    str(path.relative_to(media_root)).replace("\\", "/")
                    for path in Path(media_root).rglob("*")
                    if path.is_file()
                }

                self.assertEqual(
                    remaining_files,
                    set(original_names.values()),
                    "Database failure left orphaned replacement files.",
                )
