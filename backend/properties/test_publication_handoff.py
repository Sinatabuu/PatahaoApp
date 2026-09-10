from datetime import timedelta
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from commissions.models import (
    CommissionAgreement,
    CommissionPlan,
)
from governance.models import PartnerTier
from mandates.models import (
    MandateDocument,
    PropertyMandate,
    PropertyOwner,
)
from partners.models import Partner
from properties.models import (
    Property,
    PropertyAmenity,
    PropertyPartner,
    PropertyPhoto,
)
from properties.photo_coverage import (
    PHOTO_TYPE_BATHROOM,
    PHOTO_TYPE_BEDROOM,
    PHOTO_TYPE_EXTERIOR,
    PHOTO_TYPE_KITCHEN,
    PHOTO_TYPE_LIVING_AREA,
)
from viewings.models import Viewing


class PropertyPublicationHandoffTests(APITestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username="publication_handoff_staff",
            email="publication-handoff-staff@example.com",
            password="test-pass-123",
            role=User.ROLE_ADMIN,
            is_staff=True,
        )
        self.partner_user = User.objects.create_user(
            username="publication_handoff_partner",
            email="publication-handoff-partner@example.com",
            password="test-pass-123",
            role=User.ROLE_PARTNER,
        )
        self.customer = User.objects.create_user(
            username="publication_handoff_customer",
            email="publication-handoff-customer@example.com",
            password="test-pass-123",
            role=User.ROLE_CUSTOMER,
        )

        commission_plan = CommissionPlan.objects.create(
            name="Publication Handoff Plan",
            partner_share_rate=Decimal("20.00"),
            minimum_completed_transactions=0,
            is_active=True,
        )
        PartnerTier.objects.create(
            code="publication-handoff-bronze",
            name="Publication Handoff Bronze",
            rank=1,
            property_limit=20,
            minimum_completed_deals=0,
            minimum_trust_score=Decimal("0.00"),
            commission_share_rate=Decimal("20.00"),
            active=True,
        )

        self.partner = Partner.objects.create(
            user=self.partner_user,
            business_name="Publication Handoff Homes",
            display_name="Publication Handoff Homes",
            partner_type=Partner.PARTNER_TYPE_AGENT,
            verification_status=Partner.STATUS_APPROVED,
            verified_by=self.staff,
            verified_at=timezone.now(),
            commission_plan=commission_plan,
            is_active=True,
            accepts_viewing_requests=True,
        )
        self.property_obj = Property.objects.create(
            partner=self.partner,
            title="Publication Handoff Home",
            property_type=Property.TYPE_HOUSE,
            listing_type=Property.LISTING_SALE,
            price=Decimal("12500000.00"),
            county="Nairobi",
            town="Roysambu",
            estate="Garden Estate",
            address="Publication Handoff Road",
            latitude=Decimal("-1.218000"),
            longitude=Decimal("36.886000"),
            bedrooms=3,
            bathrooms=2,
            description=(
                "A complete sale listing used to protect the "
                "admin-to-customer publication handoff."
            ),
            status=Property.STATUS_DRAFT,
        )

        amenity = PropertyAmenity.objects.create(
            name="Secure parking",
            slug="publication-handoff-secure-parking",
            icon="local_parking",
            display_order=1,
            is_active=True,
        )
        self.property_obj.amenities.add(amenity)

        participation, _created = PropertyPartner.objects.get_or_create(
            property=self.property_obj,
            partner=self.partner,
            defaults={
                "role": PropertyPartner.Role.SOURCE,
                "status": PropertyPartner.Status.ACTIVE,
            },
        )
        participation.role = PropertyPartner.Role.SOURCE
        participation.status = PropertyPartner.Status.ACTIVE
        participation.save(
            update_fields=[
                "role",
                "status",
            ]
        )

        self._add_complete_photo_coverage()
        mandate = self._create_approved_sale_mandate()
        self._add_approved_sale_evidence(mandate)

    def _add_complete_photo_coverage(self):
        photo_types = [
            PHOTO_TYPE_EXTERIOR,
            PHOTO_TYPE_LIVING_AREA,
            PHOTO_TYPE_KITCHEN,
            PHOTO_TYPE_BEDROOM,
            PHOTO_TYPE_BATHROOM,
        ]
        photos = []

        for index, photo_type in enumerate(photo_types):
            photos.append(
                PropertyPhoto(
                    property=self.property_obj,
                    image=(
                        "property_photos/"
                        f"publication-handoff-{index}.jpg"
                    ),
                    caption=f"Publication handoff photo {index + 1}",
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
            )

        PropertyPhoto.objects.bulk_create(photos)

    def _create_approved_sale_mandate(self):
        owner = PropertyOwner.objects.create(
            owner_type=PropertyOwner.OwnerType.INDIVIDUAL,
            legal_name="Publication Handoff Owner",
            phone_number="0700000099",
            verification_status=(
                PropertyOwner.VerificationStatus.VERIFIED
            ),
            verified_by=self.staff,
            verified_at=timezone.now(),
            created_by=self.staff,
        )
        agreement = CommissionAgreement.objects.create(
            property=self.property_obj,
            owner_name=owner.legal_name,
            owner_phone_number=owner.phone_number,
            commission_method=(
                CommissionAgreement.CommissionMethod.PERCENTAGE
            ),
            commission_basis=(
                CommissionAgreement.CommissionBasis.SALE_PRICE
            ),
            commission_rate=Decimal("3.000"),
            transaction_value=self.property_obj.price,
            created_by=self.staff,
        )
        agreement.accept_by_partner(
            user=self.partner_user,
        )
        agreement.save()
        agreement.verify(self.staff)
        agreement.save()
        agreement.lock()
        agreement.save()

        mandate = PropertyMandate.objects.create(
            property=self.property_obj,
            owner=owner,
            partner=self.partner,
            commission_agreement=agreement,
            authorization_method=(
                PropertyMandate.AuthorizationMethod.WRITTEN
            ),
            owner_authority_confirmed=True,
            no_cash_acknowledged=True,
            anti_circumvention_acknowledged=True,
            created_by=self.staff,
        )
        mandate.declare_by_partner(
            user=self.partner_user,
        )
        mandate.save()
        mandate.submit_for_review()
        mandate.save()
        mandate.approve(
            approved_by=self.staff,
        )
        mandate.save()

        return mandate

    def _add_approved_sale_evidence(self, mandate):
        document_types = [
            MandateDocument.DocumentType.OWNER_ID,
            MandateDocument.DocumentType.OWNERSHIP_PROOF,
            MandateDocument.DocumentType.SIGNED_MANDATE,
        ]

        for document_type in document_types:
            MandateDocument.objects.create(
                mandate=mandate,
                document_type=document_type,
                file=SimpleUploadedFile(
                    f"{document_type}.pdf",
                    b"publication handoff evidence",
                    content_type="application/pdf",
                ),
                status=MandateDocument.Status.APPROVED,
                is_current=True,
                uploaded_by=self.partner_user,
                reviewed_by=self.staff,
                reviewed_at=timezone.now(),
            )

    def _public_property_ids(self, response):
        payload = response.data

        if isinstance(payload, dict):
            payload = payload.get("results", [])

        return {
            item["id"]
            for item in payload
        }

    def test_admin_publish_handoff_reaches_customer_viewing_request(self):
        self.client.force_authenticate(
            user=self.partner_user,
        )
        submission_response = self.client.post(
            (
                "/api/partner/properties/"
                f"{self.property_obj.id}/submit-verification/"
            ),
            {},
            format="json",
        )

        self.assertEqual(
            submission_response.status_code,
            status.HTTP_200_OK,
        )
        self.property_obj.refresh_from_db()
        self.assertEqual(
            self.property_obj.status,
            Property.STATUS_PENDING,
        )

        self.client.force_authenticate(user=None)
        hidden_list_response = self.client.get(
            "/api/properties/",
        )
        hidden_detail_response = self.client.get(
            f"/api/properties/{self.property_obj.id}/",
        )

        self.assertEqual(
            hidden_list_response.status_code,
            status.HTTP_200_OK,
        )
        self.assertNotIn(
            self.property_obj.id,
            self._public_property_ids(hidden_list_response),
        )
        self.assertEqual(
            hidden_detail_response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

        self.client.force_authenticate(
            user=self.staff,
        )
        publish_response = self.client.post(
            (
                "/api/property-reviews/"
                f"{self.property_obj.id}/publish/"
            ),
            {},
            format="json",
        )

        self.assertEqual(
            publish_response.status_code,
            status.HTTP_200_OK,
            publish_response.data,
        )
        self.assertEqual(
            publish_response.data["status"],
            Property.STATUS_PUBLISHED,
        )

        self.property_obj.refresh_from_db()
        self.assertEqual(
            self.property_obj.status,
            Property.STATUS_PUBLISHED,
        )

        self.client.force_authenticate(user=None)
        public_list_response = self.client.get(
            "/api/properties/",
        )
        public_detail_response = self.client.get(
            f"/api/properties/{self.property_obj.id}/",
        )

        self.assertEqual(
            public_list_response.status_code,
            status.HTTP_200_OK,
        )
        self.assertIn(
            self.property_obj.id,
            self._public_property_ids(public_list_response),
        )
        self.assertEqual(
            public_detail_response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            public_detail_response.data["status"],
            Property.STATUS_PUBLISHED,
        )
        self.assertEqual(
            public_detail_response.data["amenities"][0]["slug"],
            "publication-handoff-secure-parking",
        )

        self.client.force_authenticate(
            user=self.customer,
        )
        viewing_response = self.client.post(
            "/api/viewings/",
            {
                "property": self.property_obj.id,
                "requested_date": (
                    timezone.localdate() + timedelta(days=1)
                ).isoformat(),
                "requested_time": "10:30:00",
                "customer_message": (
                    "I would like to view this property."
                ),
            },
            format="json",
        )

        self.assertEqual(
            viewing_response.status_code,
            status.HTTP_201_CREATED,
            viewing_response.data,
        )
        self.assertEqual(
            viewing_response.data["property"],
            self.property_obj.id,
        )
        self.assertEqual(
            viewing_response.data["status"],
            Viewing.Status.PENDING_PAYMENT,
        )
        self.assertEqual(
            viewing_response.data["fee_amount"],
            "300.00",
        )
        self.assertEqual(
            viewing_response.data["assigned_partner"],
            self.partner.id,
        )
