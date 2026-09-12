from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

from config.environment import (
    development_payment_handoff_enabled,
    env_bool,
    env_list,
    get_allowed_hosts,
    get_database_config,
    get_environment,
    get_secret_key,
)


class EnvironmentConfigTests(SimpleTestCase):
    def test_environment_defaults_to_development(self):
        self.assertEqual(
            get_environment({}),
            "development",
        )

    def test_environment_rejects_unknown_value(self):
        with self.assertRaisesMessage(
            ImproperlyConfigured,
            "PATAHAO_ENVIRONMENT must be one of",
        ):
            get_environment(
                {"PATAHAO_ENVIRONMENT": "preview"}
            )

    def test_boolean_and_list_values_are_parsed(self):
        environment = {
            "FEATURE_ON": "yes",
            "FEATURE_OFF": "0",
            "HOSTS": "api.example.com, admin.example.com",
        }

        self.assertTrue(
            env_bool("FEATURE_ON", environ=environment)
        )
        self.assertFalse(
            env_bool("FEATURE_OFF", environ=environment)
        )
        self.assertEqual(
            env_list("HOSTS", environ=environment),
            ["api.example.com", "admin.example.com"],
        )

    def test_deployed_environment_requires_secret_key(self):
        with self.assertRaisesMessage(
            ImproperlyConfigured,
            "DJANGO_SECRET_KEY is required",
        ):
            get_secret_key("production", {})

    def test_deployed_environment_requires_allowed_hosts(self):
        with self.assertRaisesMessage(
            ImproperlyConfigured,
            "DJANGO_ALLOWED_HOSTS is required",
        ):
            get_allowed_hosts("staging", {})

    def test_development_database_defaults_to_sqlite(self):
        database = get_database_config(
            "development",
            Path("/srv/patahao"),
            {},
        )

        self.assertEqual(
            database["ENGINE"],
            "django.db.backends.sqlite3",
        )
        self.assertEqual(
            database["NAME"],
            Path("/srv/patahao/db.sqlite3"),
        )

    def test_deployed_environment_requires_database_url(self):
        with self.assertRaisesMessage(
            ImproperlyConfigured,
            "DATABASE_URL is required",
        ):
            get_database_config(
                "production",
                Path("/srv/patahao"),
                {},
            )

    def test_postgresql_database_url_is_parsed(self):
        database = get_database_config(
            "production",
            Path("/srv/patahao"),
            {
                "DATABASE_URL": (
                    "postgresql://patahao:secret%2Fvalue@"
                    "db.example.com:5433/patahao_prod?sslmode=require"
                ),
                "DATABASE_CONN_MAX_AGE": "120",
            },
        )

        self.assertEqual(
            database,
            {
                "ENGINE": "django.db.backends.postgresql",
                "NAME": "patahao_prod",
                "USER": "patahao",
                "PASSWORD": "secret/value",
                "HOST": "db.example.com",
                "PORT": "5433",
                "CONN_MAX_AGE": 120,
                "CONN_HEALTH_CHECKS": True,
                "OPTIONS": {"sslmode": "require"},
            },
        )

    def test_deployed_environment_rejects_sqlite(self):
        with self.assertRaisesMessage(
            ImproperlyConfigured,
            "must use PostgreSQL",
        ):
            get_database_config(
                "staging",
                Path("/srv/patahao"),
                {"DATABASE_URL": "sqlite:///:memory:"},
            )

    def test_payment_handoff_is_development_only(self):
        enabled = {
            "ENABLE_DEVELOPMENT_PAYMENT_HANDOFF": "true",
        }

        self.assertTrue(
            development_payment_handoff_enabled(
                "development",
                True,
                enabled,
            )
        )
        self.assertFalse(
            development_payment_handoff_enabled(
                "development",
                False,
                enabled,
            )
        )
        self.assertFalse(
            development_payment_handoff_enabled(
                "staging",
                False,
                enabled,
            )
        )
        self.assertFalse(
            development_payment_handoff_enabled(
                "production",
                False,
                enabled,
            )
        )
