from django.db import models


class Property(models.Model):
    TYPE_APARTMENT = "apartment"
    TYPE_HOUSE = "house"
    TYPE_LAND = "land"
    TYPE_OFFICE = "office"
    TYPE_SHOP = "shop"
    TYPE_WAREHOUSE = "warehouse"

    PROPERTY_TYPE_CHOICES = [
        (TYPE_APARTMENT, "Apartment"),
        (TYPE_HOUSE, "House"),
        (TYPE_LAND, "Land"),
        (TYPE_OFFICE, "Office"),
        (TYPE_SHOP, "Shop"),
        (TYPE_WAREHOUSE, "Warehouse"),
    ]

    LISTING_TYPE_CHOICES = [
        ("rent", "Rent"),
        ("sale", "Sale"),
    ]

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("pending", "Pending Verification"),
        ("published", "Published"),
        ("reserved", "Reserved"),
        ("rented", "Rented"),
        ("sold", "Sold"),
        ("archived", "Archived"),
    ]

    TRUST_BADGE_CHOICES = [
        ("none", "None"),
        ("bronze", "Bronze"),
        ("silver", "Silver"),
        ("gold", "Gold"),
    ]

    partner = models.ForeignKey(
        "partners.Partner",
        on_delete=models.CASCADE,
        related_name="properties",
    )

    title = models.CharField(max_length=255)
    property_type = models.CharField(max_length=30, choices=PROPERTY_TYPE_CHOICES)
    listing_type = models.CharField(max_length=20, choices=LISTING_TYPE_CHOICES)
    price = models.DecimalField(max_digits=14, decimal_places=2)

    county = models.CharField(max_length=100)
    town = models.CharField(max_length=100)
    estate = models.CharField(max_length=100, blank=True)
    address = models.CharField(max_length=255, blank=True)

    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)

    bedrooms = models.PositiveIntegerField(default=0)
    bathrooms = models.PositiveIntegerField(default=0)

    description = models.TextField()

    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="draft")
    trust_badge = models.CharField(max_length=20, choices=TRUST_BADGE_CHOICES, default="none")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class PropertyPhoto(models.Model):
    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name="photos",
    )

    image = models.ImageField(upload_to="property_photos/")
    caption = models.CharField(max_length=255, blank=True)
    is_cover = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_cover", "uploaded_at"]

    def __str__(self):
        return f"Photo for {self.property.title}"
