from decimal import Decimal
from unittest.mock import patch

from django.contrib import admin
from django.contrib.messages.storage.fallback import FallbackStorage
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models.deletion import ProtectedError
from django.test import RequestFactory, TestCase
from django.utils import timezone

from rest_framework.test import APIClient

from accounts.models import User
from commissions.models import CommissionAgreement
from mandates.admin import MandateDocumentAdmin
from mandates.models import (
    MandateDocument,
    MandateEvent,
    PropertyMandate,
    PropertyOwner,
)
from mandates.services import (
    evaluate_property_publication,
    reject_mandate_document,
    supersede_mandate_document,
)

from partners.models import Partner
from properties.models import Property


class SaleMandatePublicationTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="sale_admin",
            email="sale-admin@example.com",
            password="test-pass-123",
            role=User.ROLE_ADMIN,
            is_staff=True,
        )

        self.partner_user = User.objects.create_user(
            username="sale_partner",
            email="sale-partner@example.com",
            password="test-pass-123",
            role=User.ROLE_PARTNER,
        )

        self.partner = Partner.objects.create(
            user=self.partner_user,
            business_name="Sale Test Partner",
            verification_status=Partner.STATUS_APPROVED,
            verified_by=self.admin,
            verified_at=timezone.now(),
        )

    def _create_property(self, *, listing_type):
        return Property.objects.create(
            partner=self.partner,
            title=(
                "Sale Test Property"
                if listing_type == Property.LISTING_SALE
                else "Rental Test Property"
            ),
            property_type=Property.TYPE_HOUSE,
            listing_type=listing_type,
            price=Decimal("10000000.00"),
            county="Nairobi",
            town="Nairobi",
            description="Mandate publication governance test property.",
            status=Property.STATUS_DRAFT,
        )

    def _create_owner(self, *, verified=True):
        owner = PropertyOwner.objects.create(
            owner_type=PropertyOwner.OwnerType.INDIVIDUAL,
            legal_name="Test Property Owner",
            phone_number="0700000001",
            verification_status=(
                PropertyOwner.VerificationStatus.VERIFIED
                if verified
                else PropertyOwner.VerificationStatus.PENDING
            ),
            verified_by=self.admin if verified else None,
            verified_at=timezone.now() if verified else None,
            created_by=self.admin,
        )

        return owner

    def _create_locked_commission_agreement(self, property_obj):
        if property_obj.listing_type == Property.LISTING_SALE:
            commission_basis = (
                CommissionAgreement.CommissionBasis.SALE_PRICE
            )
        else:
            commission_basis = (
                CommissionAgreement.CommissionBasis.FIRST_MONTH_RENT
            )

        agreement = CommissionAgreement.objects.create(
            property=property_obj,
            owner_name="Test Property Owner",
            owner_phone_number="0700000001",
            commission_method=(
                CommissionAgreement.CommissionMethod.PERCENTAGE
            ),
            commission_basis=commission_basis,
            commission_rate=Decimal("3.000"),
            transaction_value=property_obj.price,
            created_by=self.admin,
        )

        agreement.accept_by_partner(
            user=self.partner_user,
        )
        agreement.save()

        agreement.verify(
            self.admin,
        )
        agreement.save()

        agreement.lock()
        agreement.save()

        agreement.refresh_from_db()

        self.assertTrue(
            agreement.is_publish_ready(),
        )

        return agreement

    def _create_approved_mandate(
        self,
        *,
        property_obj,
        owner,
    ):
        agreement = self._create_locked_commission_agreement(
            property_obj,
        )

        mandate = PropertyMandate.objects.create(
            property=property_obj,
            owner=owner,
            partner=self.partner,
            commission_agreement=agreement,
            authorization_method=(
                PropertyMandate.AuthorizationMethod.WRITTEN
            ),
            owner_authority_confirmed=True,
            no_cash_acknowledged=True,
            anti_circumvention_acknowledged=True,
            created_by=self.admin,
        )

        mandate.declare_by_partner(
            user=self.partner_user,
        )
        mandate.save()

        mandate.submit_for_review()
        mandate.save()

        mandate.approve(
            approved_by=self.admin,
        )
        mandate.save()

        mandate.refresh_from_db()

        self.assertEqual(
            mandate.status,
            PropertyMandate.Status.APPROVED,
        )

        return mandate

    def _add_document(
        self,
        *,
        mandate,
        document_type,
        approved=True,
        is_current=True,
        filename=None,
    ):
        filename = filename or f"{document_type}.pdf"

        return MandateDocument.objects.create(
            mandate=mandate,
            document_type=document_type,
            file=SimpleUploadedFile(
                filename,
                b"test mandate evidence",
                content_type="application/pdf",
            ),
            status=(
                MandateDocument.Status.APPROVED
                if approved
                else MandateDocument.Status.UPLOADED
            ),
            is_current=is_current,
            uploaded_by=self.partner_user,
            reviewed_by=self.admin if approved else None,
            reviewed_at=timezone.now() if approved else None,
        )

    def _add_complete_sale_evidence(self, mandate):
        self._add_document(
            mandate=mandate,
            document_type=MandateDocument.DocumentType.OWNER_ID,
        )

        self._add_document(
            mandate=mandate,
            document_type=(
                MandateDocument.DocumentType.OWNERSHIP_PROOF
            ),
        )

        self._add_document(
            mandate=mandate,
            document_type=(
                MandateDocument.DocumentType.SIGNED_MANDATE
            ),
        )

    def test_rental_path_remains_publishable_without_sale_evidence(self):
        property_obj = self._create_property(
            listing_type=Property.LISTING_RENT,
        )

        owner = self._create_owner(
            verified=False,
        )

        self._create_approved_mandate(
            property_obj=property_obj,
            owner=owner,
        )

        readiness = evaluate_property_publication(
            property_obj,
        )

        self.assertTrue(
            readiness.allowed,
            readiness.reasons,
        )

    def test_sale_requires_verified_owner(self):
        property_obj = self._create_property(
            listing_type=Property.LISTING_SALE,
        )

        owner = self._create_owner(
            verified=False,
        )

        mandate = self._create_approved_mandate(
            property_obj=property_obj,
            owner=owner,
        )

        self._add_complete_sale_evidence(
            mandate,
        )

        readiness = evaluate_property_publication(
            property_obj,
        )

        self.assertFalse(
            readiness.allowed,
        )

        self.assertIn(
            "The property owner must be verified before a sale property "
            "can be published.",
            readiness.reasons,
        )

    def test_sale_requires_owner_identification(self):
        property_obj = self._create_property(
            listing_type=Property.LISTING_SALE,
        )

        mandate = self._create_approved_mandate(
            property_obj=property_obj,
            owner=self._create_owner(),
        )

        self._add_document(
            mandate=mandate,
            document_type=(
                MandateDocument.DocumentType.OWNERSHIP_PROOF
            ),
        )

        self._add_document(
            mandate=mandate,
            document_type=(
                MandateDocument.DocumentType.SIGNED_MANDATE
            ),
        )

        readiness = evaluate_property_publication(
            property_obj,
        )

        self.assertFalse(
            readiness.allowed,
        )

        self.assertIn(
            "Approved owner identification is required for a sale property.",
            readiness.reasons,
        )

    def test_sale_requires_ownership_proof(self):
        property_obj = self._create_property(
            listing_type=Property.LISTING_SALE,
        )

        mandate = self._create_approved_mandate(
            property_obj=property_obj,
            owner=self._create_owner(),
        )

        self._add_document(
            mandate=mandate,
            document_type=MandateDocument.DocumentType.OWNER_ID,
        )

        self._add_document(
            mandate=mandate,
            document_type=(
                MandateDocument.DocumentType.SIGNED_MANDATE
            ),
        )

        readiness = evaluate_property_publication(
            property_obj,
        )

        self.assertFalse(
            readiness.allowed,
        )

        self.assertIn(
            "Approved ownership proof is required for a sale property.",
            readiness.reasons,
        )

    def test_sale_requires_signed_mandate(self):
        property_obj = self._create_property(
            listing_type=Property.LISTING_SALE,
        )

        mandate = self._create_approved_mandate(
            property_obj=property_obj,
            owner=self._create_owner(),
        )

        self._add_document(
            mandate=mandate,
            document_type=MandateDocument.DocumentType.OWNER_ID,
        )

        self._add_document(
            mandate=mandate,
            document_type=(
                MandateDocument.DocumentType.OWNERSHIP_PROOF
            ),
        )

        readiness = evaluate_property_publication(
            property_obj,
        )

        self.assertFalse(
            readiness.allowed,
        )

        self.assertIn(
            "An approved signed sale mandate is required for a sale property.",
            readiness.reasons,
        )

    def test_uploaded_but_unapproved_document_does_not_count(self):
        property_obj = self._create_property(
            listing_type=Property.LISTING_SALE,
        )

        mandate = self._create_approved_mandate(
            property_obj=property_obj,
            owner=self._create_owner(),
        )

        self._add_document(
            mandate=mandate,
            document_type=MandateDocument.DocumentType.OWNER_ID,
        )

        self._add_document(
            mandate=mandate,
            document_type=(
                MandateDocument.DocumentType.OWNERSHIP_PROOF
            ),
        )

        self._add_document(
            mandate=mandate,
            document_type=(
                MandateDocument.DocumentType.SIGNED_MANDATE
            ),
            approved=False,
        )

        readiness = evaluate_property_publication(
            property_obj,
        )

        self.assertFalse(
            readiness.allowed,
        )

        self.assertIn(
            "An approved signed sale mandate is required for a sale property.",
            readiness.reasons,
        )

    def test_approved_but_non_current_document_does_not_count(self):
        property_obj = self._create_property(
            listing_type=Property.LISTING_SALE,
        )

        mandate = self._create_approved_mandate(
            property_obj=property_obj,
            owner=self._create_owner(),
        )

        self._add_document(
            mandate=mandate,
            document_type=MandateDocument.DocumentType.OWNER_ID,
        )

        self._add_document(
            mandate=mandate,
            document_type=(
                MandateDocument.DocumentType.OWNERSHIP_PROOF
            ),
        )

        self._add_document(
            mandate=mandate,
            document_type=(
                MandateDocument.DocumentType.SIGNED_MANDATE
            ),
            is_current=False,
        )

        readiness = evaluate_property_publication(
            property_obj,
        )

        self.assertFalse(
            readiness.allowed,
        )

        self.assertIn(
            "An approved signed sale mandate is required for a sale property.",
            readiness.reasons,
        )

    def test_complete_sale_evidence_pack_allows_publication(self):
        property_obj = self._create_property(
            listing_type=Property.LISTING_SALE,
        )

        mandate = self._create_approved_mandate(
            property_obj=property_obj,
            owner=self._create_owner(),
        )

        self._add_complete_sale_evidence(
            mandate,
        )

        readiness = evaluate_property_publication(
            property_obj,
        )

        self.assertTrue(
            readiness.allowed,
            readiness.reasons,
        )
    def test_existing_document_file_cannot_be_replaced(self):
        property_obj = self._create_property(
            listing_type=Property.LISTING_SALE,
        )

        mandate = self._create_approved_mandate(
            property_obj=property_obj,
            owner=self._create_owner(),
        )

        document = self._add_document(
            mandate=mandate,
            document_type=MandateDocument.DocumentType.OWNER_ID,
        )

        document.file = SimpleUploadedFile(
            "replacement.pdf",
            b"replacement evidence",
            content_type="application/pdf",
        )

        with self.assertRaises(ValidationError):
            document.save()

    def test_existing_document_type_cannot_be_changed(self):
        property_obj = self._create_property(
            listing_type=Property.LISTING_SALE,
        )

        mandate = self._create_approved_mandate(
            property_obj=property_obj,
            owner=self._create_owner(),
        )

        document = self._add_document(
            mandate=mandate,
            document_type=MandateDocument.DocumentType.OWNER_ID,
        )

        document.document_type = (
            MandateDocument.DocumentType.OWNERSHIP_PROOF
        )

        with self.assertRaises(ValidationError):
            document.save()

    def test_existing_document_cannot_be_moved_to_another_mandate(self):
        first_property = self._create_property(
            listing_type=Property.LISTING_SALE,
        )

        first_mandate = self._create_approved_mandate(
            property_obj=first_property,
            owner=self._create_owner(),
        )

        second_property = Property.objects.create(
            partner=self.partner,
            title="Second Sale Test Property",
            property_type=Property.TYPE_HOUSE,
            listing_type=Property.LISTING_SALE,
            price=Decimal("12000000.00"),
            county="Nairobi",
            town="Nairobi",
            description="Second mandate test property.",
            status=Property.STATUS_DRAFT,
        )

        second_mandate = self._create_approved_mandate(
            property_obj=second_property,
            owner=self._create_owner(),
        )

        document = self._add_document(
            mandate=first_mandate,
            document_type=MandateDocument.DocumentType.OWNER_ID,
        )

        document.mandate = second_mandate

        with self.assertRaises(ValidationError):
            document.save()

    def test_existing_document_uploader_cannot_be_changed(self):
        property_obj = self._create_property(
            listing_type=Property.LISTING_SALE,
        )

        mandate = self._create_approved_mandate(
            property_obj=property_obj,
            owner=self._create_owner(),
        )

        document = self._add_document(
            mandate=mandate,
            document_type=MandateDocument.DocumentType.OWNER_ID,
        )

        document.uploaded_by = self.admin

        with self.assertRaises(ValidationError):
            document.save()

    def test_document_approval_remains_allowed(self):
        property_obj = self._create_property(
            listing_type=Property.LISTING_SALE,
        )

        mandate = self._create_approved_mandate(
            property_obj=property_obj,
            owner=self._create_owner(),
        )

        document = self._add_document(
            mandate=mandate,
            document_type=MandateDocument.DocumentType.OWNER_ID,
            approved=False,
        )

        document.approve(
            reviewed_by=self.admin,
        )

        document.refresh_from_db()

        self.assertEqual(
            document.status,
            MandateDocument.Status.APPROVED,
        )
        self.assertEqual(
            document.reviewed_by,
            self.admin,
        )
        self.assertIsNotNone(
            document.reviewed_at,
        )

    def test_non_current_document_cannot_be_approved_by_model_or_admin(self):
        property_obj = self._create_property(
            listing_type=Property.LISTING_SALE,
        )

        mandate = self._create_approved_mandate(
            property_obj=property_obj,
            owner=self._create_owner(),
        )

        old_document = self._add_document(
            mandate=mandate,
            document_type=MandateDocument.DocumentType.OWNER_ID,
            approved=False,
        )

        supersede_mandate_document(
            document_id=old_document.id,
            actor=self.admin,
            file=SimpleUploadedFile(
                "replacement-owner-id.pdf",
                b"replacement owner identification evidence",
                content_type="application/pdf",
            ),
        )

        old_document.refresh_from_db()

        with self.assertRaisesMessage(
            ValidationError,
            "Only the current version of a mandate document can be approved.",
        ):
            old_document.approve(
                reviewed_by=self.admin,
            )

        request = RequestFactory().post(
            "/admin/mandates/mandatedocument/",
        )
        request.user = self.admin
        request.session = {}
        request._messages = FallbackStorage(request)

        document_admin = MandateDocumentAdmin(
            MandateDocument,
            admin.site,
        )
        document_admin.approve_selected_documents(
            request,
            MandateDocument.objects.filter(pk=old_document.pk),
        )

        old_document.refresh_from_db()

        self.assertFalse(
            old_document.is_current,
        )
        self.assertEqual(
            old_document.status,
            MandateDocument.Status.UPLOADED,
        )
        self.assertIsNone(
            old_document.reviewed_by,
        )
        self.assertIsNone(
            old_document.reviewed_at,
        )

        approval_events = MandateEvent.objects.filter(
            mandate=mandate,
            action="document_approved",
        )

        self.assertFalse(
            any(
                event.metadata.get("document_id") == old_document.id
                for event in approval_events
            ),
        )

    def test_rejected_current_document_blocks_sale_publication(self):
        property_obj = self._create_property(
            listing_type=Property.LISTING_SALE,
        )

        mandate = self._create_approved_mandate(
            property_obj=property_obj,
            owner=self._create_owner(),
        )

        self._add_complete_sale_evidence(
            mandate,
        )

        readiness_before_rejection = evaluate_property_publication(
            property_obj,
        )

        self.assertTrue(
            readiness_before_rejection.allowed,
            readiness_before_rejection.reasons,
        )

        owner_id_document = mandate.documents.get(
            document_type=MandateDocument.DocumentType.OWNER_ID,
            is_current=True,
        )

        reject_mandate_document(
            document_id=owner_id_document.id,
            actor=self.admin,
            reason="Owner identification is unreadable.",
        )

        readiness_after_rejection = evaluate_property_publication(
            property_obj,
        )

        self.assertFalse(
            readiness_after_rejection.allowed,
        )
        self.assertIn(
            "Approved owner identification is required for a sale property.",
            readiness_after_rejection.reasons,
        )

    def test_admin_rejection_view_renders_and_rejects_document(self):
        property_obj = self._create_property(
            listing_type=Property.LISTING_SALE,
        )

        mandate = self._create_approved_mandate(
            property_obj=property_obj,
            owner=self._create_owner(),
        )

        document = self._add_document(
            mandate=mandate,
            document_type=MandateDocument.DocumentType.OWNER_ID,
            approved=False,
        )

        self.admin.is_superuser = True
        self.admin.save(
            update_fields=[
                "is_superuser",
            ]
        )

        document_admin = MandateDocumentAdmin(
            MandateDocument,
            admin.site,
        )

        get_request = RequestFactory().get(
            f"/admin/mandates/mandatedocument/{document.pk}/reject/",
        )
        get_request.user = self.admin
        get_request.session = {}
        get_request._messages = FallbackStorage(get_request)

        get_response = document_admin.reject_document_view(
            get_request,
            str(document.pk),
        )
        get_response.render()

        self.assertEqual(
            get_response.status_code,
            200,
        )
        self.assertContains(
            get_response,
            "Reject mandate evidence",
        )
        self.assertContains(
            get_response,
            document.original_filename,
        )
        self.assertIn(
            "rejection_reason",
            document_admin.get_readonly_fields(
                get_request,
                document,
            ),
        )

        post_request = RequestFactory().post(
            f"/admin/mandates/mandatedocument/{document.pk}/reject/",
            data={
                "reason": "Uploaded identification is unreadable.",
            },
        )
        post_request.user = self.admin
        post_request.session = {}
        post_request._messages = FallbackStorage(post_request)

        post_response = document_admin.reject_document_view(
            post_request,
            str(document.pk),
        )

        self.assertEqual(
            post_response.status_code,
            302,
        )

        document.refresh_from_db()

        self.assertEqual(
            document.status,
            MandateDocument.Status.REJECTED,
        )
        self.assertEqual(
            document.rejection_reason,
            "Uploaded identification is unreadable.",
        )
        self.assertTrue(
            mandate.events.filter(
                action="document_rejected",
                actor=self.admin,
            ).exists(),
        )

    def test_document_rejection_guards_invalid_attempts(self):
        property_obj = self._create_property(
            listing_type=Property.LISTING_SALE,
        )

        mandate = self._create_approved_mandate(
            property_obj=property_obj,
            owner=self._create_owner(),
        )

        old_document = self._add_document(
            mandate=mandate,
            document_type=MandateDocument.DocumentType.OWNER_ID,
            approved=False,
        )

        with self.assertRaisesMessage(
            ValidationError,
            "A document rejection reason is required.",
        ):
            reject_mandate_document(
                document_id=old_document.id,
                actor=self.admin,
                reason="   ",
            )

        with self.assertRaisesMessage(
            ValidationError,
            "Only a Pata Hao administrator may reject mandate evidence.",
        ):
            reject_mandate_document(
                document_id=old_document.id,
                actor=self.partner_user,
                reason="Unauthorized rejection attempt.",
            )

        new_document = supersede_mandate_document(
            document_id=old_document.id,
            actor=self.admin,
            file=SimpleUploadedFile(
                "replacement-owner-id.pdf",
                b"replacement owner identification evidence",
                content_type="application/pdf",
            ),
        )

        old_document.refresh_from_db()

        with self.assertRaisesMessage(
            ValidationError,
            "Only the current version of a mandate document can be rejected.",
        ):
            reject_mandate_document(
                document_id=old_document.id,
                actor=self.admin,
                reason="Historical evidence rejection attempt.",
            )

        reject_mandate_document(
            document_id=new_document.id,
            actor=self.admin,
            reason="Replacement evidence is unreadable.",
        )

        with self.assertRaisesMessage(
            ValidationError,
            "This mandate document has already been rejected.",
        ):
            reject_mandate_document(
                document_id=new_document.id,
                actor=self.admin,
                reason="Duplicate rejection attempt.",
            )

        old_document.refresh_from_db()
        new_document.refresh_from_db()

        self.assertFalse(
            old_document.is_current,
        )
        self.assertEqual(
            old_document.status,
            MandateDocument.Status.UPLOADED,
        )
        self.assertEqual(
            new_document.status,
            MandateDocument.Status.REJECTED,
        )
        self.assertEqual(
            mandate.events.filter(
                action="document_rejected",
            ).count(),
            1,
        )

    def test_document_rejection_rolls_back_when_event_creation_fails(
        self,
    ):
        property_obj = self._create_property(
            listing_type=Property.LISTING_SALE,
        )

        mandate = self._create_approved_mandate(
            property_obj=property_obj,
            owner=self._create_owner(),
        )

        document = self._add_document(
            mandate=mandate,
            document_type=MandateDocument.DocumentType.OWNER_ID,
            approved=False,
        )

        with patch.object(
            MandateEvent.objects,
            "create",
            side_effect=RuntimeError("simulated rejection audit failure"),
        ):
            with self.assertRaisesMessage(
                RuntimeError,
                "simulated rejection audit failure",
            ):
                reject_mandate_document(
                    document_id=document.id,
                    actor=self.admin,
                    reason="Unreadable identification.",
                )

        document.refresh_from_db()

        self.assertEqual(
            document.status,
            MandateDocument.Status.UPLOADED,
        )
        self.assertTrue(
            document.is_current,
        )
        self.assertIsNone(
            document.reviewed_by,
        )
        self.assertIsNone(
            document.reviewed_at,
        )
        self.assertEqual(
            document.rejection_reason,
            "",
        )
        self.assertFalse(
            mandate.events.filter(
                action="document_rejected",
            ).exists(),
        )

    def test_current_document_can_be_rejected_with_audit_event(self):
        property_obj = self._create_property(
            listing_type=Property.LISTING_SALE,
        )

        mandate = self._create_approved_mandate(
            property_obj=property_obj,
            owner=self._create_owner(),
        )

        document = self._add_document(
            mandate=mandate,
            document_type=MandateDocument.DocumentType.OWNER_ID,
        )

        rejected_document = reject_mandate_document(
            document_id=document.id,
            actor=self.admin,
            reason="  Identification image is unreadable.  ",
        )

        rejected_document.refresh_from_db()

        self.assertEqual(
            rejected_document.status,
            MandateDocument.Status.REJECTED,
        )
        self.assertTrue(
            rejected_document.is_current,
        )
        self.assertEqual(
            rejected_document.reviewed_by,
            self.admin,
        )
        self.assertIsNotNone(
            rejected_document.reviewed_at,
        )
        self.assertEqual(
            rejected_document.rejection_reason,
            "Identification image is unreadable.",
        )

        event = mandate.events.get(
            action="document_rejected",
        )

        self.assertEqual(
            event.actor,
            self.admin,
        )
        self.assertEqual(
            event.notes,
            "Identification image is unreadable.",
        )
        self.assertEqual(
            event.metadata["document_id"],
            document.id,
        )
        self.assertEqual(
            event.metadata["file_hash"],
            document.file_hash,
        )
        self.assertEqual(
            event.metadata["document_type"],
            MandateDocument.DocumentType.OWNER_ID,
        )
        self.assertEqual(
            event.metadata["previous_status"],
            MandateDocument.Status.APPROVED,
        )
        self.assertEqual(
            event.metadata["new_status"],
            MandateDocument.Status.REJECTED,
        )
        self.assertTrue(
            event.metadata["is_current"],
        )

    def test_document_approval_is_idempotent(self):
        property_obj = self._create_property(
            listing_type=Property.LISTING_SALE,
        )

        mandate = self._create_approved_mandate(
            property_obj=property_obj,
            owner=self._create_owner(),
        )

        document = self._add_document(
            mandate=mandate,
            document_type=MandateDocument.DocumentType.OWNER_ID,
            approved=False,
        )

        request = RequestFactory().post(
            "/admin/mandates/mandatedocument/",
        )
        request.user = self.admin
        request.session = {}
        request._messages = FallbackStorage(request)

        document_admin = MandateDocumentAdmin(
            MandateDocument,
            admin.site,
        )

        document_admin.approve_selected_documents(
            request,
            MandateDocument.objects.filter(pk=document.pk),
        )

        document.refresh_from_db()
        first_reviewed_at = document.reviewed_at

        first_approval_events = [
            event
            for event in mandate.events.filter(
                action="document_approved",
            )
            if event.metadata.get("document_id") == document.id
        ]

        self.assertEqual(
            len(first_approval_events),
            1,
        )

        with self.assertRaisesMessage(
            ValidationError,
            "This mandate document has already been approved.",
        ):
            document.approve(
                reviewed_by=self.admin,
            )

        document_admin.approve_selected_documents(
            request,
            MandateDocument.objects.filter(pk=document.pk),
        )

        document.refresh_from_db()

        final_approval_events = [
            event
            for event in mandate.events.filter(
                action="document_approved",
            )
            if event.metadata.get("document_id") == document.id
        ]

        self.assertEqual(
            document.reviewed_at,
            first_reviewed_at,
        )
        self.assertEqual(
            len(final_approval_events),
            1,
        )

    def test_mandate_event_actor_cannot_be_deleted(self):
        property_obj = self._create_property(
            listing_type=Property.LISTING_SALE,
        )

        mandate = self._create_approved_mandate(
            property_obj=property_obj,
            owner=self._create_owner(),
        )

        event_actor = User.objects.create_user(
            username="mandate_event_actor",
            email="mandate-event-actor@example.com",
            password="test-pass-123",
            role=User.ROLE_ADMIN,
            is_staff=True,
        )

        event = MandateEvent.objects.create(
            mandate=mandate,
            action="actor_protection_test",
            actor=event_actor,
            notes="Actor identity must remain preserved.",
        )

        with self.assertRaises(ProtectedError):
            event_actor.delete()

        event.refresh_from_db()

        self.assertEqual(
            event.actor_id,
            event_actor.id,
        )
        self.assertTrue(
            User.objects.filter(
                pk=event_actor.pk,
            ).exists(),
        )

    def test_mandate_events_are_immutable(self):
        property_obj = self._create_property(
            listing_type=Property.LISTING_SALE,
        )

        mandate = self._create_approved_mandate(
            property_obj=property_obj,
            owner=self._create_owner(),
        )

        event = MandateEvent.objects.create(
            mandate=mandate,
            action="immutability_test",
            actor=self.admin,
            notes="Original immutable audit evidence.",
            metadata={
                "source": "test",
            },
        )

        event.notes = "Tampered audit evidence."

        with self.assertRaisesMessage(
            ValidationError,
            "Mandate events are immutable and cannot be updated.",
        ):
            event.save()

        event.refresh_from_db()

        self.assertEqual(
            event.notes,
            "Original immutable audit evidence.",
        )

        with self.assertRaisesMessage(
            ValidationError,
            "Mandate events are immutable and cannot be deleted.",
        ):
            event.delete()

        with self.assertRaisesMessage(
            ValidationError,
            "Mandate events are immutable and cannot be updated.",
        ):
            MandateEvent.objects.filter(
                pk=event.pk,
            ).update(
                notes="Bulk tampering attempt.",
            )

        with self.assertRaisesMessage(
            ValidationError,
            "Mandate events are immutable and cannot be deleted.",
        ):
            MandateEvent.objects.filter(
                pk=event.pk,
            ).delete()

        self.assertTrue(
            MandateEvent.objects.filter(
                pk=event.pk,
            ).exists(),
        )

    def test_admin_document_approval_rolls_back_when_event_creation_fails(
        self,
    ):
        property_obj = self._create_property(
            listing_type=Property.LISTING_SALE,
        )

        mandate = self._create_approved_mandate(
            property_obj=property_obj,
            owner=self._create_owner(),
        )

        document = self._add_document(
            mandate=mandate,
            document_type=MandateDocument.DocumentType.OWNER_ID,
            approved=False,
        )

        request = RequestFactory().post(
            "/admin/mandates/mandatedocument/",
        )
        request.user = self.admin
        request.session = {}
        request._messages = FallbackStorage(request)

        document_admin = MandateDocumentAdmin(
            MandateDocument,
            admin.site,
        )

        with patch.object(
            MandateEvent.objects,
            "create",
            side_effect=RuntimeError("simulated audit failure"),
        ):
            with self.assertRaisesMessage(
                RuntimeError,
                "simulated audit failure",
            ):
                document_admin.approve_selected_documents(
                    request,
                    MandateDocument.objects.filter(pk=document.pk),
                )

        document.refresh_from_db()

        self.assertTrue(
            document.is_current,
        )
        self.assertEqual(
            document.status,
            MandateDocument.Status.UPLOADED,
        )
        self.assertIsNone(
            document.reviewed_by,
        )
        self.assertIsNone(
            document.reviewed_at,
        )
        self.assertFalse(
            mandate.events.filter(
                action="document_approved",
            ).exists(),
        )

    def test_current_document_can_be_superseded(self):
        property_obj = self._create_property(
            listing_type=Property.LISTING_SALE,
        )

        mandate = self._create_approved_mandate(
            property_obj=property_obj,
            owner=self._create_owner(),
        )

        old_document = self._add_document(
            mandate=mandate,
            document_type=MandateDocument.DocumentType.OWNER_ID,
        )

        old_document_id = old_document.id
        old_hash = old_document.file_hash
        old_filename = old_document.original_filename

        new_document = supersede_mandate_document(
            document_id=old_document.id,
            actor=self.admin,
            file=SimpleUploadedFile(
                "replacement-owner-id.pdf",
                b"replacement owner identification evidence",
                content_type="application/pdf",
            ),
            notes="Updated owner identification.",
        )

        old_document.refresh_from_db()
        new_document.refresh_from_db()

        self.assertFalse(
            old_document.is_current,
        )

        self.assertEqual(
            old_document.id,
            old_document_id,
        )

        self.assertEqual(
            old_document.file_hash,
            old_hash,
        )

        self.assertEqual(
            old_document.original_filename,
            old_filename,
        )

        self.assertTrue(
            new_document.is_current,
        )

        self.assertNotEqual(
            new_document.id,
            old_document.id,
        )

        self.assertNotEqual(
            new_document.file_hash,
            old_document.file_hash,
        )

        self.assertEqual(
            new_document.document_type,
            old_document.document_type,
        )

        self.assertEqual(
            new_document.status,
            MandateDocument.Status.UPLOADED,
        )

        self.assertEqual(
            new_document.uploaded_by,
            self.admin,
        )

    def test_supersession_creates_audit_event(self):
        property_obj = self._create_property(
            listing_type=Property.LISTING_SALE,
        )

        mandate = self._create_approved_mandate(
            property_obj=property_obj,
            owner=self._create_owner(),
        )

        old_document = self._add_document(
            mandate=mandate,
            document_type=MandateDocument.DocumentType.OWNERSHIP_PROOF,
        )

        old_hash = old_document.file_hash

        new_document = supersede_mandate_document(
            document_id=old_document.id,
            actor=self.admin,
            file=SimpleUploadedFile(
                "replacement-title.pdf",
                b"new ownership proof evidence",
                content_type="application/pdf",
            ),
            notes="Updated ownership evidence.",
        )

        event = mandate.events.get(
            action="document_superseded",
        )

        self.assertEqual(
            event.actor,
            self.admin,
        )

        self.assertEqual(
            event.notes,
            "Updated ownership evidence.",
        )

        self.assertEqual(
            event.metadata["old_document_id"],
            old_document.id,
        )

        self.assertEqual(
            event.metadata["old_file_hash"],
            old_hash,
        )

        self.assertEqual(
            event.metadata["new_document_id"],
            new_document.id,
        )

        self.assertEqual(
            event.metadata["new_file_hash"],
            new_document.file_hash,
        )

        self.assertEqual(
            event.metadata["document_type"],
            MandateDocument.DocumentType.OWNERSHIP_PROOF,
        )

    def test_non_current_document_cannot_be_superseded_again(self):
        property_obj = self._create_property(
            listing_type=Property.LISTING_SALE,
        )

        mandate = self._create_approved_mandate(
            property_obj=property_obj,
            owner=self._create_owner(),
        )

        old_document = self._add_document(
            mandate=mandate,
            document_type=MandateDocument.DocumentType.OWNER_ID,
        )

        supersede_mandate_document(
            document_id=old_document.id,
            actor=self.admin,
            file=SimpleUploadedFile(
                "replacement-owner-id.pdf",
                b"replacement evidence",
                content_type="application/pdf",
            ),
        )

        old_document.refresh_from_db()

        with self.assertRaises(ValidationError):
            supersede_mandate_document(
                document_id=old_document.id,
                actor=self.admin,
                file=SimpleUploadedFile(
                    "another-owner-id.pdf",
                    b"another replacement",
                    content_type="application/pdf",
                ),
            )

    def test_partner_cannot_supersede_document(self):
        property_obj = self._create_property(
            listing_type=Property.LISTING_SALE,
        )

        mandate = self._create_approved_mandate(
            property_obj=property_obj,
            owner=self._create_owner(),
        )

        document = self._add_document(
            mandate=mandate,
            document_type=MandateDocument.DocumentType.OWNER_ID,
        )

        with self.assertRaises(ValidationError):
            supersede_mandate_document(
                document_id=document.id,
                actor=self.partner_user,
                file=SimpleUploadedFile(
                    "unauthorized-replacement.pdf",
                    b"unauthorized replacement",
                    content_type="application/pdf",
                ),
            )

        document.refresh_from_db()

        self.assertTrue(
            document.is_current,
        )


    def test_partner_can_read_three_step_sale_pack_status(self):
        property_obj = self._create_property(
            listing_type=Property.LISTING_SALE,
        )

        mandate = self._create_approved_mandate(
            property_obj=property_obj,
            owner=self._create_owner(),
        )

        self._add_complete_sale_evidence(
            mandate,
        )

        client = APIClient()
        client.force_authenticate(
            user=self.partner_user,
        )

        response = client.get(
            f"/api/mandates/{mandate.id}/sale-pack/",
        )

        self.assertEqual(
            response.status_code,
            200,
            response.data,
        )

        self.assertTrue(
            response.data["sale_pack_required"],
        )
        self.assertEqual(
            response.data["completed_steps"],
            3,
        )
        self.assertEqual(
            response.data["total_steps"],
            3,
        )
        self.assertTrue(
            response.data["pack_complete"],
        )
        self.assertTrue(
            response.data["publication_allowed"],
            response.data["blocking_reasons"],
        )

        steps = {
            step["key"]: step
            for step in response.data["steps"]
        }

        self.assertEqual(
            set(steps),
            {
                "owner_identity",
                "ownership_proof",
                "sale_authority",
            },
        )

        for step in steps.values():
            self.assertTrue(
                step["completed"],
            )
            self.assertIsNotNone(
                step["document"],
            )
            self.assertNotIn(
                "file",
                step["document"],
            )

    def test_sale_pack_api_returns_rejection_feedback(self):
        property_obj = self._create_property(
            listing_type=Property.LISTING_SALE,
        )

        mandate = self._create_approved_mandate(
            property_obj=property_obj,
            owner=self._create_owner(),
        )

        document = self._add_document(
            mandate=mandate,
            document_type=(
                MandateDocument.DocumentType.OWNER_ID
            ),
            approved=False,
            filename="rejected-owner-id.pdf",
        )

        reason = "Owner identification image is unreadable."

        reject_mandate_document(
            document_id=document.id,
            actor=self.admin,
            reason=reason,
        )

        client = APIClient()
        client.force_authenticate(
            user=self.partner_user,
        )

        response = client.get(
            f"/api/mandates/{mandate.id}/sale-pack/",
        )

        self.assertEqual(
            response.status_code,
            200,
            response.data,
        )

        owner_identity = next(
            step
            for step in response.data["steps"]
            if step["key"] == "owner_identity"
        )

        self.assertFalse(
            owner_identity["completed"],
        )
        self.assertEqual(
            owner_identity["document"]["status"],
            MandateDocument.Status.REJECTED,
        )
        self.assertEqual(
            owner_identity["document"]["rejection_reason"],
            reason,
        )
        self.assertNotIn(
            "file",
            owner_identity["document"],
        )

    def test_sale_pack_api_enforces_partner_ownership(self):
        property_obj = self._create_property(
            listing_type=Property.LISTING_SALE,
        )

        mandate = self._create_approved_mandate(
            property_obj=property_obj,
            owner=self._create_owner(),
        )

        customer = User.objects.create_user(
            username="sale_pack_customer",
            email="sale-pack-customer@example.com",
            password="test-pass-123",
            role=User.ROLE_CUSTOMER,
        )

        other_partner_user = User.objects.create_user(
            username="other_sale_partner",
            email="other-sale-partner@example.com",
            password="test-pass-123",
            role=User.ROLE_PARTNER,
        )

        Partner.objects.create(
            user=other_partner_user,
            business_name="Other Sale Partner",
            verification_status=Partner.STATUS_APPROVED,
            verified_by=self.admin,
            verified_at=timezone.now(),
        )

        client = APIClient()

        client.force_authenticate(
            user=customer,
        )

        customer_response = client.get(
            f"/api/mandates/{mandate.id}/sale-pack/",
        )

        self.assertEqual(
            customer_response.status_code,
            403,
        )

        client.force_authenticate(
            user=other_partner_user,
        )

        other_partner_response = client.get(
            f"/api/mandates/{mandate.id}/sale-pack/",
        )

        self.assertEqual(
            other_partner_response.status_code,
            404,
        )
