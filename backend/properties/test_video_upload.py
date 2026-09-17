from decimal import Decimal
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from partners.models import Partner

from .models import Property, PropertyVideo
from .video_quality import (
    PropertyVideoAnalysis,
    _validate_probe,
    analyze_property_video,
)


def uploaded_mp4(name="walkthrough.mp4", marker=b"test"):
    return SimpleUploadedFile(
        name,
        b"\x00\x00\x00\x18ftypmp42" + marker,
        content_type="video/mp4",
    )


def video_analysis(content_hash="a" * 64):
    return PropertyVideoAnalysis(
        file_size=4_000_000,
        content_sha256=content_hash,
        width=1920,
        height=1080,
        duration=75,
        video_codec="h264",
        audio_codec="aac",
        thumbnail_bytes=b"\xff\xd8\xff\xd9",
    )


@override_settings(MEDIA_ROOT=None)
class PropertyVideoApiTests(APITestCase):
    def setUp(self):
        self.media_directory = TemporaryDirectory()
        self.settings_override = override_settings(
            MEDIA_ROOT=self.media_directory.name,
        )
        self.settings_override.enable()

        self.staff = User.objects.create_user(
            username="video_staff",
            email="video-staff@example.com",
            password="test-password",
            role=User.ROLE_ADMIN,
            is_staff=True,
        )
        self.partner_user = User.objects.create_user(
            username="video_partner",
            email="video-partner@example.com",
            password="test-password",
            role=User.ROLE_PARTNER,
        )
        self.partner = Partner.objects.create(
            user=self.partner_user,
            business_name="Video Partner",
            verification_status=Partner.STATUS_APPROVED,
            verified_by=self.staff,
        )
        self.other_user = User.objects.create_user(
            username="other_video_partner",
            email="other-video-partner@example.com",
            password="test-password",
            role=User.ROLE_PARTNER,
        )
        self.other_partner = Partner.objects.create(
            user=self.other_user,
            business_name="Other Video Partner",
            verification_status=Partner.STATUS_APPROVED,
            verified_by=self.staff,
        )
        self.property_obj = Property.objects.create(
            partner=self.partner,
            title="Walkthrough Home",
            property_type=Property.TYPE_HOUSE,
            listing_type=Property.LISTING_RENT,
            price=Decimal("45000.00"),
            county="Nairobi",
            town="Roysambu",
            bedrooms=3,
            bathrooms=2,
            description="A home used to test walkthrough videos.",
            status=Property.STATUS_DRAFT,
        )
        self.client.force_authenticate(user=self.partner_user)

    def tearDown(self):
        self.settings_override.disable()
        self.media_directory.cleanup()

    def _create_video(
        self,
        *,
        content_hash,
        featured=False,
        review_status=PropertyVideo.ReviewStatus.PENDING,
    ):
        return PropertyVideo.objects.create(
            property=self.property_obj,
            video=uploaded_mp4(marker=content_hash.encode()),
            thumbnail=SimpleUploadedFile(
                "thumbnail.jpg",
                b"\xff\xd8\xff\xd9",
                content_type="image/jpeg",
            ),
            title="Existing walkthrough",
            duration=60,
            is_featured=featured,
            file_size=1000,
            content_sha256=content_hash,
            width=1280,
            height=720,
            video_codec="h264",
            audio_codec="aac",
            uploaded_by=self.partner_user,
            review_status=review_status,
        )

    @patch("properties.serializers.analyze_property_video")
    def test_source_partner_upload_is_pending_with_verified_metadata(
        self,
        analyze_mock,
    ):
        analyze_mock.return_value = video_analysis()

        response = self.client.post(
            "/api/partner/videos/",
            {
                "property": self.property_obj.id,
                "video": uploaded_mp4(),
                "title": "Room-by-room tour",
                "description": "A clear guided walkthrough.",
            },
            format="multipart",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            response.data,
        )
        video = PropertyVideo.objects.get()
        self.assertEqual(video.uploaded_by, self.partner_user)
        self.assertEqual(video.review_status, "pending")
        self.assertTrue(video.is_featured)
        self.assertEqual(video.duration, 75)
        self.assertEqual((video.width, video.height), (1920, 1080))
        self.assertEqual(video.content_sha256, "a" * 64)
        self.assertTrue(video.thumbnail.name.endswith(".jpg"))
        self.assertEqual(response.data["review_status"], "pending")

    @patch("properties.serializers.analyze_property_video")
    def test_partner_cannot_upload_for_another_source_partner(
        self,
        analyze_mock,
    ):
        analyze_mock.return_value = video_analysis()
        self.client.force_authenticate(user=self.other_user)

        response = self.client.post(
            "/api/partner/videos/",
            {
                "property": self.property_obj.id,
                "video": uploaded_mp4(),
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(PropertyVideo.objects.exists())

    @patch("properties.serializers.analyze_property_video")
    def test_duplicate_video_is_rejected(self, analyze_mock):
        existing_hash = "b" * 64
        self._create_video(
            content_hash=existing_hash,
            featured=True,
        )
        analyze_mock.return_value = video_analysis(existing_hash)

        response = self.client.post(
            "/api/partner/videos/",
            {
                "property": self.property_obj.id,
                "video": uploaded_mp4(),
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already been uploaded", str(response.data))

    def test_fourth_video_is_rejected(self):
        for index in range(3):
            self._create_video(
                content_hash=str(index) * 64,
                featured=index == 0,
            )

        response = self.client.post(
            "/api/partner/videos/",
            {
                "property": self.property_obj.id,
                "video": uploaded_mp4(),
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("up to three", str(response.data))

    def test_public_property_only_exposes_approved_videos(self):
        pending = self._create_video(
            content_hash="c" * 64,
            featured=True,
        )
        approved = self._create_video(
            content_hash="d" * 64,
            review_status=PropertyVideo.ReviewStatus.APPROVED,
        )
        Property.objects.filter(pk=self.property_obj.pk).update(
            status=Property.STATUS_PUBLISHED,
        )
        self.client.force_authenticate(user=None)

        response = self.client.get(
            f"/api/properties/{self.property_obj.id}/",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [item["id"] for item in response.data["videos"]],
            [approved.id],
        )
        self.assertNotEqual(pending.id, approved.id)

    def test_setting_featured_video_unsets_previous_video(self):
        first = self._create_video(
            content_hash="e" * 64,
            featured=True,
        )
        second = self._create_video(content_hash="f" * 64)

        response = self.client.patch(
            f"/api/partner/videos/{second.id}/",
            {"is_featured": True},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertFalse(first.is_featured)
        self.assertTrue(second.is_featured)

    def test_only_staff_can_approve_or_return_video(self):
        video = self._create_video(
            content_hash="1" * 64,
            featured=True,
        )

        with self.assertRaises(ValidationError):
            video.approve(reviewed_by=self.partner_user)

        video.approve(reviewed_by=self.staff)
        self.assertEqual(video.review_status, "approved")

        video.reject(
            reviewed_by=self.staff,
            reason="The rooms are too dark.",
        )
        self.assertEqual(video.review_status, "rejected")
        self.assertEqual(video.rejection_reason, "The rooms are too dark.")

    def test_closed_property_video_cannot_be_changed_or_deleted(self):
        video = self._create_video(
            content_hash="2" * 64,
            featured=True,
        )
        Property.objects.filter(pk=self.property_obj.pk).update(
            status=Property.STATUS_RENTED,
        )

        update_response = self.client.patch(
            f"/api/partner/videos/{video.id}/",
            {"title": "Changed after closing"},
            format="json",
        )
        delete_response = self.client.delete(
            f"/api/partner/videos/{video.id}/",
        )

        self.assertEqual(
            update_response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(
            delete_response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertTrue(PropertyVideo.objects.filter(pk=video.pk).exists())

    def test_deleting_video_removes_stored_media_files(self):
        video = self._create_video(
            content_hash="3" * 64,
            featured=True,
        )
        video_storage = video.video.storage
        video_name = video.video.name
        thumbnail_name = video.thumbnail.name

        response = self.client.delete(
            f"/api/partner/videos/{video.id}/",
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(video_storage.exists(video_name))
        self.assertFalse(video_storage.exists(thumbnail_name))


class PropertyVideoQualityTests(TestCase):
    def test_non_mp4_upload_is_rejected_before_processing(self):
        upload = SimpleUploadedFile(
            "walkthrough.mov",
            b"not-a-video",
            content_type="video/quicktime",
        )

        with self.assertRaisesMessage(ValidationError, "Upload an MP4"):
            analyze_property_video(upload)

    @patch("properties.video_quality._generate_thumbnail")
    @patch("properties.video_quality._probe_video")
    def test_valid_mp4_returns_authoritative_analysis(
        self,
        probe_mock,
        thumbnail_mock,
    ):
        probe_mock.return_value = {
            "width": 1280,
            "height": 720,
            "duration_value": 61.4,
            "video_codec": "h264",
            "audio_codec": "aac",
        }
        thumbnail_mock.return_value = b"thumbnail"
        upload = uploaded_mp4()

        result = analyze_property_video(upload)

        self.assertEqual(result.duration, 61)
        self.assertEqual((result.width, result.height), (1280, 720))
        self.assertEqual(len(result.content_sha256), 64)
        self.assertEqual(upload.tell(), 0)

    def test_4k_video_is_rejected_for_mvp(self):
        with self.assertRaisesMessage(ValidationError, "1080p or lower"):
            _validate_probe(
                {
                    "width": 3840,
                    "height": 2160,
                    "duration_value": 60,
                    "video_codec": "h264",
                    "audio_codec": "aac",
                }
            )
