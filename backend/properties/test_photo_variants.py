from io import BytesIO
from tempfile import TemporaryDirectory

from django.core.files.base import ContentFile
from django.test import SimpleTestCase, override_settings
from PIL import Image

from properties.models import PropertyPhoto
from properties.photo_variants import generate_photo_variants


class PhotoVariantGenerationTests(SimpleTestCase):

    def test_generates_both_variants_without_changing_original(self):
        source = BytesIO()
        Image.new("RGB", (1800, 1200), "lightblue").save(
            source, format="PNG"
        )
        original_bytes = source.getvalue()

        with TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                photo = PropertyPhoto()

                photo.image.save(
                    "test_original.png",
                    ContentFile(original_bytes),
                    save=False,
                )

                original_name = photo.image.name

                generate_photo_variants(photo)

                self.assertEqual(photo.image.name, original_name)

                for field_name, expected_size in (
                    ("thumbnail_image", (360, 240)),
                    ("listing_image", (900, 600)),
                ):
                    field = getattr(photo, field_name)

                    self.assertTrue(field.name)
                    self.assertTrue(field.storage.exists(field.name))

                    with field.open("rb") as stored:
                        with Image.open(stored) as image:
                            self.assertEqual(image.size, expected_size)
                            self.assertEqual(image.format, "JPEG")

                with photo.image.open("rb") as original:
                    self.assertEqual(original.read(), original_bytes)

    def test_failed_listing_upload_cleans_up_thumbnail(self):
        from unittest.mock import patch

        source = BytesIO()
        Image.new("RGB", (1800, 1200), "lightblue").save(
            source, format="PNG"
        )
        original_bytes = source.getvalue()

        with TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                photo = PropertyPhoto()
                photo.image.save(
                    "failure_test_original.png",
                    ContentFile(original_bytes),
                    save=False,
                )

                original_name = photo.image.name
                listing_field = photo._meta.get_field("listing_image")
                storage = listing_field.storage
                original_save = storage.save

                def fail_listing_save(name, content, *args, **kwargs):
                    if "listings/" in name:
                        raise OSError("Simulated R2 listing upload failure")
                    return original_save(name, content, *args, **kwargs)

                with patch.object(
                    storage,
                    "save",
                    side_effect=fail_listing_save,
                ):
                    with self.assertRaisesRegex(
                        OSError,
                        "Simulated R2 listing upload failure",
                    ):
                        generate_photo_variants(photo)

                self.assertFalse(bool(photo.thumbnail_image))
                self.assertFalse(bool(photo.listing_image))

                self.assertEqual(photo.image.name, original_name)

                with photo.image.open("rb") as original:
                    self.assertEqual(original.read(), original_bytes)

                thumbnail_name = (
                    "property_photos/thumbnails/"
                    "failure_test_original_thumbnail.jpg"
                )
                self.assertFalse(storage.exists(thumbnail_name))
