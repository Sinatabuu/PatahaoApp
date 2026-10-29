from io import BytesIO
from unittest import TestCase

from PIL import Image

from properties.photo_optimization import optimize_property_photo


class PhotoOptimizationTests(TestCase):

    def make_image(self, width=2400, height=1600):
        image = Image.new("RGB", (width, height), "lightblue")
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        buffer.seek(0)
        return buffer

    def test_thumbnail_dimensions(self):
        source = self.make_image()

        result = optimize_property_photo(source, 360)

        with Image.open(BytesIO(result)) as image:
            self.assertEqual(image.format, "JPEG")
            self.assertEqual(image.size, (360, 240))

    def test_listing_dimensions(self):
        source = self.make_image()

        result = optimize_property_photo(source, 900)

        with Image.open(BytesIO(result)) as image:
            self.assertEqual(image.size, (900, 600))

    def test_original_is_preserved(self):
        source = self.make_image()
        original_bytes = source.getvalue()

        result = optimize_property_photo(source, 360)

        self.assertEqual(source.getvalue(), original_bytes)
        self.assertEqual(source.tell(), 0)
        self.assertLess(len(result), len(original_bytes))

    def test_transparent_image_has_white_background(self):
        source = BytesIO()
        image = Image.new("RGBA", (1600, 900), (0, 0, 0, 0))
        image.save(source, format="PNG")
        source.seek(0)

        result = optimize_property_photo(source, 360)

        with Image.open(BytesIO(result)) as optimized:
            pixel = optimized.getpixel((0, 0))
            self.assertTrue(all(channel >= 245 for channel in pixel))

    def test_exif_orientation_is_applied(self):
        source = BytesIO()
        image = Image.new("RGB", (1600, 900), "blue")
        exif = Image.Exif()
        exif[274] = 6
        image.save(source, format="JPEG", exif=exif)
        source.seek(0)

        result = optimize_property_photo(source, 360)

        with Image.open(BytesIO(result)) as optimized:
            self.assertEqual(optimized.size, (360, 640))
