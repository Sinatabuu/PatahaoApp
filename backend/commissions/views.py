from decimal import Decimal

from django.db.models import Count, Q, Sum
from django.db.models.functions import Coalesce

from rest_framework import permissions, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ReadOnlyModelViewSet

from partners.models import Partner

from .models import (
    CommissionSettlement,
    CommissionSettlementParticipant,
)
from .serializers import (
    PartnerCommissionSettlementSerializer,
)


class PartnerCommissionAccessMixin:
    """
    Shared partner authentication and verification logic.
    """

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


class PartnerCommissionSettlementViewSet(
    PartnerCommissionAccessMixin,
    ReadOnlyModelViewSet,
):
    """
    Read-only partner commission settlement endpoint.

    A partner sees only settlements where they have a settlement
    participant record.
    """

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
    """
    Aggregated commission dashboard totals for the authenticated partner.
    """

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
                        settlement__status=(
                            CommissionSettlement.Status.APPROVED
                        ),
                    ),
                ),
                Decimal("0.00"),
            ),

            partially_paid_commission=Coalesce(
                Sum(
                    "amount",
                    filter=Q(
                        settlement__status=(
                            CommissionSettlement.Status.PARTIALLY_PAID
                        ),
                    ),
                ),
                Decimal("0.00"),
            ),

            paid_commission=Coalesce(
                Sum(
                    "amount",
                    filter=Q(
                        settlement__status=(
                            CommissionSettlement.Status.PAID
                        ),
                    ),
                ),
                Decimal("0.00"),
            ),

            disputed_commission=Coalesce(
                Sum(
                    "amount",
                    filter=Q(
                        settlement__status=(
                            CommissionSettlement.Status.DISPUTED
                        ),
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
