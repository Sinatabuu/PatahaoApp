"""Environment parsing helpers for Django settings."""

import os
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from django.core.exceptions import ImproperlyConfigured


ENVIRONMENT_VARIABLE = "PATAHAO_ENVIRONMENT"
SUPPORTED_ENVIRONMENTS = {
    "development",
    "staging",
    "production",
}


def env_bool(name, default=False, environ=None):
    """Read a conventional boolean environment variable."""
    source = environ if environ is not None else os.environ
    raw_value = source.get(name)

    if raw_value is None or not str(raw_value).strip():
        return default

    normalized = str(raw_value).strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False

    raise ImproperlyConfigured(
        f"{name} must be one of true/false, yes/no, on/off, or 1/0."
    )


def env_int(name, default, environ=None):
    """Read an integer environment variable with a useful error."""
    source = environ if environ is not None else os.environ
    raw_value = source.get(name)

    if raw_value is None or not str(raw_value).strip():
        return default

    try:
        return int(raw_value)
    except (TypeError, ValueError) as exc:
        raise ImproperlyConfigured(f"{name} must be an integer.") from exc


def env_list(name, default=(), environ=None):
    """Read a comma-separated environment variable."""
    source = environ if environ is not None else os.environ
    raw_value = source.get(name)

    if raw_value is None:
        return list(default)

    return [
        item.strip()
        for item in str(raw_value).split(",")
        if item.strip()
    ]


def get_environment(environ=None):
    source = environ if environ is not None else os.environ
    environment = source.get(
        ENVIRONMENT_VARIABLE,
        "development",
    ).strip().lower()

    if environment not in SUPPORTED_ENVIRONMENTS:
        choices = ", ".join(sorted(SUPPORTED_ENVIRONMENTS))
        raise ImproperlyConfigured(
            f"{ENVIRONMENT_VARIABLE} must be one of: {choices}."
        )

    return environment


def get_secret_key(environment, environ=None):
    source = environ if environ is not None else os.environ
    secret_key = source.get("DJANGO_SECRET_KEY", "").strip()

    if secret_key:
        return secret_key

    if environment == "development":
        return (
            "django-insecure-development-only-patahao-key-"
            "never-use-this-in-a-deployed-environment"
        )

    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY is required in staging and production."
    )


def get_allowed_hosts(environment, environ=None):
    development_hosts = (
        "localhost",
        "127.0.0.1",
        "10.0.0.175",
        "0.0.0.0",
        ".trycloudflare.com",
        "patahao-api.roysafi.com",
    )
    hosts = env_list(
        "DJANGO_ALLOWED_HOSTS",
        default=(development_hosts if environment == "development" else ()),
        environ=environ,
    )

    if environment != "development" and not hosts:
        raise ImproperlyConfigured(
            "DJANGO_ALLOWED_HOSTS is required in staging and production."
        )

    return hosts


def get_database_config(environment, base_dir, environ=None):
    """Build Django's default database config without an extra dependency."""
    source = environ if environ is not None else os.environ
    database_url = source.get("DATABASE_URL", "").strip()

    if not database_url:
        if environment != "development":
            raise ImproperlyConfigured(
                "DATABASE_URL is required in staging and production."
            )

        return {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": Path(base_dir) / "db.sqlite3",
        }

    parsed = urlparse(database_url)
    scheme = parsed.scheme.lower()

    if scheme in {"postgres", "postgresql"}:
        database_name = unquote(parsed.path.lstrip("/"))
        if not parsed.hostname or not database_name:
            raise ImproperlyConfigured(
                "DATABASE_URL must include a PostgreSQL host and database name."
            )

        try:
            port = parsed.port or 5432
        except ValueError as exc:
            raise ImproperlyConfigured(
                "DATABASE_URL contains an invalid PostgreSQL port."
            ) from exc

        config = {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": database_name,
            "USER": unquote(parsed.username or ""),
            "PASSWORD": unquote(parsed.password or ""),
            "HOST": parsed.hostname,
            "PORT": str(port),
            "CONN_MAX_AGE": env_int(
                "DATABASE_CONN_MAX_AGE",
                60,
                environ=source,
            ),
            "CONN_HEALTH_CHECKS": True,
        }
        query = parse_qs(parsed.query)
        sslmode = query.get("sslmode", [""])[-1].strip()
        if sslmode:
            config["OPTIONS"] = {"sslmode": sslmode}

        return config

    if scheme == "sqlite":
        if environment != "development":
            raise ImproperlyConfigured(
                "Staging and production must use PostgreSQL, not SQLite."
            )

        database_name = unquote(parsed.path)
        if database_name == "/:memory:":
            database_name = ":memory:"
        if not database_name:
            raise ImproperlyConfigured(
                "A sqlite DATABASE_URL must include a database path."
            )

        return {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": database_name,
        }

    raise ImproperlyConfigured(
        "DATABASE_URL must use postgresql://, postgres://, or sqlite://."
    )


def development_payment_handoff_enabled(environment, debug, environ=None):
    """Keep payment simulation impossible in every deployed environment."""
    return (
        environment == "development"
        and debug
        and env_bool(
            "ENABLE_DEVELOPMENT_PAYMENT_HANDOFF",
            True,
            environ=environ,
        )
    )
