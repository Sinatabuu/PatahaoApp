import builtins
from decimal import Decimal


RENTAL_VIEWING_FEE = Decimal("400.00")
SALE_VIEWING_FEE = Decimal("2000.00")

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Viewing(models.Model):
    """
    A paid viewing reservation.

    The status field represents the booking and payment lifecycle.

    Live operational progress is stored as immutable ViewingEvent records.
    """

    class Status(models.TextChoices):
        PENDING_PAYMENT = (
            "pending_payment",
            "Pending payment",
        )
        PAYMENT_PROCESSING = (
            "payment_processing",
            "Payment processing",
        )
        PAID_PENDING_PARTNER = (
            "paid_pending_partner",
            "Paid - awaiting partner",
        )
        RESCHEDULE_PROPOSED = (
            "reschedule_proposed",
            "Partner proposed another time",
        )
        CONFIRMED = (
            "confirmed",
            "Confirmed",
        )
        DECLINED = (
            "declined",
            "Declined by partner",
        )
        COMPLETED = (
            "completed",
            "Completed",
        )
        CANCELLED = (
            "cancelled",
            "Cancelled",
        )
        PAYMENT_FAILED = (
            "payment_failed",
            "Payment failed",
        )
        REFUNDED = (
            "refunded",
            "Refunded",
        )
        DISPUTED = (
            "disputed",
            "Disputed",
        )

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="viewing_reservations",
    )

    property = models.ForeignKey(
        "properties.Property",
        on_delete=models.PROTECT,
        related_name="viewing_reservations",
    )

    assigned_partner = models.ForeignKey(
        "partners.Partner",
        on_delete=models.PROTECT,
        related_name="assigned_viewings",
        null=True,
        blank=True,
    )

    requested_date = models.DateField()
    requested_time = models.TimeField()

    customer_message = models.TextField(
        blank=True,
        default="",
    )

    fee_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=RENTAL_VIEWING_FEE,
        editable=False,
    )

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.PENDING_PAYMENT,
        db_index=True,
    )

    payment_reference = models.CharField(
        max_length=100,
        blank=True,
        default="",
        db_index=True,
    )

    partner_response_message = models.TextField(
        blank=True,
        default="",
    )

    proposed_date = models.DateField(
        null=True,
        blank=True,
    )

    proposed_time = models.TimeField(
        null=True,
        blank=True,
    )

    confirmed_date = models.DateField(
        null=True,
        blank=True,
    )

    confirmed_time = models.TimeField(
        null=True,
        blank=True,
    )

    partner_responded_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-created_at"]

        indexes = [
            models.Index(
                fields=[
                    "customer",
                    "status",
                    "-created_at",
                ],
                name="viewing_customer_status_idx",
            ),
            models.Index(
                fields=[
                    "assigned_partner",
                    "status",
                    "requested_date",
                ],
                name="viewing_partner_status_idx",
            ),
            models.Index(
                fields=[
                    "property",
                    "requested_date",
                    "requested_time",
                ],
                name="viewing_property_slot_idx",
            ),
        ]

    def calculate_viewing_fee(self):
        """
        Calculate the official viewing fee from the property's
        listing type.

        Rental property: KES 400
        Sale property: KES 2,000
        """

        if not self.property_id:
            return RENTAL_VIEWING_FEE

        if self.property.listing_type == "rent":
            return RENTAL_VIEWING_FEE

        if self.property.listing_type == "sale":
            return SALE_VIEWING_FEE

        raise ValidationError(
            {
                "property": (
                    "This property has an unsupported listing type."
                )
            }
        )

    def save(self, *args, **kwargs):
        if self.property_id:
            self.fee_amount = self.calculate_viewing_fee()

            if self.assigned_partner_id is None:
                self.assigned_partner = self.property.partner

        super().save(*args, **kwargs)

        @builtins.property
        def booking_status(self):
            return self.status

        @builtins.property
        def operational_status(self):
            latest_event = (
                self.events.filter(
                    event_type__in=ViewingEvent.OPERATIONAL_EVENT_TYPES,
                )
                .order_by(
                    "-created_at",
                    "-id",
                )
                .first()
            )

            if latest_event is None:
                return "idle"

            return ViewingEvent.OPERATIONAL_STATUS_BY_EVENT.get(
                latest_event.event_type,
                "idle",
            )

    def record_event(
        self,
        *,
        event_type,
        actor=None,
        notes="",
        metadata=None,
    ):
        return ViewingEvent.objects.create(
            viewing=self,
            event_type=event_type,
            actor=actor,
            notes=notes,
            metadata=metadata or {},
        )

    def latest_event(self, event_type):
        return (
            self.events.filter(
                event_type=event_type,
            )
            .order_by(
                "-created_at",
                "-id",
            )
            .first()
        )

    def has_event(self, event_type):
        return self.events.filter(
            event_type=event_type,
        ).exists()

    def __str__(self):
        return (
            f"Viewing #{self.pk} - "
            f"{self.property} - "
            f"{self.status}"
        )


