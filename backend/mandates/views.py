from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework import parsers, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import (
    PermissionDenied,
    ValidationError as APIValidationError,
)
from rest_framework.response import Response

from commissions.models import CommissionAgreement

from .models import (
    MandateDocument,
    MandateEvent,
    PropertyMandate,
    PropertyOwner,
)
from .serializers import (
    MandateDocumentReplacementSerializer,
    MandateDocumentUploadSerializer,
    PartnerMandateDeclarationSerializer,
    PropertyMandateSerializer,
)
from .services import (
    get_sale_mandate_pack_status,
    replace_rejected_mandate_document,
    upload_mandate_document,
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

        requested_status = (
            self.request.query_params.get("status", "")
            or ""
        ).strip()

        if requested_status:
            valid_statuses = {
                value
                for value, _label
                in PropertyMandate.Status.choices
            }

            if requested_status not in valid_statuses:
                raise APIValidationError(
                    {
                        "status": (
                            "Unknown mandate review status."
                        ),
                    }
                )

            queryset = queryset.filter(
                status=requested_status,
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


    @action(
        detail=True,
        methods=["post"],
        url_path="complete-review",
    )
    @transaction.atomic
    def complete_review(
        self,
        request,
        pk=None,
    ):
        """
        Complete one staff authorization decision atomically.

        The staff member explicitly approves the owner, commission terms,
        current sale evidence, and mandate from one review screen. Domain
        model checks remain authoritative and every approved evidence hash
        is recorded in the immutable mandate event trail.
        """

        if not request.user.is_staff:
            raise PermissionDenied(
                "Only Pata Hao administrators may complete "
                "authorization reviews."
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

        if mandate.status == PropertyMandate.Status.APPROVED:
            return Response(
                {
                    "detail": "Authorization is already approved.",
                    "mandate": self.get_serializer(mandate).data,
                    "sale_pack": get_sale_mandate_pack_status(
                        mandate,
                    ),
                },
                status=status.HTTP_200_OK,
            )

        if mandate.status != PropertyMandate.Status.UNDER_REVIEW:
            raise APIValidationError(
                {
                    "detail": (
                        "Only an authorization submitted for review "
                        "can be approved."
                    ),
                }
            )

        agreement = mandate.commission_agreement

        if agreement is None:
            raise APIValidationError(
                {
                    "detail": (
                        "A commission agreement is required before "
                        "authorization approval."
                    ),
                }
            )

        agreement = (
            CommissionAgreement.objects
            .select_for_update()
            .get(pk=agreement.pk)
        )

        owner = (
            PropertyOwner.objects
            .select_for_update()
            .get(pk=mandate.owner_id)
        )

        if not owner.is_active:
            raise APIValidationError(
                {
                    "detail": (
                        "The property owner record is inactive and "
                        "cannot be approved."
                    ),
                }
            )

        if owner.verification_status in {
            PropertyOwner.VerificationStatus.REJECTED,
            PropertyOwner.VerificationStatus.SUSPENDED,
        }:
            raise APIValidationError(
                {
                    "detail": (
                        "The property owner record must be resolved "
                        "before this authorization can be approved."
                    ),
                }
            )

        current_documents = list(
            MandateDocument.objects
            .select_for_update()
            .filter(
                mandate=mandate,
                is_current=True,
            )
            .order_by("document_type", "id")
        )

        required_document_types = set()

        if (
            mandate.property.listing_type
            == mandate.property.LISTING_SALE
        ):
            required_document_types = {
                MandateDocument.DocumentType.OWNER_ID,
                MandateDocument.DocumentType.OWNERSHIP_PROOF,
                MandateDocument.DocumentType.SIGNED_MANDATE,
            }

            documents_by_type = {
                document.document_type: document
                for document in current_documents
            }

            missing_types = (
                required_document_types
                - set(documents_by_type)
            )

            if missing_types:
                missing_labels = [
                    str(
                        MandateDocument.DocumentType(
                            document_type,
                        ).label
                    )
                    for document_type in sorted(missing_types)
                ]

                raise APIValidationError(
                    {
                        "detail": (
                            "The Sale Mandate Pack is incomplete: "
                            + ", ".join(missing_labels)
                            + "."
                        ),
                    }
                )

        review_documents = [
            document
            for document in current_documents
            if (
                not required_document_types
                or document.document_type
                in required_document_types
            )
        ]

        rejected_documents = [
            document.get_document_type_display()
            for document in review_documents
            if document.status == MandateDocument.Status.REJECTED
        ]

        if rejected_documents:
            raise APIValidationError(
                {
                    "detail": (
                        "Rejected evidence must be replaced before "
                        "approval: "
                        + ", ".join(rejected_documents)
                        + "."
                    ),
                }
            )

        try:
            if not agreement.is_verified:
                agreement.verify(
                    verified_by=request.user,
                )
                agreement.save()

            if not agreement.is_locked:
                agreement.lock()
                agreement.save()

            if not owner.is_verified:
                owner.verification_status = (
                    PropertyOwner.VerificationStatus.VERIFIED
                )
                owner.verified_by = request.user
                owner.verified_at = timezone.now()
                owner.verification_notes = (
                    "Verified through the Pata Hao authorization "
                    "review queue."
                )
                owner.save()

            for document in review_documents:
                if document.status != MandateDocument.Status.APPROVED:
                    document.approve(
                        reviewed_by=request.user,
                    )

            mandate.commission_agreement = agreement
            mandate.owner = owner
            mandate.approve(
                approved_by=request.user,
            )
            mandate.save()

        except DjangoValidationError as error:
            raise APIValidationError(
                {
                    "detail": error.messages,
                }
            ) from error

        MandateEvent.objects.create(
            mandate=mandate,
            action="authorization_review_completed",
            actor=request.user,
            notes=(
                "Pata Hao completed the authorization review and "
                "approved the owner, commercial terms, evidence, "
                "and digital mandate."
            ),
            metadata={
                "owner_id": owner.id,
                "commission_agreement_id": agreement.id,
                "approved_documents": [
                    {
                        "id": document.id,
                        "document_type": document.document_type,
                        "file_hash": document.file_hash,
                    }
                    for document in review_documents
                ],
            },
        )

        mandate.refresh_from_db()

        return Response(
            {
                "detail": "Authorization approved.",
                "mandate": self.get_serializer(mandate).data,
                "sale_pack": get_sale_mandate_pack_status(
                    mandate,
                ),
            },
            status=status.HTTP_200_OK,
        )


    @action(
        detail=True,
        methods=["get"],
        url_path="sale-pack",
    )
    def sale_pack(
        self,
        request,
        pk=None,
    ):
        mandate = self.get_object()

        return Response(
            get_sale_mandate_pack_status(mandate),
            status=status.HTTP_200_OK,
        )


    @action(
        detail=True,
        methods=["post"],
        url_path="documents",
        parser_classes=[
            parsers.MultiPartParser,
            parsers.FormParser,
        ],
    )
    def upload_document(
        self,
        request,
        pk=None,
    ):
        mandate = self.get_object()

        serializer = MandateDocumentUploadSerializer(
            data=request.data,
        )
        serializer.is_valid(
            raise_exception=True,
        )

        try:
            document = upload_mandate_document(
                mandate_id=mandate.id,
                actor=request.user,
                document_type=(
                    serializer.validated_data[
                        "document_type"
                    ]
                ),
                file=serializer.validated_data["file"],
            )

        except DjangoValidationError as error:
            raise APIValidationError(
                {
                    "detail": error.messages,
                }
            ) from error

        return Response(
            get_sale_mandate_pack_status(
                document.mandate,
            ),
            status=status.HTTP_201_CREATED,
        )


    @action(
        detail=True,
        methods=["post"],
        url_path=(
            r"documents/"
            r"(?P<document_id>[^/.]+)/"
            r"replace"
        ),
        parser_classes=[
            parsers.MultiPartParser,
            parsers.FormParser,
        ],
    )
    def replace_rejected_document(
        self,
        request,
        pk=None,
        document_id=None,
    ):
        mandate = self.get_object()

        get_object_or_404(
            MandateDocument.objects.only(
                "id",
            ),
            pk=document_id,
            mandate_id=mandate.id,
        )

        serializer = (
            MandateDocumentReplacementSerializer(
                data=request.data,
            )
        )
        serializer.is_valid(
            raise_exception=True,
        )

        try:
            replacement = (
                replace_rejected_mandate_document(
                    mandate_id=mandate.id,
                    document_id=document_id,
                    actor=request.user,
                    file=serializer.validated_data[
                        "file"
                    ],
                )
            )

        except DjangoValidationError as error:
            raise APIValidationError(
                {
                    "detail": error.messages,
                }
            ) from error

        return Response(
            get_sale_mandate_pack_status(
                replacement.mandate,
            ),
            status=status.HTTP_201_CREATED,
        )
