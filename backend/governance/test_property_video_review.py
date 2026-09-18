from decimal import Decimal
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from core.models import ActivityLog
from governance.models import PartnerTier
from partners.models import Partner
from properties.models import Property, PropertyVideo
from properties.service import PublishingResult


class StaffPropertyVideoReviewTests(APITestCase):
    def setUp(self):
        self.media_directory = TemporaryDirectory()
        self.settings_override = override_settings(
            MEDIA_ROOT=self.media_directory.name,
        )
        self.settings_override.enable()

        self.staff = User.objects.create_user(
            username="flutter_review_staff",
            email="flutter-review-staff@example.com",
            password="test-password",
            role=User.ROLE_ADMIN,
            is_staff=True,
        )
        self.partner_user = User.objects.create_user(
            username="flutter_review_partner",
            email="flutter-review-partner@example.com",
            password="test-password",
            role=User.ROLE_PARTNER,
        )
        self.customer = User.objects.create_user(
            username="flutter_review_customer",
            email="flutter-review-customer@example.com",
            password="test-password",
            role=User.ROLE_CUSTOMER,
        )
        self.partner = Partner.objects.create(
            user=self.partner_user,
            business_name="Flutter Review Homes",
            display_name="Flutter Review Homes",
            partner_type=Partner.PARTNER_TYPE_AGENT,
            verification_status=Partner.STATUS_APPROVED,
            verified_by=self.staff,
            is_active=True,
            accepts_viewing_requests=True,
        )
        PartnerTier.objects.create(
            code="flutter-review-bronze",
            name="Flutter Review Bronze",
            rank=1,
            property_limit=20,
            minimum_completed_deals=0,
            minimum_trust_score=Decimal("0.00"),
            commission_share_rate=Decimal("20.00"),
            active=True,
        )
        self.pending_property = self._create_property(
            title="Kitu Poa",
            status=Property.STATUS_PENDING,
        )
        self.published_property = self._create_property(
            title="Published Replacement Home",
            status=Property.STATUS_PUBLISHED,
        )

    def tearDown(self):
        self.settings_override.disable()
        self.media_directory.cleanup()

    def _create_property(self, *, title, status):
        property_obj = Property.objects.create(
            partner=self.partner,
            title=title,
            property_type=Property.TYPE_HOUSE,
            listing_type=Property.LISTING_RENT,
            price=Decimal("45000.00"),
            county="Nairobi",
            town="Roysambu",
            bedrooms=3,
            bathrooms=2,
            description="A property used for Flutter staff review tests.",
            status=Property.STATUS_DRAFT,
        )
        Property.objects.filter(pk=property_obj.pk).update(status=status)
        property_obj.refresh_from_db()
        return property_obj

    def _create_video(
        self,
        property_obj,
        *,
        marker,
        review_status=PropertyVideo.ReviewStatus.PENDING,
        featured=False,
    ):
        return PropertyVideo.objects.create(
            property=property_obj,
            video=SimpleUploadedFile(
                f"walkthrough-{marker}.mp4",
                b"\x00\x00\x00\x18ftypmp42" + marker.encode(),
                content_type="video/mp4",
            ),
            thumbnail=SimpleUploadedFile(
                f"thumbnail-{marker}.jpg",
                b"\xff\xd8\xff\xd9",
                content_type="image/jpeg",
            ),
            title=f"Walkthrough {marker}",
            duration=39,
            is_featured=featured,
            file_size=4_000_000,
            content_sha256=(marker * 64)[:64],
            width=1920,
            height=1080,
            video_codec="h264",
            audio_codec="aac",
            uploaded_by=self.partner_user,
            review_status=review_status,
        )

    @staticmethod
    def _publish(property_obj):
        property_obj.status = Property.STATUS_PUBLISHED
        Property.objects.filter(pk=property_obj.pk).update(
            status=Property.STATUS_PUBLISHED,
        )
        return PublishingResult(
            can_publish=True,
            readiness_score=100,
            passed_checks=["Test publication checks passed."],
        )

    def test_queue_includes_property_and_published_video_reviews(self):
        initial_video = self._create_video(
            self.pending_property,
            marker="a",
            featured=True,
        )
        replacement = self._create_video(
            self.published_property,
            marker="b",
        )
        self.client.force_authenticate(user=self.staff)

        response = self.client.get("/api/property-reviews/")
        summary_response = self.client.get(
            "/api/admin/operations-summary/"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            summary_response.status_code,
            status.HTTP_200_OK,
        )
        results_by_id = {
            item["property"]["id"]: item
            for item in response.data["results"]
        }
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(summary_response.data["pending_reviews"], 2)
        self.assertEqual(
            results_by_id[self.pending_property.id]["review_scope"],
            "property_and_video",
        )
        self.assertEqual(
            results_by_id[self.pending_property.id]["video_review"][
                "pending_video_id"
            ],
            initial_video.id,
        )
        self.assertEqual(
            results_by_id[self.published_property.id]["review_scope"],
            "video",
        )
        self.assertEqual(
            results_by_id[self.published_property.id]["video_review"][
                "pending_video_id"
            ],
            replacement.id,
        )

    def test_detail_exposes_staff_video_preview_metadata(self):
        video = self._create_video(
            self.pending_property,
            marker="c",
            featured=True,
        )
        self.client.force_authenticate(user=self.staff)

        response = self.client.get(
            f"/api/property-reviews/{self.pending_property.id}/"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        video_payload = response.data["videos"][0]
        self.assertEqual(video_payload["id"], video.id)
        self.assertEqual(video_payload["review_status"], "pending")
        self.assertEqual(video_payload["duration"], 39)
        self.assertEqual(video_payload["width"], 1920)
        self.assertTrue(video_payload["video_url"].startswith("http://testserver/"))
        self.assertTrue(
            video_payload["thumbnail_url"].startswith("http://testserver/")
        )

    @patch(
        "governance.views.PublishingEngine.publish",
        side_effect=_publish,
    )
    def test_flutter_publish_approves_initial_video_together(self, _publish_mock):
        video = self._create_video(
            self.pending_property,
            marker="d",
            featured=True,
        )
        self.client.force_authenticate(user=self.staff)

        response = self.client.post(
            f"/api/property-reviews/{self.pending_property.id}/publish/",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.pending_property.refresh_from_db()
        video.refresh_from_db()
        self.assertEqual(
            self.pending_property.status,
            Property.STATUS_PUBLISHED,
        )
        self.assertEqual(
            video.review_status,
            PropertyVideo.ReviewStatus.APPROVED,
        )
        self.assertEqual(video.reviewed_by, self.staff)
        self.assertEqual(response.data["approved_video_ids"], [video.id])
        self.assertTrue(
            ActivityLog.objects.filter(
                actor=self.staff,
                action="property_video_approved",
                entity_id=str(video.id),
            ).exists()
        )

    @patch(
        "governance.views.PublishingEngine.publish",
        side_effect=_publish,
    )
    def test_flutter_publish_rolls_back_property_and_video_on_audit_failure(
        self,
        _publish_mock,
    ):
        video = self._create_video(
            self.pending_property,
            marker="e",
            featured=True,
        )
        self.client.force_authenticate(user=self.staff)

        with patch(
            "governance.views.ActivityLog.objects.create",
            side_effect=RuntimeError("audit unavailable"),
        ):
            with self.assertRaisesMessage(RuntimeError, "audit unavailable"):
                self.client.post(
                    (
                        "/api/property-reviews/"
                        f"{self.pending_property.id}/publish/"
                    ),
                    {},
                    format="json",
                )

        self.pending_property.refresh_from_db()
        video.refresh_from_db()
        self.assertEqual(
            self.pending_property.status,
            Property.STATUS_PENDING,
        )
        self.assertEqual(
            video.review_status,
            PropertyVideo.ReviewStatus.PENDING,
        )

    def test_staff_can_approve_a_published_replacement(self):
        current = self._create_video(
            self.published_property,
            marker="f",
            review_status=PropertyVideo.ReviewStatus.APPROVED,
            featured=True,
        )
        replacement = self._create_video(
            self.published_property,
            marker="g",
        )
        self.client.force_authenticate(user=self.staff)

        response = self.client.post(
            (
                f"/api/property-reviews/{self.published_property.id}/"
                f"videos/{replacement.id}/approve/"
            ),
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        replacement.refresh_from_db()
        self.assertFalse(PropertyVideo.objects.filter(pk=current.pk).exists())
        self.assertEqual(
            replacement.review_status,
            PropertyVideo.ReviewStatus.APPROVED,
        )
        self.assertTrue(replacement.is_featured)
        self.assertEqual(response.data["review_scope"], "property")
        self.assertFalse(response.data["video_review"]["required"])

    def test_returning_replacement_keeps_current_video_live(self):
        current = self._create_video(
            self.published_property,
            marker="h",
            review_status=PropertyVideo.ReviewStatus.APPROVED,
            featured=True,
        )
        replacement = self._create_video(
            self.published_property,
            marker="i",
        )
        self.client.force_authenticate(user=self.staff)

        response = self.client.post(
            (
                f"/api/property-reviews/{self.published_property.id}/"
                f"videos/{replacement.id}/return-to-partner/"
            ),
            {"reason": "The rooms are too dark."},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        current.refresh_from_db()
        replacement.refresh_from_db()
        self.assertEqual(
            current.review_status,
            PropertyVideo.ReviewStatus.APPROVED,
        )
        self.assertTrue(current.is_featured)
        self.assertEqual(
            replacement.review_status,
            PropertyVideo.ReviewStatus.REJECTED,
        )
        self.assertEqual(
            replacement.rejection_reason,
            "The rooms are too dark.",
        )
        self.assertFalse(response.data["video_review"]["required"])

    def test_non_staff_cannot_use_property_video_review_queue(self):
        replacement = self._create_video(
            self.published_property,
            marker="j",
        )
        self.client.force_authenticate(user=self.customer)

        queue_response = self.client.get("/api/property-reviews/")
        approve_response = self.client.post(
            (
                f"/api/property-reviews/{self.published_property.id}/"
                f"videos/{replacement.id}/approve/"
            ),
            {},
            format="json",
        )

        self.assertEqual(queue_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(approve_response.status_code, status.HTTP_403_FORBIDDEN)
