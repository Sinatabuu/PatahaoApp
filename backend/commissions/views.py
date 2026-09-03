from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.db.models.functions import Coalesce
from django.utils.dateparse import parse_date

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ReadOnlyModelViewSet

from partners.models import Partner

from .models import (
    CommissionAgreement,
    CommissionSettlement,
    CommissionSettlementParticipant,
    CommissionSettlementPayment,
)
from .serializers import (
    PartnerCommissionAgreementSerializer,
    PartnerCommissionSettlementSerializer,
    StaffCommissionPayoutSerializer,
    StaffCommissionSettlementSerializer,
)


from .services import (
    approve_commission_settlement,
    pay_commission_participant_outstanding,
)

class PartnerCommissionAccessMixin:
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get_authenticated_partner(self):
        user = self.request.user

        if getattr(user, "role", None) != "partner":
            raise PermissionDenied(
                "Only partner accounts may access commission records."
            )

        partner = getattr(
            user,
            "partner_profile",
            None,
        )

        if partner is None:
            raise PermissionDenied(
                "This account does not have a partner profile."
            )

        if not partner.is_active:
            raise PermissionDenied(
                "This partner profile is currently inactive."
            )

        if partner.verification_status != Partner.STATUS_APPROVED:
            raise PermissionDenied(
                "The partner profile must be approved before "
                "accessing commission records."
            )

        return partner


