MINIMUM_PROPERTY_PHOTO_COUNT = 5

PHOTO_TYPE_EXTERIOR = "exterior"
PHOTO_TYPE_LIVING_AREA = "living_area"
PHOTO_TYPE_BEDROOM = "bedroom"
PHOTO_TYPE_KITCHEN = "kitchen"
PHOTO_TYPE_BATHROOM = "bathroom"
PHOTO_TYPE_SITE_OVERVIEW = "site_overview"
PHOTO_TYPE_BOUNDARY = "boundary"
PHOTO_TYPE_ACCESS = "access"
PHOTO_TYPE_MAIN_SPACE = "main_space"
PHOTO_TYPE_AMENITY = "amenity"
PHOTO_TYPE_OTHER = "other"

PHOTO_TYPE_CHOICES = (
    (PHOTO_TYPE_EXTERIOR, "Exterior"),
    (PHOTO_TYPE_LIVING_AREA, "Living area"),
    (PHOTO_TYPE_BEDROOM, "Bedroom"),
    (PHOTO_TYPE_KITCHEN, "Kitchen"),
    (PHOTO_TYPE_BATHROOM, "Bathroom"),
    (PHOTO_TYPE_SITE_OVERVIEW, "Site overview"),
    (PHOTO_TYPE_BOUNDARY, "Boundary"),
    (PHOTO_TYPE_ACCESS, "Access or entrance"),
    (PHOTO_TYPE_MAIN_SPACE, "Main commercial space"),
    (PHOTO_TYPE_AMENITY, "Amenity"),
    (PHOTO_TYPE_OTHER, "Other"),
)

PHOTO_TYPE_LABELS = dict(PHOTO_TYPE_CHOICES)

RESIDENTIAL_PROPERTY_TYPES = {
    "apartment",
    "house",
}

COMMERCIAL_PROPERTY_TYPES = {
    "office",
    "shop",
    "warehouse",
}


def required_photo_types_for(property_obj):
    property_type = property_obj.property_type

    if property_type in RESIDENTIAL_PROPERTY_TYPES:
        required = [
            PHOTO_TYPE_EXTERIOR,
            PHOTO_TYPE_LIVING_AREA,
            PHOTO_TYPE_KITCHEN,
        ]

        if property_obj.bedrooms > 0:
            required.append(PHOTO_TYPE_BEDROOM)

        if property_obj.bathrooms > 0:
            required.append(PHOTO_TYPE_BATHROOM)

        return tuple(required)

    if property_type == "land":
        return (
            PHOTO_TYPE_SITE_OVERVIEW,
            PHOTO_TYPE_BOUNDARY,
            PHOTO_TYPE_ACCESS,
        )

    if property_type in COMMERCIAL_PROPERTY_TYPES:
        required = [
            PHOTO_TYPE_EXTERIOR,
            PHOTO_TYPE_MAIN_SPACE,
            PHOTO_TYPE_ACCESS,
        ]

        if property_obj.bathrooms > 0:
            required.append(PHOTO_TYPE_BATHROOM)

        return tuple(required)

    return (PHOTO_TYPE_EXTERIOR,)


def evaluate_photo_coverage(property_obj, photos):
    photo_list = list(photos)
    required_types = required_photo_types_for(property_obj)

    present_types = {
        photo.photo_type
        for photo in photo_list
    }

    missing_types = [
        photo_type
        for photo_type in required_types
        if photo_type not in present_types
    ]

    photo_count = len(photo_list)

    return {
        "complete": (
            photo_count >= MINIMUM_PROPERTY_PHOTO_COUNT
            and not missing_types
        ),
        "photo_count": photo_count,
        "minimum_photo_count": MINIMUM_PROPERTY_PHOTO_COUNT,
        "required_photo_types": list(required_types),
        "required_photo_labels": [
            PHOTO_TYPE_LABELS[photo_type]
            for photo_type in required_types
        ],
        "missing_photo_types": missing_types,
        "missing_photo_labels": [
            PHOTO_TYPE_LABELS[photo_type]
            for photo_type in missing_types
        ],
    }