class ViewingEvent(models.Model):
    """
    Immutable operational and audit history for a viewing.
    """

    class EventType(models.TextChoices):
        PAYMENT_RECEIVED = (
            "payment_received",
            "Payment received",
        )

        PARTNER_CONFIRMED = (
            "partner_confirmed",
            "Partner confirmed",
        )

        RESCHEDULE_PROPOSED = (
            "reschedule_proposed",
            "Reschedule proposed",
        )

        PARTNER_EN_ROUTE = (
            "partner_en_route",
            "Partner en route",
        )

        PARTNER_ARRIVED = (
            "partner_arrived",
            "Partner arrived",
        )

        VIEWING_STARTED = (
            "viewing_started",
            "Viewing started",
        )

        VIEWING_COMPLETED = (
            "viewing_completed",
            "Viewing completed",
        )

        CUSTOMER_NO_SHOW = (
            "customer_no_show",
            "Customer did not attend",
        )

        PARTNER_NO_SHOW = (
            "partner_no_show",
            "Partner did not attend",
        )

        VIEWING_CANCELLED = (
            "viewing_cancelled",
            "Viewing cancelled",
        )

        REFUND_ISSUED = (
            "refund_issued",
            "Refund issued",
        )

        DISPUTE_OPENED = (
            "dispute_opened",
            "Dispute opened",
        )

    OPERATIONAL_EVENT_TYPES = (
        EventType.PARTNER_EN_ROUTE,
        EventType.PARTNER_ARRIVED,
        EventType.VIEWING_STARTED,
        EventType.VIEWING_COMPLETED,
        EventType.CUSTOMER_NO_SHOW,
        EventType.PARTNER_NO_SHOW,
    )

    OPERATIONAL_STATUS_BY_EVENT = {
        EventType.PARTNER_EN_ROUTE: "partner_en_route",
        EventType.PARTNER_ARRIVED: "partner_arrived",
        EventType.VIEWING_STARTED: "viewing_in_progress",
        EventType.VIEWING_COMPLETED: "finished",
        EventType.CUSTOMER_NO_SHOW: "finished",
        EventType.PARTNER_NO_SHOW: "finished",
    }

    viewing = models.ForeignKey(
        Viewing,
        on_delete=models.CASCADE,
        related_name="events",
    )

    event_type = models.CharField(
        max_length=40,
        choices=EventType.choices,
        db_index=True,
    )

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="recorded_viewing_events",
        null=True,
        blank=True,
    )

    notes = models.TextField(
        blank=True,
        default="",
    )

    metadata = models.JSONField(
        blank=True,
        default=dict,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )

    class Meta:
        ordering = [
            "created_at",
            "id",
        ]

        indexes = [
            models.Index(
                fields=[
                    "viewing",
                    "-created_at",
                ],
                name="viewevent_viewing_time_idx",
            ),
            models.Index(
                fields=[
                    "event_type",
                    "-created_at",
                ],
                name="viewevent_type_time_idx",
            ),
        ]

    def __str__(self):
        return (
            f"Viewing #{self.viewing_id} - "
            f"{self.get_event_type_display()}"
        )


