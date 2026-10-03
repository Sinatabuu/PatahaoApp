"""Gunicorn configuration for Pata HAO staging and production."""

import os


def _positive_int(name, default):
    raw_value = os.environ.get(name, str(default)).strip()

    try:
        value = int(raw_value)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(f"{name} must be an integer.") from exc

    if value <= 0:
        raise RuntimeError(f"{name} must be greater than zero.")

    return value


bind = os.environ.get(
    "GUNICORN_BIND",
    "127.0.0.1:8000",
).strip()

workers = _positive_int("GUNICORN_WORKERS", 2)
threads = _positive_int("GUNICORN_THREADS", 2)
worker_class = "gthread"

# Video inspection and thumbnail generation can legitimately take 45 seconds.
# Keep the application timeout above both that limit and the proxy timeout.
timeout = _positive_int("GUNICORN_TIMEOUT_SECONDS", 120)
graceful_timeout = _positive_int(
    "GUNICORN_GRACEFUL_TIMEOUT_SECONDS",
    30,
)
keepalive = _positive_int("GUNICORN_KEEPALIVE_SECONDS", 5)

# Periodically recycle workers to limit the impact of gradual memory growth.
max_requests = _positive_int("GUNICORN_MAX_REQUESTS", 1000)
max_requests_jitter = _positive_int(
    "GUNICORN_MAX_REQUESTS_JITTER",
    100,
)

accesslog = "-"
errorlog = "-"
capture_output = True
loglevel = os.environ.get(
    "GUNICORN_LOG_LEVEL",
    os.environ.get("DJANGO_LOG_LEVEL", "INFO"),
).strip().lower()

# Only the local reverse proxy may assert the original HTTPS scheme.
forwarded_allow_ips = os.environ.get(
    "GUNICORN_FORWARDED_ALLOW_IPS",
    "127.0.0.1",
).strip()

preload_app = False
