from decimal import Decimal
from datetime import date, timedelta
from django.core.exceptions import ValidationError
from django.utils import timezone
from properties.models import Property


from django.contrib.auth import get_user_model
from django.test import TestCase

from partners.models import Partner

from .models import (
    PartnerDisciplinaryAction,
    PartnerPromotionReview,
    PartnerReinstatement,
    PartnerTier,
    PartnerTierAssignment,
    PartnerViolation,
    PolicyRule,
)
from .services import (
    assign_default_tier,
    calculate_partner_metrics,
    evaluate_partner_for_promotion,
    enforce_partner_operational_access,
    get_current_tier,
    get_default_tier,
    get_next_tier,
    promotion_requirements_met,
    validate_partner_property_limit,
    confirm_partner_violation,
    get_partner_restriction_summary,
    impose_disciplinary_action,
    report_partner_violation,
    revoke_disciplinary_action,
    start_violation_review,
    expire_disciplinary_action,
    reinstate_partner,
)

from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase


User = get_user_model()


class GovernanceMetricsTests(TestCase):
    def setUp(self):
        self.partner_user = User.objects.create_user(
            username="governance_partner",
            email="governance.partner@example.com",
            password="TestPassword123!",
            role=User.ROLE_PARTNER,
        )

        self.partner = Partner.objects.create(
            user=self.partner_user,
            business_name="Governance Test Partner",
            display_name="Governance Partner",
            partner_type=Partner.PARTNER_TYPE_AGENT,
            verification_status=Partner.STATUS_APPROVED,
            is_active=True,
        )

        self.bronze = PartnerTier.objects.create(
            code="bronze",
            name="Bronze",
            rank=1,
            property_limit=20,
            minimum_completed_deals=0,
            minimum_trust_score=Decimal("0.00"),
            active=True,
        )

        self.silver = PartnerTier.objects.create(
            code="silver",
            name="Silver",
            rank=2,
            property_limit=50,
            minimum_completed_deals=50,
            minimum_trust_score=Decimal("90.00"),
            active=True,
        )

    def test_default_tier_is_lowest_active_rank(self):
        self.assertEqual(
            get_default_tier(),
            self.bronze,
        )

    def test_partner_without_assignment_has_no_current_tier(self):
        self.assertIsNone(
            get_current_tier(self.partner),
        )

    def test_assign_default_tier_creates_bronze_assignment(self):
        assignment, created = assign_default_tier(
            partner=self.partner,
        )

        self.assertTrue(created)
        self.assertEqual(
            assignment.tier,
            self.bronze,
        )
        self.assertTrue(
            assignment.active,
        )
        self.assertEqual(
            get_current_tier(self.partner),
            self.bronze,
        )

    def test_assign_default_tier_is_idempotent(self):
        first_assignment, first_created = assign_default_tier(
            partner=self.partner,
        )

        second_assignment, second_created = assign_default_tier(
            partner=self.partner,
        )

        self.assertTrue(first_created)
        self.assertFalse(second_created)

        self.assertEqual(
            first_assignment.id,
            second_assignment.id,
        )

        self.assertEqual(
            PartnerTierAssignment.objects.filter(
                partner=self.partner,
                active=True,
            ).count(),
            1,
        )

    def test_next_tier_after_bronze_is_silver(self):
        self.assertEqual(
            get_next_tier(self.bronze),
            self.silver,
        )

    def test_metrics_return_zero_for_partner_without_deals(self):
        metrics = calculate_partner_metrics(
            self.partner,
        )

        self.assertEqual(
            metrics["completed_deals"],
            0,
        )

        self.assertEqual(
            metrics["agreed_deals"],
            0,
        )

        self.assertEqual(
            metrics["disputed_deals"],
            0,
        )

        self.assertEqual(
            metrics["owner_confirmation_rate"],
            "0.00",
        )

        self.assertEqual(
            metrics["dispute_rate"],
            "0.00",
        )

        self.assertEqual(
            metrics["trust_score"],
            "0.00",
        )

        self.assertEqual(
            metrics["trust_grade"],
            "unrated",
        )

        self.assertEqual(
            metrics["trust_confidence"],
            "0.00",
        )

    def test_silver_requirements_fail_without_completed_deals(self):
        metrics = calculate_partner_metrics(
            self.partner,
        )

        result = promotion_requirements_met(
            metrics=metrics,
            proposed_tier=self.silver,
        )

        self.assertFalse(
            result["eligible"],
        )

        self.assertFalse(
            result["completed_deals"]["passed"],
        )

        self.assertTrue(
            result["trust_score"]["available"],
        )

        self.assertFalse(
            result["trust_score"]["passed"],
        )

        self.assertEqual(
            result["trust_score"]["actual"],
            "0.00",
        )

        self.assertIn(
            "Completed deal requirement not met: 0/50.",
            result["blocking_reasons"],
        )

        self.assertIn(
            "Trust score requirement not met: 0.00/90.00.",
            result["blocking_reasons"],
        )

    def test_evaluation_assigns_bronze_and_creates_review(self):
        review = evaluate_partner_for_promotion(
            self.partner,
        )

        self.assertIsNotNone(review)

        self.assertEqual(
            get_current_tier(self.partner),
            self.bronze,
        )

        self.assertEqual(
            review.current_tier,
            self.bronze,
        )

        self.assertEqual(
            review.proposed_tier,
            self.silver,
        )

        self.assertEqual(
            review.decision,
            PartnerPromotionReview.Decision.NOT_ELIGIBLE,
        )

        self.assertEqual(
            review.completed_deals,
            0,
        )

    def test_review_preserves_metrics_snapshot(self):
        review = evaluate_partner_for_promotion(
            self.partner,
        )

        snapshot = review.metrics_snapshot

        self.assertEqual(
            snapshot["partner_id"],
            self.partner.id,
        )

        self.assertEqual(
            snapshot["current_tier"]["code"],
            "bronze",
        )

        self.assertEqual(
            snapshot["proposed_tier"]["code"],
            "silver",
        )

        self.assertEqual(
            snapshot["metrics"]["completed_deals"],
            0,
        )

        self.assertFalse(
            snapshot["requirements"]["eligible"],
        )

        self.assertEqual(
            snapshot["metrics"]["trust_score"],
            "0.00",
        )

        self.assertEqual(
            snapshot["metrics"]["trust_grade"],
            "unrated",
        )

        self.assertEqual(
            snapshot["metrics"]["trust_confidence"],
            "0.00",
        )

        self.assertIn(
            "Trust score requirement not met: 0.00/90.00.",
            snapshot["requirements"]["blocking_reasons"],
        )

