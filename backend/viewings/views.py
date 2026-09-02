from datetime import date
from django.db.models import Count, Q
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from trust.services import recalculate_trust_from_feedback
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from django.core.exceptions import (
    ValidationError as DjangoValidationError,
)
from governance.services import (
    enforce_partner_operational_access,
)
from core.models import ActivityLog
from introductions.services import (
    create_property_introduction_certificate,
)
from .models import (
    Viewing,
    ViewingBooking,
    ViewingEvent,
)
from .serializers import (
    ViewingBookingCreateSerializer,
    ViewingBookingSerializer,
    ViewingEventSerializer,
    ViewingSerializer,
)

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Viewing, ViewingFeedback
from .serializers import ViewingFeedbackSerializer
from properties.models import PropertyPartner
from deals.services import (
    create_deal_from_pic,
)

def choose_participation_for_property(property_obj):
    """
    Choose the active property participation that should
    receive a new viewing.

    Partners with fewer active viewings for this property are
    preferred. Ties are resolved by participation join date.
    """

    active_viewing_statuses = [
        Viewing.Status.PENDING_PAYMENT,
        Viewing.Status.PAYMENT_PROCESSING,
        Viewing.Status.PAID_PENDING_PARTNER,
        Viewing.Status.RESCHEDULE_PROPOSED,
        Viewing.Status.CONFIRMED,
    ]

    return (
        PropertyPartner.objects
        .filter(
            property=property_obj,
            status=PropertyPartner.Status.ACTIVE,
            partner__is_active=True,
            partner__accepts_viewing_requests=True,
        )
        .annotate(
            active_viewing_count=Count(
                "partner__assigned_viewings",
                filter=Q(
                    partner__assigned_viewings__property=property_obj,
                    partner__assigned_viewings__status__in=(
                        active_viewing_statuses
                    ),
                ),
            )
        )
        .select_related("partner")
        .order_by(
            "active_viewing_count",
            "joined_at",
            "id",
        )
        .first()
    )

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
        Return the logged-in user's approved and operationally
        authorized partner profile.

        All partner viewing operations pass through this central
        governance gate.
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

        try:
            enforce_partner_operational_access(
                partner,
                operation="manage_assigned_viewing",
            )

        except DjangoValidationError as exc:
            detail = getattr(
                exc,
                "message_dict",
                None,
            )

            if detail is None:
                detail = getattr(
                    exc,
                    "messages",
                    None,
                )

            if detail is None:
                detail = str(exc)

            raise PermissionDenied(
                detail=detail,
            ) from exc

        return partner

    def _get_partner_viewing(self, pk):
        """
        Return a viewing only when it belongs to the logged-in partner.
        """

        partner = self._get_partner_profile()

        queryset = (
            self._base_queryset()
            .select_for_update(
                of=("self",),
            )
        )

        return get_object_or_404(
            queryset,
            pk=pk,
            assigned_partner=partner,
        )

    def _require_confirmed_viewing(self, viewing):
        if viewing.status != Viewing.Status.CONFIRMED:
            raise ValidationError(
                {
                    "status": (
                        "Only a confirmed viewing can be "
                        "started or completed."
                    ),
                    "current_status": viewing.status,
                }
            )

    @transaction.atomic
    def perform_create(self, serializer):
        property_obj = serializer.validated_data["property"]

        participation = choose_participation_for_property(
            property_obj
        )

        if participation is None:
            raise ValidationError(
                {
                    "property": (
                        "No active partner is currently available "
                        "to handle viewings for this property."
                    )
                }
            )

        viewing = serializer.save(
            customer=self.request.user,
            assigned_partner=participation.partner,
            source_participation=participation,
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

        introduction, introduction_created = (
            create_property_introduction_certificate(
                viewing=viewing,
                actor=request.user,
            )
        )
        deal, deal_created = create_deal_from_pic(
            introduction=introduction,
            actor=request.user,
        )

        ActivityLog.objects.create(
            actor=request.user,
            action="viewing_completed",
            entity_type="Viewing",
            entity_id=str(viewing.pk),
            description=(
                f"Viewing completed at "
                f"{viewing.property.title}; "
                f"PIC {introduction.certificate_number} "
                f"{'created' if introduction_created else 'reused'}; "
                f"deal {deal.deal_number} "
                f"{'created' if deal_created else 'reused'}."
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
                "property_introduction_certificate": {
                    "id": introduction.id,
                    "certificate_number": (
                        introduction.certificate_number
                    ),
                    "created": introduction_created,
                    "status": introduction.status,
                    "protected_from": (
                        introduction.protected_from
                    ),
                    "protected_until": (
                        introduction.protected_until
                    ),
                    "protection_period_days": (
                        introduction.protection_period_days
                    ),
                },

                "deal": {
                    "id": deal.id,
                    "deal_number": deal.deal_number,
                    "created": deal_created,
                    "status": deal.status,
                    "deal_type": deal.deal_type,
                    "customer_id": deal.customer_id,
                    "partner_id": deal.partner_id,
                    "property_id": deal.property_id,
                    "commission_amount": (
                        deal.commission_amount
                    ),
                },
                "viewing": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

class AdminViewingListView(APIView):
    """
    Staff-only viewing operations list.

    Supports:
    - search
    - status filter
    - date scope
    - pagination
    """

    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get(self, request):
        if not request.user.is_staff:
            return Response(
                {
                    "detail": (
                        "Only Pata Hao administrators may access "
                        "viewing operations."
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        search = request.query_params.get(
            "search",
            "",
        ).strip()

        requested_status = request.query_params.get(
            "status",
            "",
        ).strip()

        date_scope = request.query_params.get(
            "date_scope",
            "",
        ).strip().lower()

        try:
            page = int(
                request.query_params.get(
                    "page",
                    "1",
                )
            )
        except ValueError:
            page = 1

        try:
            page_size = int(
                request.query_params.get(
                    "page_size",
                    "50",
                )
            )
        except ValueError:
            page_size = 50

        page = max(page, 1)

        page_size = max(
            1,
            min(page_size, 100),
        )

        queryset = (
            Viewing.objects
            .select_related(
                "customer",
                "property",
                "assigned_partner",
                "assigned_partner__user",
            )
            .prefetch_related(
                "events",
            )
            .order_by(
                "-created_at",
                "-id",
            )
        )

        if search:
            queryset = queryset.filter(
                Q(
                    customer__username__icontains=search,
                )
                | Q(
                    customer__email__icontains=search,
                )
                | Q(
                    customer__full_name__icontains=search,
                )
                | Q(
                    property__title__icontains=search,
                )
                | Q(
                    assigned_partner__display_name__icontains=search,
                )
                | Q(
                    assigned_partner__business_name__icontains=search,
                )
                | Q(
                    payment_reference__icontains=search,
                )
            )

        if requested_status:
            queryset = queryset.filter(
                status=requested_status,
            )

        today = timezone.localdate()

        if date_scope == "today":
            queryset = queryset.filter(
                requested_date=today,
            )

        elif date_scope == "upcoming":
            queryset = queryset.filter(
                requested_date__gt=today,
            )

        elif date_scope == "past":
            queryset = queryset.filter(
                requested_date__lt=today,
            )

        total_count = queryset.count()

        start = (page - 1) * page_size
        end = start + page_size

        page_items = queryset[
            start:end
        ]

        serializer = ViewingSerializer(
            page_items,
            many=True,
            context={
                "request": request,
            },
        )

        total_pages = (
            total_count + page_size - 1
        ) // page_size

        return Response(
            {
                "count": total_count,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_previous": page > 1,
                "results": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

class AdminViewingDetailView(APIView):
    """
    Staff-only viewing operational detail.

    Includes the immutable ViewingEvent timeline.
    """

    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get(self, request, viewing_id):
        if not request.user.is_staff:
            return Response(
                {
                    "detail": (
                        "Only Pata Hao administrators may access "
                        "viewing details."
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        viewing = (
            Viewing.objects
            .select_related(
                "customer",
                "property",
                "assigned_partner",
                "assigned_partner__user",
            )
            .prefetch_related(
                "events",
                "events__actor",
            )
            .filter(
                pk=viewing_id,
            )
            .first()
        )

        if viewing is None:
            return Response(
                {
                    "detail": "Viewing not found.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        viewing_data = ViewingSerializer(
            viewing,
            context={
                "request": request,
            },
        ).data

        events = (
            viewing.events
            .select_related(
                "actor",
            )
            .order_by(
                "created_at",
                "id",
            )
        )

        event_data = ViewingEventSerializer(
            events,
            many=True,
            context={
                "request": request,
            },
        ).data

        return Response(
            {
                "viewing": viewing_data,
                "events": event_data,
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