#!/usr/bin/env python3
"""Manually observe fixed public URLs, without credentials or private page access.

No scheduler, writes, retry loop, auth, crawling, URL discovery or launch verdict.
Print only bounded public metadata; raw pages/headers/cookies are never persisted.
"""

import hashlib
from html.parser import HTMLParser
import json
import socket
import urllib.error
import urllib.request
from datetime import datetime, timezone
from urllib.parse import urlsplit
from xml.etree import ElementTree

URLS = (
    "https://fincopilot.app/",
    "https://fincopilot.app/robots.txt",
    "https://fincopilot.app/sitemap.xml",
    "https://fincopilot.app/api/health/ready",
    "https://www.fincopilot.app/",
    "https://www.fincopilot.app/robots.txt",
    "https://www.fincopilot.app/sitemap.xml",
    "https://api.fincopilot.app/api/health/ready",
)
MAX_BYTES = 256 * 1024
MAX_REDIRECTS = 3
TIMEOUT_SECONDS = 15
HEADERS = ("content-type", "cache-control", "x-robots-tag", "server")


class PublicRedirects(urllib.request.HTTPRedirectHandler):
    """Allow only fixed public destinations; never forward to sign-in or tokens."""

    def __init__(self):
        super().__init__()
        self.count = 0

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        self.count += 1
        if self.count > MAX_REDIRECTS or newurl not in URLS:
            raise urllib.error.URLError("redirect_outside_fixed_public_budget")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class PublicHTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.h1_count = 0
        self.canonical_count = 0
        self.robots = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "h1":
            self.h1_count += 1
        if tag == "link" and "canonical" in (values.get("rel") or "").lower().split():
            self.canonical_count += 1
        if tag == "meta" and (values.get("name") or "").lower() == "robots":
            self.robots.append((values.get("content") or "")[:160])


def summarize(url, status, headers, body, truncated=False):
    """Interpret public responses without copying potentially sensitive bodies."""
    result = {
        "url": url,
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "headers": {key: headers[key] for key in HEADERS if key in headers},
        "bytes_read": len(body),
        "truncated": truncated,
        "sha256": hashlib.sha256(body).hexdigest(),
    }
    mime = headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if mime in ("text/html", "application/xhtml+xml"):
        parser = PublicHTML()
        parser.feed(body.decode("utf-8", errors="replace"))
        result["initial_html"] = {
            "h1_count": parser.h1_count,
            "canonical_count": parser.canonical_count,
            "meta_robots": parser.robots,
        }
    path = urlsplit(url).path
    if path == "/sitemap.xml":
        result["xml_sitemap_document"] = False
        # XML parsing checks format only. Eligibility requires separate URL QA.
        if not truncated and mime in ("application/xml", "text/xml"):
            try:
                root = ElementTree.fromstring(body)
                result["xml_sitemap_document"] = root.tag in (
                    "{http://www.sitemaps.org/schemas/sitemap/0.9}urlset",
                    "{http://www.sitemaps.org/schemas/sitemap/0.9}sitemapindex",
                )
            except ElementTree.ParseError:
                pass
    if path == "/robots.txt":
        result["robots_text_plain"] = mime == "text/plain"
        text = body.decode("utf-8", errors="replace")
        result["sitemap_declarations"] = sum(
            line.strip().lower().startswith("sitemap:") for line in text.splitlines()
        )
        # Do not use Python robotparser to certify effective merged bot policy.
    if path == "/api/health/ready" and mime == "application/json" and not truncated:
        try:
            value = json.loads(body)
            if isinstance(value, dict) and value.get("status") in ("ready", "not_ready"):
                result["readiness_status"] = value["status"]
        except (ValueError, UnicodeDecodeError):
            pass
    return result


def probe(url):
    if url not in URLS:
        raise ValueError("Only fixed public URLs are allowed")
    opener = urllib.request.build_opener(PublicRedirects())
    request = urllib.request.Request(url, headers={"User-Agent": "FinCoPilot-Growth-Audit/1.0"})
    try:
        try:
            response = opener.open(request, timeout=TIMEOUT_SECONDS)
        except urllib.error.HTTPError as exc:
            response = exc
        with response:
            body = response.read(MAX_BYTES + 1)
            headers = {key.lower(): val for key, val in response.headers.items()}
            return summarize(url, response.code, headers, body[:MAX_BYTES], len(body) > MAX_BYTES)
    except (urllib.error.URLError, TimeoutError, socket.timeout, OSError):
        # Do not print exception URLs: redirects can contain credentials.
        return {"url": url, "observed_at": datetime.now(timezone.utc).isoformat(),
                "error": "network_or_redirect_check_failed"}


def main():
    print(json.dumps({
        "scope": "Anonymous fixed-public HTTP observations; not browser, auth, indexing or launch acceptance",
        "request_budget_including_redirects": len(URLS) * (1 + MAX_REDIRECTS),
        "observations": [probe(url) for url in URLS],
    }, indent=2))


if __name__ == "__main__":
    main()
