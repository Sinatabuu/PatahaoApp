from dataclasses import dataclass, field

from properties.models import Property
from properties.photo_coverage import evaluate_photo_coverage


@dataclass(frozen=True)
class PropertySubmissionReadiness:
    ready: bool
    missing_fields: tuple[str, ...]
    photo_coverage: dict
    has_cover: bool


def evaluate_property_submission_readiness(
    property_obj: Property,
) -> PropertySubmissionReadiness:
    """Evaluate the partner-to-staff property review handoff."""

    required_fields = {
        "title": property_obj.title.strip(),
        "property type": property_obj.property_type,
        "listing type": property_obj.listing_type,
        "price": (
            property_obj.price is not None
            and property_obj.price > 0
        ),
        "county": property_obj.county.strip(),
        "town": property_obj.town.strip(),
        "description": property_obj.description.strip(),
        "GPS latitude": property_obj.latitude is not None,
        "GPS longitude": property_obj.longitude is not None,
    }

    missing_fields = tuple(
        label
        for label, value in required_fields.items()
        if not value
    )

    photos = list(property_obj.photos.all())
    photo_coverage = evaluate_photo_coverage(
        property_obj,
        photos,
    )
    has_cover = any(photo.is_cover for photo in photos)

    return PropertySubmissionReadiness(
        ready=(
            not missing_fields
            and photo_coverage["complete"]
            and has_cover
        ),
        missing_fields=missing_fields,
        photo_coverage=photo_coverage,
        has_cover=has_cover,
    )


def submit_property_for_verification_if_ready(
    property_obj: Property,
    *,
    actor,
    automatic=False,
) -> tuple[PropertySubmissionReadiness, bool]:
    """Move a complete draft into staff review without bypassing checks."""

    readiness = evaluate_property_submission_readiness(
        property_obj,
    )

    if (
        property_obj.status != Property.STATUS_DRAFT
        or not readiness.ready
    ):
        return readiness, False

    property_obj.status = Property.STATUS_PENDING
    property_obj.save(
        update_fields=[
            "status",
            "updated_at",
        ]
    )

    from core.models import ActivityLog

    if automatic:
        description = (
            f"{property_obj.title} automatically entered property "
            "verification after Pata Hao approved its authorization."
        )
    else:
        description = (
            f"{property_obj.partner} submitted property "
            f"{property_obj.title} for verification."
        )

    ActivityLog.objects.create(
        actor=actor,
        action="property_submitted_for_verification",
        entity_type="Property",
        entity_id=str(property_obj.id),
        description=description,
    )

    return readiness, True


@dataclass
class PublishingResult:
    can_publish: bool
    readiness_score: int
    passed_checks: list[str] = field(default_factory=list)
    missing_requirements: list[str] = field(default_factory=list)


class PublishingEngine:
    REQUIRED_PHOTO_COUNT = 5

    @classmethod
    def evaluate(cls, property_obj: Property) -> PublishingResult:
        passed = []
        missing = []

        partner = property_obj.partner

        # 1. Partner checks
        if partner is None:
            missing.append("Assign a partner to the property.")
        else:
            if partner.is_verified:
                passed.append("Partner is verified.")
            else:
                missing.append("Partner verification is required.")

            if partner.accepts_viewing_requests:
                passed.append("Partner accepts viewing requests.")
            else:
                missing.append(
                    "Partner must accept viewing requests."
                )

            if partner.commission_plan_id:
                passed.append("Partner commission plan is assigned.")
            else:
                missing.append(
                    "Partner commission plan must be assigned."
                )

        # 2. Property information
        required_text_fields = {
            "title": "Property title is required.",
            "description": "Property description is required.",
            "county": "County is required.",
            "town": "Town is required.",
            "property_type": "Property type is required.",
            "listing_type": "Listing type is required.",
        }

        for field_name, message in required_text_fields.items():
            value = getattr(property_obj, field_name, None)

            if isinstance(value, str):
                value = value.strip()

            if value:
                passed.append(
                    f"{field_name.replace('_', ' ').title()} is complete."
                )
            else:
                missing.append(message)

        if property_obj.price and property_obj.price > 0:
            passed.append("Property price is valid.")
        else:
            missing.append(
                "Property price must be greater than zero."
            )

        # 3. Photo checks
        photo_count = property_obj.photos.count()

        if photo_count >= cls.REQUIRED_PHOTO_COUNT:
            passed.append(
                f"Property has at least "
                f"{cls.REQUIRED_PHOTO_COUNT} photos."
            )
        else:
            photos_needed = cls.REQUIRED_PHOTO_COUNT - photo_count
            missing.append(
                f"Upload {photos_needed} more "
                f"{'photo' if photos_needed == 1 else 'photos'}."
            )

        if property_obj.photos.filter(is_cover=True).exists():
            passed.append("Cover photo is selected.")
        else:
            missing.append("Select one property cover photo.")

        total_checks = len(passed) + len(missing)

        readiness_score = (
            round((len(passed) / total_checks) * 100)
            if total_checks
            else 0
        )

        return PublishingResult(
            can_publish=len(missing) == 0,
            readiness_score=readiness_score,
            passed_checks=passed,
            missing_requirements=missing,
        )

    @classmethod
    def publish(cls, property_obj: Property) -> PublishingResult:
        result = cls.evaluate(property_obj)

        if not result.can_publish:
            return result

        property_obj.status = Property.STATUS_PUBLISHED
        property_obj.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        return result