class PartnerCommissionAgreementViewSet(
    PartnerCommissionAccessMixin,
    viewsets.ModelViewSet,
):
    serializer_class = PartnerCommissionAgreementSerializer

    http_method_names = [
        "get",
        "post",
        "patch",
        "head",
        "options",
    ]

    def get_queryset(self):
        if self.request.user.is_staff:
            return (
                CommissionAgreement.objects
                .select_related(
                    "property",
                    "property__partner",
                    "property__partner__user",
                    "accepted_by",
                    "verified_by",
                )
                .order_by("-created_at")
            )

        partner = self.get_authenticated_partner()

        return (
            CommissionAgreement.objects
            .filter(property__partner=partner)
            .select_related(
                "property",
                "property__partner",
                "property__partner__user",
                "accepted_by",
                "verified_by",
            )
            .order_by("-created_at")
        )

    def perform_create(self, serializer):
        partner = self.get_authenticated_partner()

        property_obj = serializer.validated_data["property"]

        if property_obj.partner_id != partner.id:
            raise PermissionDenied(
                "You can create a commission agreement only "
                "for your own property."
            )

        if CommissionAgreement.objects.filter(
            property=property_obj,
        ).exists():
            raise PermissionDenied(
                "This property already has a commission agreement."
            )

        serializer.save(
            created_by=self.request.user,
            currency="KES",
            status=CommissionAgreement.Status.DRAFT,
        )

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()

        if (
            instance.partner_accepted
            or instance.is_verified
            or instance.is_locked
        ):
            return Response(
                {
                    "detail": (
                        "Commission terms cannot be changed "
                        "after partner acceptance."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        return super().partial_update(
            request,
            *args,
            **kwargs,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="accept",
    )
    @transaction.atomic
    def accept(self, request, pk=None):
        agreement = (
            self.get_queryset()
            .select_for_update()
            .get(pk=pk)
        )

        if agreement.partner_accepted:
            return Response(
                self.get_serializer(agreement).data,
                status=status.HTTP_200_OK,
            )

        agreement.accept_by_partner(
            user=request.user,
        )
        agreement.save()

        return Response(
            self.get_serializer(agreement).data,
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="verify",
    )
    @transaction.atomic
    def verify_agreement(self, request, pk=None):
        if not request.user.is_staff:
            raise PermissionDenied(
                "Only Pata Hao administrators may verify "
                "commission agreements."
            )

        agreement = (
            CommissionAgreement.objects
            .select_for_update()
            .get(pk=pk)
        )

        if agreement.is_verified:
            return Response(
                self.get_serializer(agreement).data,
                status=status.HTTP_200_OK,
            )

        agreement.verify(
            verified_by=request.user,
        )
        agreement.save()

        return Response(
            self.get_serializer(agreement).data,
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="lock",
    )
    @transaction.atomic
    def lock_agreement(self, request, pk=None):
        if not request.user.is_staff:
            raise PermissionDenied(
                "Only Pata Hao administrators may lock "
                "commission agreements."
            )

        agreement = (
            CommissionAgreement.objects
            .select_for_update()
            .get(pk=pk)
        )

        if agreement.is_locked:
            return Response(
                self.get_serializer(agreement).data,
                status=status.HTTP_200_OK,
            )

        agreement.lock()
        agreement.save()

        return Response(
            self.get_serializer(agreement).data,
            status=status.HTTP_200_OK,
        )


class PartnerCommissionSettlementViewSet(
    PartnerCommissionAccessMixin,
    ReadOnlyModelViewSet,
):
    serializer_class = PartnerCommissionSettlementSerializer

    def get_queryset(self):
        partner = self.get_authenticated_partner()

        return (
            CommissionSettlement.objects
            .filter(
                participants__partner=partner,
                participants__is_platform_share=False,
            )
            .select_related(
                "deal",
                "deal__customer",
                "deal__property",
                "agreement",
                "agreement__property",
            )
            .prefetch_related(
                "participants",
                "participants__partner",
                "participants__partner__user",
                "participants__payments",
            )
            .distinct()
            .order_by(
                "-created_at",
                "-id",
            )
        )


class PartnerCommissionSummaryView(
    PartnerCommissionAccessMixin,
    APIView,
):
    def get(self, request):
        partner = self.get_authenticated_partner()

        participation_queryset = (
            CommissionSettlementParticipant.objects
            .filter(
                partner=partner,
                is_platform_share=False,
            )
            .select_related(
                "settlement",
            )
        )

        payment_totals = (
            CommissionSettlementPayment.objects
            .filter(
                participant__partner=partner,
                participant__is_platform_share=False,
            )
            .aggregate(
                paid_to_date=Coalesce(
                    Sum("amount"),
                    Decimal("0.00"),
                ),
            )
        )

        totals = participation_queryset.aggregate(
            total_commission=Coalesce(
                Sum("amount"),
                Decimal("0.00"),
            ),
            pending_commission=Coalesce(
                Sum(
                    "amount",
                    filter=Q(
                        settlement__status__in=[
                            CommissionSettlement.Status.DRAFT,
                            CommissionSettlement.Status.ALLOCATION_PENDING,
                            CommissionSettlement.Status.ALLOCATED,
                        ],
                    ),
                ),
                Decimal("0.00"),
            ),
            approved_commission=Coalesce(
                Sum(
                    "amount",
                    filter=Q(
                        settlement__status=CommissionSettlement.Status.APPROVED,
                    ),
                ),
                Decimal("0.00"),
            ),
            partially_paid_commission=Coalesce(
                Sum(
                    "amount",
                    filter=Q(
                        settlement__status=CommissionSettlement.Status.PARTIALLY_PAID,
                    ),
                ),
                Decimal("0.00"),
            ),
            paid_commission=Coalesce(
                Sum(
                    "amount",
                    filter=Q(
                        settlement__status=CommissionSettlement.Status.PAID,
                    ),
                ),
                Decimal("0.00"),
            ),
            disputed_commission=Coalesce(
                Sum(
                    "amount",
                    filter=Q(
                        settlement__status=CommissionSettlement.Status.DISPUTED,
                    ),
                ),
                Decimal("0.00"),
            ),
            settlement_count=Count(
                "settlement",
                distinct=True,
            ),
        )

        return Response(
            {
                "partner_id": partner.id,
                "partner_name": (
                    partner.display_name
                    or partner.business_name
                    or partner.user.get_full_name()
                    or partner.user.email
                ),
                "total_commission": totals["total_commission"],
                "paid_to_date": payment_totals["paid_to_date"],
                "outstanding_commission": (
                    totals["total_commission"]
                    - payment_totals["paid_to_date"]
                ),
                "pending_commission": totals["pending_commission"],
                "approved_commission": totals["approved_commission"],
                "partially_paid_commission": totals[
                    "partially_paid_commission"
                ],
                "paid_commission": totals["paid_commission"],
                "disputed_commission": totals[
                    "disputed_commission"
                ],
                "settlement_count": totals["settlement_count"],
            },
            status=status.HTTP_200_OK,
        )


class StaffCommissionParticipantPayoutView(APIView):
    """
    Staff-controlled commission participant payout.

    Staff supplies payment evidence only.
    The backend derives the exact outstanding entitlement.
    """

    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def post(self, request, participant_id):
        if not request.user.is_staff:
            raise PermissionDenied(
                "Only Pata Hao administrators may authorize "
                "commission payouts."
            )

        serializer = StaffCommissionPayoutSerializer(
            data=request.data,
        )
        serializer.is_valid(
            raise_exception=True,
        )

        validated = serializer.validated_data

        try:
            payment, settlement = (
                pay_commission_participant_outstanding(
                    participant_id=participant_id,
                    actor=request.user,
                    payment_method=validated[
                        "payment_method"
                    ],
                    payment_reference=validated[
                        "payment_reference"
                    ],
                    paid_at=validated.get(
                        "paid_at"
                    ),
                    notes=validated.get(
                        "notes",
                        "",
                    ),
                )
            )

        except ValidationError as exc:
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

            return Response(
                {
                    "detail": detail,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "payment": {
                    "id": payment.id,
                    "participant_id": (
                        payment.participant_id
                    ),
                    "amount": str(
                        payment.amount
                    ),
                    "currency": (
                        payment.currency
                    ),
                    "payment_method": (
                        payment.payment_method
                    ),
                    "payment_reference": (
                        payment.payment_reference
                    ),
                    "paid_at": (
                        payment.paid_at
                    ),
                    "notes": payment.notes,
                    "created_at": (
                        payment.created_at
                    ),
                },
                "settlement": {
                    "id": settlement.id,
                    "status": (
                        settlement.status
                    ),
                    "gross_commission_amount": str(
                        settlement.gross_commission_amount
                    ),
                },
            },
            status=status.HTTP_201_CREATED,
        )


class StaffCommissionSettlementDetailView(APIView):
    """
    Staff read-only view of the backend-controlled
    commission settlement for one deal.

    Financial amounts are derived from immutable/backend
    accounting records. This endpoint accepts no financial
    input from staff.
    """

    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get(self, request, deal_id):
        if not request.user.is_staff:
            raise PermissionDenied(
                "Only Pata Hao administrators may view "
                "staff commission settlement details."
            )

        try:
            settlement = (
                CommissionSettlement.objects
                .select_related(
                    "deal",
                    "deal__property",
                    "agreement",
                )
                .prefetch_related(
                    "participants",
                    "participants__partner",
                    "participants__partner__user",
                    "participants__payments",
                )
                .get(
                    deal_id=deal_id,
                )
            )

        except CommissionSettlement.DoesNotExist:
            return Response(
                {
                    "detail": (
                        "No commission settlement exists "
                        "for this deal."
                    )
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = StaffCommissionSettlementSerializer(
            settlement,
            context={
                "request": request,
            },
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )


class StaffCommissionSettlementApprovalView(APIView):
    """
    Staff-only approval of an existing backend-calculated
    commission settlement.

    This endpoint accepts no financial amounts, percentages,
    recipients, or allocation data.
    """

    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def post(self, request, settlement_id):
        if not request.user.is_staff:
            raise PermissionDenied(
                "Only Pata Hao administrators may approve "
                "commission settlements."
            )

        if request.data:
            return Response(
                {
                    "detail": (
                        "Commission settlement approval does not "
                        "accept financial input."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            settlement, approved = (
                approve_commission_settlement(
                    settlement_id=settlement_id,
                    actor=request.user,
                )
            )

        except ValidationError as exc:
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

            return Response(
                {
                    "detail": detail,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = StaffCommissionSettlementSerializer(
            settlement,
            context={
                "request": request,
            },
        )

        return Response(
            {
                "approved": approved,
                "settlement": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class StaffCommissionReportView(APIView):
    """
    Staff-only searchable commission audit report.

    All financial totals are derived from backend settlement,
    allocation, and immutable payment evidence.

    Supports:
    - free-text audit search
    - deal type filtering
    - settlement status filtering
    - payout state filtering
    - closed date range filtering
    - server-side sorting
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
                        "commission reporting."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        search = request.query_params.get(
            "search",
            "",
        ).strip()

        deal_type = request.query_params.get(
            "deal_type",
            "",
        ).strip()

        settlement_status = request.query_params.get(
            "settlement_status",
            "",
        ).strip()

        payout_state = request.query_params.get(
            "payout_state",
            "",
        ).strip()

        closed_from_raw = request.query_params.get(
            "closed_from",
            "",
        ).strip()

        closed_to_raw = request.query_params.get(
            "closed_to",
            "",
        ).strip()

        sort = request.query_params.get(
            "sort",
            "newest_closed",
        ).strip()

        closed_only = (
            request.query_params.get(
                "closed_only",
                "true",
            )
            .strip()
            .lower()
            not in {
                "0",
                "false",
                "no",
            }
        )

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

        page = max(
            page,
            1,
        )

        page_size = max(
            1,
            min(
                page_size,
                100,
            ),
        )

        closed_from = None
        closed_to = None

        if closed_from_raw:
            closed_from = parse_date(
                closed_from_raw
            )

            if closed_from is None:
                return Response(
                    {
                        "closed_from": [
                            "Use YYYY-MM-DD."
                        ]
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        if closed_to_raw:
            closed_to = parse_date(
                closed_to_raw
            )

            if closed_to is None:
                return Response(
                    {
                        "closed_to": [
                            "Use YYYY-MM-DD."
                        ]
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        if (
            closed_from is not None
            and closed_to is not None
            and closed_from > closed_to
        ):
            return Response(
                {
                    "closed_to": [
                        "The end date cannot be before "
                        "the start date."
                    ]
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        reportable_statuses = [
            CommissionSettlement.Status.APPROVED,
            CommissionSettlement.Status.PARTIALLY_PAID,
            CommissionSettlement.Status.PAID,
        ]

        queryset = (
            CommissionSettlement.objects
            .filter(
                status__in=reportable_statuses,
            )
            .select_related(
                "deal",
                "deal__property",
                "deal__customer",
                "deal__partner",
                "deal__partner__user",
                "agreement",
            )
        )

        if closed_only:
            queryset = queryset.filter(
                deal__status="completed",
                deal__closed_at__isnull=False,
            )

        if search:
            queryset = queryset.filter(
                Q(
                    deal__deal_number__icontains=search,
                )
                | Q(
                    deal__property__title__icontains=search,
                )
                | Q(
                    deal__customer__username__icontains=search,
                )
                | Q(
                    deal__customer__email__icontains=search,
                )
                | Q(
                    deal__customer__full_name__icontains=search,
                )
                | Q(
                    deal__partner__display_name__icontains=search,
                )
                | Q(
                    deal__partner__business_name__icontains=search,
                )
                | Q(
                    deal__partner__user__full_name__icontains=search,
                )
                | Q(
                    deal__partner__user__email__icontains=search,
                )
                | Q(
                    agreement__owner_name__icontains=search,
                )
                | Q(
                    deal__commission_invoice__invoice_number__icontains=search,
                )
                | Q(
                    participants__payments__payment_reference__icontains=search,
                )
            ).distinct()

        if deal_type:
            queryset = queryset.filter(
                deal__deal_type=deal_type,
            )

        if settlement_status:
            valid_statuses = {
                value
                for value, _label
                in CommissionSettlement.Status.choices
            }

            if settlement_status not in valid_statuses:
                return Response(
                    {
                        "settlement_status": [
                            "Invalid settlement status."
                        ]
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            queryset = queryset.filter(
                status=settlement_status,
            )

        if payout_state == "fully_paid":
            queryset = queryset.filter(
                status=CommissionSettlement.Status.PAID,
            )

        elif payout_state == "outstanding":
            queryset = queryset.filter(
                status__in=[
                    CommissionSettlement.Status.APPROVED,
                    CommissionSettlement.Status.PARTIALLY_PAID,
                ],
            )

        elif payout_state:
            return Response(
                {
                    "payout_state": [
                        "Use fully_paid or outstanding."
                    ]
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if closed_from is not None:
            queryset = queryset.filter(
                deal__closed_at__date__gte=closed_from,
            )

        if closed_to is not None:
            queryset = queryset.filter(
                deal__closed_at__date__lte=closed_to,
            )

        sort_options = {
            "newest_closed": (
                "-deal__closed_at",
                "-id",
            ),
            "oldest_closed": (
                "deal__closed_at",
                "id",
            ),
            "highest_commission": (
                "-gross_commission_amount",
                "-deal__closed_at",
            ),
            "lowest_commission": (
                "gross_commission_amount",
                "-deal__closed_at",
            ),
        }

        if sort not in sort_options:
            return Response(
                {
                    "sort": [
                        "Invalid report sort option."
                    ]
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        queryset = queryset.order_by(
            *sort_options[sort]
        )

        # Financial summaries are calculated over the entire
        # filtered queryset, not only the current page.
        gross_commission = (
            queryset.aggregate(
                total=Sum(
                    "gross_commission_amount"
                )
            )["total"]
            or Decimal("0.00")
        )

        platform_participants = (
            CommissionSettlementParticipant.objects
            .filter(
                settlement__in=queryset,
                is_platform_share=True,
            )
        )

        external_participants = (
            CommissionSettlementParticipant.objects
            .filter(
                settlement__in=queryset,
                is_platform_share=False,
            )
        )

        pata_hao_retained_revenue = (
            platform_participants.aggregate(
                total=Sum("amount")
            )["total"]
            or Decimal("0.00")
        )

        external_allocations = (
            external_participants.aggregate(
                total=Sum("amount")
            )["total"]
            or Decimal("0.00")
        )

        external_payouts = (
            CommissionSettlementPayment.objects
            .filter(
                participant__settlement__in=queryset,
                participant__is_platform_share=False,
            )
            .aggregate(
                total=Sum("amount")
            )["total"]
            or Decimal("0.00")
        )

        outstanding_payouts = (
            external_allocations
            - external_payouts
        ).quantize(
            Decimal("0.01")
        )

        total_count = queryset.count()

        fully_settled_deals = queryset.filter(
            status=CommissionSettlement.Status.PAID,
        ).count()

        total_pages = (
            total_count
            + page_size
            - 1
        ) // page_size

        start = (
            page - 1
        ) * page_size

        end = start + page_size

        page_items = list(
            queryset[
                start:end
            ]
            .prefetch_related(
                "participants",
                "participants__payments",
            )
        )

        results = []

        zero = Decimal("0.00")

        for settlement in page_items:
            platform_share = zero
            external_allocation = zero
            external_paid = zero

            for participant in settlement.participants.all():
                if participant.is_platform_share:
                    platform_share += participant.amount
                    continue

                external_allocation += participant.amount

                external_paid += sum(
                    (
                        payment.amount
                        for payment
                        in participant.payments.all()
                    ),
                    zero,
                )

            external_outstanding = (
                external_allocation
                - external_paid
            ).quantize(
                Decimal("0.01")
            )

            deal = settlement.deal

            customer_name = (
                deal.customer.get_full_name().strip()
                or getattr(
                    deal.customer,
                    "full_name",
                    "",
                )
                or deal.customer.email
                or deal.customer.username
            )

            partner_name = (
                deal.partner.display_name.strip()
                or deal.partner.business_name.strip()
                or deal.partner.user.get_full_name().strip()
                or deal.partner.user.email
            )

            invoice_number = ""

            try:
                invoice_number = (
                    deal.commission_invoice.invoice_number
                )
            except Exception:
                invoice_number = ""

            results.append(
                {
                    "deal_id": deal.id,
                    "deal_number": deal.deal_number,
                    "property_title": deal.property.title,
                    "customer_name": customer_name,
                    "partner_name": partner_name,
                    "owner_name": settlement.agreement.owner_name,
                    "invoice_number": invoice_number,
                    "deal_type": deal.deal_type,
                    "deal_status": deal.status,
                    "settlement_id": settlement.id,
                    "settlement_status": settlement.status,
                    "currency": settlement.currency,
                    "gross_commission": str(
                        settlement.gross_commission_amount
                    ),
                    "pata_hao_retained_revenue": str(
                        platform_share
                    ),
                    "external_allocations": str(
                        external_allocation
                    ),
                    "external_payouts": str(
                        external_paid
                    ),
                    "outstanding_payouts": str(
                        external_outstanding
                    ),
                    "completed_at": deal.completed_at,
                    "closed_at": deal.closed_at,
                }
            )

        return Response(
            {
                "currency": "KES",
                "completed_deals": total_count,
                "fully_settled_deals": fully_settled_deals,
                "gross_commission": str(
                    gross_commission.quantize(
                        Decimal("0.01")
                    )
                ),
                "pata_hao_retained_revenue": str(
                    pata_hao_retained_revenue.quantize(
                        Decimal("0.01")
                    )
                ),
                "external_allocations": str(
                    external_allocations.quantize(
                        Decimal("0.01")
                    )
                ),
                "external_payouts": str(
                    external_payouts.quantize(
                        Decimal("0.01")
                    )
                ),
                "outstanding_payouts": str(
                    outstanding_payouts
                ),
                "count": total_count,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_previous": page > 1,
                "filters": {
                    "search": search,
                    "deal_type": deal_type,
                    "settlement_status": settlement_status,
                    "payout_state": payout_state,
                    "closed_from": closed_from_raw,
                    "closed_to": closed_to_raw,
                    "sort": sort,
                    "closed_only": closed_only,
                },

                # Keep this key for the existing Flutter client.
                "recent_deals": results,
            },
            status=status.HTTP_200_OK,
        )


class PartnerTransactionHistoryView(
    PartnerCommissionAccessMixin,
    APIView,
):
    """
    Partner-only completed transaction history.

    Combines deal context with only the authenticated
    partner's own commission entitlement and payout evidence.

    Supports:
    - search
    - deal type filter
    - payout state filter
    - pagination
    """

    def get(self, request):
        partner = self.get_authenticated_partner()

        search = request.query_params.get(
            "search",
            "",
        ).strip()

        deal_type = request.query_params.get(
            "deal_type",
            "",
        ).strip()

        payout_state = request.query_params.get(
            "payout_state",
            "",
        ).strip()

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
                    "25",
                )
            )
        except ValueError:
            page_size = 25

        page = max(page, 1)

        page_size = max(
            1,
            min(page_size, 100),
        )

        participants = (
            CommissionSettlementParticipant.objects
            .filter(
                partner=partner,
                is_platform_share=False,
                settlement__deal__partner=partner,
                settlement__deal__status="completed",
                settlement__deal__closed_at__isnull=False,
            )
            .select_related(
                "settlement",
                "settlement__deal",
                "settlement__deal__property",
                "settlement__deal__customer",
            )
            .prefetch_related(
                "payments",
            )
            .order_by(
                "-settlement__deal__closed_at",
                "-id",
            )
        )

        if search:
            participants = participants.filter(
                Q(
                    settlement__deal__deal_number__icontains=search,
                )
                | Q(
                    settlement__deal__property__title__icontains=search,
                )
                | Q(
                    settlement__deal__customer__username__icontains=search,
                )
                | Q(
                    settlement__deal__customer__email__icontains=search,
                )
                | Q(
                    settlement__deal__customer__full_name__icontains=search,
                )
                | Q(
                    payments__payment_reference__icontains=search,
                )
            ).distinct()

        if deal_type:
            if deal_type not in {
                "rental",
                "sale",
            }:
                return Response(
                    {
                        "deal_type": [
                            "Use rental or sale."
                        ]
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            participants = participants.filter(
                settlement__deal__deal_type=deal_type,
            )

        if payout_state == "paid":
            participants = participants.filter(
                settlement__status=(
                    CommissionSettlement.Status.PAID
                ),
            )

        elif payout_state == "outstanding":
            participants = participants.filter(
                settlement__status__in=[
                    CommissionSettlement.Status.APPROVED,
                    CommissionSettlement.Status.PARTIALLY_PAID,
                ],
            )

        elif payout_state:
            return Response(
                {
                    "payout_state": [
                        "Use paid or outstanding."
                    ]
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        total_count = participants.count()

        total_pages = (
            total_count
            + page_size
            - 1
        ) // page_size

        start = (
            page - 1
        ) * page_size

        end = start + page_size

        page_items = list(
            participants[start:end]
        )

        results = []

        zero = Decimal("0.00")

        for participant in page_items:
            settlement = participant.settlement
            deal = settlement.deal

            payments = list(
                participant.payments.all()
            )

            paid_amount = sum(
                (
                    payment.amount
                    for payment in payments
                ),
                zero,
            )

            outstanding_amount = (
                participant.amount
                - paid_amount
            ).quantize(
                Decimal("0.01")
            )

            customer_name = (
                deal.customer.get_full_name().strip()
                or getattr(
                    deal.customer,
                    "full_name",
                    "",
                )
                or deal.customer.email
                or deal.customer.username
            )

            results.append(
                {
                    "deal_id": deal.id,
                    "deal_number": deal.deal_number,
                    "property_id": deal.property_id,
                    "property_title": deal.property.title,
                    "customer_name": customer_name,
                    "deal_type": deal.deal_type,
                    "deal_status": deal.status,
                    "completed_at": deal.completed_at,
                    "closed_at": deal.closed_at,

                    "settlement_id": settlement.id,
                    "settlement_status": settlement.status,
                    "currency": settlement.currency,

                    "my_share": str(
                        participant.amount
                    ),
                    "paid_amount": str(
                        paid_amount.quantize(
                            Decimal("0.01")
                        )
                    ),
                    "outstanding_amount": str(
                        outstanding_amount
                    ),

                    "payments": [
                        {
                            "id": payment.id,
                            "amount": str(
                                payment.amount
                            ),
                            "currency": payment.currency,
                            "payment_method": (
                                payment.payment_method
                            ),
                            "payment_reference": (
                                payment.payment_reference
                            ),
                            "paid_at": payment.paid_at,
                        }
                        for payment in payments
                    ],
                }
            )

        return Response(
            {
                "count": total_count,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_previous": page > 1,
                "results": results,
            },
            status=status.HTTP_200_OK,
        )
