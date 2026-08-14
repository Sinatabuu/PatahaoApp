from decimal import Decimal

from django.db import transaction
from django.db.models import Count, Q, Sum
from django.db.models.functions import Coalesce

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
)
from .serializers import (
    PartnerCommissionAgreementSerializer,
    PartnerCommissionSettlementSerializer,
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