class ViewingBooking(models.Model):
    class BookingType(models.TextChoices):
        RENTAL_SINGLE = (
            "rental_single",
            "Single Rental View",
        )

        RENTAL_THREE = (
            "rental_three",
            "3 Home Views",
        )

        SALE_SINGLE = (
            "sale_single",
            "Sales Property View",
        )

    class Status(models.TextChoices):
        PENDING_PAYMENT = (
            "pending_payment",
            "Pending Payment",
        )

        PAID_PENDING_PARTNER = (
            "paid_pending_partner",
            "Paid - Awaiting Partner",
        )

        CONFIRMED = (
            "confirmed",
            "Confirmed",
        )

        COMPLETED = (
            "completed",
            "Completed",
        )

        RESCHEDULE_PROPOSED = (
            "reschedule_proposed",
            "Reschedule Proposed",
        )

        DECLINED = (
            "declined",
            "Declined",
        )

        CANCELLED = (
            "cancelled",
            "Cancelled",
        )

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="viewing_bookings",
    )

    booking_type = models.CharField(
        max_length=30,
        choices=BookingType.choices,
    )

    viewing_date = models.DateField()

    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        editable=False,
    )

    status = models.CharField(
        max_length=40,
        choices=Status.choices,
        default=Status.PENDING_PAYMENT,
        db_index=True,
    )

    payment_reference = models.CharField(
        max_length=100,
        blank=True,
        default="",
        db_index=True,
    )

    assigned_partner = models.ForeignKey(
        "partners.Partner",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="viewing_bookings",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-created_at"]

        indexes = [
            models.Index(
                fields=[
                    "customer",
                    "status",
                    "-created_at",
                ],
                name="vbooking_customer_status_idx",
            ),
            models.Index(
                fields=[
                    "assigned_partner",
                    "status",
                    "viewing_date",
                ],
                name="vbooking_partner_status_idx",
            ),
        ]

    def calculate_total(self):
        """
        Legacy booking calculation.

        New bookings must use the individual Viewing model.
        The rental-three value is retained temporarily only
        for compatibility with existing database records.
        """

        prices = {
            self.BookingType.RENTAL_SINGLE: (
                RENTAL_VIEWING_FEE
            ),
            self.BookingType.RENTAL_THREE: (
                RENTAL_VIEWING_FEE * Decimal("3")
            ),
            self.BookingType.SALE_SINGLE: (
                SALE_VIEWING_FEE
            ),
        }

        return prices[self.booking_type]

    def save(self, *args, **kwargs):
        self.total_amount = self.calculate_total()

        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"Booking #{self.pk} - "
            f"{self.get_booking_type_display()} - "
            f"{self.status}"
        )


class ViewingBookingItem(models.Model):
    booking = models.ForeignKey(
        ViewingBooking,
        on_delete=models.CASCADE,
        related_name="items",
    )

    property = models.ForeignKey(
        "properties.Property",
        on_delete=models.PROTECT,
        related_name="viewing_booking_items",
    )

    viewing_time = models.TimeField(
        null=True,
        blank=True,
    )

    position = models.PositiveSmallIntegerField(
        default=1,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = [
            "position",
            "id",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "booking",
                    "property",
                ],
                name="unique_property_per_viewing_booking",
            ),
        ]

    def clean(self):
        if not self.booking_id or not self.property_id:
            return

        listing_type = self.property.listing_type
        booking_type = self.booking.booking_type

        if (
            booking_type
            in {
                ViewingBooking.BookingType.RENTAL_SINGLE,
                ViewingBooking.BookingType.RENTAL_THREE,
            }
            and listing_type != "rent"
        ):
            raise ValidationError(
                "Rental bookings can only contain rental properties."
            )

        if (
            booking_type
            == ViewingBooking.BookingType.SALE_SINGLE
            and listing_type != "sale"
        ):
            raise ValidationError(
                "Sales bookings can only contain properties for sale."
            )

    def save(self, *args, **kwargs):
        self.full_clean()

        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"Booking #{self.booking_id} - "
            f"{self.property}"
        )

class ViewingFeedback(models.Model):
    class PropertyAccuracy(models.TextChoices):
        YES = "yes", "Yes"
        PARTIALLY = "partially", "Partially"
        NO = "no", "No"

    viewing = models.OneToOneField(
        Viewing,
        on_delete=models.CASCADE,
        related_name="customer_feedback",
    )

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="viewing_feedback",
    )

    attended = models.BooleanField(
        default=True,
    )

    property_accuracy = models.CharField(
        max_length=20,
        choices=PropertyAccuracy.choices,
    )

    partner_rating = models.PositiveSmallIntegerField()

    property_rating = models.PositiveSmallIntegerField()

    comments = models.TextField(
        blank=True,
    )

    submitted_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "-submitted_at",
        ]

    def __str__(self):
        return (
            f"Feedback for viewing #{self.viewing_id} "
            f"by {self.customer}"
        )

    def clean(self):
        from django.core.exceptions import ValidationError

        errors = {}

        if self.partner_rating < 1 or self.partner_rating > 5:
            errors["partner_rating"] = (
                "Partner rating must be between 1 and 5."
            )

        if self.property_rating < 1 or self.property_rating > 5:
            errors["property_rating"] = (
                "Property rating must be between 1 and 5."
            )

        if (
            self.viewing_id
            and self.customer_id
            and self.viewing.customer_id != self.customer_id
        ):
            errors["customer"] = (
                "Only the customer who requested the viewing "
                "can submit feedback."
            )

        if (
            self.viewing_id
            and self.viewing.status != Viewing.Status.COMPLETED
        ):
            errors["viewing"] = (
                "Feedback can only be submitted after "
                "the viewing is completed."
            )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()

        return super().save(*args, **kwargs)