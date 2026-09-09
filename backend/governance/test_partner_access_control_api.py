from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from governance.models import (
    PartnerDisciplinaryAction,
    PartnerReinstatement,
    PartnerViolation,
    PolicyRule,
)
from partners.models import Partner


class PartnerAccessControlApiTests(APITestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username="access_control_staff",
            email="access-control-staff@example.com",
            password="test-pass-123",
            role=User.ROLE_ADMIN,
            is_staff=True,
        )
        self.non_staff = User.objects.create_user(
            username="access_control_customer",
            email="access-control-customer@example.com",
            password="test-pass-123",
            role=User.ROLE_CUSTOMER,
        )
        self.partner_user = User.objects.create_user(
            username="access_control_partner",
            email="access-control-partner@example.com",
            password="test-pass-123",
            role=User.ROLE_PARTNER,
        )
        self.partner = Partner.objects.create(
            user=self.partner_user,
            business_name="Access Control Partner",
            display_name="Access Control Partner",
            verification_status=Partner.STATUS_APPROVED,
            verified_by=self.staff,
            verified_at=timezone.now(),
            is_active=True,
            accepts_viewing_requests=True,
        )
        self.suspension_policy = PolicyRule.objects.create(
            code="TEST-ACCESS-001",
            title="Viewing conduct policy",
            description="Test policy for temporary suspension.",
            severity=PolicyRule.Severity.MODERATE,
            recommended_action=(
                PolicyRule.RecommendedAction.SHORT_SUSPENSION
            ),
            effective_from=timezone.localdate(),
            active=True,
        )
        self.ban_policy = PolicyRule.objects.create(
            code="TEST-ACCESS-002",
            title="Document falsification policy",
            description="Test policy for permanent removal.",
            severity=PolicyRule.Severity.GROSS_MISCONDUCT,
            recommended_action=(
                PolicyRule.RecommendedAction.PERMANENT_BAN
            ),
            effective_from=timezone.localdate(),
            active=True,
        )
        self.client.force_authenticate(user=self.staff)

    def _suspend_partner(self):
        return self.client.post(
            (
                "/api/admin/partners/"
                f"{self.partner.id}/disciplinary-action/"
            ),
            {
                "policy_code": self.suspension_policy.code,
                "action_type": (
                    PartnerDisciplinaryAction
                    .ActionType
                    .SHORT_SUSPENSION
                ),
                "duration_days": 7,
                "reason": (
                    "The partner failed to honor a confirmed "
                    "customer viewing."
                ),
            },
            format="json",
        )

    def test_partner_detail_exposes_access_control_information(self):
        response = self.client.get(
            f"/api/admin/partners/{self.partner.id}/",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertFalse(
            response.data["governance"]["restricted"],
        )

        policy_codes = {
            item["code"]
            for item in (
                response.data["governance"]
                ["policy_options"]
            )
        }

        self.assertIn(
            self.suspension_policy.code,
            policy_codes,
        )
        self.assertIn(
            self.ban_policy.code,
            policy_codes,
        )

    def test_staff_can_suspend_partner_with_audited_records(self):
        response = self._suspend_partner()

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.partner.refresh_from_db()

        self.assertFalse(self.partner.is_active)
        self.assertFalse(
            self.partner.accepts_viewing_requests,
        )
        self.assertEqual(
            self.partner.verification_status,
            Partner.STATUS_SUSPENDED,
        )
        self.assertTrue(
            response.data["governance"]["restricted"],
        )

        violation = PartnerViolation.objects.get(
            partner=self.partner,
        )
        action = PartnerDisciplinaryAction.objects.get(
            partner=self.partner,
        )

        self.assertEqual(
            violation.status,
            PartnerViolation.Status.CONFIRMED,
        )
        self.assertEqual(
            action.status,
            PartnerDisciplinaryAction.Status.ACTIVE,
        )
        self.assertIsNotNone(action.ends_at)

    def test_non_staff_cannot_suspend_partner(self):
        self.client.force_authenticate(
            user=self.non_staff,
        )

        response = self._suspend_partner()

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertFalse(
            PartnerDisciplinaryAction.objects.exists(),
        )

    def test_permanent_ban_requires_explicit_confirmation(self):
        response = self.client.post(
            (
                "/api/admin/partners/"
                f"{self.partner.id}/disciplinary-action/"
            ),
            {
                "policy_code": self.ban_policy.code,
                "action_type": (
                    PartnerDisciplinaryAction
                    .ActionType
                    .PERMANENT_BAN
                ),
                "reason": (
                    "Verified falsified ownership evidence "
                    "was submitted."
                ),
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertFalse(
            PartnerDisciplinaryAction.objects.exists(),
        )

    def test_staff_can_permanently_ban_partner(self):
        response = self.client.post(
            (
                "/api/admin/partners/"
                f"{self.partner.id}/disciplinary-action/"
            ),
            {
                "policy_code": self.ban_policy.code,
                "action_type": (
                    PartnerDisciplinaryAction
                    .ActionType
                    .PERMANENT_BAN
                ),
                "reason": (
                    "Verified falsified ownership evidence "
                    "was submitted."
                ),
                "confirm_permanent_ban": True,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )
        self.assertTrue(
            response.data["governance"]
            ["permanently_banned"],
        )

        action = PartnerDisciplinaryAction.objects.get(
            partner=self.partner,
        )

        self.assertTrue(action.is_permanent)
        self.assertIsNone(action.ends_at)

    def test_staff_can_restore_suspended_partner(self):
        suspension_response = self._suspend_partner()

        self.assertEqual(
            suspension_response.status_code,
            status.HTTP_201_CREATED,
        )

        response = self.client.post(
            (
                "/api/admin/partners/"
                f"{self.partner.id}/reinstate/"
            ),
            {
                "reason": (
                    "The incident was reviewed and corrective "
                    "steps were completed."
                ),
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.partner.refresh_from_db()

        self.assertTrue(self.partner.is_active)
        self.assertTrue(
            self.partner.accepts_viewing_requests,
        )
        self.assertEqual(
            self.partner.verification_status,
            Partner.STATUS_APPROVED,
        )
        self.assertFalse(
            response.data["governance"]["restricted"],
        )
        self.assertTrue(
            PartnerReinstatement.objects.filter(
                partner=self.partner,
                approved_by=self.staff,
            ).exists(),
        )
        self.assertEqual(
            PartnerDisciplinaryAction.objects.get(
                partner=self.partner,
            ).status,
            PartnerDisciplinaryAction.Status.REVOKED,
        )

    def test_permanent_ban_reversal_requires_confirmation(self):
        ban_response = self.client.post(
            (
                "/api/admin/partners/"
                f"{self.partner.id}/disciplinary-action/"
            ),
            {
                "policy_code": self.ban_policy.code,
                "action_type": (
                    PartnerDisciplinaryAction
                    .ActionType
                    .PERMANENT_BAN
                ),
                "reason": (
                    "Verified falsified ownership evidence "
                    "was submitted."
                ),
                "confirm_permanent_ban": True,
            },
            format="json",
        )

        self.assertEqual(
            ban_response.status_code,
            status.HTTP_201_CREATED,
        )

        response = self.client.post(
            (
                "/api/admin/partners/"
                f"{self.partner.id}/reinstate/"
            ),
            {
                "reason": (
                    "Senior review approved a formal reversal "
                    "of the permanent ban."
                ),
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.partner.refresh_from_db()
        self.assertFalse(self.partner.is_active)

    def test_staff_can_reverse_permanent_ban_with_confirmation(self):
        ban_response = self.client.post(
            (
                "/api/admin/partners/"
                f"{self.partner.id}/disciplinary-action/"
            ),
            {
                "policy_code": self.ban_policy.code,
                "action_type": (
                    PartnerDisciplinaryAction
                    .ActionType
                    .PERMANENT_BAN
                ),
                "reason": (
                    "Verified falsified ownership evidence "
                    "was submitted."
                ),
                "confirm_permanent_ban": True,
            },
            format="json",
        )

        self.assertEqual(
            ban_response.status_code,
            status.HTTP_201_CREATED,
        )

        response = self.client.post(
            (
                "/api/admin/partners/"
                f"{self.partner.id}/reinstate/"
            ),
            {
                "reason": (
                    "Senior review approved a documented "
                    "reversal of the permanent ban."
                ),
                "confirm_permanent_ban_reversal": True,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.partner.refresh_from_db()
        self.assertTrue(self.partner.is_active)
        self.assertEqual(
            self.partner.verification_status,
            Partner.STATUS_APPROVED,
        )
        self.assertEqual(
            PartnerDisciplinaryAction.objects.get(
                partner=self.partner,
            ).status,
            PartnerDisciplinaryAction.Status.REVOKED,
        )
