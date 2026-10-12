"""Generate optimized property photographs without altering originals."""

from io import BytesIO

from PIL import Image, ImageOps


IMAGE_VARIANTS = {
    "thumbnail": 360,
    "listing": 900,
}


def optimize_property_photo(source, width, quality=80):
    """Return optimized JPEG bytes, preserving the image aspect ratio."""
    source.seek(0)

    try:
        with Image.open(source) as opened:
            image = ImageOps.exif_transpose(opened)
            image.load()

            if image.mode in ("RGBA", "LA") or (
                image.mode == "P" and "transparency" in image.info
            ):
                rgba = image.convert("RGBA")
                background = Image.new("RGB", rgba.size, "white")
                background.paste(rgba, mask=rgba.getchannel("A"))
                image = background
            elif image.mode != "RGB":
                image = image.convert("RGB")

            image.thumbnail(
                (width, width * 4),
                Image.Resampling.LANCZOS,
            )

            output = BytesIO()
            image.save(
                output,
                format="JPEG",
                quality=quality,
                optimize=True,
            )
            return output.getvalue()
    finally:
        source.seek(0)
