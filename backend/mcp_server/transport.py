"""Bounded JSON HTTP transport: modern metadata and legacy handshake clients.

Authentication remains FinCo-Pilot's registered bearer credential, not clientInfo.
No protocol sessions, sampling, subscriptions or autonomous writes are advertised.
"""
from __future__ import annotations

import base64
import binascii
from urllib.parse import urlsplit

from fastapi import Request

from app.agents.config import get_agent_settings
from app.core.config import get_settings

MODERN_VERSION = "2026-07-28"
LEGACY_VERSIONS = ("2025-11-25", "2025-06-18", "2025-03-26")
SUPPORTED_VERSIONS = (MODERN_VERSION, *LEGACY_VERSIONS)
META_PREFIX = "io.modelcontextprotocol/"
MAX_BODY_BYTES = 1024 * 1024


def origin_of(value: str) -> str | None:
    try:
        parsed = urlsplit(value)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            return None
        if parsed.username is not None or parsed.password is not None:
            return None
        port = parsed.port
        host = parsed.hostname.lower()
        if ":" in host:
            host = f"[{host}]"
        suffix = f":{port}" if port and port != {"http": 80, "https": 443}[parsed.scheme] else ""
        return f"{parsed.scheme}://{host}{suffix}"
    except ValueError:
        return None


def valid_origin(request: Request) -> bool:
    values = request.headers.getlist("origin")
    if not values:
        return True  # CLI/server clients need not send browser Origin.
    if len(values) != 1:
        return False
    raw = values[0]
    candidate = origin_of(raw)
    # Origin is an origin, never a URL with a path/query/userinfo.
    if candidate is None or raw != candidate:
        return False
    allowed = {origin_of(get_settings().frontend_url),
               origin_of(get_agent_settings().external_mcp_url)}
    return candidate in allowed


def decode_header(value: str | None) -> str | None:
    if value is None:
        return None
    if value.startswith("=?base64?") and value.endswith("?="):
        try:
            return base64.b64decode(value[9:-2], validate=True).decode("utf-8")
        except (binascii.Error, UnicodeDecodeError):
            return None
    if value != value.strip() or any(ord(c) < 32 or ord(c) > 126 for c in value):
        return None
    return value


def validate_protocol(request: Request, method: str, params: dict):
    """Return (modern, error tuple), validating before any tool execution."""
    header = request.headers.get("mcp-protocol-version")
    if any(len(request.headers.getlist(name)) > 1 for name in
           ("mcp-protocol-version", "mcp-method", "mcp-name")):
        return False, (-32020, "Ambiguous protocol headers", None)
    meta = params.get("_meta", {})
    if not isinstance(meta, dict):
        return False, (-32602, "Invalid metadata", None)
    declared = meta.get(META_PREFIX + "protocolVersion")
    modern = header == MODERN_VERSION or declared is not None
    if modern:
        if not isinstance(declared, str) or not isinstance(meta.get(META_PREFIX + "clientCapabilities"), dict):
            return True, (-32602, "Required protocol metadata missing or invalid", None)
        if header != declared or request.headers.get("mcp-method") != method:
            return True, (-32020, "Protocol header mismatch", None)
        if method in ("tools/call", "resources/read", "prompts/get"):
            name = params.get("uri") if method == "resources/read" else params.get("name")
            if not isinstance(name, str) or decode_header(request.headers.get("mcp-name")) != name:
                return True, (-32020, "Protocol name header mismatch", None)
        if declared != MODERN_VERSION:
            return True, (-32022, "Unsupported protocol version", {"supported": list(SUPPORTED_VERSIONS), "requested": declared})
    elif header is not None and header not in LEGACY_VERSIONS:
        return False, (-32022, "Unsupported protocol version", {"supported": list(SUPPORTED_VERSIONS), "requested": header})
    return modern, None