class PartnerCapacityAPITests(APITestCase):
    def setUp(self):
        self.partner_user = User.objects.create_user(
            username="capacity_partner",
            email="capacity.partner@example.com",
            password="TestPassword123!",
            role=User.ROLE_PARTNER,
        )

        self.partner = Partner.objects.create(
            user=self.partner_user,
            business_name="Capacity Test Partner",
            display_name="Capacity Partner",
            partner_type=Partner.PARTNER_TYPE_AGENT,
            verification_status=Partner.STATUS_APPROVED,
            is_active=True,
        )

        self.customer = User.objects.create_user(
            username="capacity_customer",
            email="capacity.customer@example.com",
            password="TestPassword123!",
            role=User.ROLE_CUSTOMER,
        )

        self.staff_user = User.objects.create_user(
            username="capacity_staff",
            email="capacity.staff@example.com",
            password="TestPassword123!",
            role=User.ROLE_ADMIN,
            is_staff=True,
        )

        self.bronze = PartnerTier.objects.create(
            code="bronze",
            name="Bronze",
            rank=1,
            property_limit=20,
            minimum_completed_deals=0,
            minimum_trust_score=Decimal("0.00"),
            active=True,
        )

        self.url = reverse(
            "governance-my-capacity",
        )

    def make_property(
        self,
        *,
        number,
        status_value=Property.STATUS_DRAFT,
    ):
        property_obj = Property.objects.create(
            partner=self.partner,
            title=f"Capacity Property {number}",
            property_type=Property.TYPE_APARTMENT,
            listing_type=Property.LISTING_RENT,
            price=Decimal("25000.00"),
            county="Nairobi",
            town="Roysambu",
            estate="Roysambu",
            address=f"Capacity Address {number}",
            bedrooms=1,
            bathrooms=1,
            description="Capacity API test property.",
            status=Property.STATUS_DRAFT,
        )

        if status_value != Property.STATUS_DRAFT:
            Property.objects.filter(
                pk=property_obj.pk,
            ).update(
                status=status_value,
            )

            property_obj.refresh_from_db()

        return property_obj

    def test_unauthenticated_user_cannot_view_capacity(self):
        response = self.client.get(
            self.url,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_customer_cannot_view_partner_capacity(self):
        self.client.force_authenticate(
            user=self.customer,
        )

        response = self.client.get(
            self.url,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_staff_cannot_view_personal_partner_capacity(self):
        self.client.force_authenticate(
            user=self.staff_user,
        )

        response = self.client.get(
            self.url,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_partner_without_tier_is_assigned_bronze(self):
        self.client.force_authenticate(
            user=self.partner_user,
        )

        response = self.client.get(
            self.url,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["tier"]["code"],
            "bronze",
        )

        self.assertEqual(
            response.data["property_capacity"][
                "property_limit"
            ],
            20,
        )

        self.assertEqual(
            PartnerTierAssignment.objects.filter(
                partner=self.partner,
                active=True,
                tier=self.bronze,
            ).count(),
            1,
        )

    def test_capacity_reports_published_properties(self):
        for number in range(1, 8):
            self.make_property(
                number=number,
                status_value=Property.STATUS_PUBLISHED,
            )

        for number in range(8, 11):
            self.make_property(
                number=number,
                status_value=Property.STATUS_DRAFT,
            )

        self.client.force_authenticate(
            user=self.partner_user,
        )

        response = self.client.get(
            self.url,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        capacity = response.data[
            "property_capacity"
        ]

        self.assertEqual(
            capacity["published_properties"],
            7,
        )

        self.assertEqual(
            capacity["remaining_property_slots"],
            13,
        )

        self.assertFalse(
            capacity["limit_reached"],
        )

        self.assertEqual(
            capacity["usage_percentage"],
            35.0,
        )

    def test_capacity_reports_limit_reached(self):
        for number in range(1, 21):
            self.make_property(
                number=number,
                status_value=Property.STATUS_PUBLISHED,
            )

        self.client.force_authenticate(
            user=self.partner_user,
        )

        response = self.client.get(
            self.url,
        )

        capacity = response.data[
            "property_capacity"
        ]

        self.assertEqual(
            capacity["published_properties"],
            20,
        )

        self.assertEqual(
            capacity["remaining_property_slots"],
            0,
        )

        self.assertTrue(
            capacity["limit_reached"],
        )

        self.assertEqual(
            capacity["usage_percentage"],
            100.0,
        )

    def test_inactive_partner_cannot_view_capacity(self):
        self.partner.is_active = False
        self.partner.save(
            update_fields=[
                "is_active",
            ]
        )

        self.client.force_authenticate(
            user=self.partner_user,
        )

        response = self.client.get(
            self.url,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_unapproved_partner_cannot_view_capacity(self):
        self.partner.verification_status = (
            Partner.STATUS_PENDING
        )

        self.partner.save(
            update_fields=[
                "verification_status",
            ]
        )

        self.client.force_authenticate(
            user=self.partner_user,
        )

        response = self.client.get(
            self.url,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

class PartnerPropertyLimitTests(TestCase):
    def setUp(self):
        self.partner_user = User.objects.create_user(
            username="listing_limit_partner",
            email="listing.limit@example.com",
            password="TestPassword123!",
            role=User.ROLE_PARTNER,
        )

        self.partner = Partner.objects.create(
            user=self.partner_user,
            business_name="Listing Limit Partner",
            display_name="Listing Limit Partner",
            partner_type=Partner.PARTNER_TYPE_AGENT,
            verification_status=Partner.STATUS_APPROVED,
            is_active=True,
        )

        self.bronze = PartnerTier.objects.create(
            code="bronze",
            name="Bronze",
            rank=1,
            property_limit=20,
            minimum_completed_deals=0,
            minimum_trust_score=Decimal("0.00"),
            active=True,
        )

        self.silver = PartnerTier.objects.create(
            code="silver",
            name="Silver",
            rank=2,
            property_limit=50,
            minimum_completed_deals=50,
            minimum_trust_score=Decimal("90.00"),
            active=True,
        )

        PartnerTierAssignment.objects.create(
            partner=self.partner,
            tier=self.bronze,
            reason="Test Bronze assignment.",
            active=True,
        )

    def make_property(
        self,
        *,
        number,
        status=Property.STATUS_DRAFT,
        partner=None,
    ):
        return Property.objects.create(
            partner=partner or self.partner,
            title=f"Governance Property {number}",
            property_type=Property.TYPE_APARTMENT,
            listing_type=Property.LISTING_RENT,
            price=Decimal("25000.00"),
            county="Nairobi",
            town="Roysambu",
            estate="Roysambu",
            address=f"Test Address {number}",
            bedrooms=1,
            bathrooms=1,
            description="Property limit governance test.",
            status=status,
        )

    def publish_without_mandate_validation(
        self,
        property_obj,
    ):
        """
        Test only the governance property-limit service.

        Mandate publication rules are already protected by their
        own tests, so these records are moved to published using
        QuerySet.update().
        """

        Property.objects.filter(
            pk=property_obj.pk,
        ).update(
            status=Property.STATUS_PUBLISHED,
        )

        property_obj.refresh_from_db()

        return property_obj

        def test_bronze_partner_can_publish_when_nineteen_slots_are_used(self):
            for number in range(1, 20):
                property_obj = self.make_property(
                    number=number,
                )

                self.publish_without_mandate_validation(
                    property_obj,
                )

            result = validate_partner_property_limit(
                self.make_property(
                    number=20,
                ),
            )

            self.assertEqual(
                result["published_count"],
                19,
            )

            self.assertEqual(
                result["property_limit"],
                20,
            )

            self.assertEqual(
                result["remaining_slots"],
                1,
            )

    def test_bronze_partner_cannot_publish_property_twenty_one(self):
        for number in range(1, 21):
            property_obj = self.make_property(
                number=number,
            )

            self.publish_without_mandate_validation(
                property_obj,
            )

        property_twenty_one = self.make_property(
            number=21,
        )

        with self.assertRaises(ValidationError) as context:
            validate_partner_property_limit(
                property_twenty_one,
            )

        self.assertIn(
            "status",
            context.exception.message_dict,
        )

        self.assertIn(
            "Bronze partners may publish up to 20",
            context.exception.message_dict["status"][0],
        )

    def test_silver_partner_can_publish_beyond_twenty(self):
        PartnerTierAssignment.objects.filter(
            partner=self.partner,
            active=True,
        ).update(
            active=False,
        )

        PartnerTierAssignment.objects.create(
            partner=self.partner,
            tier=self.silver,
            reason="Test Silver assignment.",
            active=True,
        )

        for number in range(1, 26):
            property_obj = self.make_property(
                number=number,
            )

            self.publish_without_mandate_validation(
                property_obj,
            )

        result = validate_partner_property_limit(
            self.make_property(
                number=26,
            ),
        )

        self.assertEqual(
            result["published_count"],
            25,
        )

        self.assertEqual(
            result["property_limit"],
            50,
        )

        self.assertEqual(
            result["remaining_slots"],
            25,
        )

    def test_draft_properties_do_not_count_toward_limit(self):
        for number in range(1, 31):
            self.make_property(
                number=number,
                status=Property.STATUS_DRAFT,
            )

        result = validate_partner_property_limit(
            self.make_property(
                number=31,
            ),
        )

        self.assertEqual(
            result["published_count"],
            0,
        )

        self.assertEqual(
            result["remaining_slots"],
            20,
        )

    def test_non_published_property_statuses_do_not_count(self):
        statuses = [
            Property.STATUS_DRAFT,
            Property.STATUS_PENDING,
            Property.STATUS_RESERVED,
            Property.STATUS_RENTED,
            Property.STATUS_SOLD,
            Property.STATUS_ARCHIVED,
        ]

        for number, property_status in enumerate(
            statuses,
            start=1,
        ):
            self.make_property(
                number=number,
                status=property_status,
            )

        result = validate_partner_property_limit(
            self.make_property(
                number=100,
            ),
        )

        self.assertEqual(
            result["published_count"],
            0,
        )

    def test_inactive_partner_cannot_publish(self):
        self.partner.is_active = False
        self.partner.save(
            update_fields=[
                "is_active",
            ]
        )

        property_obj = self.make_property(
            number=1,
        )

        with self.assertRaises(ValidationError) as context:
            validate_partner_property_limit(
                property_obj,
            )

        self.assertIn(
            "partner",
            context.exception.message_dict,
        )

        self.assertIn(
            "inactive",
            context.exception.message_dict["partner"][0],
        )

    def test_unapproved_partner_cannot_publish(self):
        self.partner.verification_status = (
            Partner.STATUS_PENDING
        )

        self.partner.save(
            update_fields=[
                "verification_status",
            ]
        )

        property_obj = self.make_property(
            number=1,
        )

        with self.assertRaises(ValidationError) as context:
            validate_partner_property_limit(
                property_obj,
            )

        self.assertIn(
            "partner",
            context.exception.message_dict,
        )

        self.assertIn(
            "approved",
            context.exception.message_dict["partner"][0],
        )

    def test_partner_without_tier_is_assigned_bronze(self):
        PartnerTierAssignment.objects.filter(
            partner=self.partner,
        ).delete()

        property_obj = self.make_property(
            number=1,
        )

        result = validate_partner_property_limit(
            property_obj,
        )

        assignment = (
            PartnerTierAssignment.objects
            .select_related("tier")
            .get(
                partner=self.partner,
                active=True,
            )
        )

        self.assertEqual(
            assignment.tier,
            self.bronze,
        )

        self.assertEqual(
            result["tier"],
            {
                "id": self.bronze.id,
                "code": self.bronze.code,
                "name": self.bronze.name,
                "rank": self.bronze.rank,
            },
        )

        self.assertEqual(
            result["property_limit"],
            20,
        )

    def test_editing_existing_published_property_does_not_add_slot(self):
        published_property = self.make_property(
            number=1,
        )

        self.publish_without_mandate_validation(
            published_property,
        )

        for number in range(2, 21):
            property_obj = self.make_property(
                number=number,
            )

            self.publish_without_mandate_validation(
                property_obj,
            )

        result = validate_partner_property_limit(
            published_property,
        )

        self.assertEqual(
            result["published_count"],
            19,
        )

        self.assertEqual(
            result["remaining_slots"],
            1,
        )

class PartnerDisciplinaryActionTests(TestCase):
    def setUp(self):
        self.partner_user = User.objects.create_user(
            username="discipline_partner",
            email="discipline.partner@example.com",
            password="TestPassword123!",
            role=User.ROLE_PARTNER,
        )

        self.partner = Partner.objects.create(
            user=self.partner_user,
            business_name="Discipline Test Partner",
            display_name="Discipline Partner",
            partner_type=Partner.PARTNER_TYPE_AGENT,
            verification_status=Partner.STATUS_APPROVED,
            is_active=True,
        )

        self.staff_user = User.objects.create_user(
            username="discipline_staff",
            email="discipline.staff@example.com",
            password="TestPassword123!",
            role=User.ROLE_ADMIN,
            is_staff=True,
        )

        self.non_staff_user = User.objects.create_user(
            username="discipline_non_staff",
            email="discipline.nonstaff@example.com",
            password="TestPassword123!",
            role=User.ROLE_CUSTOMER,
        )

        self.policy = PolicyRule.objects.create(
            code="TEST-POL-006",
            title="Outside-platform transaction",
            description="Test gross-misconduct policy.",
            severity=PolicyRule.Severity.GROSS_MISCONDUCT,
            recommended_action=(
                PolicyRule.RecommendedAction.PERMANENT_BAN
            ),
            effective_from=date.today(),
            active=True,
        )

        self.violation = report_partner_violation(
            partner=self.partner,
            policy=self.policy,
            summary=(
                "Partner allegedly completed a protected "
                "transaction outside the platform."
            ),
            evidence_snapshot={
                "deal_id": 100,
                "pic_number": "PIC-TEST-001",
            },
            reported_by=self.staff_user,
        )

        start_violation_review(
            violation=self.violation,
            reviewer=self.staff_user,
        )

        confirm_partner_violation(
            violation=self.violation,
            reviewer=self.staff_user,
            decision_notes=(
                "The transaction evidence confirms "
                "circumvention."
            ),
        )

    def test_unconfirmed_violation_cannot_receive_action(self):
        reported_violation = report_partner_violation(
            partner=self.partner,
            policy=self.policy,
            summary="Unreviewed allegation.",
            reported_by=self.staff_user,
        )

        with self.assertRaises(ValidationError):
            impose_disciplinary_action(
                violation=reported_violation,
                action_type=(
                    PartnerDisciplinaryAction
                    .ActionType
                    .PERMANENT_BAN
                ),
                imposed_by=self.staff_user,
                reason="Should not be allowed.",
            )

    def test_non_staff_cannot_impose_action(self):
        with self.assertRaises(ValidationError):
            impose_disciplinary_action(
                violation=self.violation,
                action_type=(
                    PartnerDisciplinaryAction
                    .ActionType
                    .PERMANENT_BAN
                ),
                imposed_by=self.non_staff_user,
                reason="Unauthorized decision.",
            )

    def test_permanent_ban_deactivates_partner(self):
        action = impose_disciplinary_action(
            violation=self.violation,
            action_type=(
                PartnerDisciplinaryAction
                .ActionType
                .PERMANENT_BAN
            ),
            imposed_by=self.staff_user,
            reason=(
                "Confirmed outside-platform transaction."
            ),
        )

        self.partner.refresh_from_db()

        self.assertEqual(
            action.status,
            PartnerDisciplinaryAction.Status.ACTIVE,
        )

        self.assertTrue(
            action.is_permanent,
        )

        self.assertIsNone(
            action.ends_at,
        )

        self.assertFalse(
            self.partner.is_active,
        )

    def test_temporary_suspension_requires_duration(self):
        short_policy = PolicyRule.objects.create(
            code="TEST-POL-005",
            title="Viewing obligation",
            description="Test moderate policy.",
            severity=PolicyRule.Severity.MODERATE,
            recommended_action=(
                PolicyRule.RecommendedAction.SHORT_SUSPENSION
            ),
            effective_from=date.today(),
            active=True,
        )

        violation = report_partner_violation(
            partner=self.partner,
            policy=short_policy,
            summary="Missed confirmed viewing.",
            reported_by=self.staff_user,
        )

        start_violation_review(
            violation=violation,
            reviewer=self.staff_user,
        )

        confirm_partner_violation(
            violation=violation,
            reviewer=self.staff_user,
            decision_notes="Evidence confirmed.",
        )

        with self.assertRaises(ValidationError):
            impose_disciplinary_action(
                violation=violation,
                action_type=(
                    PartnerDisciplinaryAction
                    .ActionType
                    .SHORT_SUSPENSION
                ),
                imposed_by=self.staff_user,
                reason="Seven-day suspension.",
            )

    def test_temporary_suspension_sets_end_date(self):
        short_policy = PolicyRule.objects.create(
            code="TEST-POL-004",
            title="Professional conduct",
            description="Test moderate policy.",
            severity=PolicyRule.Severity.MODERATE,
            recommended_action=(
                PolicyRule.RecommendedAction.SHORT_SUSPENSION
            ),
            effective_from=date.today(),
            active=True,
        )

        violation = report_partner_violation(
            partner=self.partner,
            policy=short_policy,
            summary="Confirmed misconduct.",
            reported_by=self.staff_user,
        )

        start_violation_review(
            violation=violation,
            reviewer=self.staff_user,
        )

        confirm_partner_violation(
            violation=violation,
            reviewer=self.staff_user,
            decision_notes="Evidence confirmed.",
        )

        action = impose_disciplinary_action(
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

        self.assertIsNotNone(
            action.ends_at,
        )

        self.assertGreater(
            action.ends_at,
            action.starts_at,
        )

    def test_different_action_requires_override_reason(self):
        with self.assertRaises(ValidationError):
            impose_disciplinary_action(
                violation=self.violation,
                action_type=(
                    PartnerDisciplinaryAction
                    .ActionType
                    .LONG_SUSPENSION
                ),
                imposed_by=self.staff_user,
                reason="Different action.",
                duration_days=30,
            )

    def test_restriction_summary_reports_permanent_ban(self):
        action = impose_disciplinary_action(
            violation=self.violation,
            action_type=(
                PartnerDisciplinaryAction
                .ActionType
                .PERMANENT_BAN
            ),
            imposed_by=self.staff_user,
            reason="Confirmed gross misconduct.",
        )

        summary = get_partner_restriction_summary(
            self.partner,
        )

        self.assertTrue(
            summary["restricted"],
        )

        self.assertTrue(
            summary["permanently_banned"],
        )

        self.assertEqual(
            summary["active_restrictive_action_count"],
            1,
        )

        self.assertEqual(
            summary["actions"][0]["id"],
            action.id,
        )

    def test_staff_can_revoke_active_action(self):
        action = impose_disciplinary_action(
            violation=self.violation,
            action_type=(
                PartnerDisciplinaryAction
                .ActionType
                .PERMANENT_BAN
            ),
            imposed_by=self.staff_user,
            reason="Confirmed gross misconduct.",
        )

        revoked_action = revoke_disciplinary_action(
            action=action,
            revoked_by=self.staff_user,
            reason="Decision overturned after review.",
        )

        self.assertEqual(
            revoked_action.status,
            PartnerDisciplinaryAction.Status.REVOKED,
        )

        self.assertIsNotNone(
            revoked_action.revoked_at,
        )

class PartnerOperationalAccessTests(TestCase):
    def setUp(self):
        self.partner_user = User.objects.create_user(
            username="operational_partner",
            email="operational.partner@example.com",
            password="TestPassword123!",
            role=User.ROLE_PARTNER,
        )

        self.partner = Partner.objects.create(
            user=self.partner_user,
            business_name="Operational Partner",
            display_name="Operational Partner",
            partner_type=Partner.PARTNER_TYPE_AGENT,
            verification_status=Partner.STATUS_APPROVED,
            is_active=True,
        )

        self.staff_user = User.objects.create_user(
            username="operational_staff",
            email="operational.staff@example.com",
            password="TestPassword123!",
            role=User.ROLE_ADMIN,
            is_staff=True,
        )

        self.policy = PolicyRule.objects.create(
            code="TEST-OPS-001",
            title="Operational restriction test",
            description="Policy used to test central enforcement.",
            severity=PolicyRule.Severity.SERIOUS,
            recommended_action=(
                PolicyRule
                .RecommendedAction
                .LONG_SUSPENSION
            ),
            effective_from=date.today(),
            active=True,
        )

    def create_confirmed_violation(self):
        violation = report_partner_violation(
            partner=self.partner,
            policy=self.policy,
            summary="Confirmed operational violation.",
            reported_by=self.staff_user,
        )

        start_violation_review(
            violation=violation,
            reviewer=self.staff_user,
        )

        confirm_partner_violation(
            violation=violation,
            reviewer=self.staff_user,
            decision_notes="Evidence confirmed.",
        )

        return violation

    def test_approved_active_partner_is_allowed(self):
        result = enforce_partner_operational_access(
            self.partner,
            operation="publish_property",
        )

        self.assertTrue(
            result["allowed"],
        )

        self.assertEqual(
            result["operation"],
            "publish_property",
        )

    def test_unapproved_partner_is_blocked(self):
        self.partner.verification_status = (
            Partner.STATUS_PENDING
        )

        self.partner.save(
            update_fields=[
                "verification_status",
            ]
        )

        with self.assertRaises(ValidationError):
            enforce_partner_operational_access(
                self.partner,
                operation="publish_property",
            )

    def test_inactive_partner_without_action_is_blocked(self):
        self.partner.is_active = False

        self.partner.save(
            update_fields=[
                "is_active",
            ]
        )

        with self.assertRaises(ValidationError):
            enforce_partner_operational_access(
                self.partner,
                operation="view_partner_capacity",
            )

    def test_suspended_partner_is_blocked(self):
        violation = self.create_confirmed_violation()

        impose_disciplinary_action(
            violation=violation,
            action_type=(
                PartnerDisciplinaryAction
                .ActionType
                .LONG_SUSPENSION
            ),
            imposed_by=self.staff_user,
            reason="Thirty-day suspension.",
            duration_days=30,
        )

        self.partner.refresh_from_db()

        with self.assertRaises(ValidationError) as context:
            enforce_partner_operational_access(
                self.partner,
                operation="issue_owner_confirmation",
            )

        self.assertIn(
            "suspended",
            str(context.exception).lower(),
        )

    def test_permanently_banned_partner_is_blocked(self):
        gross_policy = PolicyRule.objects.create(
            code="TEST-OPS-006",
            title="Outside-platform transaction",
            description="Gross misconduct test.",
            severity=(
                PolicyRule.Severity.GROSS_MISCONDUCT
            ),
            recommended_action=(
                PolicyRule
                .RecommendedAction
                .PERMANENT_BAN
            ),
            effective_from=date.today(),
            active=True,
        )

        violation = report_partner_violation(
            partner=self.partner,
            policy=gross_policy,
            summary="Confirmed outside-platform transaction.",
            reported_by=self.staff_user,
        )

        start_violation_review(
            violation=violation,
            reviewer=self.staff_user,
        )

        confirm_partner_violation(
            violation=violation,
            reviewer=self.staff_user,
            decision_notes="Gross misconduct confirmed.",
        )

        impose_disciplinary_action(
            violation=violation,
            action_type=(
                PartnerDisciplinaryAction
                .ActionType
                .PERMANENT_BAN
            ),
            imposed_by=self.staff_user,
            reason="Permanent expulsion.",
        )

        self.partner.refresh_from_db()

        with self.assertRaises(ValidationError) as context:
            enforce_partner_operational_access(
                self.partner,
                operation="publish_property",
            )

        self.assertIn(
            "permanently banned",
            str(context.exception).lower(),
        )

    def test_restrictive_action_blocks_even_if_partner_flag_is_wrong(self):
        violation = self.create_confirmed_violation()

        impose_disciplinary_action(
            violation=violation,
            action_type=(
                PartnerDisciplinaryAction
                .ActionType
                .LONG_SUSPENSION
            ),
            imposed_by=self.staff_user,
            reason="Thirty-day suspension.",
            duration_days=30,
        )

        # Simulate inconsistent legacy or manually altered data.
        Partner.objects.filter(
            pk=self.partner.pk,
        ).update(
            is_active=True,
        )

        self.partner.refresh_from_db()

        self.assertTrue(
            self.partner.is_active,
        )

        with self.assertRaises(ValidationError):
            enforce_partner_operational_access(
                self.partner,
                operation="publish_property",
            )

class PartnerReinstatementTests(TestCase):
    def setUp(self):
        self.partner_user = User.objects.create_user(
            username="reinstatement_partner",
            email="reinstatement.partner@example.com",
            password="TestPassword123!",
            role=User.ROLE_PARTNER,
        )

        self.partner = Partner.objects.create(
            user=self.partner_user,
            business_name="Reinstatement Test Partner",
            display_name="Reinstatement Partner",
            partner_type=Partner.PARTNER_TYPE_AGENT,
            verification_status=Partner.STATUS_APPROVED,
            is_active=True,
        )

        self.staff_user = User.objects.create_user(
            username="reinstatement_staff",
            email="reinstatement.staff@example.com",
            password="TestPassword123!",
            role=User.ROLE_ADMIN,
            is_staff=True,
        )

        self.non_staff_user = User.objects.create_user(
            username="reinstatement_customer",
            email="reinstatement.customer@example.com",
            password="TestPassword123!",
            role=User.ROLE_CUSTOMER,
        )

        self.policy = PolicyRule.objects.create(
            code="TEST-REINSTATE-001",
            title="Temporary suspension policy",
            description="Policy used for reinstatement tests.",
            severity=PolicyRule.Severity.SERIOUS,
            recommended_action=(
                PolicyRule
                .RecommendedAction
                .LONG_SUSPENSION
            ),
            effective_from=date.today(),
            active=True,
        )

    def create_confirmed_violation(self):
        violation = report_partner_violation(
            partner=self.partner,
            policy=self.policy,
            summary="Confirmed temporary suspension violation.",
            reported_by=self.staff_user,
        )

        start_violation_review(
            violation=violation,
            reviewer=self.staff_user,
        )

        confirm_partner_violation(
            violation=violation,
            reviewer=self.staff_user,
            decision_notes="Evidence confirmed.",
        )

        return violation

    def create_expired_suspension(self):
        violation = self.create_confirmed_violation()

        action = impose_disciplinary_action(
            violation=violation,
            action_type=(
                PartnerDisciplinaryAction
                .ActionType
                .LONG_SUSPENSION
            ),
            imposed_by=self.staff_user,
            reason="Temporary suspension.",
            duration_days=30,
        )

        PartnerDisciplinaryAction.objects.filter(
            pk=action.pk,
        ).update(
            ends_at=timezone.now() - timedelta(days=1),
        )

        action.refresh_from_db()

        return action

    def test_expired_suspension_does_not_reactivate_partner(self):
        action = self.create_expired_suspension()

        expired_action = expire_disciplinary_action(
            action=action,
        )

        self.partner.refresh_from_db()

        self.assertEqual(
            expired_action.status,
            PartnerDisciplinaryAction.Status.EXPIRED,
        )

        self.assertFalse(
            self.partner.is_active,
        )

    def test_partner_cannot_be_reinstated_with_active_suspension(self):
        violation = self.create_confirmed_violation()

        impose_disciplinary_action(
            violation=violation,
            action_type=(
                PartnerDisciplinaryAction
                .ActionType
                .LONG_SUSPENSION
            ),
            imposed_by=self.staff_user,
            reason="Active suspension.",
            duration_days=30,
        )

        with self.assertRaises(ValidationError):
            reinstate_partner(
                partner=self.partner,
                approved_by=self.staff_user,
                reason="Attempted early reinstatement.",
            )

    def test_non_staff_cannot_reinstate_partner(self):
        action = self.create_expired_suspension()

        expire_disciplinary_action(
            action=action,
        )

        with self.assertRaises(ValidationError):
            reinstate_partner(
                partner=self.partner,
                approved_by=self.non_staff_user,
                reason="Unauthorized reinstatement.",
            )

    def test_staff_can_reinstate_after_restrictions_resolved(self):
        action = self.create_expired_suspension()

        expire_disciplinary_action(
            action=action,
        )

        reinstatement = reinstate_partner(
            partner=self.partner,
            approved_by=self.staff_user,
            reason=(
                "Suspension completed and compliance review passed."
            ),
        )

        self.partner.refresh_from_db()

        self.assertTrue(
            self.partner.is_active,
        )

        self.assertEqual(
            reinstatement.partner,
            self.partner,
        )

        self.assertEqual(
            reinstatement.approved_by,
            self.staff_user,
        )

        self.assertEqual(
            list(
                reinstatement.reviewed_actions.values_list(
                    "id",
                    flat=True,
                )
            ),
            [
                action.id,
            ],
        )

    def test_reinstatement_preserves_decision_snapshot(self):
        action = self.create_expired_suspension()

        expire_disciplinary_action(
            action=action,
        )

        reinstatement = reinstate_partner(
            partner=self.partner,
            approved_by=self.staff_user,
            reason="Compliance review completed.",
        )

        snapshot = reinstatement.evidence_snapshot

        self.assertEqual(
            snapshot["partner_id"],
            self.partner.id,
        )

        self.assertIn(
            action.id,
            snapshot["reviewed_action_ids"],
        )

        self.assertEqual(
            snapshot["approved_by_id"],
            self.staff_user.id,
        )