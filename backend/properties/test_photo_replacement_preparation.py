from io import BytesIO
from unittest import TestCase

from PIL import Image

from properties.photo_variants import prepare_replacement_variants


class ReplacementPreparationTests(TestCase):

    def test_prepares_both_variants_without_modifying_original(self):
        source = BytesIO()

        Image.new("RGB", (1800, 1200), "red").save(
            source,
            format="JPEG",
        )

        original_bytes = source.getvalue()
        source.seek(0)

        prepared = prepare_replacement_variants(source)

        self.assertEqual(
            set(prepared.keys()),
            {"thumbnail", "listing"},
        )

        for variant_name, expected_size in (
            ("thumbnail", (360, 240)),
            ("listing", (900, 600)),
        ):
            with Image.open(prepared[variant_name]) as image:
                self.assertEqual(image.format, "JPEG")
                self.assertEqual(image.size, expected_size)

        self.assertEqual(source.getvalue(), original_bytes)
        self.assertEqual(source.tell(), 0)
