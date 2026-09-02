from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone


class OwnerConfirmationPageTests(TestCase):
    raw_token = "development-owner-token"

    def _token_record(self):
        property_obj = SimpleNamespace(
            title="Kwetu view",
            listing_type="sale",
        )

        deal = SimpleNamespace(
            id=2,
            deal_number="PH-DEAL-2026-E070F7AC8569",
            deal_type="sale",
            property=property_obj,
        )

        owner = SimpleNamespace(
            owner_number="PH-OWNER-TEST",
            legal_name="Kwetu View Test Owner",
        )

        return SimpleNamespace(
            id=10,
            is_usable=True,
            deal=deal,
            owner=owner,
            expires_at=(
                timezone.now()
                + timedelta(hours=48)
            ),
        )

    def _url(self):
        return reverse(
            "owner-confirmation-page",
            kwargs={
                "token": self.raw_token,
            },
        )

    def test_owner_can_open_confirmation_page_without_login(self):
        with patch(
            "deals.public_views._get_token_record",
            return_value=self._token_record(),
        ):
            response = self.client.get(
                self._url(),
            )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            "Kwetu view",
        )

        self.assertContains(
            response,
            "Kwetu View Test Owner",
        )

        self.assertContains(
            response,
            "Customer bought property",
        )

        self.assertNotContains(
            response,
            self.raw_token,
        )

        self.assertEqual(
            response.headers["Cache-Control"],
            "max-age=0, no-cache, no-store, must-revalidate, private",
        )

        self.assertEqual(
            response.headers["Referrer-Policy"],
            "no-referrer",
        )

        self.assertEqual(
            response.headers["X-Robots-Tag"],
            "noindex, nofollow",
        )

    def test_owner_can_submit_confirmation_from_page(self):
        submitted_outcome = SimpleNamespace(
            outcome="purchased",
        )

        evaluated_deal = SimpleNamespace(
            deal_number="PH-DEAL-2026-E070F7AC8569",
            status="agreed",
        )

        with patch(
            "deals.public_views._get_token_record",
            return_value=self._token_record(),
        ):
            with patch(
                "deals.public_views.submit_owner_outcome",
                return_value=(
                    submitted_outcome,
                    evaluated_deal,
                ),
            ) as submit:
                response = self.client.post(
                    self._url(),
                    {
                        "outcome": "purchased",
                        "notes": (
                            "Owner confirms the development "
                            "sale-flow smoke test."
                        ),
                    },
                )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            "Confirmation recorded",
        )

        self.assertContains(
            response,
            "Terms agreed",
        )

        submit.assert_called_once_with(
            raw_token=self.raw_token,
            outcome="purchased",
            notes=(
                "Owner confirms the development "
                "sale-flow smoke test."
            ),
        )

    def test_invalid_or_expired_token_is_rejected_generically(self):
        with patch(
            "deals.public_views._get_token_record",
            return_value=None,
        ):
            response = self.client.get(
                self._url(),
            )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertContains(
            response,
            "This confirmation link is invalid or no longer usable.",
            status_code=400,
        )
