from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from .models import Property
from .serializers import PropertyCardSerializer, PropertySerializer


class PropertyMeasurementTests(TestCase):
    def property_data(self):
        return {
            "title": "Roysambu Marketing Home",
            "property_type": Property.TYPE_HOUSE,
            "listing_type": Property.LISTING_SALE,
            "price": "12500000.00",
            "county": "Nairobi",
            "town": "Roysambu",
            "estate": "Garden Estate",
            "address": "Test address",
            "bedrooms": 4,
            "bathrooms": 3,
            "description": "Bright family home with a private garden.",
        }

    def test_measurements_are_optional_for_existing_listings(self):
        serializer = PropertySerializer(data=self.property_data())

        self.assertTrue(serializer.is_valid(), serializer.errors)
        property_obj = serializer.save()

        self.assertIsNone(property_obj.floor_area)
        self.assertIsNone(property_obj.land_area)

    def test_full_and_compact_serializers_expose_measurements(self):
        property_obj = Property.objects.create(
            **self.property_data(),
            floor_area=Decimal("1850.50"),
            floor_area_unit=Property.AREA_UNIT_SQUARE_FEET,
            land_area=Decimal("0.1250"),
            land_area_unit=Property.AREA_UNIT_ACRES,
        )

        for serializer_class in (PropertySerializer, PropertyCardSerializer):
            payload = serializer_class(property_obj).data

            self.assertEqual(payload["floor_area"], "1850.50")
            self.assertEqual(payload["floor_area_unit"], "sq_ft")
            self.assertEqual(payload["land_area"], "0.1250")
            self.assertEqual(payload["land_area_unit"], "acres")

    def test_measurements_must_be_positive(self):
        property_obj = Property(
            **self.property_data(),
            floor_area=Decimal("0"),
            land_area=Decimal("-1"),
        )

        with self.assertRaises(ValidationError) as error:
            property_obj.full_clean()

        self.assertIn("floor_area", error.exception.message_dict)
        self.assertIn("land_area", error.exception.message_dict)

    def test_serializer_rejects_unknown_measurement_unit(self):
        serializer = PropertySerializer(
            data={
                **self.property_data(),
                "floor_area": "1000.00",
                "floor_area_unit": "yards",
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("floor_area_unit", serializer.errors)
