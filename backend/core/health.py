"""Unauthenticated health probes for the hosting platform."""

import logging

from django.db import connections
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_safe


logger = logging.getLogger(__name__)


def _response(payload, *, status=200):
    response = JsonResponse(payload, status=status)
    response["Cache-Control"] = "no-store"
    return response


@never_cache
@require_safe
def liveness(request):
    """Confirm that the web process can receive and answer requests."""
    return _response({"status": "ok", "service": "patahao-api"})


@never_cache
@require_safe
def readiness(request):
    """Confirm that the process can serve requests that require the database."""
    try:
        with connections["default"].cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        logger.exception("Database readiness check failed.")
        return _response(
            {
                "status": "unavailable",
                "checks": {"database": "failed"},
            },
            status=503,
        )

    return _response(
        {
            "status": "ready",
            "checks": {"database": "ok"},
        }
    )
