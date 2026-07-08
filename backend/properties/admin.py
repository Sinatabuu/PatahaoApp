from django.contrib import admin
from .models import Property, PropertyPhoto


class PropertyPhotoInline(admin.TabularInline):
    model = PropertyPhoto
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

    inlines = [PropertyPhotoInline]


@admin.register(PropertyPhoto)
class PropertyPhotoAdmin(admin.ModelAdmin):
    list_display = (
        "property",
        "caption",
        "is_cover",
        "uploaded_at",
    )

    list_filter = ("is_cover",)
