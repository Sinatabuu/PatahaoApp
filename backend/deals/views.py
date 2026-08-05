from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from partners.models import Partner

from .models import Deal, DealOutcome
from .serializers import (
    DealOutcomeSubmissionSerializer,
    DealSerializer,
    DealTimelineSerializer,
    OwnerOutcomeSubmissionSerializer,
)
from .services import (
    build_deal_timeline,
    evaluate_deal_outcomes,
    issue_owner_confirmation_token,
    submit_owner_outcome,
)


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
    - Can issue owner confirmation for assigned deals.

    Staff:
    - Can view all deals.
    - Can issue owner confirmation.
    - Deal administration remains in Django Admin.

    Supported endpoints:

    GET  /api/deals/
    GET  /api/deals/<id>/
    GET  /api/deals/<id>/timeline/
    POST /api/deals/<id>/customer-outcome/
    POST /api/deals/<id>/partner-outcome/
    POST /api/deals/<id>/issue-owner-confirmation/
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
        Create one immutable reporter outcome and run the central
        three-party deal evaluation service.
        """

        input_serializer = DealOutcomeSubmissionSerializer(
            data=request.data,
        )

        input_serializer.is_valid(
            raise_exception=True,
        )

        existing_outcome = DealOutcome.objects.filter(
            deal=deal,
            reporter=reporter,
        ).first()

        if existing_outcome is not None:
            return Response(
                {
                    "detail": (
                        "This confirmation has already been submitted "
                        "and cannot be changed."
                    ),
                    "submitted_outcome": {
                        "id": existing_outcome.id,
                        "reporter": existing_outcome.reporter,
                        "outcome": existing_outcome.outcome,
                        "notes": existing_outcome.notes,
                        "created_at": existing_outcome.created_at,
                    },
                },
                status=status.HTTP_409_CONFLICT,
            )

        outcome = DealOutcome.objects.create(
            deal=deal,
            reporter=reporter,
            outcome=input_serializer.validated_data["outcome"],
            notes=input_serializer.validated_data.get(
                "notes",
                "",
            ),
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
                "message": "Confirmation submitted successfully.",
                "submitted_outcome": {
                    "id": outcome.id,
                    "reporter": outcome.reporter,
                    "outcome": outcome.outcome,
                    "notes": outcome.notes,
                },
                "deal": output_serializer.data,
            },
            status=status.HTTP_201_CREATED,
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

    @action(
        detail=True,
        methods=["get"],
        url_path="timeline",
    )
    def timeline(self, request, pk=None):
        """
        Return the unified chronological timeline for one accessible deal.
        """

        deal = (
    self.get_queryset()
        .select_related(
            "customer",
            "partner",
            "partner__user",
            "property",
            "viewing",
            "introduction",
            "introduction__mandate",
            "introduction__mandate__owner",
            "introduction__mandate__partner",
            "introduction__commission_agreement",
        )
        .prefetch_related(
            "outcomes",
            "events__actor",
            "owner_confirmation_tokens__owner",
            "owner_confirmation_tokens__mandate",
            "owner_confirmation_tokens__created_by",
            "introduction__events__actor",
            "introduction__mandate__events__actor",
        )
        .filter(pk=pk)
        .first()
    )
        if deal is None:
            return Response(
                {
                    "detail": "Deal not found.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        timeline_items = build_deal_timeline(
            deal,
        )

        payload = {
            "deal": {
                "id": deal.id,
                "deal_number": deal.deal_number,
                "status": deal.status,
                "status_label": deal.get_status_display(),
                "property_id": deal.property_id,
                "property_title": deal.property.title,
                "customer_id": deal.customer_id,
                "partner_id": deal.partner_id,
            },
            "timeline": timeline_items,
        }

        serializer = DealTimelineSerializer(
            payload,
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="issue-owner-confirmation",
    )
    def issue_owner_confirmation(self, request, pk=None):
        """
        Issue a single-use owner confirmation token.

        Only Pata Hao staff or the deal's assigned partner may
        perform this action.
        """

        try:
            token_record, raw_token = (
                issue_owner_confirmation_token(
                    deal_id=pk,
                    actor=request.user,
                )
            )

        except Deal.DoesNotExist:
            return Response(
                {
                    "detail": "Deal not found.",
                },
                status=status.HTTP_404_NOT_FOUND,
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

        owner = token_record.owner
        mandate = token_record.mandate
        deal = token_record.deal

        return Response(
            {
                "status": "issued",
                "message": (
                    "Owner confirmation token issued successfully."
                ),
                "deal": {
                    "id": deal.id,
                    "deal_number": deal.deal_number,
                    "property_id": deal.property_id,
                },
                "owner": {
                    "owner_number": owner.owner_number,
                    "legal_name": owner.legal_name,
                    "phone_number": owner.phone_number,
                    "email": owner.email,
                },
                "mandate": {
                    "id": mandate.id,
                    "mandate_number": mandate.mandate_number,
                },
                "confirmation": {
                    "token": raw_token,
                    "expires_at": token_record.expires_at,
                    "submission_endpoint": (
                        "/api/deals/owner-confirmation/"
                    ),
                },
            },
            status=status.HTTP_201_CREATED,
        )


class OwnerOutcomeSubmissionView(APIView):
    """
    Public single-use-token endpoint for a property owner.

    The owner does not need a Pata Hao user account.
    """

    permission_classes = [
        permissions.AllowAny,
    ]

    def post(self, request):
        input_serializer = OwnerOutcomeSubmissionSerializer(
            data=request.data,
        )

        input_serializer.is_valid(
            raise_exception=True,
        )

        try:
            owner_outcome, evaluated_deal = submit_owner_outcome(
                raw_token=input_serializer.validated_data["token"],
                outcome=input_serializer.validated_data["outcome"],
                notes=input_serializer.validated_data.get(
                    "notes",
                    "",
                ),
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

        evaluated_deal = (
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
            .get(pk=evaluated_deal.pk)
        )

        return Response(
            {
                "message": (
                    "Owner confirmation submitted successfully."
                ),
                "submitted_outcome": {
                    "id": owner_outcome.id,
                    "reporter": owner_outcome.reporter,
                    "outcome": owner_outcome.outcome,
                    "notes": owner_outcome.notes,
                    "created_at": owner_outcome.created_at,
                },
                "deal": DealSerializer(
                    evaluated_deal,
                ).data,
            },
            status=status.HTTP_201_CREATED,
        )
