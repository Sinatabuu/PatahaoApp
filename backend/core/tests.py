from unittest.mock import patch

from django.db import OperationalError
from django.test import TestCase
from django.urls import reverse


class HealthEndpointTests(TestCase):
    def test_liveness_does_not_require_authentication(self):
        response = self.client.get(reverse("health-live"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"status": "ok", "service": "patahao-api"},
        )
        self.assertIn("no-store", response["Cache-Control"])

    def test_readiness_confirms_database_connection(self):
        response = self.client.get(reverse("health-ready"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "status": "ready",
                "checks": {"database": "ok"},
            },
        )

    @patch("core.health.connections")
    def test_readiness_returns_503_without_leaking_database_error(
        self,
        mock_connections,
    ):
        mock_connections.__getitem__.return_value.cursor.side_effect = (
            OperationalError("secret database details")
        )

        response = self.client.get(reverse("health-ready"))

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json(),
            {
                "status": "unavailable",
                "checks": {"database": "failed"},
            },
        )
        self.assertNotContains(
            response,
            "secret database details",
            status_code=503,
        )
