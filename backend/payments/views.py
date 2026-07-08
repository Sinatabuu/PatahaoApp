from rest_framework import viewsets, permissions
from .models import Deal, Payment
from .serializers import DealSerializer, PaymentSerializer
from core.models import ActivityLog


class DealViewSet(viewsets.ModelViewSet):
    queryset = Deal.objects.all()
    serializer_class = DealSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        if user.is_staff:
            return Deal.objects.all()

        return Deal.objects.filter(customer=user)

    def perform_create(self, serializer):
        deal = serializer.save()

        ActivityLog.objects.create(
            actor=self.request.user,
            action="deal_created",
            entity_type="Deal",
            entity_id=str(deal.id),
            description=f"Deal created for {deal.property.title}",
        )


class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        if user.is_staff:
            return Payment.objects.all()

        return Payment.objects.filter(payer=user)

    def perform_create(self, serializer):
        payment = serializer.save()

        ActivityLog.objects.create(
            actor=self.request.user,
            action="payment_created",
            entity_type="Payment",
            entity_id=str(payment.id),
            description=f"Payment created: {payment.payment_method} {payment.amount}",
        )