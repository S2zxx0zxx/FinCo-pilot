"""Bounded, per-process Prometheus metrics. Never use user data or raw URLs."""

import math
import secrets
import time
from collections import Counter, defaultdict

from fastapi import HTTPException, Request
from fastapi.responses import PlainTextResponse

from app.core.config import get_settings

_started = time.monotonic()
_methods = frozenset({"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"})
# Histograms are cumulative; +Inf is rendered from the total count.
_duration_bucket_bounds = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10)
_requests: Counter[tuple[str, str]] = Counter()
_duration_counts: Counter[tuple[str, str]] = Counter()
_duration_sums: defaultdict[tuple[str, str], float] = defaultdict(float)
_duration_buckets: dict[tuple[str, str], list[int]] = {}


def record_request(method: str, status: int, duration_seconds: float | None = None) -> None:
    """Record one response and optionally its server-side elapsed time.

    Label cardinality is bounded by HTTP method and status class. No URL,
    route parameters, account ID, workspace, token or request body is captured.
    """
    if not get_settings().metrics_enabled:
        return

    key = (method if method in _methods else "OTHER", f"{status // 100}xx")
    _requests[key] += 1
    if duration_seconds is None or not math.isfinite(duration_seconds) or duration_seconds < 0:
        return

    _duration_counts[key] += 1
    _duration_sums[key] += duration_seconds
    buckets = _duration_buckets.setdefault(key, [0] * len(_duration_bucket_bounds))
    for index, upper_bound in enumerate(_duration_bucket_bounds):
        if duration_seconds <= upper_bound:
            buckets[index] += 1


async def metrics(request: Request):
    settings = get_settings()
    if not settings.metrics_enabled:
        raise HTTPException(404, "Not found")
    expected = settings.metrics_token.get_secret_value()
    supplied = request.headers.get("authorization", "")
    if not expected or not secrets.compare_digest(supplied, f"Bearer {expected}"):
        raise HTTPException(401, "Metrics authentication required")

    lines = [
        "# HELP finco_process_uptime_seconds Uptime of this API process.",
        "# TYPE finco_process_uptime_seconds gauge",
        f"finco_process_uptime_seconds {time.monotonic() - _started:.3f}",
        "# HELP finco_http_requests_total Requests completed by this API process.",
        "# TYPE finco_http_requests_total counter",
    ]
    for (method, status), count in sorted(_requests.items()):
        lines.append(
            f'finco_http_requests_total{{method="{method}",status_class="{status}"}} {count}'
        )

    lines.extend([
        "# HELP finco_http_request_duration_seconds Time until application response headers "
        "are available; excludes network transfer and response-body streaming.",
        "# TYPE finco_http_request_duration_seconds histogram",
    ])
    for (method, status), count in sorted(_duration_counts.items()):
        key = (method, status)
        for upper_bound, cumulative_count in zip(
            _duration_bucket_bounds, _duration_buckets[key], strict=True
        ):
            lines.append(
                f'finco_http_request_duration_seconds_bucket{{method="{method}",'
                f'status_class="{status}",le="{upper_bound:g}"}} {cumulative_count}'
            )
        lines.extend([
            f'finco_http_request_duration_seconds_bucket{{method="{method}",'
            f'status_class="{status}",le="+Inf"}} {count}',
            f'finco_http_request_duration_seconds_sum{{method="{method}",'
            f'status_class="{status}"}} {_duration_sums[key]:.9f}',
            f'finco_http_request_duration_seconds_count{{method="{method}",'
            f'status_class="{status}"}} {count}',
        ])

    return PlainTextResponse(
        "\n".join(lines) + "\n",
        media_type="text/plain; version=0.0.4",
    )
