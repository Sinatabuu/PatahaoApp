from decimal import Decimal, InvalidOperation
import re
from uuid import uuid4

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response

from viewings.models import Viewing, ViewingEvent
from notifications.models import Notification

from .models import Payment, PaymentAttempt
from .serializers import PaymentSerializer
from .services import MpesaAPIError, MpesaClient


def _callback_metadata(callback):
    result = {}

    metadata = callback.get("CallbackMetadata", {})

    if not isinstance(metadata, dict):
        return result

    items = metadata.get("Item", [])

    if not isinstance(items, list):
        return result

    for item in items:
        if not isinstance(item, dict):
            continue

        name = item.get("Name")

        if name:
            result[name] = item.get("Value")

    return result


def _callback_response(*, accepted=True, description=None):
    if description is None:
        description = "Accepted" if accepted else "Rejected"

    return Response(
        {
            "ResultCode": 0 if accepted else 1,
            "ResultDesc": description,
        },
        status=(
            status.HTTP_200_OK
            if accepted
            else status.HTTP_400_BAD_REQUEST
        ),
    )


def _parse_callback_amount(value):
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None

    if not amount.is_finite() or amount <= Decimal("0.00"):
        return None

    try:
        normalized_amount = amount.quantize(Decimal("0.01"))
    except InvalidOperation:
        return None

    if amount != normalized_amount:
        return None

    return normalized_amount


def _legacy_payment_attempt(payment):
    """Create an attempt record for a pre-ledger in-flight payment."""

    defaults = {
        "status": PaymentAttempt.Status.PROCESSING,
        "merchant_request_id": payment.merchant_request_id,
        "requested_amount": payment.amount,
        "phone_number": payment.phone_number,
        "provider_response_code": payment.provider_response_code,
        "provider_response_description": (
            payment.provider_response_description
        ),
        "provider_request_payload": payment.provider_request_payload,
        "initiated_at": payment.initiated_at or payment.created_at,
    }

    try:
        attempt, _ = PaymentAttempt.objects.get_or_create(
            checkout_request_id=payment.checkout_request_id,
            defaults={
                "payment": payment,
                **defaults,
            },
        )
    except IntegrityError:
        attempt = PaymentAttempt.objects.get(
            checkout_request_id=payment.checkout_request_id,
        )

    return attempt


def _mark_attempt_for_review(
    attempt,
    payment,
    *,
    reason,
    callback_payload=None,
    query_payload=None,
):
    now = timezone.now()

    attempt.status = PaymentAttempt.Status.REVIEW_REQUIRED
    attempt.failure_reason = reason

    update_fields = [
        "status",
        "failure_reason",
        "updated_at",
    ]

    if callback_payload is not None:
        attempt.provider_callback_payload = callback_payload
        attempt.callback_received_at = now
        update_fields.extend(
            [
                "provider_callback_payload",
                "callback_received_at",
            ]
        )

    if query_payload is not None:
        attempt.provider_query_payload = query_payload
        attempt.reconciled_at = now
        update_fields.extend(
            [
                "provider_query_payload",
                "reconciled_at",
            ]
        )

    attempt.save(update_fields=update_fields)

    if (
        payment.status != Payment.Status.SUCCESSFUL
        and payment.checkout_request_id
        == attempt.checkout_request_id
    ):
        payment.status = Payment.Status.PROCESSING
        payment.failure_reason = reason
        payment.save(
            update_fields=[
                "status",
                "failure_reason",
                "updated_at",
            ]
        )


