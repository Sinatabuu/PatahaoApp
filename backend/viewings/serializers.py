from datetime import date

from django.db import transaction
from rest_framework import serializers

from properties.models import Property

from .models import (
    Viewing,
    ViewingBooking,
    ViewingBookingItem,
    ViewingEvent,
)


class ViewingEventSerializer(serializers.ModelSerializer):
    event_label = serializers.CharField(
        source="get_event_type_display",
        read_only=True,
    )

    actor_name = serializers.SerializerMethodField()

    class Meta:
        model = ViewingEvent

        fields = [
            "id",
            "event_type",
            "event_label",
            "actor",
            "actor_name",
            "notes",
            "metadata",
            "created_at",
        ]

        read_only_fields = fields

    def get_actor_name(self, obj):
        if obj.actor is None:
            return ""

        full_name = obj.actor.get_full_name().strip()

        return full_name or obj.actor.get_username()


class ViewingSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(
        source="customer.get_full_name",
        read_only=True,
    )

    property_title = serializers.CharField(
        source="property.title",
        read_only=True,
    )

    assigned_partner_name = serializers.SerializerMethodField()

    booking_status = serializers.CharField(
        source="status",
        read_only=True,
    )

    operational_status = serializers.SerializerMethodField()

    partner_departed_at = serializers.SerializerMethodField()
    partner_arrived_at = serializers.SerializerMethodField()
    viewing_started_at = serializers.SerializerMethodField()
    completion_notes = serializers.SerializerMethodField()

    class Meta:
        model = Viewing

        fields = [
            "id",
            "customer",
            "customer_name",
            "property",
            "property_title",
            "assigned_partner",
            "assigned_partner_name",
            "requested_date",
            "requested_time",
            "customer_message",
            "fee_amount",
            "status",
            "booking_status",
            "operational_status",
            "payment_reference",
            "partner_response_message",
            "proposed_date",
            "proposed_time",
            "confirmed_date",
            "confirmed_time",
            "partner_responded_at",
            "completed_at",
            "partner_departed_at",
            "partner_arrived_at",
            "viewing_started_at",
            "completion_notes",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "customer",
            "customer_name",
            "property_title",
            "assigned_partner",
            "assigned_partner_name",
            "fee_amount",
            "status",
            "booking_status",
            "operational_status",
            "payment_reference",
            "partner_response_message",
            "proposed_date",
            "proposed_time",
            "confirmed_date",
            "confirmed_time",
            "partner_responded_at",
            "completed_at",
            "partner_departed_at",
            "partner_arrived_at",
            "viewing_started_at",
            "completion_notes",
            "created_at",
            "updated_at",
        ]

    def get_assigned_partner_name(self, obj):
        if obj.assigned_partner is None:
            return ""

        return str(obj.assigned_partner)

    def get_operational_status(self, obj):
        return obj.operational_status

    def _latest_event(self, obj, event_type):
        return (
            obj.events.filter(
                event_type=event_type,
            )
            .order_by(
                "-created_at",
                "-id",
            )
            .first()
        )

    def _event_timestamp(self, obj, event_type):
        event = self._latest_event(
            obj,
            event_type,
        )

        return event.created_at if event else None

    def get_partner_departed_at(self, obj):
        return self._event_timestamp(
            obj,
            ViewingEvent.EventType.PARTNER_EN_ROUTE,
        )

    def get_partner_arrived_at(self, obj):
        return self._event_timestamp(
            obj,
            ViewingEvent.EventType.PARTNER_ARRIVED,
        )

    def get_viewing_started_at(self, obj):
        return self._event_timestamp(
            obj,
            ViewingEvent.EventType.VIEWING_STARTED,
        )

    def get_completion_notes(self, obj):
        event = self._latest_event(
            obj,
            ViewingEvent.EventType.VIEWING_COMPLETED,
        )

        return event.notes if event else ""

    def validate_requested_date(self, value):
        if value < date.today():
            raise serializers.ValidationError(
                "The viewing date cannot be in the past."
            )

        return value

    def validate(self, attrs):
        property_obj = attrs.get("property")
        requested_date = attrs.get("requested_date")
        requested_time = attrs.get("requested_time")

        if not property_obj:
            raise serializers.ValidationError(
                {
                    "property": "Please select a property.",
                }
            )

        if property_obj.status != Property.STATUS_PUBLISHED:
            raise serializers.ValidationError(
                {
                    "property": (
                        "This property is no longer available "
                        "for viewing."
                    ),
                }
            )

        if not requested_date:
            raise serializers.ValidationError(
                {
                    "requested_date": (
                        "Please select a viewing date."
                    ),
                }
            )

        if not requested_time:
            raise serializers.ValidationError(
                {
                    "requested_time": (
                        "Please select a viewing time."
                    ),
                }
            )

        request = self.context.get("request")

        if request and request.user.is_authenticated:
            duplicate_exists = Viewing.objects.filter(
                customer=request.user,
                property=property_obj,
                requested_date=requested_date,
                requested_time=requested_time,
                status__in=[
                    Viewing.Status.PENDING_PAYMENT,
                    Viewing.Status.PAYMENT_PROCESSING,
                    Viewing.Status.PAID_PENDING_PARTNER,
                    Viewing.Status.RESCHEDULE_PROPOSED,
                    Viewing.Status.CONFIRMED,
                ],
            ).exists()

            if duplicate_exists:
                raise serializers.ValidationError(
                    "You already have an active viewing request "
                    "for this property at the selected date "
                    "and time."
                )

        return attrs


