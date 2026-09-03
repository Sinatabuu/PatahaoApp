from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from viewings.serializers import ViewingSerializer

from .models import Property


class PropertySuccessBroadcastTestMixin:
    def create_property(
        self,
        *,
        title,
        listing_type,
    ):
        return Property.objects.create(
            title=title,
            property_type=Property.TYPE_APARTMENT,
            listing_type=listing_type,
            price=Decimal("100000.00"),
            county="Nairobi",
            town="Roysambu",
            estate="Roysambu",
            address="Test address",
            bedrooms=2,
            bathrooms=1,
            description=(
                "Property used to test transaction "
                "success broadcasts."
            ),
            status=Property.STATUS_DRAFT,
        )


class PropertySuccessBroadcastModelTests(
    PropertySuccessBroadcastTestMixin,
    TestCase,
):
    def test_sale_broadcast_runs_for_thirty_days(self):
        property_obj = self.create_property(
            title="Completed Sale",
            listing_type=Property.LISTING_SALE,
        )

        completed_at = timezone.now()

        broadcast_days = (
            property_obj.mark_transaction_completed(
                completed_at=completed_at,
            )
        )

        property_obj.refresh_from_db()

        self.assertEqual(
            broadcast_days,
            Property.SALE_SUCCESS_BROADCAST_DAYS,
        )
        self.assertEqual(
            property_obj.status,
            Property.STATUS_SOLD,
        )
        self.assertEqual(
            property_obj.transaction_completed_at,
            completed_at,
        )
        self.assertEqual(
            property_obj.success_broadcast_until,
            completed_at
            + timedelta(
                days=Property.SALE_SUCCESS_BROADCAST_DAYS,
            ),
        )
        self.assertTrue(
            property_obj.is_success_broadcast_active,
        )
        self.assertEqual(
            property_obj.success_badge,
            "Sold Through Pata Hao",
        )
        self.assertFalse(
            property_obj.is_available,
        )

    def test_rental_broadcast_runs_for_fifteen_days(self):
        property_obj = self.create_property(
            title="Completed Rental",
            listing_type=Property.LISTING_RENT,
        )

        completed_at = timezone.now()

        broadcast_days = (
            property_obj.mark_transaction_completed(
                completed_at=completed_at,
            )
        )

        property_obj.refresh_from_db()

        self.assertEqual(
            broadcast_days,
            Property.RENT_SUCCESS_BROADCAST_DAYS,
        )
        self.assertEqual(
            property_obj.status,
            Property.STATUS_RENTED,
        )
        self.assertEqual(
            property_obj.transaction_completed_at,
            completed_at,
        )
        self.assertEqual(
            property_obj.success_broadcast_until,
            completed_at
            + timedelta(
                days=Property.RENT_SUCCESS_BROADCAST_DAYS,
            ),
        )
        self.assertTrue(
            property_obj.is_success_broadcast_active,
        )
        self.assertEqual(
            property_obj.success_badge,
            "Rented Through Pata Hao",
        )
        self.assertFalse(
            property_obj.is_available,
        )

    def test_expired_broadcast_is_inactive(self):
        property_obj = self.create_property(
            title="Expired Sale Broadcast",
            listing_type=Property.LISTING_SALE,
        )

        property_obj.mark_transaction_completed(
            completed_at=(
                timezone.now()
                - timedelta(
                    days=31,
                )
            ),
        )

        property_obj.refresh_from_db()

        self.assertFalse(
            property_obj.is_success_broadcast_active,
        )
        self.assertEqual(
            property_obj.success_badge,
            "",
        )


class PublicPropertySuccessBroadcastTests(
    PropertySuccessBroadcastTestMixin,
    APITestCase,
):
    def setUp(self):
        self.published_property = self.create_property(
            title="Available Property",
            listing_type=Property.LISTING_RENT,
        )

        Property.objects.filter(
            pk=self.published_property.pk,
        ).update(
            status=Property.STATUS_PUBLISHED,
        )

        self.published_property.refresh_from_db()

        self.sold_property = self.create_property(
            title="Recently Sold Property",
            listing_type=Property.LISTING_SALE,
        )
        self.sold_property.mark_transaction_completed()

        self.rented_property = self.create_property(
            title="Recently Rented Property",
            listing_type=Property.LISTING_RENT,
        )
        self.rented_property.mark_transaction_completed()

        self.expired_property = self.create_property(
            title="Old Sold Property",
            listing_type=Property.LISTING_SALE,
        )
        self.expired_property.mark_transaction_completed(
            completed_at=(
                timezone.now()
                - timedelta(
                    days=31,
                )
            ),
        )

        self.reserved_property = self.create_property(
            title="Reserved Property",
            listing_type=Property.LISTING_RENT,
        )

        Property.objects.filter(
            pk=self.reserved_property.pk,
        ).update(
            status=Property.STATUS_RESERVED,
        )

    def response_items(self, response):
        payload = response.json()

        if isinstance(payload, dict):
            return payload.get(
                "results",
                [],
            )

        return payload

    def test_public_list_contains_only_available_and_active_broadcasts(
        self,
    ):
        response = self.client.get(
            "/api/properties/",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        items = self.response_items(response)

        returned_ids = {
            item["id"]
            for item in items
        }

        self.assertEqual(
            returned_ids,
            {
                self.published_property.id,
                self.sold_property.id,
                self.rented_property.id,
            },
        )

        sold_item = next(
            item
            for item in items
            if item["id"] == self.sold_property.id
        )

        self.assertEqual(
            sold_item["status"],
            Property.STATUS_SOLD,
        )
        self.assertFalse(
            sold_item["is_available"],
        )
        self.assertTrue(
            sold_item[
                "is_success_broadcast_active"
            ],
        )
        self.assertEqual(
            sold_item["success_badge"],
            "Sold Through Pata Hao",
        )
        self.assertIsNotNone(
            sold_item["transaction_completed_at"],
        )
        self.assertIsNotNone(
            sold_item["success_broadcast_until"],
        )

    def test_expired_broadcast_cannot_be_retrieved_publicly(
        self,
    ):
        response = self.client.get(
            (
                "/api/properties/"
                f"{self.expired_property.id}/"
            ),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )


class CompletedPropertyViewingGuardTests(
    PropertySuccessBroadcastTestMixin,
    TestCase,
):
    def test_sold_and_rented_properties_reject_new_viewings(
        self,
    ):
        cases = (
            (
                Property.LISTING_SALE,
                Property.STATUS_SOLD,
            ),
            (
                Property.LISTING_RENT,
                Property.STATUS_RENTED,
            ),
        )

        for listing_type, expected_status in cases:
            with self.subTest(
                listing_type=listing_type,
            ):
                property_obj = self.create_property(
                    title=(
                        "Unavailable "
                        f"{listing_type} property"
                    ),
                    listing_type=listing_type,
                )

                property_obj.mark_transaction_completed()
                property_obj.refresh_from_db()

                self.assertEqual(
                    property_obj.status,
                    expected_status,
                )

                serializer = ViewingSerializer(
                    data={
                        "property": property_obj.id,
                        "requested_date": (
                            timezone.localdate()
                            + timedelta(
                                days=1,
                            )
                        ),
                        "requested_time": "10:00:00",
                    },
                )

                self.assertFalse(
                    serializer.is_valid(),
                )
                self.assertIn(
                    "property",
                    serializer.errors,
                )
                self.assertIn(
                    "no longer available",
                    str(
                        serializer.errors[
                            "property"
                        ][0]
                    ).lower(),
                )
