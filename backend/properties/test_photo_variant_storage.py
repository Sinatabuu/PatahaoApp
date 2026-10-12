from io import BytesIO
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.files.base import ContentFile
from django.test import SimpleTestCase, override_settings
from PIL import Image

from properties.models import PropertyPhoto
from properties.photo_optimization import optimize_property_photo


class PhotoVariantStorageTests(SimpleTestCase):

    def test_optimized_variants_save_to_storage(self):
        source = BytesIO()
        Image.new("RGB", (1800, 1200), "lightblue").save(
            source, format="PNG"
        )
        source.seek(0)

        with TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                photo = PropertyPhoto()

                for field_name, width in (
                    ("thumbnail_image", 360),
                    ("listing_image", 900),
                ):
                    data = optimize_property_photo(source, width)

                    field = getattr(photo, field_name)
                    field.save(
                        f"test_{field_name}.jpg",
                        ContentFile(data),
                        save=False,
                    )

                    self.assertTrue(field.storage.exists(field.name))

                    with field.storage.open(field.name, "rb") as stored:
                        with Image.open(stored) as image:
                            self.assertEqual(image.width, width)

                self.assertFalse(bool(photo.image))
