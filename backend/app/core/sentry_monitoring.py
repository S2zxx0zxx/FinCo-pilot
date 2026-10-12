"""Privacy-first, optional Sentry error tracking for API and Celery processes.

No financial records, tokens, request bodies, user IDs or URL query strings
are sent. Sentry is explicitly opt-in; missing credentials never block startup.
"""
from __future__ import annotations

import logging
import os
from typing import Any, cast
from urllib.parse import urlsplit

from app.core.config import get_settings

logger = logging.getLogger(__name__)
_INITIALIZED = False


def sanitize_event(event: dict[str, Any], component: str = "api") -> dict[str, Any]:
    """Retain exception types and frame locations, never private payloads."""
    for key in (
        "request", "user", "contexts", "extra", "breadcrumbs", "logentry",
        "message", "modules", "fingerprint", "tags",
    ):
        event.pop(key, None)

    # Third-party integrations may put account IDs into transaction names.
    event.pop("transaction", None)
    values = (event.get("exception") or {}).get("values", [])
    if isinstance(values, list):
        for value in values:
            if not isinstance(value, dict):
                continue
            if "value" in value:
                value["value"] = "[redacted]"
            stack = value.get("stacktrace") or {}
            for frame in stack.get("frames", []):
                if not isinstance(frame, dict):
                    continue
                for key in ("vars", "pre_context", "post_context", "context_line", "abs_path"):
                    frame.pop(key, None)
    # Only this constant, non-user-derived label is allowed.
    event["tags"] = {"component": "worker" if component == "worker" else "api"}
    return event


def init_sentry(component: str = "api") -> bool:
    """Register error capture after Settings validation, once per process."""
    global _INITIALIZED
    if _INITIALIZED:
        return True
    settings = get_settings()
    if not settings.sentry_enabled:
        return False
    dsn = settings.sentry_dsn.get_secret_value().strip()
    if not dsn:
        logger.warning("Sentry enabled but DSN is not configured; telemetry disabled")
        return False
    parts = urlsplit(dsn)
    if parts.scheme != "https" or not parts.hostname or not parts.username or parts.password:
        logger.warning("Sentry DSN configuration invalid; telemetry disabled")
        return False

    # Import only when enabled: boot, tests and disaster recovery stay independent.
    import sentry_sdk
    from sentry_sdk.types import Event
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.celery import CeleryIntegration

    environment = settings.sentry_environment.strip() or settings.deployment_environment.strip().lower()
    environment = environment if environment in {"production", "staging", "preview", "development", "test"} else "unknown"
    release = settings.sentry_release.strip() or os.environ.get(
        "VERCEL_GIT_COMMIT_SHA", ""
    ).strip() or None

    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        release=release,
        integrations=[FastApiIntegration(), CeleryIntegration()],
        # Never capture request bodies, headers, user identities, log breadcrumbs,
        # stack-frame variables, financial error messages, or source excerpts.
        send_default_pii=False,
        max_request_body_size="never",
        include_local_variables=False,
        include_source_context=False,
        attach_stacktrace=False,
        enable_logs=False,
        sample_rate=1.0,
        traces_sample_rate=0.0,
        profiles_sample_rate=0.0,
        before_send=lambda event, hint: cast(Event, sanitize_event(cast(dict[str, Any], event), component)),
    )
    _INITIALIZED = True
    logger.info("Privacy-safe Sentry error instrumentation enabled for %s", component)
    return True
