from django.db import transaction
from django.shortcuts import get_object_or_404

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from partners.models import Partner

from .models import Deal, DealOutcome
from .serializers import (
    DealOutcomeSubmissionSerializer,
    DealSerializer,
)
from .services import evaluate_deal_outcomes


class DealViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only deal endpoint with controlled outcome submission.

    Access rules:

    Customer:
    - Can view only their own deals.
    - Can submit only the customer outcome.

    Partner:
    - Can view only deals assigned to their partner profile.
    - Can submit only the partner outcome.

    Staff:
    - Can view all deals.
    - Deal administration remains in Django Admin.

    Supported endpoints:

    GET  /api/deals/
    GET  /api/deals/<id>/
    POST /api/deals/<id>/customer-outcome/
    POST /api/deals/<id>/partner-outcome/
    """

    serializer_class = DealSerializer
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def _base_queryset(self):
        return (
            Deal.objects
            .select_related(
                "customer",
                "partner",
                "partner__user",
                "property",
                "viewing",
            )
            .prefetch_related(
                "outcomes",
            )
            .order_by(
                "-created_at",
                "-id",
            )
        )

    def _get_active_partner(self):
        partner = getattr(
            self.request.user,
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
                "accessing deals."
            )

        return partner

    def get_queryset(self):
        queryset = self._base_queryset()
        user = self.request.user

        if user.is_staff:
            return queryset

        if getattr(user, "role", None) == "partner":
            partner = self._get_active_partner()

            return queryset.filter(
                partner=partner,
            )

        return queryset.filter(
            customer=user,
        )

    def _get_customer_deal(self, pk):
        """
        Return the deal only when it belongs to the authenticated customer.
        """

        user = self.request.user

        if user.is_staff:
            raise PermissionDenied(
                "Staff accounts cannot submit customer outcomes."
            )

        if getattr(user, "role", None) != "customer":
            raise PermissionDenied(
                "Only a customer may submit a customer outcome."
            )

        return get_object_or_404(
            self._base_queryset(),
            pk=pk,
            customer=user,
        )

    def _get_partner_deal(self, pk):
        """
        Return the deal only when it belongs to the authenticated partner.
        """

        if self.request.user.is_staff:
            raise PermissionDenied(
                "Staff accounts cannot submit partner outcomes."
            )

        if getattr(self.request.user, "role", None) != "partner":
            raise PermissionDenied(
                "Only a partner may submit a partner outcome."
            )

        partner = self._get_active_partner()

        return get_object_or_404(
            self._base_queryset(),
            pk=pk,
            partner=partner,
        )

    def _save_outcome(
        self,
        *,
        request,
        deal,
        reporter,
    ):
        """
        Create or update one reporter's outcome and then run the central
        deal evaluation service.
        """

        input_serializer = DealOutcomeSubmissionSerializer(
            data=request.data,
        )

        input_serializer.is_valid(
            raise_exception=True,
        )

        outcome, created = DealOutcome.objects.update_or_create(
            deal=deal,
            reporter=reporter,
            defaults={
                "outcome": input_serializer.validated_data["outcome"],
                "notes": input_serializer.validated_data.get(
                    "notes",
                    "",
                ),
            },
        )

        evaluated_deal = evaluate_deal_outcomes(
            deal.id,
        )

        evaluated_deal = (
            self._base_queryset()
            .get(pk=evaluated_deal.pk)
        )

        output_serializer = self.get_serializer(
            evaluated_deal,
        )

        return Response(
            {
                "message": (
                    "Outcome submitted successfully."
                    if created
                    else "Outcome updated successfully."
                ),
                "outcome_created": created,
                "submitted_outcome": {
                    "id": outcome.id,
                    "reporter": outcome.reporter,
                    "outcome": outcome.outcome,
                    "notes": outcome.notes,
                },
                "deal": output_serializer.data,
            },
            status=(
                status.HTTP_201_CREATED
                if created
                else status.HTTP_200_OK
            ),
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="customer-outcome",
    )
    @transaction.atomic
    def customer_outcome(self, request, pk=None):
        deal = self._get_customer_deal(pk)

        return self._save_outcome(
            request=request,
            deal=deal,
            reporter=DealOutcome.Reporter.CUSTOMER,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="partner-outcome",
    )
    @transaction.atomic
    def partner_outcome(self, request, pk=None):
        deal = self._get_partner_deal(pk)

        return self._save_outcome(
            request=request,
            deal=deal,
            reporter=DealOutcome.Reporter.PARTNER,
        )