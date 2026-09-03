from dataclasses import dataclass
from hashlib import sha256

from django.core.exceptions import ValidationError
from PIL import (
    Image,
    ImageFilter,
    ImageOps,
    ImageStat,
    UnidentifiedImageError,
)


MAX_PHOTO_BYTES = 10 * 1024 * 1024
MIN_PHOTO_SHORT_EDGE = 720
MIN_PHOTO_LONG_EDGE = 1280
ALLOWED_PHOTO_FORMATS = {
    "JPEG",
    "PNG",
    "WEBP",
}

LOW_LIGHT_THRESHOLD = 45
OVEREXPOSED_THRESHOLD = 235
BLUR_EDGE_VARIANCE_THRESHOLD = 75


@dataclass(frozen=True)
class PhotoQualityAnalysis:
    width: int
    height: int
    file_size: int
    image_format: str
    content_sha256: str
    quality_status: str
    quality_score: int
    quality_warnings: tuple[str, ...]


def _file_object(uploaded_file):
    return getattr(
        uploaded_file,
        "file",
        uploaded_file,
    )


def _seek(file_obj, position=0):
    try:
        file_obj.seek(position)
    except (AttributeError, OSError):
        pass


def _content_sha256(file_obj):
    digest = sha256()
    _seek(file_obj)

    while True:
        chunk = file_obj.read(64 * 1024)

        if not chunk:
            break

        digest.update(chunk)

    _seek(file_obj)
    return digest.hexdigest()


def analyze_property_photo(uploaded_file):
    """
    Apply inexpensive, deterministic checks to an uploaded photo.

    Hard failures protect storage and listing quality. Lighting and
    possible-blur findings remain advisory so staff retain final
    review control.
    """

    file_size = int(
        getattr(
            uploaded_file,
            "size",
            0,
        )
        or 0
    )

    if file_size <= 0:
        raise ValidationError(
            "The selected photo is empty."
        )

    if file_size > MAX_PHOTO_BYTES:
        raise ValidationError(
            "Property photos must be 10 MB or smaller."
        )

    file_obj = _file_object(uploaded_file)
    content_hash = _content_sha256(file_obj)

    try:
        with Image.open(file_obj) as opened_image:
            image_format = (
                opened_image.format
                or ""
            ).upper()

            if image_format not in ALLOWED_PHOTO_FORMATS:
                raise ValidationError(
                    "Use a JPEG, PNG, or WebP property photo."
                )

            image = ImageOps.exif_transpose(
                opened_image,
            )
            image.load()

            width, height = image.size
            short_edge = min(width, height)
            long_edge = max(width, height)

            if (
                short_edge < MIN_PHOTO_SHORT_EDGE
                or long_edge < MIN_PHOTO_LONG_EDGE
            ):
                raise ValidationError(
                    "Property photos must be at least "
                    "1280 x 720 pixels in either orientation."
                )

            sample = image.copy()
            sample.thumbnail(
                (
                    512,
                    512,
                )
            )

            grayscale = ImageOps.grayscale(sample)

            brightness = ImageStat.Stat(
                grayscale,
            ).mean[0]

            edge_variance = ImageStat.Stat(
                grayscale.filter(
                    ImageFilter.FIND_EDGES,
                )
            ).var[0]

    except ValidationError:
        raise
    except (
        Image.DecompressionBombError,
        UnidentifiedImageError,
        OSError,
        ValueError,
    ) as exc:
        raise ValidationError(
            "The selected file is not a readable property photo."
        ) from exc
    finally:
        _seek(file_obj)
        _seek(uploaded_file)

    warnings = []

    if brightness < LOW_LIGHT_THRESHOLD:
        warnings.append(
            "The photo may be too dark."
        )
    elif brightness > OVEREXPOSED_THRESHOLD:
        warnings.append(
            "The photo may be overexposed."
        )

    if edge_variance < BLUR_EDGE_VARIANCE_THRESHOLD:
        warnings.append(
            "The photo may be blurry or lack detail."
        )

    quality_score = max(
        40,
        100 - (20 * len(warnings)),
    )

    quality_status = (
        "needs_review"
        if warnings
        else "accepted"
    )

    return PhotoQualityAnalysis(
        width=width,
        height=height,
        file_size=file_size,
        image_format=image_format,
        content_sha256=content_hash,
        quality_status=quality_status,
        quality_score=quality_score,
        quality_warnings=tuple(warnings),
    )