def _complete_payment(
    payment,
    viewing,
    *,
    provider_receipt,
    transaction_date,
    provider_transaction_id=None,
    actor=None,
):
    if payment.status == Payment.Status.SUCCESSFUL:
        return

    now = timezone.now()

    payment.status = Payment.Status.SUCCESSFUL
    payment.provider_transaction_id = (
        provider_transaction_id
        or payment.checkout_request_id
    )
    payment.provider_receipt_number = str(provider_receipt)

    if not payment.receipt_number:
        payment.receipt_number = Payment.generate_receipt_number()

    payment.failure_reason = ""
    payment.failed_at = None
    payment.paid_at = transaction_date or now

    payment.save(
        update_fields=[
            "status",
            "provider_transaction_id",
            "provider_receipt_number",
            "receipt_number",
            "failure_reason",
            "failed_at",
            "paid_at",
            "updated_at",
        ]
    )

    if viewing.status != Viewing.Status.PAID_PENDING_PARTNER:
        viewing.status = Viewing.Status.PAID_PENDING_PARTNER
        viewing.payment_reference = payment.payment_reference

        viewing.save(
            update_fields=[
                "status",
                "payment_reference",
                "updated_at",
            ]
        )

    event_exists = viewing.events.filter(
        event_type=ViewingEvent.EventType.PAYMENT_RECEIVED,
        metadata__payment_id=payment.id,
    ).exists()

    if not event_exists:
        viewing.record_event(
            event_type=ViewingEvent.EventType.PAYMENT_RECEIVED,
            actor=actor,
            notes=f"Payment received: {payment.receipt_number}",
            metadata={
                "payment_id": payment.id,
                "payment_reference": payment.payment_reference,
                "receipt_number": payment.receipt_number,
                "provider": payment.payment_method,
                "provider_receipt_number": (
                    payment.provider_receipt_number
                ),
                "amount": str(payment.amount),
                "currency": payment.currency,
            },
        )

        partner = (
            viewing.assigned_partner
            or viewing.property.partner
        )

        if partner and partner.user_id:
            Notification.objects.create(
                user=partner.user,
                title="New paid viewing request",
                message=(
                    f"A customer has paid for a viewing of "
                    f"{viewing.property.title}. "
                    f"Please review and respond to the request."
                ),
                notification_type=Notification.TYPE_VIEWING,
            )


