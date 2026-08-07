from uuid import uuid4

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response

from viewings.models import Viewing, ViewingEvent
from notifications.models import Notification
from .models import Payment
from .serializers import PaymentSerializer
from .services import MpesaAPIError, MpesaClient


def _callback_metadata(callback):
    result = {}
    items = (
        callback.get("CallbackMetadata", {})
        .get("Item", [])
    )
    for item in items:
        name = item.get("Name")
        if name:
            result[name] = item.get("Value")
    return result


def _complete_payment(payment, viewing, *, provider_receipt, transaction_date, actor=None):
    if payment.status == Payment.Status.SUCCESSFUL:
        return

    now = timezone.now()
    payment.status = Payment.Status.SUCCESSFUL
    payment.provider_transaction_id = payment.checkout_request_id
    payment.provider_receipt_number = str(provider_receipt)
    if not payment.receipt_number:
        payment.receipt_number = Payment.generate_receipt_number()
    payment.failure_reason = ""
    payment.failed_at = None
    payment.paid_at = transaction_date or now
    payment.save(update_fields=[
        "status", "provider_transaction_id", "provider_receipt_number",
        "receipt_number", "failure_reason", "failed_at", "paid_at", "updated_at",
    ])

    if viewing.status != Viewing.Status.PAID_PENDING_PARTNER:
        viewing.status = Viewing.Status.PAID_PENDING_PARTNER
        viewing.payment_reference = payment.payment_reference
        viewing.save(update_fields=["status", "payment_reference", "updated_at"])

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
                "provider_receipt_number": payment.provider_receipt_number,
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
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        queryset = Payment.objects.select_related(
            "payer", "viewing", "viewing__property"
        ).order_by("-created_at")
        if not self.request.user.is_staff:
            queryset = queryset.filter(payer=self.request.user)
        viewing_id = self.request.query_params.get("viewing")
        if viewing_id:
            queryset = queryset.filter(viewing_id=viewing_id)
        return queryset

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        viewing = Viewing.objects.select_for_update().select_related("property").get(
            pk=serializer.validated_data["viewing"].pk
        )
        if viewing.customer_id != request.user.id:
            return Response(
                {"detail": "You cannot pay for another customer's viewing."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if viewing.status != Viewing.Status.PENDING_PAYMENT:
            return Response(
                {"detail": "This viewing is not awaiting payment.", "current_status": viewing.status},
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
            existing = Payment.objects.filter(viewing=viewing).first()
            if existing and existing.payer_id == request.user.id:
                return Response(self.get_serializer(existing).data, status=status.HTTP_200_OK)
            raise

        viewing.status = Viewing.Status.PAYMENT_PROCESSING
        viewing.payment_reference = payment.payment_reference
        viewing.save(update_fields=["status", "payment_reference", "updated_at"])
        return Response(self.get_serializer(payment).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="initiate")
    @transaction.atomic
    def initiate(self, request, pk=None):
        payment = self.get_queryset().select_for_update().get(pk=pk)
        if payment.payment_method != Payment.PaymentMethod.MPESA:
            return Response(
                {"detail": "Only M-Pesa initiation is available in this phase."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if payment.status == Payment.Status.SUCCESSFUL:
            return Response(self.get_serializer(payment).data)
        if payment.status == Payment.Status.PROCESSING and payment.checkout_request_id:
            return Response({
                "detail": "M-Pesa request was already sent.",
                "payment": self.get_serializer(payment).data,
            })
        if payment.status not in {Payment.Status.PENDING, Payment.Status.FAILED}:
            return Response(
                {"detail": "This payment cannot currently be initiated.", "current_status": payment.status},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            request_payload, provider_response = MpesaClient().stk_push(
                phone_number=payment.phone_number,
                amount=payment.amount,
                account_reference=payment.payment_reference,
                description="Viewing fee",
            )
        except MpesaAPIError as exc:
            payment.status = Payment.Status.FAILED
            payment.failure_reason = str(exc)
            payment.failed_at = timezone.now()
            payment.provider_callback_payload = exc.payload
            payment.save(update_fields=[
                "status", "failure_reason", "failed_at",
                "provider_callback_payload", "updated_at",
            ])
            return Response(
                {"detail": str(exc), "provider_error": exc.payload},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        payment.status = Payment.Status.PROCESSING
        payment.initiated_at = timezone.now()
        payment.failure_reason = ""
        payment.failed_at = None
        payment.provider_request_payload = request_payload
        payment.merchant_request_id = provider_response.get("MerchantRequestID", "")
        payment.checkout_request_id = provider_response.get("CheckoutRequestID", "")
        payment.provider_response_code = str(provider_response.get("ResponseCode", ""))
        payment.provider_response_description = provider_response.get(
            "ResponseDescription", ""
        )
        payment.save(update_fields=[
            "status", "initiated_at", "failure_reason", "failed_at",
            "provider_request_payload", "merchant_request_id", "checkout_request_id",
            "provider_response_code", "provider_response_description", "updated_at",
        ])
        return Response({
            "detail": provider_response.get(
                "CustomerMessage", "M-Pesa request sent to the customer's phone."
            ),
            "payment": self.get_serializer(payment).data,
        })

    @action(detail=True, methods=["post"], url_path="mock-success")
    @transaction.atomic
    def mock_success(self, request, pk=None):
        if not settings.DEBUG:
            return Response(
                {"detail": "Mock payments are disabled outside development."},
                status=status.HTTP_404_NOT_FOUND,
            )
        payment = self.get_queryset().select_for_update().select_related("viewing").get(pk=pk)
        viewing = Viewing.objects.select_for_update().get(pk=payment.viewing_id)
        if payment.status == Payment.Status.SUCCESSFUL:
            return Response(self.get_serializer(payment).data)
        payment.checkout_request_id = payment.checkout_request_id or f"MOCK-{uuid4().hex[:12].upper()}"
        payment.save(update_fields=["checkout_request_id", "updated_at"])
        _complete_payment(
            payment,
            viewing,
            provider_receipt=f"RCT-{uuid4().hex[:10].upper()}",
            transaction_date=timezone.now(),
            actor=request.user,
        )
        payment.refresh_from_db()
        return Response(self.get_serializer(payment).data)


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def mpesa_callback(request):
    body = request.data.get("Body", {})
    callback = body.get("stkCallback", {})
    checkout_request_id = callback.get("CheckoutRequestID", "")
    if not checkout_request_id:
        return Response({"ResultCode": 1, "ResultDesc": "Missing CheckoutRequestID"}, status=400)

    with transaction.atomic():
        try:
            payment = Payment.objects.select_for_update().select_related("viewing").get(
                checkout_request_id=checkout_request_id
            )
        except Payment.DoesNotExist:
            return Response({"ResultCode": 0, "ResultDesc": "Accepted"})

        payment.provider_callback_payload = request.data
        payment.callback_received_at = timezone.now()
        payment.merchant_request_id = callback.get(
            "MerchantRequestID", payment.merchant_request_id
        )
        result_code = int(callback.get("ResultCode", 1))
        result_description = callback.get("ResultDesc", "")
        payment.provider_response_code = str(result_code)
        payment.provider_response_description = result_description
        payment.save(update_fields=[
            "provider_callback_payload", "callback_received_at",
            "merchant_request_id", "provider_response_code",
            "provider_response_description", "updated_at",
        ])

        if payment.status == Payment.Status.SUCCESSFUL:
            return Response({"ResultCode": 0, "ResultDesc": "Accepted"})

        if result_code != 0:
            payment.status = Payment.Status.FAILED
            payment.failure_reason = result_description or "M-Pesa payment failed."
            payment.failed_at = timezone.now()
            payment.save(update_fields=[
                "status", "failure_reason", "failed_at", "updated_at",
            ])
            return Response({"ResultCode": 0, "ResultDesc": "Accepted"})

        metadata = _callback_metadata(callback)
        amount = metadata.get("Amount")
        receipt = metadata.get("MpesaReceiptNumber")
        phone = str(metadata.get("PhoneNumber", ""))
        if amount is None or receipt is None:
            payment.status = Payment.Status.FAILED
            payment.failure_reason = "M-Pesa success callback omitted amount or receipt."
            payment.failed_at = timezone.now()
            payment.save(update_fields=["status", "failure_reason", "failed_at", "updated_at"])
            return Response({"ResultCode": 0, "ResultDesc": "Accepted"})

        if str(int(float(amount))) != str(int(payment.amount)):
            payment.status = Payment.Status.FAILED
            payment.failure_reason = "M-Pesa amount did not match the payment intent."
            payment.failed_at = timezone.now()
            payment.save(update_fields=["status", "failure_reason", "failed_at", "updated_at"])
            return Response({"ResultCode": 0, "ResultDesc": "Accepted"})

        if phone and phone != payment.phone_number:
            payment.status = Payment.Status.FAILED
            payment.failure_reason = "M-Pesa phone number did not match the payment intent."
            payment.failed_at = timezone.now()
            payment.save(update_fields=["status", "failure_reason", "failed_at", "updated_at"])
            return Response({"ResultCode": 0, "ResultDesc": "Accepted"})

        transaction_date = None
        raw_date = metadata.get("TransactionDate")
        if raw_date:
            try:
                transaction_date = timezone.make_aware(
                    timezone.datetime.strptime(str(raw_date), "%Y%m%d%H%M%S")
                )
            except (TypeError, ValueError):
                transaction_date = timezone.now()

        viewing = Viewing.objects.select_for_update().get(pk=payment.viewing_id)
        _complete_payment(
            payment,
            viewing,
            provider_receipt=receipt,
            transaction_date=transaction_date,
            actor=None,
        )

    return Response({"ResultCode": 0, "ResultDesc": "Accepted"})
