import os
from pathlib import Path
import runpy
from unittest.mock import patch

from django.conf import settings
from django.test import SimpleTestCase


class GunicornConfigurationTests(SimpleTestCase):
    def setUp(self):
        self.config_path = Path(settings.BASE_DIR) / "config" / "gunicorn.py"

    def test_safe_defaults_bind_to_local_reverse_proxy(self):
        with patch.dict(os.environ, {}, clear=True):
            config = runpy.run_path(str(self.config_path))

        self.assertEqual(config["bind"], "127.0.0.1:8000")
        self.assertEqual(config["timeout"], 120)
        self.assertEqual(config["forwarded_allow_ips"], "127.0.0.1")
        self.assertEqual(config["accesslog"], "-")
        self.assertEqual(config["errorlog"], "-")

    def test_non_positive_worker_count_fails_closed(self):
        with patch.dict(
            os.environ,
            {"GUNICORN_WORKERS": "0"},
            clear=True,
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "GUNICORN_WORKERS must be greater than zero",
            ):
                runpy.run_path(str(self.config_path))


class ReverseProxyTemplateTests(SimpleTestCase):
    def test_private_media_has_no_public_nginx_fallback(self):
        template_path = (
            Path(settings.BASE_DIR)
            / "deploy"
            / "patahao-api.nginx.example"
        )
        template = template_path.read_text(encoding="utf-8")

        self.assertIn("location ^~ /media/ {", template)
        self.assertIn("return 404;", template)
        self.assertNotIn(
            "alias /var/lib/patahao/media/;",
            template,
        )
        self.assertNotIn("/media/mandates/ {", template)