class PaymentViewSet(viewsets.ModelViewSet):
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    http_method_names = [
        "get",
        "post",
        "head",
        "options",
    ]

    def get_queryset(self):
        queryset = (
            Payment.objects.select_related(
                "payer",
                "viewing",
                "viewing__property",
            )
            .order_by("-created_at")
        )

        if not self.request.user.is_staff:
            queryset = queryset.filter(
                payer=self.request.user,
            )

        viewing_id = self.request.query_params.get(
            "viewing"
        )

        if viewing_id:
            queryset = queryset.filter(
                viewing_id=viewing_id,
            )

        return queryset

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            data=request.data,
        )

        serializer.is_valid(
            raise_exception=True,
        )

        viewing = (
            Viewing.objects.select_for_update()
            .select_related("property")
            .get(
                pk=serializer.validated_data[
                    "viewing"
                ].pk
            )
        )

        if viewing.customer_id != request.user.id:
            return Response(
                {
                    "detail": (
                        "You cannot pay for another "
                        "customer's viewing."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        if (
            viewing.status
            != Viewing.Status.PENDING_PAYMENT
        ):
            return Response(
                {
                    "detail": (
                        "This viewing is not "
                        "awaiting payment."
                    ),
                    "current_status": viewing.status,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            payment = serializer.save(
                payer=request.user,
                viewing=viewing,
                amount=viewing.fee_amount,
                currency="KES",
                purpose="viewing_fee",
                status=Payment.Status.PENDING,
            )

        except IntegrityError:
            existing = (
                Payment.objects.filter(
                    viewing=viewing,
                )
                .first()
            )

            if (
                existing
                and existing.payer_id
                == request.user.id
            ):
                return Response(
                    self.get_serializer(
                        existing
                    ).data,
                    status=status.HTTP_200_OK,
                )

            raise

        viewing.status = (
            Viewing.Status.PAYMENT_PROCESSING
        )

        viewing.payment_reference = (
            payment.payment_reference
        )

        viewing.save(
            update_fields=[
                "status",
                "payment_reference",
                "updated_at",
            ]
        )

        return Response(
            self.get_serializer(payment).data,
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="initiate",
    )
    @transaction.atomic
    def initiate(self, request, pk=None):
        if (
            getattr(settings, "IS_PRODUCTION", False)
            and not settings.MPESA_LIVE_PAYMENTS_ENABLED
        ):
            return Response(
                {
                    "detail": (
                        "Live M-Pesa payments are not enabled "
                        "for this deployment."
                    )
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        payment = (
            self.get_queryset()
            .select_for_update()
            .get(pk=pk)
        )

        if (
            payment.payment_method
            != Payment.PaymentMethod.MPESA
        ):
            return Response(
                {
                    "detail": (
                        "Only M-Pesa initiation is "
                        "available in this phase."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if (
            payment.status
            == Payment.Status.SUCCESSFUL
        ):
            return Response(
                self.get_serializer(payment).data
            )

        if (
            payment.status
            == Payment.Status.PROCESSING
            and payment.checkout_request_id
        ):
            return Response(
                {
                    "detail": (
                        "M-Pesa request was already sent."
                    ),
                    "payment": self.get_serializer(
                        payment
                    ).data,
                }
            )

        if payment.status not in {
            Payment.Status.PENDING,
            Payment.Status.FAILED,
        }:
            return Response(
                {
                    "detail": (
                        "This payment cannot currently "
                        "be initiated."
                    ),
                    "current_status": payment.status,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            request_payload, provider_response = (
                MpesaClient().stk_push(
                    phone_number=payment.phone_number,
                    amount=payment.amount,
                    account_reference=(
                        payment.payment_reference
                    ),
                    description="Viewing fee",
                )
            )

        except MpesaAPIError as exc:
            payment.status = Payment.Status.FAILED
            payment.failure_reason = str(exc)
            payment.failed_at = timezone.now()
            payment.provider_callback_payload = (
                exc.payload
            )

            payment.save(
                update_fields=[
                    "status",
                    "failure_reason",
                    "failed_at",
                    "provider_callback_payload",
                    "updated_at",
                ]
            )

            return Response(
                {
                    "detail": str(exc),
                    "provider_error": exc.payload,
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        merchant_request_id = provider_response.get(
            "MerchantRequestID",
            "",
        )
        checkout_request_id = provider_response.get(
            "CheckoutRequestID",
            "",
        )

        if not merchant_request_id or not checkout_request_id:
            payment.status = Payment.Status.FAILED
            payment.failure_reason = (
                "M-Pesa accepted the request without returning "
                "its required request identifiers."
            )
            payment.failed_at = timezone.now()
            payment.provider_request_payload = request_payload

            payment.save(
                update_fields=[
                    "status",
                    "failure_reason",
                    "failed_at",
                    "provider_request_payload",
                    "updated_at",
                ]
            )

            return Response(
                {
                    "detail": payment.failure_reason,
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        try:
            with transaction.atomic():
                attempt = PaymentAttempt.objects.create(
                    payment=payment,
                    status=PaymentAttempt.Status.PROCESSING,
                    merchant_request_id=merchant_request_id,
                    checkout_request_id=checkout_request_id,
                    requested_amount=payment.amount,
                    phone_number=payment.phone_number,
                    provider_response_code=str(
                        provider_response.get(
                            "ResponseCode",
                            "",
                        )
                    ),
                    provider_response_description=(
                        provider_response.get(
                            "ResponseDescription",
                            "",
                        )
                    ),
                    provider_request_payload=request_payload,
                    provider_response_payload=provider_response,
                    initiated_at=timezone.now(),
                )

        except IntegrityError:
            existing_attempt = (
                PaymentAttempt.objects.filter(
                    checkout_request_id=checkout_request_id,
                )
                .first()
            )

            if (
                existing_attempt is None
                or existing_attempt.payment_id != payment.id
            ):
                payment.status = Payment.Status.FAILED
                payment.failure_reason = (
                    "M-Pesa returned a duplicate checkout identifier. "
                    "The payment requires staff review."
                )
                payment.failed_at = timezone.now()
                payment.save(
                    update_fields=[
                        "status",
                        "failure_reason",
                        "failed_at",
                        "updated_at",
                    ]
                )

                return Response(
                    {
                        "detail": payment.failure_reason,
                    },
                    status=status.HTTP_502_BAD_GATEWAY,
                )

            attempt = existing_attempt

        payment.status = Payment.Status.PROCESSING
        payment.initiated_at = timezone.now()
        payment.failure_reason = ""
        payment.failed_at = None
        payment.provider_request_payload = (
            request_payload
        )

        payment.merchant_request_id = merchant_request_id

        payment.checkout_request_id = checkout_request_id

        payment.provider_response_code = str(
            provider_response.get(
                "ResponseCode",
                "",
            )
        )

        payment.provider_response_description = (
            provider_response.get(
                "ResponseDescription",
                "",
            )
        )

        payment.save(
            update_fields=[
                "status",
                "initiated_at",
                "failure_reason",
                "failed_at",
                "provider_request_payload",
                "merchant_request_id",
                "checkout_request_id",
                "provider_response_code",
                "provider_response_description",
                "updated_at",
            ]
        )

        return Response(
            {
                "detail": provider_response.get(
                    "CustomerMessage",
                    (
                        "M-Pesa request sent to "
                        "the customer's phone."
                    ),
                ),
                "payment": self.get_serializer(
                    payment
                ).data,
                "attempt_reference": (
                    attempt.attempt_reference
                ),
            }
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="mock-success",
    )
    @transaction.atomic
    def mock_success(
        self,
        request,
        pk=None,
    ):
        if not settings.ENABLE_DEVELOPMENT_PAYMENT_HANDOFF:
            return Response(
                {
                    "detail": (
                        "Mock payments are disabled "
                        "outside development."
                    )
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        payment = (
            self.get_queryset()
            .select_for_update()
            .select_related("viewing")
            .get(pk=pk)
        )

        viewing = (
            Viewing.objects.select_for_update()
            .get(
                pk=payment.viewing_id
            )
        )

        if (
            payment.status
            == Payment.Status.SUCCESSFUL
        ):
            return Response(
                self.get_serializer(payment).data
            )

        payment.checkout_request_id = (
            payment.checkout_request_id
            or (
                f"MOCK-"
                f"{uuid4().hex[:12].upper()}"
            )
        )

        payment.save(
            update_fields=[
                "checkout_request_id",
                "updated_at",
            ]
        )

        now = timezone.now()
        mock_receipt = f"RCT-{uuid4().hex[:10].upper()}"

        attempt, _ = PaymentAttempt.objects.get_or_create(
            checkout_request_id=payment.checkout_request_id,
            defaults={
                "payment": payment,
                "status": PaymentAttempt.Status.PROCESSING,
                "requested_amount": payment.amount,
                "phone_number": payment.phone_number,
                "provider_request_payload": {
                    "development_simulation": True,
                },
                "initiated_at": now,
            },
        )

        attempt.status = PaymentAttempt.Status.SUCCESSFUL
        attempt.provider_receipt_number = mock_receipt
        attempt.callback_amount = payment.amount
        attempt.phone_number = payment.phone_number
        attempt.provider_response_code = "0"
        attempt.provider_response_description = (
            "Development payment simulation completed successfully."
        )
        attempt.provider_callback_payload = {
            "development_simulation": True,
            "simulated_by_user_id": request.user.pk,
            "simulated_at": now.isoformat(),
        }
        attempt.callback_received_at = now
        attempt.completed_at = now
        attempt.failure_reason = ""
        attempt.save(
            update_fields=[
                "status",
                "provider_receipt_number",
                "callback_amount",
                "phone_number",
                "provider_response_code",
                "provider_response_description",
                "provider_callback_payload",
                "callback_received_at",
                "completed_at",
                "failure_reason",
                "updated_at",
            ]
        )

        _complete_payment(
            payment,
            viewing,
            provider_receipt=mock_receipt,
            transaction_date=now,
            provider_transaction_id=(
                attempt.checkout_request_id
            ),
            actor=request.user,
        )

        payment.refresh_from_db()

        return Response(
            self.get_serializer(payment).data
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="reconcile",
    )
    def reconcile(self, request, pk=None):
        if not request.user.is_staff:
            return Response(
                {
                    "detail": (
                        "Only Pata HAO staff may reconcile "
                        "M-Pesa payments."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        payment = self.get_queryset().get(pk=pk)

        attempt = (
            payment.attempts
            .exclude(checkout_request_id="")
            .order_by("-created_at", "-id")
            .first()
        )

        if attempt is None and payment.checkout_request_id:
            with transaction.atomic():
                locked_payment = (
                    Payment.objects.select_for_update()
                    .get(pk=payment.pk)
                )
                attempt = _legacy_payment_attempt(
                    locked_payment
                )

        if attempt is None:
            return Response(
                {
                    "detail": (
                        "This payment has no M-Pesa checkout "
                        "attempt to reconcile."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            query_request, provider_response = (
                MpesaClient().query_stk_push(
                    checkout_request_id=(
                        attempt.checkout_request_id
                    ),
                )
            )
        except MpesaAPIError as exc:
            return Response(
                {
                    "detail": str(exc),
                    "attempt_reference": (
                        attempt.attempt_reference
                    ),
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        query_audit = {
            "request": query_request,
            "response": provider_response,
        }

        raw_result_code = provider_response.get(
            "ResultCode"
        )

        try:
            result_code = int(str(raw_result_code))
        except (TypeError, ValueError):
            result_code = None

        with transaction.atomic():
            attempt = (
                PaymentAttempt.objects.select_for_update()
                .get(pk=attempt.pk)
            )
            payment = (
                Payment.objects.select_for_update()
                .get(pk=payment.pk)
            )

            attempt.provider_query_payload = query_audit
            attempt.reconciled_at = timezone.now()
            attempt.provider_response_code = str(
                raw_result_code
                if raw_result_code is not None
                else ""
            )
            attempt.provider_response_description = (
                provider_response.get(
                    "ResultDesc",
                    provider_response.get(
                        "ResponseDescription",
                        "",
                    ),
                )
            )

            attempt.save(
                update_fields=[
                    "provider_query_payload",
                    "reconciled_at",
                    "provider_response_code",
                    "provider_response_description",
                    "updated_at",
                ]
            )

            if attempt.status == PaymentAttempt.Status.SUCCESSFUL:
                # Reconciliation is supplemental audit evidence. It must
                # never downgrade a receipt already verified by callback.
                pass

            elif result_code is None:
                _mark_attempt_for_review(
                    attempt,
                    payment,
                    reason=(
                        "M-Pesa reconciliation returned an invalid "
                        "result code."
                    ),
                    query_payload=query_audit,
                )

            elif result_code == 0:
                if payment.status != Payment.Status.SUCCESSFUL:
                    _mark_attempt_for_review(
                        attempt,
                        payment,
                        reason=(
                            "M-Pesa reports a successful request, "
                            "but a verified receipt callback is still "
                            "required before crediting the payment."
                        ),
                        query_payload=query_audit,
                    )

            else:
                now = timezone.now()
                attempt.status = PaymentAttempt.Status.FAILED
                attempt.failure_reason = (
                    attempt.provider_response_description
                    or "M-Pesa reports that the payment failed."
                )
                attempt.failed_at = now
                attempt.save(
                    update_fields=[
                        "status",
                        "failure_reason",
                        "failed_at",
                        "updated_at",
                    ]
                )

                if (
                    payment.status != Payment.Status.SUCCESSFUL
                    and payment.checkout_request_id
                    == attempt.checkout_request_id
                ):
                    payment.status = Payment.Status.FAILED
                    payment.failure_reason = attempt.failure_reason
                    payment.failed_at = now
                    payment.save(
                        update_fields=[
                            "status",
                            "failure_reason",
                            "failed_at",
                            "updated_at",
                        ]
                    )

        payment.refresh_from_db()
        attempt.refresh_from_db()

        return Response(
            {
                "payment": self.get_serializer(payment).data,
                "attempt": {
                    "attempt_reference": (
                        attempt.attempt_reference
                    ),
                    "status": attempt.status,
                    "checkout_request_id": (
                        attempt.checkout_request_id
                    ),
                    "provider_response_code": (
                        attempt.provider_response_code
                    ),
                    "provider_response_description": (
                        attempt.provider_response_description
                    ),
                    "reconciled_at": attempt.reconciled_at,
                },
            }
        )

    @action(
        detail=False,
        methods=["get"],
        url_path=(
            r"viewing/"
            r"(?P<viewing_id>[^/.]+)/"
            r"receipt"
        ),
    )
    def viewing_receipt(
        self,
        request,
        viewing_id=None,
    ):
        payment = (
            self.get_queryset()
            .filter(
                viewing_id=viewing_id,
                status__in={
                    Payment.Status.SUCCESSFUL,
                    Payment.Status.REFUNDED,
                },
            )
            .order_by(
                "-paid_at",
                "-created_at",
            )
            .first()
        )

        if payment is None:
            return Response(
                {
                    "detail": (
                        "A successful payment receipt "
                        "was not found for this viewing."
                    )
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = self.get_serializer(
            payment
        )

        return Response(
            serializer.data
        )


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def mpesa_callback(request):
    if not isinstance(request.data, dict):
        return _callback_response(
            accepted=False,
            description="Invalid callback payload",
        )

    body = request.data.get(
        "Body",
        {},
    )

    if not isinstance(body, dict):
        return _callback_response(
            accepted=False,
            description="Invalid callback body",
        )

    callback = body.get(
        "stkCallback",
        {},
    )

    if not isinstance(callback, dict):
        return _callback_response(
            accepted=False,
            description="Invalid STK callback",
        )

    checkout_request_id = str(
        callback.get(
            "CheckoutRequestID",
            "",
        )
    ).strip()

    if not checkout_request_id:
        return _callback_response(
            accepted=False,
            description="Missing CheckoutRequestID",
        )

    with transaction.atomic():
        try:
            attempt = (
                PaymentAttempt.objects.select_for_update()
                .get(
                    checkout_request_id=checkout_request_id,
                )
            )

        except PaymentAttempt.DoesNotExist:
            try:
                legacy_payment = (
                    Payment.objects.select_for_update()
                    .get(
                        checkout_request_id=(
                            checkout_request_id
                        )
                    )
                )
            except Payment.DoesNotExist:
                return _callback_response()

            attempt = _legacy_payment_attempt(
                legacy_payment
            )

            attempt = (
                PaymentAttempt.objects.select_for_update()
                .get(pk=attempt.pk)
            )

        payment = (
            Payment.objects.select_for_update()
            .select_related("viewing")
            .get(pk=attempt.payment_id)
        )

        if attempt.status == PaymentAttempt.Status.SUCCESSFUL:
            return _callback_response()

        callback_received_at = timezone.now()
        callback_merchant_request_id = str(
            callback.get(
                "MerchantRequestID",
                "",
            )
        ).strip()

        raw_result_code = callback.get(
            "ResultCode"
        )

        try:
            result_code = int(str(raw_result_code))
        except (TypeError, ValueError):
            result_code = None

        result_description = str(
            callback.get(
                "ResultDesc",
                "",
            )
            or ""
        )

        attempt.provider_callback_payload = request.data
        attempt.callback_received_at = callback_received_at
        attempt.provider_response_code = str(
            raw_result_code
            if raw_result_code is not None
            else ""
        )
        attempt.provider_response_description = (
            result_description
        )

        attempt.save(
            update_fields=[
                "provider_callback_payload",
                "callback_received_at",
                "provider_response_code",
                "provider_response_description",
                "updated_at",
            ]
        )

        if result_code is None:
            _mark_attempt_for_review(
                attempt,
                payment,
                reason=(
                    "M-Pesa callback contained an invalid result code."
                ),
                callback_payload=request.data,
            )

            return _callback_response()

        if (
            attempt.merchant_request_id
            and callback_merchant_request_id
            != attempt.merchant_request_id
        ):
            _mark_attempt_for_review(
                attempt,
                payment,
                reason=(
                    "M-Pesa callback merchant request identifier "
                    "did not match the payment attempt."
                ),
                callback_payload=request.data,
            )

            return _callback_response()

        if result_code != 0:
            attempt.status = PaymentAttempt.Status.FAILED
            attempt.failure_reason = (
                result_description
                or "M-Pesa payment failed."
            )
            attempt.failed_at = callback_received_at
            attempt.save(
                update_fields=[
                    "status",
                    "failure_reason",
                    "failed_at",
                    "updated_at",
                ]
            )

            if (
                payment.status != Payment.Status.SUCCESSFUL
                and payment.checkout_request_id
                == attempt.checkout_request_id
            ):
                payment.status = Payment.Status.FAILED
                payment.failure_reason = attempt.failure_reason
                payment.failed_at = callback_received_at
                payment.provider_callback_payload = request.data
                payment.callback_received_at = callback_received_at
                payment.provider_response_code = str(result_code)
                payment.provider_response_description = (
                    result_description
                )
                payment.save(
                    update_fields=[
                        "status",
                        "failure_reason",
                        "failed_at",
                        "provider_callback_payload",
                        "callback_received_at",
                        "provider_response_code",
                        "provider_response_description",
                        "updated_at",
                    ]
                )

            return _callback_response()

        metadata = _callback_metadata(
            callback
        )

        amount = metadata.get(
            "Amount"
        )

        receipt = metadata.get(
            "MpesaReceiptNumber"
        )

        receipt = str(receipt or "").strip().upper()

        phone = re.sub(
            r"[^0-9]",
            "",
            str(
                metadata.get(
                    "PhoneNumber",
                    "",
                )
            ),
        )

        if (
            amount is None
            or not receipt
            or not phone
        ):
            _mark_attempt_for_review(
                attempt,
                payment,
                reason=(
                    "M-Pesa success callback omitted "
                    "amount, receipt, or phone evidence."
                ),
                callback_payload=request.data,
            )

            return _callback_response()

        callback_amount = _parse_callback_amount(amount)

        if (
            callback_amount is None
            or callback_amount != payment.amount
        ):
            _mark_attempt_for_review(
                attempt,
                payment,
                reason=(
                    "M-Pesa amount did not exactly match "
                    "the payment intent."
                ),
                callback_payload=request.data,
            )

            return _callback_response()

        if phone != payment.phone_number:
            _mark_attempt_for_review(
                attempt,
                payment,
                reason=(
                    "M-Pesa phone number did not "
                    "match the payment intent."
                ),
                callback_payload=request.data,
            )

            return _callback_response()

        raw_date = metadata.get(
            "TransactionDate"
        )

        try:
            transaction_date = timezone.make_aware(
                timezone.datetime.strptime(
                    str(raw_date),
                    "%Y%m%d%H%M%S",
                ),
                timezone.get_current_timezone(),
            )
        except (TypeError, ValueError):
            _mark_attempt_for_review(
                attempt,
                payment,
                reason=(
                    "M-Pesa success callback omitted a valid "
                    "transaction timestamp."
                ),
                callback_payload=request.data,
            )

            return _callback_response()

        duplicate_attempt = (
            PaymentAttempt.objects.filter(
                provider_receipt_number__iexact=receipt,
            )
            .exclude(pk=attempt.pk)
            .first()
        )
        duplicate_payment = (
            Payment.objects.filter(
                provider_receipt_number__iexact=receipt,
            )
            .exclude(pk=payment.pk)
            .first()
        )

        if duplicate_attempt or duplicate_payment:
            _mark_attempt_for_review(
                attempt,
                payment,
                reason=(
                    "M-Pesa receipt was already attached to "
                    "a different payment attempt."
                ),
                callback_payload=request.data,
            )

            return _callback_response()

        if payment.status == Payment.Status.SUCCESSFUL:
            if (
                payment.provider_receipt_number.upper()
                == receipt
            ):
                attempt.status = PaymentAttempt.Status.SUCCESSFUL
                attempt.provider_receipt_number = receipt
                attempt.callback_amount = callback_amount
                attempt.phone_number = phone
                attempt.failure_reason = ""
                attempt.completed_at = (
                    payment.paid_at
                    or callback_received_at
                )
                attempt.save(
                    update_fields=[
                        "status",
                        "provider_receipt_number",
                        "callback_amount",
                        "phone_number",
                        "failure_reason",
                        "completed_at",
                        "updated_at",
                    ]
                )

                return _callback_response()

            attempt.provider_receipt_number = receipt
            attempt.callback_amount = callback_amount
            attempt.phone_number = phone
            attempt.save(
                update_fields=[
                    "provider_receipt_number",
                    "callback_amount",
                    "phone_number",
                    "updated_at",
                ]
            )
            _mark_attempt_for_review(
                attempt,
                payment,
                reason=(
                    "A second successful M-Pesa charge was received "
                    "for an already-paid viewing."
                ),
                callback_payload=request.data,
            )

            return _callback_response()

        attempt.status = PaymentAttempt.Status.SUCCESSFUL
        attempt.provider_receipt_number = receipt
        attempt.callback_amount = callback_amount
        attempt.phone_number = phone
        attempt.failure_reason = ""
        attempt.failed_at = None
        attempt.completed_at = transaction_date
        attempt.save(
            update_fields=[
                "status",
                "provider_receipt_number",
                "callback_amount",
                "phone_number",
                "failure_reason",
                "failed_at",
                "completed_at",
                "updated_at",
            ]
        )

        payment.checkout_request_id = attempt.checkout_request_id
        payment.merchant_request_id = attempt.merchant_request_id
        payment.provider_callback_payload = request.data
        payment.callback_received_at = callback_received_at
        payment.provider_response_code = str(result_code)
        payment.provider_response_description = result_description
        payment.save(
            update_fields=[
                "checkout_request_id",
                "merchant_request_id",
                "provider_callback_payload",
                "callback_received_at",
                "provider_response_code",
                "provider_response_description",
                "updated_at",
            ]
        )

        viewing = (
            Viewing.objects.select_for_update()
            .get(
                pk=payment.viewing_id
            )
        )

        _complete_payment(
            payment,
            viewing,
            provider_receipt=receipt,
            transaction_date=transaction_date,
            provider_transaction_id=(
                attempt.checkout_request_id
            ),
            actor=None,
        )

    return _callback_response()
