from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.db.models import Q
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from partners.models import Partner

from .models import (
    CommissionInvoice,
    CommissionReceipt,
    Deal,
    DealOutcome,
)
from .serializers import (
    DealOutcomeSubmissionSerializer,
    DealSerializer,
    DealTimelineSerializer,
    OwnerOutcomeSubmissionSerializer,
    CustomerCompletedDealSerializer,
)
from .services import (
    build_deal_timeline,
    close_commission_paid_deal,
    complete_agreed_deal_and_raise_commission,
    evaluate_deal_outcomes,
    evaluate_owner_confirmation_governance,
    issue_owner_confirmation_token,
    record_commission_receipt,
    submit_owner_outcome,
)
from governance.services import (
    raise_deal_governance_case,
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

    @action(
        detail=False,
        methods=["get"],
        url_path="my-completed",
    )
    def my_completed(self, request):
        """
        Return only the authenticated customer's
        administratively closed transactions.
        """

        user = request.user

        if user.is_staff:
            raise PermissionDenied(
                "Staff accounts cannot use customer transaction history."
            )

        if getattr(user, "role", None) != "customer":
            raise PermissionDenied(
                "Only customers may access customer transaction history."
            )

        queryset = (
            self._base_queryset()
            .filter(
                customer=user,
                status=Deal.Status.COMPLETED,
                closed_at__isnull=False,
            )
        )

        serializer = CustomerCompletedDealSerializer(
            queryset,
            many=True,
            context=self.get_serializer_context(),
        )

        return Response(serializer.data)

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
    @action(
        detail=True,
        methods=["post"],
        url_path="complete",
    )
    @transaction.atomic
    def complete_deal(self, request, pk=None):
        """
        Staff-only final transaction verification.

        This closes an AGREED property transaction and activates
        the locked commission obligation.
        """

        if not request.user.is_staff:
            return Response(
                {
                    "detail": (
                        "Only Pata Hao administrators may "
                        "complete a deal."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        notes = str(
            request.data.get(
                "notes",
                "",
            )
            or ""
        ).strip()

        if len(notes) > 2000:
            return Response(
                {
                    "notes": [
                        "Completion notes cannot exceed "
                        "2,000 characters."
                    ]
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            deal, settlement, settlement_created = (
                complete_agreed_deal_and_raise_commission(
                    deal_id=pk,
                    actor=request.user,
                    notes=notes,
                )
            )

        except Deal.DoesNotExist:
            return Response(
                {
                    "detail": "Deal not found."
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

        deal = (
            self._base_queryset()
            .get(pk=deal.pk)
        )

        return Response(
            {
                "message": (
                    "Deal completed and commission "
                    "obligation raised successfully."
                ),
                "deal": self.get_serializer(
                    deal
                ).data,
                "commission_settlement": {
                    "id": settlement.id,
                    "created": settlement_created,
                    "status": settlement.status,
                    "gross_commission_amount": (
                        settlement.gross_commission_amount
                    ),
                    "currency": settlement.currency,
                    "agreement_id": settlement.agreement_id,
                },
            },
            status=status.HTTP_200_OK,
        )


    @action(
        detail=True,
        methods=["post"],
        url_path="record-commission-receipt",
    )
    @transaction.atomic
    def record_commission_receipt_action(
        self,
        request,
        pk=None,
    ):
        """
        Staff-only recording of immutable commission
        receipt evidence.
        """

        if not request.user.is_staff:
            return Response(
                {
                    "detail": (
                        "Only Pata Hao administrators may "
                        "record commission receipts."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            deal = (
                self._base_queryset()
                .select_related(
                    "commission_invoice",
                )
                .get(pk=pk)
            )

        except Deal.DoesNotExist:
            return Response(
                {
                    "detail": "Deal not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            invoice = deal.commission_invoice

        except CommissionInvoice.DoesNotExist:
            return Response(
                {
                    "detail": (
                        "This deal does not have a "
                        "commission invoice."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        raw_amount = request.data.get("amount")

        try:
            amount = Decimal(
                str(raw_amount)
            ).quantize(
                Decimal("0.01")
            )

        except (
            TypeError,
            ValueError,
            ArithmeticError,
        ):
            return Response(
                {
                    "amount": [
                        "Enter a valid receipt amount."
                    ]
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        payment_method = str(
            request.data.get(
                "payment_method",
                "",
            )
            or ""
        ).strip()

        payment_reference = str(
            request.data.get(
                "payment_reference",
                "",
            )
            or ""
        ).strip()

        received_at = request.data.get(
            "received_at"
        )

        notes = str(
            request.data.get(
                "notes",
                "",
            )
            or ""
        ).strip()

        if amount in (None, ""):
            return Response(
                {
                    "amount": [
                        "Receipt amount is required."
                    ]
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not payment_method:
            return Response(
                {
                    "payment_method": [
                        "Payment method is required."
                    ]
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        valid_payment_methods = {
            choice[0]
            for choice in (
                CommissionReceipt
                .PaymentMethod
                .choices
            )
        }

        if payment_method not in valid_payment_methods:
            return Response(
                {
                    "payment_method": [
                        "Invalid commission payment method."
                    ]
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not payment_reference:
            return Response(
                {
                    "payment_reference": [
                        "Payment reference is required."
                    ]
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(payment_reference) > 150:
            return Response(
                {
                    "payment_reference": [
                        "Payment reference cannot exceed "
                        "150 characters."
                    ]
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(notes) > 2000:
            return Response(
                {
                    "notes": [
                        "Receipt notes cannot exceed "
                        "2,000 characters."
                    ]
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        parsed_received_at = None

        if received_at not in (None, ""):
            from django.utils.dateparse import (
                parse_datetime,
            )

            parsed_received_at = parse_datetime(
                str(received_at)
            )

            if parsed_received_at is None:
                return Response(
                    {
                        "received_at": [
                            "Enter a valid ISO-8601 "
                            "date and time."
                        ]
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        try:
            receipt, invoice = record_commission_receipt(
                invoice_id=invoice.id,
                actor=request.user,
                amount=amount,
                payment_method=payment_method,
                payment_reference=payment_reference,
                received_at=parsed_received_at,
                notes=notes,
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

        invoice.refresh_from_db()
        deal.refresh_from_db()

        total_received = sum(
            (
                item.amount
                for item in invoice.receipts.all()
            ),
            0,
        )

        outstanding = (
            invoice.amount
            - total_received
        )

        return Response(
            {
                "message": (
                    "Commission receipt recorded "
                    "successfully."
                ),
                "receipt": {
                    "id": receipt.id,
                    "amount": receipt.amount,
                    "currency": receipt.currency,
                    "payment_method": (
                        receipt.payment_method
                    ),
                    "payment_reference": (
                        receipt.payment_reference
                    ),
                    "received_at": (
                        receipt.received_at
                    ),
                    "notes": receipt.notes,
                },
                "invoice": {
                    "id": invoice.id,
                    "invoice_number": (
                        invoice.invoice_number
                    ),
                    "amount": invoice.amount,
                    "currency": invoice.currency,
                    "status": invoice.status,
                    "paid_at": invoice.paid_at,
                    "total_received": total_received,
                    "outstanding_amount": outstanding,
                },
                "deal": {
                    "id": deal.id,
                    "status": deal.status,
                },
            },
            status=status.HTTP_201_CREATED,
        )


    @action(
        detail=True,
        methods=["post"],
        url_path="close",
    )
    @transaction.atomic
    def close_deal(self, request, pk=None):
        """
        Staff-only final administrative closure.

        The deal must already have reached COMMISSION_PAID and
        its commission invoice must be fully paid.
        """

        if not request.user.is_staff:
            return Response(
                {
                    "detail": (
                        "Only Pata Hao administrators may "
                        "close a deal."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        notes = str(
            request.data.get(
                "notes",
                "",
            )
            or ""
        ).strip()

        if len(notes) > 2000:
            return Response(
                {
                    "notes": [
                        "Closure notes cannot exceed "
                        "2,000 characters."
                    ]
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            deal = close_commission_paid_deal(
                deal_id=pk,
                actor=request.user,
                notes=notes,
            )

        except Deal.DoesNotExist:
            return Response(
                {
                    "detail": "Deal not found."
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

        deal = (
            self._base_queryset()
            .get(pk=deal.pk)
        )

        return Response(
            {
                "message": "Deal closed successfully.",
                "deal": self.get_serializer(
                    deal
                ).data,
            },
            status=status.HTTP_200_OK,
        )


class AdminDealListView(APIView):
    """
    Staff-only scalable deal operations list.

    Supports:
    - search
    - status filter
    - deal type filter
    - pagination

    Existing /api/deals/ behaviour is intentionally
    left unchanged for customers and partners.
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
                        "deal operations."
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

        deal_type = request.query_params.get(
            "deal_type",
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

        if search:
            queryset = queryset.filter(
                Q(
                    deal_number__icontains=search,
                )
                | Q(
                    property__title__icontains=search,
                )
                | Q(
                    customer__username__icontains=search,
                )
                | Q(
                    customer__email__icontains=search,
                )
                | Q(
                    customer__full_name__icontains=search,
                )
                | Q(
                    partner__display_name__icontains=search,
                )
                | Q(
                    partner__business_name__icontains=search,
                )
            )

        if requested_status:
            queryset = queryset.filter(
                status=requested_status,
            )

        if deal_type:
            queryset = queryset.filter(
                deal_type=deal_type,
            )

        total_count = queryset.count()

        start = (page - 1) * page_size
        end = start + page_size

        page_items = queryset[
            start:end
        ]

        results = []

        for deal in page_items:
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

            transaction_value = None

            if deal.deal_type == "rental":
                transaction_value = deal.monthly_rent

            elif deal.deal_type == "sale":
                transaction_value = deal.sale_price

            results.append(
                {
                    "id": deal.id,
                    "deal_number": deal.deal_number,
                    "deal_type": deal.deal_type,
                    "status": deal.status,

                    "customer": deal.customer_id,
                    "customer_name": customer_name,

                    "partner": deal.partner_id,
                    "partner_name": partner_name,

                    "property": deal.property_id,
                    "property_title": deal.property.title,

                    "viewing": deal.viewing_id,
                    "viewing_status": deal.viewing.status,

                    "transaction_value": transaction_value,
                    "commission_amount": deal.commission_amount,

                    "customer_confirmed": (
                        deal.customer_confirmed
                    ),
                    "partner_confirmed": (
                        deal.partner_confirmed
                    ),
                    "owner_confirmed": (
                        deal.owner_confirmed
                    ),

                    "agreed_at": deal.agreed_at,
                    "completed_at": deal.completed_at,
                    "created_at": deal.created_at,
                    "updated_at": deal.updated_at,
                }
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
                "results": results,
            },
            status=status.HTTP_200_OK,
        )

class AdminDealOwnerConfirmationStatusView(APIView):
    """
    Staff-only read-only governance state for owner confirmation.
    """

    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get(self, request, deal_id):
        if not request.user.is_staff:
            return Response(
                {
                    "detail": (
                        "Only Pata Hao administrators may access "
                        "deal governance information."
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        deal = (
            Deal.objects
            .select_related(
                "property",
                "partner",
                "partner__user",
                "introduction",
                "introduction__mandate",
                "introduction__mandate__owner",
            )
            .filter(
                pk=deal_id,
            )
            .first()
        )

        if deal is None:
            return Response(
                {
                    "detail": "Deal not found.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        governance = (
            evaluate_owner_confirmation_governance(
                deal,
            )
        )

        mandate = governance["mandate"]
        owner = governance["owner"]

        payload = {
            "deal_id": deal.id,
            "deal_number": deal.deal_number,
            "eligible": governance["eligible"],
            "state": governance["state"],
            "reason_code": governance["reason_code"],
            "message": governance["message"],
            "mandate": None,
            "owner": None,
        }

        if mandate is not None:
            payload["mandate"] = {
                "id": mandate.id,
                "mandate_number": mandate.mandate_number,
                "status": mandate.status,
                "is_currently_valid": (
                    mandate.is_currently_valid
                ),
            }

        if owner is not None:
            payload["owner"] = {
                "owner_number": owner.owner_number,
                "legal_name": owner.legal_name,
                "is_verified": owner.is_verified,
                "has_phone": bool(
                    owner.phone_number
                ),
                "has_email": bool(
                    owner.email
                ),
            }

        return Response(
            payload,
            status=status.HTTP_200_OK,
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

class AdminDealGovernanceCaseView(APIView):
    """
    Staff formally raises the deal's current governance block.

    The backend independently reevaluates the deal.
    The client cannot choose the reason or responsible party.
    """

    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def post(self, request, deal_id):
        if not request.user.is_staff:
            return Response(
                {
                    "detail": (
                        "Only Pata Hao administrators may "
                        "raise deal governance cases."
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        deal = (
            Deal.objects
            .select_related(
                "property",
                "partner",
                "partner__user",
                "introduction",
                "introduction__mandate",
                "introduction__mandate__owner",
            )
            .filter(pk=deal_id)
            .first()
        )

        if deal is None:
            return Response(
                {"detail": "Deal not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        governance = (
            evaluate_owner_confirmation_governance(
                deal,
            )
        )

        try:
            case, created = (
                raise_deal_governance_case(
                    deal=deal,
                    governance=governance,
                    actor=request.user,
                )
            )
        except ValidationError as exc:
            detail = getattr(
                exc,
                "messages",
                None,
            ) or str(exc)

            return Response(
                {"detail": detail},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "id": case.id,
                "created": created,
                "status": case.status,
                "reason_code": (
                    case.reason_code
                ),
                "responsible_role": (
                    case.responsible_role
                ),
                "action_code": (
                    case.action_code
                ),
                "action_label": (
                    case.action_label
                ),
                "title": case.title,
                "message": case.message,
                "partner_id": (
                    case.partner_id
                ),
            },
            status=(
                status.HTTP_201_CREATED
                if created
                else status.HTTP_200_OK
            ),
        )