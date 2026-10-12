"""Privacy-first, optional Sentry error tracking for API and Celery processes.

No financial records, tokens, request bodies, user IDs or URL query strings
are sent. Sentry is explicitly opt-in; missing credentials never block startup.
"""
from __future__ import annotations

import logging
import os
from typing import Any
from urllib.parse import urlsplit

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
    if os.environ.get("SENTRY_ENABLED", "").strip().lower() not in {"1", "true"}:
        return False
    dsn = os.environ.get("SENTRY_DSN", "").strip()
    if not dsn:
        logger.warning("Sentry enabled but DSN is not configured; telemetry disabled")
        return False
    parts = urlsplit(dsn)
    if parts.scheme != "https" or not parts.hostname or not parts.username or parts.password:
        logger.warning("Sentry DSN configuration invalid; telemetry disabled")
        return False

    # Import only when enabled: boot, tests and disaster recovery stay independent.
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.celery import CeleryIntegration

    environment = os.environ.get("SENTRY_ENVIRONMENT", "").strip() or os.environ.get(
        "DEPLOYMENT_ENVIRONMENT", "development"
    ).strip().lower()
    environment = environment if environment in {"production", "staging", "preview", "development", "test"} else "unknown"
    release = os.environ.get("SENTRY_RELEASE", "").strip() or os.environ.get(
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
        before_send=lambda event, hint: sanitize_event(event, component),
    )
    _INITIALIZED = True
    logger.info("Privacy-safe Sentry error instrumentation enabled for %s", component)
    return True
