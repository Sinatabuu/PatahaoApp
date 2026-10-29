"""Generate optimized variants for property photographs."""

from pathlib import Path

from django.core.files.base import ContentFile

from .photo_optimization import (
    IMAGE_VARIANTS,
    optimize_property_photo,
)


def generate_photo_variants(photo):
    """
    Generate optimized photograph variants.

    The original image is never modified.
    Newly created variants are cleaned up if generation fails.
    Database changes are not saved by this function.
    """
    if not photo.image:
        raise ValueError("An original photograph is required.")

    original_name = Path(photo.image.name).stem
    created_files = []
    original_values = {
        "thumbnail_image": photo.thumbnail_image.name,
        "listing_image": photo.listing_image.name,
    }

    try:
        with photo.image.open("rb") as source:
            for variant_name, width in IMAGE_VARIANTS.items():
                optimized_bytes = optimize_property_photo(
                    source,
                    width,
                )

                field_name = {
                    "thumbnail": "thumbnail_image",
                    "listing": "listing_image",
                }[variant_name]

                field = getattr(photo, field_name)
                filename = f"{original_name}_{variant_name}.jpg"

                field.save(
                    filename,
                    ContentFile(optimized_bytes),
                    save=False,
                )

                created_files.append(
                    (field.storage, field.name)
                )

        return photo

    except Exception:
        for storage, filename in reversed(created_files):
            try:
                storage.delete(filename)
            except Exception:
                # Preserve the original failure.
                pass

        for field_name, original_value in original_values.items():
            getattr(photo, field_name).name = original_value

        raise


def prepare_replacement_variants(uploaded_image):
    """
    Prepare optimized replacement images in memory.

    Does not write to storage or modify a database record.
    The caller is responsible for saving the prepared files.
    """
    from io import BytesIO

    prepared = {}

    for variant_name, width in IMAGE_VARIANTS.items():
        uploaded_image.seek(0)

        optimized_bytes = optimize_property_photo(
            uploaded_image,
            width,
        )

        prepared[variant_name] = ContentFile(
            optimized_bytes,
            name=f"{variant_name}.jpg",
        )

    uploaded_image.seek(0)

    return prepared