class ViewingBookingItemSerializer(
    serializers.ModelSerializer,
):
    property_title = serializers.CharField(
        source="property.title",
        read_only=True,
    )

    listing_type = serializers.CharField(
        source="property.listing_type",
        read_only=True,
    )

    class Meta:
        model = ViewingBookingItem

        fields = [
            "id",
            "property",
            "property_title",
            "listing_type",
            "viewing_time",
            "position",
        ]


class ViewingBookingSerializer(
    serializers.ModelSerializer,
):
    items = ViewingBookingItemSerializer(
        many=True,
        read_only=True,
    )

    customer_name = serializers.CharField(
        source="customer.get_full_name",
        read_only=True,
    )

    assigned_partner_name = serializers.SerializerMethodField()

    class Meta:
        model = ViewingBooking

        fields = [
            "id",
            "customer",
            "customer_name",
            "booking_type",
            "viewing_date",
            "total_amount",
            "status",
            "payment_reference",
            "assigned_partner",
            "assigned_partner_name",
            "items",
            "created_at",
            "updated_at",
        ]

        read_only_fields = fields

    def get_assigned_partner_name(self, obj):
        if obj.assigned_partner is None:
            return ""

        return str(obj.assigned_partner)


class ViewingBookingCreateSerializer(
    serializers.Serializer,
):
    property_ids = serializers.ListField(
        child=serializers.IntegerField(
            min_value=1,
        ),
        min_length=1,
        max_length=3,
    )

    viewing_date = serializers.DateField()

    def validate_viewing_date(self, value):
        if value < date.today():
            raise serializers.ValidationError(
                "The viewing date cannot be in the past."
            )

        return value

    def validate_property_ids(self, value):
        unique_ids = list(
            dict.fromkeys(value)
        )

        if len(unique_ids) != len(value):
            raise serializers.ValidationError(
                "The same property cannot be selected "
                "more than once."
            )

        return unique_ids

    def validate(self, attrs):
        property_ids = attrs["property_ids"]

        properties_by_id = {
            property_obj.id: property_obj
            for property_obj in Property.objects.filter(
                id__in=property_ids,
            )
        }

        if len(properties_by_id) != len(property_ids):
            raise serializers.ValidationError(
                {
                    "property_ids": (
                        "One or more selected properties "
                        "do not exist."
                    ),
                }
            )

        properties = [
            properties_by_id[property_id]
            for property_id in property_ids
        ]

        listing_types = {
            property_obj.listing_type
            for property_obj in properties
        }

        if len(listing_types) != 1:
            raise serializers.ValidationError(
                {
                    "property_ids": (
                        "Rental and sales properties cannot "
                        "be combined in one viewing booking."
                    ),
                }
            )

        listing_type = listing_types.pop()
        property_count = len(properties)

        if listing_type == "sale":
            if property_count != 1:
                raise serializers.ValidationError(
                    {
                        "property_ids": (
                            "A sales viewing can contain "
                            "only one property."
                        ),
                    }
                )

            booking_type = (
                ViewingBooking.BookingType.SALE_SINGLE
            )

        elif listing_type == "rent":
            if property_count == 1:
                booking_type = (
                    ViewingBooking.BookingType.RENTAL_SINGLE
                )

            elif property_count in {2, 3}:
                booking_type = (
                    ViewingBooking.BookingType.RENTAL_THREE
                )

            else:
                raise serializers.ValidationError(
                    {
                        "property_ids": (
                            "Select between one and three "
                            "rental properties."
                        ),
                    }
                )

        else:
            raise serializers.ValidationError(
                {
                    "property_ids": (
                        "The selected listing type "
                        "is not supported."
                    ),
                }
            )

        inactive_properties = [
            property_obj.title
            for property_obj in properties
            if property_obj.status
            != Property.STATUS_PUBLISHED
        ]

        if inactive_properties:
            raise serializers.ValidationError(
                {
                    "property_ids": (
                        "These properties are not currently "
                        "available: "
                        + ", ".join(inactive_properties)
                    ),
                }
            )

        attrs["properties"] = properties
        attrs["booking_type"] = booking_type

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        request = self.context["request"]

        properties = validated_data.pop(
            "properties"
        )

        booking_type = validated_data.pop(
            "booking_type"
        )

        booking = ViewingBooking.objects.create(
            customer=request.user,
            booking_type=booking_type,
            viewing_date=validated_data["viewing_date"],
            status=(
                ViewingBooking.Status.PENDING_PAYMENT
            ),
        )

        for index, property_obj in enumerate(
            properties,
            start=1,
        ):
            ViewingBookingItem.objects.create(
                booking=booking,
                property=property_obj,
                position=index,
            )

        return booking