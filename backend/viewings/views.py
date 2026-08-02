from datetime import date

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from trust.services import recalculate_trust_from_feedback
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from core.models import ActivityLog

from .models import (
    Viewing,
    ViewingBooking,
    ViewingEvent,
)
from .serializers import (
    ViewingBookingCreateSerializer,
    ViewingBookingSerializer,
    ViewingSerializer,
)

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Viewing, ViewingFeedback
from .serializers import ViewingFeedbackSerializer
class ViewingViewSet(viewsets.ModelViewSet):
    """
    API endpoint for individual property viewing requests.

    Customer endpoints:
    - GET /api/viewings/
    - POST /api/viewings/
    - GET /api/viewings/{id}/

    Partner endpoints:
    - GET /api/viewings/partner-inbox/
    - POST /api/viewings/{id}/accept/
    - POST /api/viewings/{id}/propose-reschedule/
    - POST /api/viewings/{id}/decline/

    Customers can access only their own viewing requests.
    Partners can access only viewings assigned to their partner profile.
    Staff users can access all viewing requests.
    """

    serializer_class = ViewingSerializer
    permission_classes = [permissions.IsAuthenticated]

    http_method_names = [
        "get",
        "post",
        "put",
        "patch",
        "delete",
        "head",
        "options",
    ]

    def _base_queryset(self):
        return (
            Viewing.objects.select_related(
                "customer",
                "property",
                "assigned_partner",
                "assigned_partner__user",
            )
            .prefetch_related("events")
            .order_by("-created_at", "-id")
        )

    def get_queryset(self):
        queryset = self._base_queryset()
        user = self.request.user

        if user.is_staff:
            return queryset

        return queryset.filter(customer=user)

    def _get_partner_profile(self):
        """
        Return the logged-in user's active partner profile.

        Raises PermissionDenied when the user is not an active partner.
        """

        partner = getattr(
            self.request.user,
            "partner_profile",
            None,
        )

        if partner is None:
            raise PermissionDenied(
                "A partner account is required for this action."
            )

        if not partner.is_active:
            raise PermissionDenied(
                "This partner account is currently inactive."
            )

        return partner

    def _get_partner_viewing(self, pk):
        """
        Return a viewing only when it belongs to the logged-in partner.
        """

        partner = self._get_partner_profile()

        return get_object_or_404(
            self._base_queryset(),
            pk=pk,
            assigned_partner=partner,
        )

    @transaction.atomic
    def perform_create(self, serializer):
        viewing = serializer.save(
            customer=self.request.user,
        )

        ActivityLog.objects.create(
            actor=self.request.user,
            action="viewing_requested",
            entity_type="Viewing",
            entity_id=str(viewing.pk),
            description=(
                f"Viewing requested for {viewing.property.title}"
            ),
        )

    @action(
        detail=False,
        methods=["get"],
        url_path="partner-inbox",
    )
    def partner_inbox(self, request):
        """
        Return viewing requests assigned to the logged-in partner.

        Pending-payment requests are deliberately excluded because a partner
        should act only after the customer has completed payment.
        """

        partner = self._get_partner_profile()

        queryset = self._base_queryset().filter(
            assigned_partner=partner,
            status__in=[
                Viewing.Status.PAID_PENDING_PARTNER,
                Viewing.Status.RESCHEDULE_PROPOSED,
                Viewing.Status.CONFIRMED,
                Viewing.Status.COMPLETED,
                Viewing.Status.DECLINED,
            ],
        )

        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(
                page,
                many=True,
            )

            return self.get_paginated_response(
                serializer.data,
            )

        serializer = self.get_serializer(
            queryset,
            many=True,
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="accept",
    )
    @transaction.atomic
    def accept(self, request, pk=None):
        """
        Accept the customer's originally requested date and time.
        """

        viewing = self._get_partner_viewing(pk)

        if viewing.status != Viewing.Status.PAID_PENDING_PARTNER:
            raise ValidationError(
                {
                    "status": (
                        "Only a paid viewing awaiting partner response "
                        "can be accepted."
                    )
                }
            )

        now = timezone.now()

        viewing.status = Viewing.Status.CONFIRMED
        viewing.confirmed_date = viewing.requested_date
        viewing.confirmed_time = viewing.requested_time
        viewing.partner_responded_at = now

        viewing.proposed_date = None
        viewing.proposed_time = None
        viewing.partner_response_message = ""

        viewing.save(
            update_fields=[
                "status",
                "confirmed_date",
                "confirmed_time",
                "partner_responded_at",
                "proposed_date",
                "proposed_time",
                "partner_response_message",
                "updated_at",
            ]
        )

        viewing.record_event(
            event_type=ViewingEvent.EventType.PARTNER_CONFIRMED,
            actor=request.user,
            notes=(
                "Partner accepted the customer's requested "
                "viewing date and time."
            ),
            metadata={
                "confirmed_date": viewing.confirmed_date.isoformat(),
                "confirmed_time": viewing.confirmed_time.isoformat(),
            },
        )

        ActivityLog.objects.create(
            actor=request.user,
            action="viewing_partner_confirmed",
            entity_type="Viewing",
            entity_id=str(viewing.pk),
            description=(
                f"Partner confirmed viewing for "
                f"{viewing.property.title}"
            ),
        )

        serializer = self.get_serializer(viewing)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="propose-reschedule",
    )
    @transaction.atomic
    def propose_reschedule(self, request, pk=None):
        """
        Propose a different viewing date and time.

        Expected JSON:
        {
            "proposed_date": "2026-07-30",
            "proposed_time": "14:30:00",
            "partner_response_message": "Can we meet at 2:30 PM instead?"
        }
        """

        viewing = self._get_partner_viewing(pk)

        allowed_statuses = {
            Viewing.Status.PAID_PENDING_PARTNER,
            Viewing.Status.RESCHEDULE_PROPOSED,
        }

        if viewing.status not in allowed_statuses:
            raise ValidationError(
                {
                    "status": (
                        "This viewing cannot currently be rescheduled."
                    )
                }
            )

        proposed_date = request.data.get("proposed_date")
        proposed_time = request.data.get("proposed_time")
        partner_message = (
            request.data.get(
                "partner_response_message",
                "",
            )
            or ""
        ).strip()

        if not proposed_date:
            raise ValidationError(
                {
                    "proposed_date": (
                        "Please provide the proposed viewing date."
                    )
                }
            )

        if not proposed_time:
            raise ValidationError(
                {
                    "proposed_time": (
                        "Please provide the proposed viewing time."
                    )
                }
            )

        try:
            parsed_date = date.fromisoformat(
                str(proposed_date),
            )
        except (TypeError, ValueError):
            raise ValidationError(
                {
                    "proposed_date": (
                        "Use the date format YYYY-MM-DD."
                    )
                }
            )

        if parsed_date < timezone.localdate():
            raise ValidationError(
                {
                    "proposed_date": (
                        "The proposed viewing date cannot be in the past."
                    )
                }
            )

        from datetime import time

        try:
            parsed_time = time.fromisoformat(
                str(proposed_time),
            )
        except (TypeError, ValueError):
            raise ValidationError(
                {
                    "proposed_time": (
                        "Use a valid time such as 14:30 or 14:30:00."
                    )
                }
            )

        now = timezone.now()

        viewing.status = Viewing.Status.RESCHEDULE_PROPOSED
        viewing.proposed_date = parsed_date
        viewing.proposed_time = parsed_time
        viewing.partner_response_message = partner_message
        viewing.partner_responded_at = now

        viewing.confirmed_date = None
        viewing.confirmed_time = None

        viewing.save(
            update_fields=[
                "status",
                "proposed_date",
                "proposed_time",
                "partner_response_message",
                "partner_responded_at",
                "confirmed_date",
                "confirmed_time",
                "updated_at",
            ]
        )

        viewing.record_event(
            event_type=ViewingEvent.EventType.RESCHEDULE_PROPOSED,
            actor=request.user,
            notes=(
                partner_message
                or "Partner proposed another viewing date and time."
            ),
            metadata={
                "proposed_date": viewing.proposed_date.isoformat(),
                "proposed_time": viewing.proposed_time.isoformat(),
            },
        )

        ActivityLog.objects.create(
            actor=request.user,
            action="viewing_reschedule_proposed",
            entity_type="Viewing",
            entity_id=str(viewing.pk),
            description=(
                f"Partner proposed another time for "
                f"{viewing.property.title}"
            ),
        )

        serializer = self.get_serializer(viewing)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="decline",
    )
    @transaction.atomic
    def decline(self, request, pk=None):
        """
        Decline a paid viewing request.

        Expected JSON:
        {
            "partner_response_message": "The property is unavailable."
        }
        """

        viewing = self._get_partner_viewing(pk)

        allowed_statuses = {
            Viewing.Status.PAID_PENDING_PARTNER,
            Viewing.Status.RESCHEDULE_PROPOSED,
        }

        if viewing.status not in allowed_statuses:
            raise ValidationError(
                {
                    "status": (
                        "This viewing cannot currently be declined."
                    )
                }
            )

        partner_message = (
            request.data.get(
                "partner_response_message",
                "",
            )
            or ""
        ).strip()

        if not partner_message:
            raise ValidationError(
                {
                    "partner_response_message": (
                        "Please provide a reason for declining "
                        "the viewing."
                    )
                }
            )

        viewing.status = Viewing.Status.DECLINED
        viewing.partner_response_message = partner_message
        viewing.partner_responded_at = timezone.now()

        viewing.proposed_date = None
        viewing.proposed_time = None
        viewing.confirmed_date = None
        viewing.confirmed_time = None

        viewing.save(
            update_fields=[
                "status",
                "partner_response_message",
                "partner_responded_at",
                "proposed_date",
                "proposed_time",
                "confirmed_date",
                "confirmed_time",
                "updated_at",
            ]
        )

        ActivityLog.objects.create(
            actor=request.user,
            action="viewing_partner_declined",
            entity_type="Viewing",
            entity_id=str(viewing.pk),
            description=(
                f"Partner declined viewing for "
                f"{viewing.property.title}: {partner_message}"
            ),
        )

        serializer = self.get_serializer(viewing)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

        
    def _ensure_event_not_recorded(
        self,
        viewing,
        event_type,
        message,
    ):
        """
        Prevent duplicate operational events.
        """

        if viewing.has_event(event_type):
            raise ValidationError(
                {
                    "event": message,
                }
            )

    @action(
        detail=True,
        methods=["post"],
        url_path="partner-en-route",
    )
    @transaction.atomic
    def partner_en_route(self, request, pk=None):
        """
        Record that the assigned partner has started travelling
        to the viewing location.
        """

        viewing = self._get_partner_viewing(pk)
        self._require_confirmed_viewing(viewing)

        self._ensure_event_not_recorded(
            viewing,
            ViewingEvent.EventType.PARTNER_EN_ROUTE,
            "The partner is already marked as en route.",
        )

        if viewing.has_event(
            ViewingEvent.EventType.PARTNER_ARRIVED
        ):
            raise ValidationError(
                {
                    "event": (
                        "The partner has already arrived at this viewing."
                    )
                }
            )

        if viewing.has_event(
            ViewingEvent.EventType.VIEWING_STARTED
        ):
            raise ValidationError(
                {
                    "event": "This viewing has already started."
                }
            )

        if viewing.has_event(
            ViewingEvent.EventType.VIEWING_COMPLETED
        ):
            raise ValidationError(
                {
                    "event": "This viewing has already been completed."
                }
            )

        notes = (
            request.data.get("notes", "")
            or ""
        ).strip()

        if len(notes) > 2000:
            raise ValidationError(
                {
                    "notes": (
                        "Notes cannot exceed 2,000 characters."
                    )
                }
            )

        event = viewing.record_event(
            event_type=ViewingEvent.EventType.PARTNER_EN_ROUTE,
            actor=request.user,
            notes=(
                notes
                or "Partner started travelling to the viewing location."
            ),
        )

        ActivityLog.objects.create(
            actor=request.user,
            action="viewing_partner_en_route",
            entity_type="Viewing",
            entity_id=str(viewing.pk),
            description=(
                f"Partner marked en route for "
                f"{viewing.property.title}"
            ),
        )

        serializer = self.get_serializer(viewing)

        return Response(
            {
                "message": "You are now marked as en route.",
                "event": {
                    "id": event.id,
                    "event_type": event.event_type,
                    "created_at": event.created_at,
                },
                "viewing": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="partner-arrived",
    )
    @transaction.atomic
    def partner_arrived(self, request, pk=None):
        """
        Record that the assigned partner has arrived at the property.
        """

        viewing = self._get_partner_viewing(pk)
        self._require_confirmed_viewing(viewing)

        if not viewing.has_event(
            ViewingEvent.EventType.PARTNER_EN_ROUTE
        ):
            raise ValidationError(
                {
                    "event": (
                        "Mark yourself as en route before marking arrival."
                    )
                }
            )

        self._ensure_event_not_recorded(
            viewing,
            ViewingEvent.EventType.PARTNER_ARRIVED,
            "The partner is already marked as arrived.",
        )

        if viewing.has_event(
            ViewingEvent.EventType.VIEWING_STARTED
        ):
            raise ValidationError(
                {
                    "event": "This viewing has already started."
                }
            )

        if viewing.has_event(
            ViewingEvent.EventType.VIEWING_COMPLETED
        ):
            raise ValidationError(
                {
                    "event": "This viewing has already been completed."
                }
            )

        notes = (
            request.data.get("notes", "")
            or ""
        ).strip()

        if len(notes) > 2000:
            raise ValidationError(
                {
                    "notes": (
                        "Notes cannot exceed 2,000 characters."
                    )
                }
            )

        event = viewing.record_event(
            event_type=ViewingEvent.EventType.PARTNER_ARRIVED,
            actor=request.user,
            notes=(
                notes
                or "Partner arrived at the viewing location."
            ),
        )

        ActivityLog.objects.create(
            actor=request.user,
            action="viewing_partner_arrived",
            entity_type="Viewing",
            entity_id=str(viewing.pk),
            description=(
                f"Partner arrived for viewing at "
                f"{viewing.property.title}"
            ),
        )

        serializer = self.get_serializer(viewing)

        return Response(
            {
                "message": "Arrival recorded successfully.",
                "event": {
                    "id": event.id,
                    "event_type": event.event_type,
                    "created_at": event.created_at,
                },
                "viewing": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="start-viewing",
    )
    @transaction.atomic
    def start_viewing(self, request, pk=None):
        """
        Record that the customer and partner have started the viewing.
        """

        viewing = self._get_partner_viewing(pk)
        self._require_confirmed_viewing(viewing)

        if not viewing.has_event(
            ViewingEvent.EventType.PARTNER_ARRIVED
        ):
            raise ValidationError(
                {
                    "event": (
                        "Record arrival before starting the viewing."
                    )
                }
            )

        self._ensure_event_not_recorded(
            viewing,
            ViewingEvent.EventType.VIEWING_STARTED,
            "This viewing has already started.",
        )

        if viewing.has_event(
            ViewingEvent.EventType.VIEWING_COMPLETED
        ):
            raise ValidationError(
                {
                    "event": "This viewing has already been completed."
                }
            )

        notes = (
            request.data.get("notes", "")
            or ""
        ).strip()

        if len(notes) > 2000:
            raise ValidationError(
                {
                    "notes": (
                        "Notes cannot exceed 2,000 characters."
                    )
                }
            )

        event = viewing.record_event(
            event_type=ViewingEvent.EventType.VIEWING_STARTED,
            actor=request.user,
            notes=(
                notes
                or "The property viewing started."
            ),
        )

        ActivityLog.objects.create(
            actor=request.user,
            action="viewing_started",
            entity_type="Viewing",
            entity_id=str(viewing.pk),
            description=(
                f"Viewing started at {viewing.property.title}"
            ),
        )

        serializer = self.get_serializer(viewing)

        return Response(
            {
                "message": "Viewing started successfully.",
                "event": {
                    "id": event.id,
                    "event_type": event.event_type,
                    "created_at": event.created_at,
                },
                "viewing": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="complete-viewing",
    )
    @transaction.atomic
    def complete_viewing(self, request, pk=None):
        """
        Complete a confirmed viewing and optionally save notes.

        Expected JSON:

        {
            "completion_notes": (
                "Customer viewed the property successfully."
            )
        }
        """

        viewing = self._get_partner_viewing(pk)
        self._require_confirmed_viewing(viewing)


        self._ensure_event_not_recorded(
            viewing,
            ViewingEvent.EventType.VIEWING_COMPLETED,
            "This viewing has already been completed.",
        )

        completion_notes = (
            request.data.get("completion_notes", "")
            or ""
        ).strip()

        if len(completion_notes) > 2000:
            raise ValidationError(
                {
                    "completion_notes": (
                        "Completion notes cannot exceed 2,000 characters."
                    )
                }
            )

        now = timezone.now()

        viewing.status = Viewing.Status.COMPLETED
        viewing.completed_at = now

        viewing.save(
            update_fields=[
                "status",
                "completed_at",
                "updated_at",
            ]
        )

        event = viewing.record_event(
            event_type=ViewingEvent.EventType.VIEWING_COMPLETED,
            actor=request.user,
            notes=(
                completion_notes
                or "The property viewing was completed."
            ),
        )

        ActivityLog.objects.create(
            actor=request.user,
            action="viewing_completed",
            entity_type="Viewing",
            entity_id=str(viewing.pk),
            description=(
                f"Viewing completed at {viewing.property.title}"
            ),
        )

        serializer = self.get_serializer(viewing)

        return Response(
            {
                "message": "Viewing completed successfully.",
                "event": {
                    "id": event.id,
                    "event_type": event.event_type,
                    "created_at": event.created_at,
                },
                "viewing": serializer.data,
            },
            status=status.HTTP_200_OK,
        )    

class ViewingBookingViewSet(viewsets.ModelViewSet):
    """
    Legacy viewing-booking endpoint.

    The current MVP uses individual KES 400 Viewing records. This viewset
    remains temporarily to avoid destructive database changes, but no new
    package features should be developed against it.
    """

    permission_classes = [permissions.IsAuthenticated]

    http_method_names = [
        "get",
        "post",
        "put",
        "patch",
        "delete",
        "head",
        "options",
    ]

    def get_queryset(self):
        queryset = (
            ViewingBooking.objects.select_related(
                "customer",
                "assigned_partner",
            )
            .prefetch_related(
                "items",
                "items__property",
            )
            .order_by("-created_at", "-id")
        )

        user = self.request.user

        if user.is_staff:
            return queryset

        return queryset.filter(customer=user)

    def get_serializer_class(self):
        if self.action == "create":
            return ViewingBookingCreateSerializer

        return ViewingBookingSerializer

    @transaction.atomic
    def perform_create(self, serializer):
        booking = serializer.save()

        ActivityLog.objects.create(
            actor=self.request.user,
            action="viewing_booking_created",
            entity_type="ViewingBooking",
            entity_id=str(booking.pk),
            description=(
                f"Viewing booking created for "
                f"{booking.viewing_date}"
            ),
        )

class ViewingFeedbackView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get_viewing(self, request, viewing_id):
        return get_object_or_404(
            Viewing.objects.select_related(
                "customer",
                "property",
                "assigned_partner",
            ),
            id=viewing_id,
            customer=request.user,
        )

    def get(self, request, viewing_id):
        viewing = self.get_viewing(
            request,
            viewing_id,
        )

        feedback = getattr(
            viewing,
            "customer_feedback",
            None,
        )

        if feedback is None:
            return Response(
                {
                    "detail": (
                        "Feedback has not been submitted "
                        "for this viewing."
                    )
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            ViewingFeedbackSerializer(
                feedback,
                context={"request": request},
            ).data,
            status=status.HTTP_200_OK,
        )

    def post(self, request, viewing_id):
        viewing = self.get_viewing(
            request,
            viewing_id,
        )

        if viewing.status != Viewing.Status.COMPLETED:
            return Response(
                {
                    "detail": (
                        "Feedback can only be submitted "
                        "after the viewing is completed."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if hasattr(viewing, "customer_feedback"):
            return Response(
                {
                    "detail": (
                        "Feedback has already been submitted "
                        "for this viewing."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ViewingFeedbackSerializer(
            data=request.data,
            context={"request": request},
        )

        serializer.is_valid(
            raise_exception=True,
        )

        feedback = serializer.save(
            viewing=viewing,
            customer=request.user,
        )
        recalculate_trust_from_feedback(
            feedback,
        )
        return Response(
            ViewingFeedbackSerializer(
                feedback,
                context={"request": request},
            ).data,
            status=status.HTTP_201_CREATED,
        )