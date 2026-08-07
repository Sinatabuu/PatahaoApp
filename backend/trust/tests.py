from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from governance.models import (
    PartnerDisciplinaryAction,
    PartnerViolation,
    PolicyRule,
)
from governance.services import (
    confirm_partner_violation,
    impose_disciplinary_action,
    report_partner_violation,
    start_violation_review,
)
from partners.models import Partner

from .models import (
    PartnerTrustScore,
    TrustScoreHistory,
)
from .services import (
    _partner_grade,
    recalculate_partner_trust,
)


User = get_user_model()


class PartnerTrustEngineTests(TestCase):
    def setUp(self):
        self.partner_user = User.objects.create_user(
            username="trust_partner",
            email="trust.partner@example.com",
            password="TestPassword123!",
            role=User.ROLE_PARTNER,
        )

        self.partner = Partner.objects.create(
            user=self.partner_user,
            business_name="Trust Test Partner",
            display_name="Trust Partner",
            partner_type=Partner.PARTNER_TYPE_AGENT,
            verification_status=Partner.STATUS_APPROVED,
            is_active=True,
        )

        self.staff_user = User.objects.create_user(
            username="trust_staff",
            email="trust.staff@example.com",
            password="TestPassword123!",
            role=User.ROLE_ADMIN,
            is_staff=True,
        )

    def create_confirmed_violation(
        self,
        *,
        code,
        severity,
        recommended_action,
    ):
        policy = PolicyRule.objects.create(
            code=code,
            title=f"Test policy {code}",
            description="Policy used by Trust Engine tests.",
            severity=severity,
            recommended_action=recommended_action,
            effective_from=date.today(),
            active=True,
        )

        violation = report_partner_violation(
            partner=self.partner,
            policy=policy,
            summary="Confirmed Trust Engine test violation.",
            evidence_snapshot={
                "source": "trust_test",
            },
            reported_by=self.staff_user,
        )

        start_violation_review(
            violation=violation,
            reviewer=self.staff_user,
        )

        confirm_partner_violation(
            violation=violation,
            reviewer=self.staff_user,
            decision_notes="Test evidence confirmed.",
        )

        violation.refresh_from_db()

        return violation

    def test_partner_without_evidence_is_unrated(self):
        record = recalculate_partner_trust(
            self.partner,
        )

        self.assertEqual(
            record.score,
            Decimal("0.00"),
        )

        self.assertEqual(
            record.confidence,
            Decimal("0.00"),
        )

        self.assertEqual(
            record.grade,
            PartnerTrustScore.Grade.UNRATED,
        )

        self.assertEqual(
            record.feedback_count,
            0,
        )

        self.assertEqual(
            record.successful_deals,
            0,
        )

        self.assertEqual(
            record.evaluated_deals,
            0,
        )

    def test_recalculation_uses_single_partner_record(self):
        first_record = recalculate_partner_trust(
            self.partner,
        )

        second_record = recalculate_partner_trust(
            self.partner,
        )

        self.assertEqual(
            first_record.id,
            second_record.id,
        )

        self.assertEqual(
            PartnerTrustScore.objects.filter(
                partner=self.partner,
            ).count(),
            1,
        )

    def test_grade_thresholds_are_deterministic(self):
        self.assertEqual(
            _partner_grade(
                Decimal("0.00"),
                evidence_count=0,
            ),
            PartnerTrustScore.Grade.UNRATED,
        )

        self.assertEqual(
            _partner_grade(
                Decimal("39.99"),
                evidence_count=1,
            ),
            PartnerTrustScore.Grade.HIGH_RISK,
        )

        self.assertEqual(
            _partner_grade(
                Decimal("40.00"),
                evidence_count=1,
            ),
            PartnerTrustScore.Grade.DEVELOPING,
        )

        self.assertEqual(
            _partner_grade(
                Decimal("65.00"),
                evidence_count=1,
            ),
            PartnerTrustScore.Grade.GOOD,
        )

        self.assertEqual(
            _partner_grade(
                Decimal("85.00"),
                evidence_count=1,
            ),
            PartnerTrustScore.Grade.TRUSTED,
        )

        self.assertEqual(
            _partner_grade(
                Decimal("95.00"),
                evidence_count=1,
            ),
            PartnerTrustScore.Grade.EXCELLENT,
        )

    def test_confirmed_violation_is_included_in_score_snapshot(self):
        violation = self.create_confirmed_violation(
            code="TRUST-TEST-001",
            severity=PolicyRule.Severity.SERIOUS,
            recommended_action=(
                PolicyRule
                .RecommendedAction
                .LONG_SUSPENSION
            ),
        )

        record = recalculate_partner_trust(
            self.partner,
        )

        self.assertEqual(
            record.confirmed_violations,
            1,
        )

        snapshot = record.calculation_snapshot

        self.assertEqual(
            snapshot["metrics"]["confirmed_violations"],
            1,
        )

        penalties = snapshot[
            "penalties"
        ]["confirmed_violations"]

        self.assertEqual(
            len(penalties),
            1,
        )

        self.assertEqual(
            penalties[0]["violation_id"],
            violation.id,
        )

        self.assertEqual(
            penalties[0]["severity"],
            PolicyRule.Severity.SERIOUS,
        )

        self.assertEqual(
            penalties[0]["penalty"],
            "20.00",
        )

    def test_active_suspension_is_recorded_and_caps_score(self):
        violation = self.create_confirmed_violation(
            code="TRUST-TEST-002",
            severity=PolicyRule.Severity.SERIOUS,
            recommended_action=(
                PolicyRule
                .RecommendedAction
                .LONG_SUSPENSION
            ),
        )

        impose_disciplinary_action(
            violation=violation,
            action_type=(
                PartnerDisciplinaryAction
                .ActionType
                .LONG_SUSPENSION
            ),
            imposed_by=self.staff_user,
            reason="Thirty-day Trust Engine test suspension.",
            duration_days=30,
        )

        record = recalculate_partner_trust(
            self.partner,
        )

        self.assertTrue(
            record.active_restriction,
        )

        self.assertFalse(
            record.permanently_banned,
        )

        self.assertLessEqual(
            record.score,
            Decimal("20.00"),
        )

        self.assertIn(
            "Partner has an active disciplinary restriction.",
            record.calculation_snapshot["blocking_reasons"],
        )

    def test_permanent_ban_forces_score_to_zero(self):
        violation = self.create_confirmed_violation(
            code="TRUST-TEST-006",
            severity=(
                PolicyRule.Severity.GROSS_MISCONDUCT
            ),
            recommended_action=(
                PolicyRule
                .RecommendedAction
                .PERMANENT_BAN
            ),
        )

        impose_disciplinary_action(
            violation=violation,
            action_type=(
                PartnerDisciplinaryAction
                .ActionType
                .PERMANENT_BAN
            ),
            imposed_by=self.staff_user,
            reason="Confirmed gross misconduct.",
        )

        record = recalculate_partner_trust(
            self.partner,
        )

        self.assertEqual(
            record.score,
            Decimal("0.00"),
        )

        self.assertTrue(
            record.active_restriction,
        )

        self.assertTrue(
            record.permanently_banned,
        )

        self.assertIn(
            "Partner has an active permanent ban.",
            record.calculation_snapshot["blocking_reasons"],
        )

    def test_calculation_snapshot_is_preserved(self):
        record = recalculate_partner_trust(
            self.partner,
        )

        snapshot = record.calculation_snapshot

        self.assertEqual(
            snapshot["version"],
            "partner_trust_v1",
        )

        self.assertEqual(
            snapshot["partner_id"],
            self.partner.id,
        )

        self.assertIn(
            "metrics",
            snapshot,
        )

        self.assertIn(
            "components",
            snapshot,
        )

        self.assertIn(
            "penalties",
            snapshot,
        )

        self.assertIn(
            "calculation",
            snapshot,
        )

        self.assertEqual(
            snapshot["calculation"]["final_score"],
            "0.00",
        )

        self.assertEqual(
            snapshot["calculation"]["confidence"],
            "0.00",
        )

        self.assertEqual(
            snapshot["calculation"]["grade"],
            PartnerTrustScore.Grade.UNRATED,
        )

    def test_score_change_creates_history_record(self):
        initial_record = recalculate_partner_trust(
            self.partner,
        )

        self.assertEqual(
            initial_record.score,
            Decimal("0.00"),
        )

        violation = self.create_confirmed_violation(
            code="TRUST-TEST-003",
            severity=PolicyRule.Severity.MODERATE,
            recommended_action=(
                PolicyRule
                .RecommendedAction
                .SHORT_SUSPENSION
            ),
        )

        impose_disciplinary_action(
            violation=violation,
            action_type=(
                PartnerDisciplinaryAction
                .ActionType
                .SHORT_SUSPENSION
            ),
            imposed_by=self.staff_user,
            reason="Seven-day suspension.",
            duration_days=7,
        )

        updated_record = recalculate_partner_trust(
            self.partner,
        )

        self.assertEqual(
            updated_record.score,
            Decimal("0.00"),
        )

        # The score stayed at zero, so history must not contain
        # a fake score-change record.
        self.assertEqual(
            TrustScoreHistory.objects.filter(
                subject_type=(
                    TrustScoreHistory
                    .SubjectType
                    .PARTNER
                ),
                subject_id=self.partner.id,
            ).count(),
            0,
        )