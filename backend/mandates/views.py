from django.db import transaction

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from .models import MandateEvent, PropertyMandate
from .serializers import (
    PartnerMandateDeclarationSerializer,
    PropertyMandateSerializer,
)


class PropertyMandateViewSet(viewsets.ModelViewSet):
    serializer_class = PropertyMandateSerializer
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    http_method_names = [
        "get",
        "post",
        "patch",
        "head",
        "options",
    ]

    def _get_partner(self):
        partner = getattr(
            self.request.user,
            "partner_profile",
            None,
        )

        if partner is None:
            raise PermissionDenied(
                "A partner account is required."
            )

        if not partner.is_active:
            raise PermissionDenied(
                "This partner account is not active."
            )

        return partner

    def get_queryset(self):
        queryset = (
            PropertyMandate.objects
            .select_related(
                "property",
                "owner",
                "partner",
                "partner__user",
                "commission_agreement",
                "commission_agreement__accepted_by",
                "commission_agreement__verified_by",
                "declared_by",
                "approved_by",
            )
            .order_by("-created_at")
        )

        if self.request.user.is_staff:
            return queryset

        partner = self._get_partner()

        return queryset.filter(
            partner=partner,
        )

    @transaction.atomic
    def perform_create(self, serializer):
        partner = self._get_partner()

        property_obj = serializer.validated_data[
            "property"
        ]

        if property_obj.partner_id != partner.id:
            raise PermissionDenied(
                "You can create a mandate only for "
                "your own property."
            )

        agreement = serializer.validated_data.get(
            "commission_agreement",
        )

        if agreement is None:
            raise PermissionDenied(
                "A commission agreement is required "
                "before creating the mandate."
            )

        if agreement.property_id != property_obj.id:
            raise PermissionDenied(
                "The commission agreement must belong "
                "to this property."
            )

        if not agreement.partner_accepted:
            raise PermissionDenied(
                "Accept the commission agreement before "
                "creating the digital mandate."
            )

        existing = (
            PropertyMandate.objects
            .filter(property=property_obj)
            .order_by("-version")
            .first()
        )

        if (
            existing is not None
            and existing.status
            not in {
                PropertyMandate.Status.REJECTED,
                PropertyMandate.Status.EXPIRED,
                PropertyMandate.Status.CANCELLED,
            }
        ):
            raise PermissionDenied(
                "This property already has an active "
                "digital mandate."
            )

        next_version = (
            1
            if existing is None
            else existing.version + 1
        )

        serializer.save(
            partner=partner,
            created_by=self.request.user,
            version=next_version,
            status=PropertyMandate.Status.DRAFT,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="declare",
    )
    @transaction.atomic
    def declare(self, request, pk=None):
        mandate = (
            self.get_queryset()
            .select_for_update()
            .get(pk=pk)
        )

        serializer = (
            PartnerMandateDeclarationSerializer(
                data=request.data,
            )
        )

        serializer.is_valid(
            raise_exception=True,
        )

        mandate.authorization_method = (
            serializer.validated_data[
                "authorization_method"
            ]
        )

        mandate.authorization_notes = (
            serializer.validated_data.get(
                "authorization_notes",
                "",
            )
        )

        mandate.owner_authority_confirmed = (
            serializer.validated_data[
                "owner_authority_confirmed"
            ]
        )

        mandate.no_cash_acknowledged = (
            serializer.validated_data[
                "no_cash_acknowledged"
            ]
        )

        mandate.anti_circumvention_acknowledged = (
            serializer.validated_data[
                "anti_circumvention_acknowledged"
            ]
        )

        mandate.declare_by_partner(
            user=request.user,
        )
        mandate.save()

        MandateEvent.objects.create(
            mandate=mandate,
            action="partner_declared",
            actor=request.user,
            notes=(
                "Partner accepted the digital "
                "property mandate."
            ),
            metadata={
                "declaration_version": (
                    mandate.declaration_version
                ),
                "authorization_method": (
                    mandate.authorization_method
                ),
                "commission_agreement_id": (
                    mandate.commission_agreement_id
                ),
            },
        )

        return Response(
            self.get_serializer(mandate).data,
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="submit-for-review",
    )
    @transaction.atomic
    def submit_for_review(
        self,
        request,
        pk=None,
    ):
        mandate = (
            self.get_queryset()
            .select_for_update()
            .get(pk=pk)
        )

        mandate.submit_for_review()
        mandate.save()

        MandateEvent.objects.create(
            mandate=mandate,
            action="submitted_for_review",
            actor=request.user,
            notes=(
                "Digital property mandate submitted "
                "for Pata Hao review."
            ),
            metadata={
                "declaration_version": (
                    mandate.declaration_version
                ),
                "commission_agreement_id": (
                    mandate.commission_agreement_id
                ),
            },
        )

        return Response(
            self.get_serializer(mandate).data,
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="approve",
    )
    @transaction.atomic
    def approve_mandate(
        self,
        request,
        pk=None,
    ):
        if not request.user.is_staff:
            raise PermissionDenied(
                "Only Pata Hao administrators "
                "may approve mandates."
            )

        mandate = (
            PropertyMandate.objects
            .select_for_update()
            .select_related(
                "property",
                "owner",
                "partner",
                "partner__user",
                "commission_agreement",
                "commission_agreement__accepted_by",
                "commission_agreement__verified_by",
                "declared_by",
                "approved_by",
            )
            .get(pk=pk)
        )

        if (
            mandate.status
            == PropertyMandate.Status.APPROVED
        ):
            return Response(
                self.get_serializer(mandate).data,
                status=status.HTTP_200_OK,
            )

        mandate.approve(
            approved_by=request.user,
        )
        mandate.save()

        MandateEvent.objects.create(
            mandate=mandate,
            action="approved",
            actor=request.user,
            notes=(
                "Digital property mandate "
                "approved by Pata Hao."
            ),
            metadata={
                "declaration_version": (
                    mandate.declaration_version
                ),
                "commission_agreement_id": (
                    mandate.commission_agreement_id
                ),
            },
        )

        return Response(
            self.get_serializer(mandate).data,
            status=status.HTTP_200_OK,
        )
