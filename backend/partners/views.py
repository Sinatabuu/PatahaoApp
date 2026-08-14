from datetime import date, time
from decimal import Decimal

from django.db import transaction
from django.db.models import Count, Q, Sum
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_time

from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView

from properties.models import Property
from viewings.models import Viewing, ViewingEvent

from .models import Partner
from .serializers import (
    PartnerDashboardProfileSerializer,
    PartnerDashboardPropertySerializer,
    PartnerDashboardViewingSerializer,
)
from properties.models import Property
from viewings.models import Viewing, ViewingEvent
from deals.models import Deal
from introductions.models import ProtectedIntroduction
from commissions.models import (
    CommissionPlan,
    CommissionSettlementParticipant,
)
from notifications.models import Notification



def get_authenticated_partner(user, require_approved=False):
    """
    Return the active Partner profile linked to the authenticated user.

    Normal users must have the partner role. Staff users may access the
    endpoint when they also have a Partner profile.

    Operational actions can require an approved Partner profile.
    """
    if not user or not user.is_authenticated:
        return None

    user_role = getattr(user, "role", None)

    if not user.is_staff and user_role != "partner":
        return None

    filters = {
        "user": user,
        "is_active": True,
    }

    if require_approved:
        filters["verification_status"] = Partner.STATUS_APPROVED

    return (
        Partner.objects
        .select_related("user")
        .filter(**filters)
        .first()
    )


def partner_properties_queryset(partner):
    return (
        Property.objects
        .filter(partner=partner)
        .prefetch_related("photos")
        .order_by("-created_at")
    )


def partner_viewings_queryset(partner):
    """
    Include viewings explicitly assigned to the partner.

    Also include unassigned viewings belonging to properties owned by
    that partner. This supports the period before the partner confirms
    and formally accepts the viewing.
    """
    return (
        Viewing.objects
        .select_related(
            "customer",
            "property",
            "property__partner",
            "assigned_partner",
        )
        .prefetch_related(
            "events",
            "events__actor",
        )
        .filter(
            Q(assigned_partner=partner)
            | Q(
                assigned_partner__isnull=True,
                property__partner=partner,
            )
        )
        .distinct()
        .order_by("-created_at")
    )


def get_partner_viewing(partner, viewing_id, lock=False):
    queryset = partner_viewings_queryset(partner)

    if lock:
        queryset = queryset.select_for_update()

    return queryset.filter(id=viewing_id).first()


