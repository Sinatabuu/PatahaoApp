from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from rest_framework.test import APIClient

from accounts.models import User
from commissions.models import CommissionAgreement
from core.models import ActivityLog
from mandates.models import (
    MandateDocument,
    MandateEvent,
    PropertyMandate,
    PropertyOwner,
)
from partners.models import Partner
from properties.models import Property, PropertyPhoto
from properties.photo_coverage import (
    PHOTO_TYPE_BATHROOM,
    PHOTO_TYPE_BEDROOM,
    PHOTO_TYPE_EXTERIOR,
    PHOTO_TYPE_KITCHEN,
    PHOTO_TYPE_LIVING_AREA,
)


class StaffAuthorizationReviewTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="authorization_admin",
            email="authorization-admin@example.com",
            password="test-pass-123",
            role=User.ROLE_ADMIN,
            is_staff=True,
            is_superuser=True,
        )

        self.partner_user = User.objects.create_user(
            username="authorization_partner",
            email="authorization-partner@example.com",
            password="test-pass-123",
            role=User.ROLE_PARTNER,
        )

        self.partner = Partner.objects.create(
            user=self.partner_user,
            business_name="Authorization Partner",
            verification_status=Partner.STATUS_APPROVED,
            verified_by=self.admin,
            verified_at=timezone.now(),
        )

        self.property = Property.objects.create(
            partner=self.partner,
            title="Authorization Review Home",
            property_type=Property.TYPE_HOUSE,
            listing_type=Property.LISTING_SALE,
            price=Decimal("12500000.00"),
            county="Nairobi",
            town="Nairobi",
            description="A sale listing waiting for authorization review.",
            status=Property.STATUS_DRAFT,
        )

        self.agreement = CommissionAgreement.objects.create(
            property=self.property,
            owner_name="Authorization Owner",
            owner_phone_number="0700000099",
            commission_method=(
                CommissionAgreement.CommissionMethod.PERCENTAGE
            ),
            commission_basis=(
                CommissionAgreement.CommissionBasis.SALE_PRICE
            ),
            commission_rate=Decimal("3.000"),
            transaction_value=self.property.price,
            created_by=self.partner_user,
        )
        self.agreement.accept_by_partner(
            user=self.partner_user,
        )
        self.agreement.save()

        self.owner = PropertyOwner.objects.create(
            owner_type=PropertyOwner.OwnerType.INDIVIDUAL,
            legal_name="Authorization Owner",
            phone_number="0700000099",
            created_by=self.partner_user,
        )

        self.mandate = PropertyMandate.objects.create(
            property=self.property,
            owner=self.owner,
            partner=self.partner,
            commission_agreement=self.agreement,
            authorization_method=(
                PropertyMandate.AuthorizationMethod.WRITTEN
            ),
            owner_authority_confirmed=True,
            no_cash_acknowledged=True,
            anti_circumvention_acknowledged=True,
            created_by=self.partner_user,
        )
        self.mandate.declare_by_partner(
            user=self.partner_user,
        )
        self.mandate.save()
        self.mandate.submit_for_review()
        self.mandate.save()

        for document_type in [
            MandateDocument.DocumentType.OWNER_ID,
            MandateDocument.DocumentType.OWNERSHIP_PROOF,
            MandateDocument.DocumentType.SIGNED_MANDATE,
        ]:
            MandateDocument.objects.create(
                mandate=self.mandate,
                document_type=document_type,
                file=SimpleUploadedFile(
                    f"{document_type}.pdf",
                    b"%PDF-1.4\nreview evidence",
                    content_type="application/pdf",
                ),
                status=MandateDocument.Status.UPLOADED,
                is_current=True,
                uploaded_by=self.partner_user,
            )

        self.documents = list(
            self.mandate.documents.filter(
                is_current=True,
            ).order_by("id")
        )
        self.reviewed_document_ids = [
            document.id
            for document in self.documents
        ]

        self.client = APIClient()

    def test_submitted_authorization_is_visible_to_staff(self):
        self.client.force_authenticate(
            user=self.admin,
        )

        response = self.client.get(
            reverse("mandate-list"),
            {
                "status": (
                    PropertyMandate.Status.UNDER_REVIEW
                ),
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )
        self.assertEqual(
            len(response.data),
            1,
        )
        self.assertEqual(
            response.data[0]["id"],
            self.mandate.id,
        )
        self.assertEqual(
            response.data[0]["property_title"],
            self.property.title,
        )

        summary_response = self.client.get(
            reverse(
                "governance-admin-operations-summary",
            ),
        )

        self.assertEqual(
            summary_response.status_code,
            200,
        )
        self.assertEqual(
            summary_response.data[
                "pending_authorization_reviews"
            ],
            1,
        )

    def test_staff_can_complete_authorization_review(self):
        self.client.force_authenticate(
            user=self.admin,
        )

        response = self.client.post(
            reverse(
                "mandate-complete-review",
                kwargs={
                    "pk": self.mandate.id,
                },
            ),
            {
                "reviewed_document_ids": (
                    self.reviewed_document_ids
                ),
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.mandate.refresh_from_db()
        self.owner.refresh_from_db()
        self.agreement.refresh_from_db()
        self.property.refresh_from_db()

        self.assertEqual(
            self.mandate.status,
            PropertyMandate.Status.APPROVED,
        )
        self.assertTrue(
            self.owner.is_verified,
        )
        self.assertTrue(
            self.agreement.is_publish_ready(),
        )
        self.assertFalse(
            self.mandate.documents.filter(
                is_current=True,
            ).exclude(
                status=MandateDocument.Status.APPROVED,
            ).exists(),
        )
        self.assertTrue(
            MandateEvent.objects.filter(
                mandate=self.mandate,
                action="authorization_review_completed",
            ).exists(),
        )
        self.assertEqual(
            self.property.status,
            Property.STATUS_DRAFT,
        )

    def test_complete_property_enters_review_after_authorization_approval(
        self,
    ):
        self.property.latitude = Decimal("-1.2180000")
        self.property.longitude = Decimal("36.8860000")
        self.property.bedrooms = 3
        self.property.bathrooms = 2
        self.property.save()

        photo_types = [
            PHOTO_TYPE_EXTERIOR,
            PHOTO_TYPE_LIVING_AREA,
            PHOTO_TYPE_KITCHEN,
            PHOTO_TYPE_BEDROOM,
            PHOTO_TYPE_BATHROOM,
        ]

        PropertyPhoto.objects.bulk_create(
            [
                PropertyPhoto(
                    property=self.property,
                    image=(
                        "property_photos/authorization-"
                        f"{index}.jpg"
                    ),
                    photo_type=photo_type,
                    is_cover=index == 0,
                    image_width=1600,
                    image_height=900,
                    file_size=250000,
                    quality_status=(
                        PropertyPhoto.QualityStatus.ACCEPTED
                    ),
                    quality_score=100,
                )
                for index, photo_type in enumerate(photo_types)
            ]
        )

        self.client.force_authenticate(
            user=self.admin,
        )

        response = self.client.post(
            reverse(
                "mandate-complete-review",
                kwargs={
                    "pk": self.mandate.id,
                },
            ),
            {
                "reviewed_document_ids": (
                    self.reviewed_document_ids
                ),
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        self.property.refresh_from_db()

        self.assertEqual(
            self.property.status,
            Property.STATUS_PENDING,
        )
        self.assertTrue(
            ActivityLog.objects.filter(
                action="property_submitted_for_verification",
                entity_type="Property",
                entity_id=str(self.property.id),
            ).exists(),
        )

        event = MandateEvent.objects.get(
            mandate=self.mandate,
            action="authorization_review_completed",
        )
        self.assertTrue(
            event.metadata[
                "property_submitted_for_verification"
            ]
        )

    def test_staff_must_acknowledge_every_current_evidence_file(
        self,
    ):
        self.client.force_authenticate(
            user=self.admin,
        )

        response = self.client.post(
            reverse(
                "mandate-complete-review",
                kwargs={
                    "pk": self.mandate.id,
                },
            ),
            {
                "reviewed_document_ids": (
                    self.reviewed_document_ids[:-1]
                ),
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )
        self.assertIn(
            "Open and inspect every current evidence file",
            str(response.data),
        )

        self.mandate.refresh_from_db()

        self.assertEqual(
            self.mandate.status,
            PropertyMandate.Status.UNDER_REVIEW,
        )
        self.assertFalse(
            self.mandate.documents.filter(
                status=MandateDocument.Status.APPROVED,
            ).exists(),
        )

    def test_staff_can_fetch_evidence_through_protected_endpoint(
        self,
    ):
        document = self.documents[0]
        self.client.force_authenticate(
            user=self.admin,
        )

        response = self.client.get(
            reverse(
                "mandate-evidence-file",
                kwargs={
                    "pk": self.mandate.id,
                    "document_id": document.id,
                },
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response["Content-Type"],
            "application/pdf",
        )
        self.assertEqual(
            response["Cache-Control"],
            "private, no-store",
        )
        self.assertEqual(
            b"".join(response.streaming_content),
            b"%PDF-1.4\nreview evidence",
        )

    def test_partner_cannot_fetch_authorization_evidence(self):
        document = self.documents[0]
        self.client.force_authenticate(
            user=self.partner_user,
        )

        response = self.client.get(
            reverse(
                "mandate-evidence-file",
                kwargs={
                    "pk": self.mandate.id,
                    "document_id": document.id,
                },
            )
        )

        self.assertEqual(response.status_code, 403)

    def test_partner_cannot_complete_authorization_review(self):
        self.client.force_authenticate(
            user=self.partner_user,
        )

        response = self.client.post(
            reverse(
                "mandate-complete-review",
                kwargs={
                    "pk": self.mandate.id,
                },
            ),
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_django_admin_displays_authorization_review_queue(self):
        self.client.force_login(
            self.admin,
        )

        response = self.client.get(
            reverse(
                "admin:mandates_authorizationreview_changelist",
            ),
        )

        self.assertEqual(
            response.status_code,
            200,
        )
        self.assertContains(
            response,
            self.property.title,
        )
        self.assertContains(
            response,
            self.mandate.mandate_number,
        )

    def test_django_admin_review_displays_open_evidence_controls(self):
        self.client.force_login(
            self.admin,
        )

        response = self.client.get(
            reverse(
                "admin:mandates_authorizationreview_change",
                args=[
                    self.mandate.id,
                ],
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Open evidence",
            count=len(self.documents),
        )

        for document in self.documents:
            self.assertContains(
                response,
                reverse(
                    "admin:mandates_mandatedocument_evidence",
                    args=[
                        document.id,
                    ],
                ),
            )

    def test_django_admin_evidence_view_requires_staff_login(self):
        document = self.documents[0]
        evidence_url = reverse(
            "admin:mandates_mandatedocument_evidence",
            args=[
                document.id,
            ],
        )

        response = self.client.get(evidence_url)

        self.assertEqual(response.status_code, 302)

        self.client.force_login(self.admin)
        response = self.client.get(evidence_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            b"".join(response.streaming_content),
            b"%PDF-1.4\nreview evidence",
        )

    def test_django_admin_can_approve_authorization_review(self):
        self.client.force_login(
            self.admin,
        )

        response = self.client.post(
            reverse(
                "admin:mandates_authorizationreview_changelist",
            ),
            {
                "action": (
                    "complete_selected_authorization_reviews"
                ),
                "_selected_action": [
                    str(self.mandate.id),
                ],
            },
            follow=True,
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.mandate.refresh_from_db()

        self.assertEqual(
            self.mandate.status,
            PropertyMandate.Status.APPROVED,
        )
