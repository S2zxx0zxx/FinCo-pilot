"""Small bounded, per-process Prometheus metrics. No user data or raw URLs."""
import secrets
import time
from collections import Counter

from fastapi import HTTPException, Request
from fastapi.responses import PlainTextResponse
from app.core.config import get_settings

_started = time.monotonic()
_requests: Counter[tuple[str, str]] = Counter()


def record_request(method: str, status: int) -> None:
    if get_settings().metrics_enabled:
        # Fixed label sets avoid cardinality attacks via arbitrary URLs/methods.
        label = method if method in {"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"} else "OTHER"
        _requests[(label, f"{status // 100}xx")] += 1


async def metrics(request: Request):
    settings = get_settings()
    if not settings.metrics_enabled:
        raise HTTPException(404, "Not found")
    expected = settings.metrics_token.get_secret_value()
    supplied = request.headers.get("authorization", "")
    if not expected or not secrets.compare_digest(supplied, f"Bearer {expected}"):
        raise HTTPException(401, "Metrics authentication required")
    lines = ["# HELP finco_process_uptime_seconds Uptime of this API process.",
             "# TYPE finco_process_uptime_seconds gauge",
             f"finco_process_uptime_seconds {time.monotonic() - _started:.3f}",
             "# HELP finco_http_requests_total Requests completed by this API process.",
             "# TYPE finco_http_requests_total counter"]
    for (method, status), count in sorted(_requests.items()):
        lines.append(f'finco_http_requests_total{{method="{method}",status_class="{status}"}} {count}')
    return PlainTextResponse("\n".join(lines) + "\n", media_type="text/plain; version=0.0.4")