def _get_partner_viewing(
    request,
    viewing_id,
    *,
    require_approved=True,
    lock=True,
):
    partner = get_authenticated_partner(
        request.user,
        require_approved=require_approved,
    )

    if partner is None:
        detail = (
            "An approved and active partner profile is required."
            if require_approved
            else "An active partner profile is required."
        )

        return None, None, Response(
            {"detail": detail},
            status=status.HTTP_403_FORBIDDEN,
        )

    viewing = get_partner_viewing(
        partner,
        viewing_id,
        lock=lock,
    )

    if viewing is None:
        return partner, None, Response(
            {
                "detail": (
                    "Viewing not found or it does not belong "
                    "to this partner."
                )
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    return partner, viewing, None


def serialize_viewing(viewing, request):
    viewing.refresh_from_db()

    return PartnerDashboardViewingSerializer(
        viewing,
        context={"request": request},
    ).data


def _scheduled_date(viewing):
    return viewing.confirmed_date or viewing.requested_date


def _scheduled_time(viewing):
    return viewing.confirmed_time or viewing.requested_time


def _validate_operational_day(viewing):
    scheduled_date = _scheduled_date(viewing)
    today = timezone.localdate()

    if scheduled_date != today:
        return Response(
            {
                "detail": (
                    "Live viewing activity can only be updated "
                    "on the scheduled viewing date."
                ),
                "scheduled_date": scheduled_date.isoformat(),
                "current_date": today.isoformat(),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    return None


def _operational_error(viewing, detail):
    return Response(
        {
            "detail": detail,
            "booking_status": viewing.booking_status,
            "operational_status": viewing.operational_status,
        },
        status=status.HTTP_400_BAD_REQUEST,
    )


def _validate_notes(request, field_name="notes", max_length=2000):
    notes = str(request.data.get(field_name, "")).strip()

    if len(notes) > max_length:
        return None, Response(
            {
                field_name: [
                    f"This field cannot exceed {max_length} characters."
                ]
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    return notes, None


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
@transaction.atomic
def partner_viewing_en_route(request, viewing_id):
    _, viewing, error_response = _get_partner_viewing(
        request,
        viewing_id,
    )

    if error_response:
        return error_response

    if viewing.status != Viewing.Status.CONFIRMED:
        return _operational_error(
            viewing,
            "Only a confirmed viewing can be marked as partner en route.",
        )

    date_error = _validate_operational_day(viewing)

    if date_error:
        return date_error

    if viewing.operational_status != "idle":
        return _operational_error(
            viewing,
            "The partner can depart only before live activity has started.",
        )

    notes, notes_error = _validate_notes(request)

    if notes_error:
        return notes_error

    viewing.record_event(
        event_type=ViewingEvent.EventType.PARTNER_EN_ROUTE,
        actor=request.user,
        notes=notes,
    )

    return Response(
        serialize_viewing(viewing, request),
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
@transaction.atomic
def partner_viewing_arrived(request, viewing_id):
    _, viewing, error_response = _get_partner_viewing(
        request,
        viewing_id,
    )

    if error_response:
        return error_response

    if viewing.status != Viewing.Status.CONFIRMED:
        return _operational_error(
            viewing,
            "Only a confirmed viewing can be marked as arrived.",
        )

    date_error = _validate_operational_day(viewing)

    if date_error:
        return date_error

    if viewing.operational_status != "partner_en_route":
        return _operational_error(
            viewing,
            "The partner must depart before marking arrival.",
        )

    notes, notes_error = _validate_notes(request)

    if notes_error:
        return notes_error

    viewing.record_event(
        event_type=ViewingEvent.EventType.PARTNER_ARRIVED,
        actor=request.user,
        notes=notes,
    )

    return Response(
        serialize_viewing(viewing, request),
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
@transaction.atomic
def partner_viewing_start(request, viewing_id):
    _, viewing, error_response = _get_partner_viewing(
        request,
        viewing_id,
    )

    if error_response:
        return error_response

    if viewing.status != Viewing.Status.CONFIRMED:
        return _operational_error(
            viewing,
            "Only a confirmed viewing can be started.",
        )

    date_error = _validate_operational_day(viewing)

    if date_error:
        return date_error

    if viewing.operational_status != "partner_arrived":
        return _operational_error(
            viewing,
            "The partner must arrive before starting the viewing.",
        )

    notes, notes_error = _validate_notes(request)

    if notes_error:
        return notes_error

    viewing.record_event(
        event_type=ViewingEvent.EventType.VIEWING_STARTED,
        actor=request.user,
        notes=notes,
    )

    return Response(
        serialize_viewing(viewing, request),
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
@transaction.atomic
def partner_viewing_complete(request, viewing_id):
    _, viewing, error_response = _get_partner_viewing(
        request,
        viewing_id,
    )

    if error_response:
        return error_response

    if viewing.status != Viewing.Status.CONFIRMED:
        return _operational_error(
            viewing,
            "Only a confirmed viewing can be completed.",
        )

    date_error = _validate_operational_day(viewing)

    if date_error:
        return date_error

    if viewing.operational_status != "viewing_in_progress":
        return _operational_error(
            viewing,
            "Only a viewing currently in progress can be completed.",
        )

    completion_notes, notes_error = _validate_notes(
        request,
        field_name="completion_notes",
    )

    if notes_error:
        return notes_error

    completed_at = timezone.now()

    viewing.status = Viewing.Status.COMPLETED
    viewing.completed_at = completed_at
    viewing.save(
        update_fields=[
            "status",
            "completed_at",
            "updated_at",
        ]
    )

    viewing.record_event(
        event_type=ViewingEvent.EventType.VIEWING_COMPLETED,
        actor=request.user,
        notes=completion_notes,
        metadata={
            "completed_at": completed_at.isoformat(),
            "completed_by_user_id": request.user.id,
        },
    )

    return Response(
        serialize_viewing(viewing, request),
        status=status.HTTP_200_OK,
    )


class PartnerDashboardView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        partner = get_authenticated_partner(
            request.user,
            require_approved=False,
        )

        if partner is None:
            return Response(
                {
                    "detail": (
                        "This account does not have an active "
                        "partner profile."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        properties = partner_properties_queryset(partner)
        viewings = partner_viewings_queryset(partner)

        today = timezone.localdate()

        introductions = (
            ProtectedIntroduction.objects
            .filter(partner=partner)
            .select_related(
                "customer",
                "property",
                "viewing",
            )
            .order_by("-created_at")
        )

        deals = (
            Deal.objects
            .filter(partner=partner)
            .select_related(
                "customer",
                "property",
                "viewing",
                "introduction",
            )
            .order_by("-created_at")
        )

        
        partner_commission_shares = (
            CommissionSettlementParticipant.objects
            .filter(partner=partner)
            .select_related(
                "settlement",
                "settlement__deal",
            )
            .order_by("-id")
        )

        commission_total = (
            partner_commission_shares.aggregate(
                total=Sum("amount")
            ).get("total")
            or Decimal("0.00")
        )

        notifications = Notification.objects.filter(
            user=request.user,
        )

        unread_notifications = notifications.filter(
            is_read=False,
        )

        active_deal_statuses = [
            Deal.Status.DRAFT,
            Deal.Status.AWAITING_CUSTOMER,
            Deal.Status.AWAITING_OWNER,
            Deal.Status.AWAITING_CONFIRMATIONS,
            Deal.Status.NEGOTIATING,
            Deal.Status.AGREED,
            Deal.Status.DOCUMENTS_PENDING,
            Deal.Status.COMMISSION_DUE,
        ]

        active_deals = deals.filter(
            status__in=active_deal_statuses,
        )

        awaiting_partner_confirmation = deals.filter(
            partner_confirmed=False,
            status=Deal.Status.AWAITING_CONFIRMATIONS,
        )
        pending_requests = viewings.filter(
            status=Viewing.Status.PAID_PENDING_PARTNER,
        )
        inbox_items = []

        for viewing in pending_requests:
            inbox_items.append(
                {
                    "type": "viewing",
                    "id": viewing.id,
                    "priority": "high",
                    "action": "respond_to_viewing",
                    "title": (
                        f"Viewing request for {viewing.property.title}"
                    ),
                    "created_at": viewing.created_at.isoformat(),
                }
            )

        for deal in awaiting_partner_confirmation:
            inbox_items.append(
                {
                    "type": "deal",
                    "id": deal.id,
                    "priority": "high",
                    "action": "confirm_deal",
                    "title": (
                        f"Deal confirmation for {deal.property.title}"
                    ),
                    "created_at": deal.created_at.isoformat(),
                }
            )

        inbox_items.sort(
            key=lambda item: item["created_at"],
            reverse=True,
        )

        active_introductions = introductions.filter(
            status__in=[
                ProtectedIntroduction.Status.ACTIVE,
                ProtectedIntroduction.Status.DISPUTED,
            ],
        )
        try:
            trust_record = partner.trust_score_record
        except Exception:
            trust_record = None

        successful_transactions = (
            trust_record.successful_deals
            if trust_record
            else 0
        )

        current_plan = partner.commission_plan

        next_plan = (
            CommissionPlan.objects
            .filter(
                is_active=True,
                minimum_completed_transactions__gt=successful_transactions,
            )
            .order_by(
                "minimum_completed_transactions",
                "partner_share_rate",
            )
            .first()
        )

        if next_plan:
            transactions_needed = max(
                next_plan.minimum_completed_transactions
                - successful_transactions,
                0,
            )

            if current_plan:
                current_threshold = (
                    current_plan.minimum_completed_transactions
                )
            else:
                current_threshold = 0

            tier_span = max(
                next_plan.minimum_completed_transactions
                - current_threshold,
                1,
            )

            progress_in_tier = max(
                successful_transactions - current_threshold,
                0,
            )

            tier_progress_percent = min(
                (progress_in_tier / tier_span) * 100,
                100,
            )
        else:
            transactions_needed = 0
            tier_progress_percent = 100
        
        today_viewings = viewings.filter(
            Q(confirmed_date=today)
            | Q(
                confirmed_date__isnull=True,
                requested_date=today,
            )
        ).order_by(
            "confirmed_time",
            "requested_time",
            "id",
        )

        confirmed_viewings = viewings.filter(
            status=Viewing.Status.CONFIRMED,
        )

        completed_today = viewings.filter(
            status=Viewing.Status.COMPLETED,
            completed_at__date=today,
        )

        
        property_summary = properties.aggregate(
            total=Count("id"),
            published=Count(
                "id",
                filter=Q(status=Property.STATUS_PUBLISHED),
            ),
            pending=Count(
                "id",
                filter=Q(status=Property.STATUS_PENDING),
            ),
            reserved=Count(
                "id",
                filter=Q(status=Property.STATUS_RESERVED),
            ),
            rented=Count(
                "id",
                filter=Q(status=Property.STATUS_RENTED),
            ),
            sold=Count(
                "id",
                filter=Q(status=Property.STATUS_SOLD),
            ),
        )

        viewing_summary = viewings.aggregate(
            total=Count("id"),
            pending_payment=Count(
                "id",
                filter=Q(status=Viewing.Status.PENDING_PAYMENT),
            ),
            payment_processing=Count(
                "id",
                filter=Q(status=Viewing.Status.PAYMENT_PROCESSING),
            ),
            paid_pending_partner=Count(
                "id",
                filter=Q(status=Viewing.Status.PAID_PENDING_PARTNER),
            ),
            reschedule_proposed=Count(
                "id",
                filter=Q(status=Viewing.Status.RESCHEDULE_PROPOSED),
            ),
            confirmed=Count(
                "id",
                filter=Q(status=Viewing.Status.CONFIRMED),
            ),
            completed=Count(
                "id",
                filter=Q(status=Viewing.Status.COMPLETED),
            ),
            cancelled=Count(
                "id",
                filter=Q(status=Viewing.Status.CANCELLED),
            ),
        )

        paid_statuses = [
            Viewing.Status.PAID_PENDING_PARTNER,
            Viewing.Status.RESCHEDULE_PROPOSED,
            Viewing.Status.CONFIRMED,
            Viewing.Status.COMPLETED,
        ]

        viewing_fees_processed = (
            viewings
            .filter(status__in=paid_statuses)
            .aggregate(total=Sum("fee_amount"))
            .get("total")
            or Decimal("0.00")
        )

        dashboard_viewings = viewings.filter(
            status__in=[
                Viewing.Status.PAID_PENDING_PARTNER,
                Viewing.Status.RESCHEDULE_PROPOSED,
                Viewing.Status.CONFIRMED,
                Viewing.Status.COMPLETED,
            ]
        )

        return Response(
            {
                "partner": PartnerDashboardProfileSerializer(
                    partner,
                    context={"request": request},
                ).data,
                "inbox": {
                    "count": len(inbox_items),
                    "items": inbox_items,
                },
                "attention": {
                    "viewing_requests": pending_requests.count(),
                    "active_introductions": active_introductions.count(),
                    "deal_confirmations": awaiting_partner_confirmation.count(),
                    "active_deals": active_deals.count(),
                    "unread_notifications": unread_notifications.count(),
                },
                "summary": {
                    "active_properties": properties.filter(
                        status=Property.STATUS_PUBLISHED,
                    ).count(),
                    "today_viewings": today_viewings.count(),
                    "pending_requests": pending_requests.count(),
                    "confirmed_viewings": confirmed_viewings.count(),
                    "completed_today": completed_today.count(),
                    "properties": property_summary,
                    "viewings": viewing_summary,
                    "viewing_fees_processed": (
                        f"{viewing_fees_processed:.2f}"
                    ),
                    "currency": "KES",
                },
                "deals": {
                    "active": active_deals.count(),
                    "awaiting_partner_confirmation": (
                        awaiting_partner_confirmation.count()
                    ),
                    "total": deals.count(),
                },

                "commissions": {
                    "total_allocated_to_partner": f"{commission_total:.2f}",
                    "share_count": partner_commission_shares.count(),
                    "currency": "KES",
                },

                "trust": (
                    {
                        "score": f"{trust_record.score:.2f}",
                        "confidence": f"{trust_record.confidence:.2f}",
                        "grade": trust_record.grade,
                        "average_rating": f"{trust_record.average_rating:.2f}",
                        "viewing_completion_rate": (
                            f"{trust_record.viewing_completion_rate:.2f}"
                        ),
                        "successful_deals": trust_record.successful_deals,
                        "evaluated_deals": trust_record.evaluated_deals,
                        "disputed_deals": trust_record.disputed_deals,
                        "owner_confirmation_rate": (
                            f"{trust_record.owner_confirmation_rate:.2f}"
                        ),
                        "active_restriction": trust_record.active_restriction,
                        "permanently_banned": trust_record.permanently_banned,
                    }
                    if trust_record
                    else None
                ),

                "tier_progress": {
                    "successful_transactions": successful_transactions,

                    "current_plan": (
                        {
                            "id": current_plan.id,
                            "name": current_plan.name,
                            "partner_share_rate": (
                                f"{current_plan.partner_share_rate:.2f}"
                            ),
                            "minimum_completed_transactions": (
                                current_plan.minimum_completed_transactions
                            ),
                        }
                        if current_plan
                        else None
                    ),

                    "next_plan": (
                        {
                            "id": next_plan.id,
                            "name": next_plan.name,
                            "partner_share_rate": (
                                f"{next_plan.partner_share_rate:.2f}"
                            ),
                            "minimum_completed_transactions": (
                                next_plan.minimum_completed_transactions
                            ),
                        }
                        if next_plan
                        else None
                    ),

                    "transactions_needed": transactions_needed,
                    "progress_percent": f"{tier_progress_percent:.2f}",
                },

                "notifications": [
                    {
                        "id": notification.id,
                        "title": notification.title,
                        "message": notification.message,
                        "notification_type": notification.notification_type,
                        "is_read": notification.is_read,
                        "created_at": notification.created_at.isoformat(),
                    }
                    for notification in notifications[:10]
                ],
                "today_viewings": PartnerDashboardViewingSerializer(
                    today_viewings,
                    many=True,
                    context={"request": request},
                ).data,
                "viewing_requests": PartnerDashboardViewingSerializer(
                    dashboard_viewings,
                    many=True,
                    context={"request": request},
                ).data,
                "properties": PartnerDashboardPropertySerializer(
                    properties,
                    many=True,
                    context={"request": request},
                ).data,
            },
            status=status.HTTP_200_OK,
        )


class PartnerPropertiesView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        partner = get_authenticated_partner(
            request.user,
            require_approved=False,
        )

        if partner is None:
            return Response(
                {"detail": "An active partner profile is required."},
                status=status.HTTP_403_FORBIDDEN,
            )

        properties = partner_properties_queryset(partner)

        serializer = PartnerDashboardPropertySerializer(
            properties,
            many=True,
            context={"request": request},
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )


class PartnerViewingsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        partner = get_authenticated_partner(
            request.user,
            require_approved=False,
        )

        if partner is None:
            return Response(
                {"detail": "An active partner profile is required."},
                status=status.HTTP_403_FORBIDDEN,
            )

        viewings = partner_viewings_queryset(partner)

        requested_status = request.query_params.get("status")

        if requested_status:
            valid_statuses = {
                choice[0]
                for choice in Viewing.Status.choices
            }

            if requested_status not in valid_statuses:
                return Response(
                    {
                        "status": [
                            "Enter a valid viewing status."
                        ]
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            viewings = viewings.filter(
                status=requested_status,
            )

        serializer = PartnerDashboardViewingSerializer(
            viewings,
            many=True,
            context={"request": request},
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )


class PartnerTodayViewingsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        partner = get_authenticated_partner(
            request.user,
            require_approved=False,
        )

        if partner is None:
            return Response(
                {"detail": "An active partner profile is required."},
                status=status.HTTP_403_FORBIDDEN,
            )

        today = timezone.localdate()

        viewings = (
            partner_viewings_queryset(partner)
            .filter(
                Q(confirmed_date=today)
                | Q(
                    confirmed_date__isnull=True,
                    requested_date=today,
                )
            )
            .order_by(
                "confirmed_time",
                "requested_time",
                "id",
            )
        )

        serializer = PartnerDashboardViewingSerializer(
            viewings,
            many=True,
            context={"request": request},
        )

        return Response(
            {
                "date": today.isoformat(),
                "count": viewings.count(),
                "viewings": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class PartnerConfirmViewingView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request, viewing_id):
        partner, viewing, error_response = _get_partner_viewing(
            request,
            viewing_id,
        )

        if error_response:
            return error_response

        allowed_statuses = [
            Viewing.Status.PAID_PENDING_PARTNER,
            Viewing.Status.RESCHEDULE_PROPOSED,
        ]

        if viewing.status not in allowed_statuses:
            return Response(
                {
                    "detail": (
                        "Only a paid viewing awaiting partner action "
                        "or a rescheduled viewing can be confirmed."
                    ),
                    "current_status": viewing.status,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if viewing.operational_status != "idle":
            return _operational_error(
                viewing,
                "This viewing cannot be confirmed after live activity begins.",
            )

        confirmed_date_value = request.data.get("confirmed_date")
        confirmed_time_value = request.data.get("confirmed_time")

        response_message = str(
            request.data.get("partner_response_message", "")
        ).strip()

        confirmed_date = (
            parse_date(str(confirmed_date_value))
            if confirmed_date_value
            else viewing.proposed_date or viewing.requested_date
        )

        confirmed_time = (
            parse_time(str(confirmed_time_value))
            if confirmed_time_value
            else viewing.proposed_time or viewing.requested_time
        )

        if not isinstance(confirmed_date, date):
            return Response(
                {
                    "confirmed_date": [
                        "Enter a valid date in YYYY-MM-DD format."
                    ]
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not isinstance(confirmed_time, time):
            return Response(
                {
                    "confirmed_time": [
                        "Enter a valid time in HH:MM format."
                    ]
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if confirmed_date < timezone.localdate():
            return Response(
                {
                    "confirmed_date": [
                        "The confirmed viewing date cannot be in the past."
                    ]
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(response_message) > 2000:
            return Response(
                {
                    "partner_response_message": [
                        "The response message cannot exceed 2000 characters."
                    ]
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        responded_at = timezone.now()

        viewing.assigned_partner = partner
        viewing.status = Viewing.Status.CONFIRMED
        viewing.confirmed_date = confirmed_date
        viewing.confirmed_time = confirmed_time
        viewing.partner_response_message = response_message
        viewing.partner_responded_at = responded_at
        viewing.proposed_date = None
        viewing.proposed_time = None

        viewing.save(
            update_fields=[
                "assigned_partner",
                "status",
                "confirmed_date",
                "confirmed_time",
                "partner_response_message",
                "partner_responded_at",
                "proposed_date",
                "proposed_time",
                "updated_at",
            ]
        )

        viewing.record_event(
            event_type=ViewingEvent.EventType.PARTNER_CONFIRMED,
            actor=request.user,
            notes=response_message,
            metadata={
                "confirmed_date": confirmed_date.isoformat(),
                "confirmed_time": confirmed_time.isoformat(),
            },
        )

        return Response(
            {
                "detail": "Viewing confirmed successfully.",
                "viewing": serialize_viewing(viewing, request),
            },
            status=status.HTTP_200_OK,
        )


class PartnerRescheduleViewingView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request, viewing_id):
        partner, viewing, error_response = _get_partner_viewing(
            request,
            viewing_id,
        )

        if error_response:
            return error_response

        allowed_statuses = [
            Viewing.Status.PAID_PENDING_PARTNER,
            Viewing.Status.CONFIRMED,
        ]

        if viewing.status not in allowed_statuses:
            return Response(
                {
                    "detail": (
                        "Only a paid or confirmed viewing can be rescheduled."
                    ),
                    "current_status": viewing.status,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if viewing.operational_status != "idle":
            return _operational_error(
                viewing,
                "A viewing cannot be rescheduled after live activity begins.",
            )

        proposed_date_value = request.data.get("proposed_date")
        proposed_time_value = request.data.get("proposed_time")

        response_message = str(
            request.data.get("partner_response_message", "")
        ).strip()

        proposed_date = (
            parse_date(str(proposed_date_value))
            if proposed_date_value
            else None
        )

        proposed_time = (
            parse_time(str(proposed_time_value))
            if proposed_time_value
            else None
        )

        errors = {}

        if proposed_date is None:
            errors["proposed_date"] = [
                "Enter a valid date in YYYY-MM-DD format."
            ]
        elif proposed_date < timezone.localdate():
            errors["proposed_date"] = [
                "The proposed viewing date cannot be in the past."
            ]

        if proposed_time is None:
            errors["proposed_time"] = [
                "Enter a valid time in HH:MM format."
            ]

        if not response_message:
            errors["partner_response_message"] = [
                "Please explain why another time is being proposed."
            ]
        elif len(response_message) > 2000:
            errors["partner_response_message"] = [
                "The response message cannot exceed 2000 characters."
            ]

        if errors:
            return Response(
                errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        responded_at = timezone.now()

        viewing.assigned_partner = partner
        viewing.status = Viewing.Status.RESCHEDULE_PROPOSED
        viewing.proposed_date = proposed_date
        viewing.proposed_time = proposed_time
        viewing.confirmed_date = None
        viewing.confirmed_time = None
        viewing.partner_response_message = response_message
        viewing.partner_responded_at = responded_at

        viewing.save(
            update_fields=[
                "assigned_partner",
                "status",
                "proposed_date",
                "proposed_time",
                "confirmed_date",
                "confirmed_time",
                "partner_response_message",
                "partner_responded_at",
                "updated_at",
            ]
        )

        viewing.record_event(
            event_type=ViewingEvent.EventType.RESCHEDULE_PROPOSED,
            actor=request.user,
            notes=response_message,
            metadata={
                "proposed_date": proposed_date.isoformat(),
                "proposed_time": proposed_time.isoformat(),
            },
        )

        return Response(
            {
                "detail": "Alternative viewing date and time proposed.",
                "viewing": serialize_viewing(viewing, request),
            },
            status=status.HTTP_200_OK,
        )


class PartnerDeclineViewingView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request, viewing_id):
        partner, viewing, error_response = _get_partner_viewing(
            request,
            viewing_id,
        )

        if error_response:
            return error_response

        allowed_statuses = [
            Viewing.Status.PAID_PENDING_PARTNER,
            Viewing.Status.RESCHEDULE_PROPOSED,
            Viewing.Status.CONFIRMED,
        ]

        if viewing.status not in allowed_statuses:
            return Response(
                {
                    "detail": "This viewing can no longer be declined.",
                    "current_status": viewing.status,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if viewing.operational_status != "idle":
            return _operational_error(
                viewing,
                "A viewing cannot be declined after live activity begins.",
            )

        reason = str(
            request.data.get("partner_response_message", "")
        ).strip()

        if not reason:
            return Response(
                {
                    "partner_response_message": [
                        "Please provide a reason for declining the viewing."
                    ]
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(reason) > 2000:
            return Response(
                {
                    "partner_response_message": [
                        "The reason cannot exceed 2000 characters."
                    ]
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        viewing.assigned_partner = partner
        viewing.status = Viewing.Status.CANCELLED
        viewing.partner_response_message = reason
        viewing.partner_responded_at = timezone.now()

        viewing.save(
            update_fields=[
                "assigned_partner",
                "status",
                "partner_response_message",
                "partner_responded_at",
                "updated_at",
            ]
        )

        viewing.record_event(
            event_type=ViewingEvent.EventType.VIEWING_CANCELLED,
            actor=request.user,
            notes=reason,
            metadata={
                "cancelled_by": "partner",
            },
        )

        return Response(
            {
                "detail": "Viewing declined successfully.",
                "viewing": serialize_viewing(viewing, request),
            },
            status=status.HTTP_200_OK,
        )