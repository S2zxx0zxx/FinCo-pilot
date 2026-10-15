"""Offline interpretation/privacy boundaries for the manual growth probe."""

import io
import unittest
import urllib.error
import urllib.request
from email.message import Message
from unittest.mock import patch

import growth_public_audit as audit


class AuditTests(unittest.TestCase):
    def test_spa_html_is_not_a_sitemap_even_with_http_200(self):
        result = audit.summarize(audit.URLS[2], 200, {"content-type": "text/html"},
                                 b"<html><h1>App</h1></html>")
        self.assertFalse(result["xml_sitemap_document"])
        self.assertEqual(result["initial_html"]["h1_count"], 1)

    def test_valid_xml_is_format_only_and_wrong_mime_or_truncation_fails(self):
        body = b'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"/>'
        for mime, truncated, expected in [("application/xml", False, True),
                                           ("text/html", False, False),
                                           ("text/xml", True, False)]:
            with self.subTest(mime=mime, truncated=truncated):
                result = audit.summarize(audit.URLS[2], 200, {"content-type": mime}, body, truncated)
                self.assertEqual(result["xml_sitemap_document"], expected)

    def test_canonical_and_robots_are_found_without_echoing_links_or_cookies(self):
        body = b'<LINK rel="alternate canonical" href="https://example.test/?token=secret"><META NAME="ROBOTS" content="noindex"><h1>Visible</h1>'
        result = audit.summarize(audit.URLS[0], 200,
                                 {"content-type": "text/html", "set-cookie": "private"}, body)
        self.assertEqual(result["initial_html"]["canonical_count"], 1)
        self.assertEqual(result["initial_html"]["meta_robots"], ["noindex"])
        self.assertNotIn("secret", str(result))
        self.assertNotIn("set-cookie", result["headers"])

    def test_health_reports_are_origin_specific_and_do_not_echo_body(self):
        result = audit.summarize(audit.URLS[7], 503, {"content-type": "application/json"},
                                 b'{"status":"not_ready","detail":"do not retain"}')
        self.assertEqual(result["status"], 503)
        self.assertEqual(result["readiness_status"], "not_ready")
        self.assertNotIn("do not retain", str(result))
        for body in (b"[]", b"invalid"):
            self.assertNotIn("readiness_status", audit.summarize(
                audit.URLS[7], 503, {"content-type": "application/json"}, body))

    def test_arbitrary_private_and_token_urls_are_rejected(self):
        for url in ("https://fincopilot.app/accounts", "https://fincopilot.app/?token=x",
                    "http://127.0.0.1/", "https://fincopilot.app/i/secret"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                audit.probe(url)

    def test_redirects_cannot_reach_auth_provider_or_exceed_budget(self):
        handler = audit.PublicRedirects()
        req = urllib.request.Request(audit.URLS[0])
        with self.assertRaises(urllib.error.URLError):
            handler.redirect_request(req, None, 302, "Found", {}, "https://accounts.fincopilot.app/?token=x")
        handler = audit.PublicRedirects()
        for _ in range(audit.MAX_REDIRECTS):
            self.assertIsNotNone(handler.redirect_request(req, None, 302, "Found", {}, audit.URLS[4]))
        with self.assertRaises(urllib.error.URLError):
            handler.redirect_request(req, None, 302, "Found", {}, audit.URLS[4])

    def test_http_errors_are_observations_not_exceptions(self):
        headers = Message()
        headers["Content-Type"] = "text/html"
        error = urllib.error.HTTPError(audit.URLS[0], 403, "Forbidden", headers, io.BytesIO(b"blocked"))
        with patch("urllib.request.OpenerDirector.open", side_effect=error):
            self.assertEqual(audit.probe(audit.URLS[0])["status"], 403)


if __name__ == "__main__":
    unittest.main()
