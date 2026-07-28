from django.contrib import admin

from .models import (
    Property,
    PropertyPhoto,
    PropertyVideo,
)


class PropertyPhotoInline(admin.TabularInline):
    model = PropertyPhoto
    extra = 1


class PropertyVideoInline(admin.TabularInline):
    model = PropertyVideo
    extra = 1


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "partner",
        "property_type",
        "listing_type",
        "price",
        "town",
        "status",
        "trust_badge",
        "created_at",
    )

    list_editable = (
        "status",
    )

    list_filter = (
        "property_type",
        "listing_type",
        "status",
        "trust_badge",
        "county",
        "town",
    )

    search_fields = (
        "title",
        "description",
        "partner__business_name",
        "county",
        "town",
        "estate",
    )

    fieldsets = (
        (
            "Property ownership",
            {
                "fields": (
                    "partner",
                )
            },
        ),
        (
            "Listing details",
            {
                "fields": (
                    "title",
                    "property_type",
                    "listing_type",
                    "price",
                    "description",
                )
            },
        ),
        (
            "Location",
            {
                "fields": (
                    "county",
                    "town",
                    "estate",
                    "address",
                    "latitude",
                    "longitude",
                )
            },
        ),
        (
            "Property features",
            {
                "fields": (
                    "bedrooms",
                    "bathrooms",
                )
            },
        ),
        (
            "Availability and trust",
            {
                "fields": (
                    "status",
                    "trust_badge",
                )
            },
        ),
    )

    inlines = [
        PropertyPhotoInline,
        PropertyVideoInline,
    ]


@admin.register(PropertyPhoto)
class PropertyPhotoAdmin(admin.ModelAdmin):
    list_display = (
        "property",
        "caption",
        "is_cover",
        "uploaded_at",
    )

    list_filter = (
        "is_cover",
    )


@admin.register(PropertyVideo)
class PropertyVideoAdmin(admin.ModelAdmin):
    list_display = (
        "property",
        "title",
        "duration",
        "is_featured",
        "uploaded_at",
    )

    list_filter = (
        "is_featured",
    )

    search_fields = (
        "title",
        "property__title",
    )