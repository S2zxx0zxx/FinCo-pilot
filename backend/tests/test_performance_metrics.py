"""Privacy-safe, low-cardinality request latency instrumentation regression tests."""

import math
from collections import Counter, defaultdict

import pytest
from pydantic import SecretStr

from app.core import metrics as perf_metrics
from app.core.config import get_settings


def test_duration_buckets_are_cumulative_and_cardinality_is_bounded(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "metrics_enabled", True)
    monkeypatch.setattr(perf_metrics, "_requests", Counter())
    monkeypatch.setattr(perf_metrics, "_duration_counts", Counter())
    monkeypatch.setattr(perf_metrics, "_duration_sums", defaultdict(float))
    monkeypatch.setattr(perf_metrics, "_duration_buckets", {})

    perf_metrics.record_request("GET", 200, 0.12)
    perf_metrics.record_request("POST", 404, 3.0)
    perf_metrics.record_request("UNTRUSTED", 429, math.inf)
    perf_metrics.record_request("DELETE", 503, -0.1)

    assert perf_metrics._requests[("GET", "2xx")] == 1
    assert perf_metrics._requests[("POST", "4xx")] == 1
    assert perf_metrics._requests[("OTHER", "4xx")] == 1
    assert perf_metrics._requests[("DELETE", "5xx")] == 1

    buckets = perf_metrics._duration_buckets[("GET", "2xx")]
    bounds = perf_metrics._duration_bucket_bounds
    assert buckets[bounds.index(0.1)] == 0
    assert buckets[bounds.index(0.25)] == 1
    assert buckets[bounds.index(10)] == 1
    assert perf_metrics._duration_counts[("GET", "2xx")] == 1
    assert perf_metrics._duration_sums[("GET", "2xx")] == pytest.approx(0.12)
    assert perf_metrics._duration_counts[("POST", "4xx")] == 1
    assert ("OTHER", "4xx") not in perf_metrics._duration_counts
    assert ("DELETE", "5xx") not in perf_metrics._duration_counts


@pytest.mark.asyncio
async def test_duration_histograms_stay_auth_gated_and_do_not_expose_private_labels(client, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "metrics_enabled", True)
    monkeypatch.setattr(settings, "metrics_token", SecretStr("synthetic-performance-key"))

    perf_metrics.record_request("PATCH", 200, 0.125)

    denied = await client.get("/metrics")
    assert denied.status_code == 401

    response = await client.get(
        "/metrics",
        headers={"Authorization": "Bearer synthetic-performance-key"},
    )
    assert response.status_code == 200
    body = response.text
    assert "# TYPE finco_http_request_duration_seconds histogram" in body
    assert 'finco_http_request_duration_seconds_bucket{method="PATCH",status_class="2xx",le="0.25"}' in body
    assert 'finco_http_request_duration_seconds_bucket{method="PATCH",status_class="2xx",le="+Inf"}' in body
    assert 'finco_http_request_duration_seconds_sum{method="PATCH",status_class="2xx"}' in body
    assert 'finco_http_request_duration_seconds_count{method="PATCH",status_class="2xx"}' in body
    assert "synthetic-performance-key" not in body
    assert "workspace_id=" not in body
    assert "user_id=" not in body


def test_disabled_metrics_do_not_collect_durations(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "metrics_enabled", False)
    monkeypatch.setattr(perf_metrics, "_requests", Counter())
    monkeypatch.setattr(perf_metrics, "_duration_counts", Counter())
    perf_metrics.record_request("GET", 200, 0.01)
    assert not perf_metrics._requests
    assert not perf_metrics._duration_counts
