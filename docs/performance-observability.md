# FinCo-Pilot performance observability (baseline v1)

Tracking: [Performance Program #58](https://github.com/S2zxx0zxx/FinCo-pilot/issues/58).

## What this PR adds

The existing authenticated \`/metrics\` endpoint now exposes a bounded
Prometheus **server response-header latency** histogram, in seconds:

- \`finco_http_request_duration_seconds_bucket\`
- \`finco_http_request_duration_seconds_sum\`
- \`finco_http_request_duration_seconds_count\`

The existing request-count and uptime metrics remain intact. Histogram labels
are restricted to a small fixed set of HTTP methods and response-status classes:
**no raw URL, route parameter, user ID, workspace, IP, token or payload labels**.
The metric is per API worker process; aggregate across workers/replicas in a
Prometheus-compatible collector. Histogram buckets are cumulative with a
\`+Inf\` bucket, supporting approximate percentile estimates.

The metric measures time spent in the ASGI request chain until application
response headers are ready. It does **not** measure full response-body streaming
or users' network/download/rendering times. It cannot identify the slowest
individual endpoint because no route label is emitted in baseline v1.

## Example PromQL

Request throughput (per second across all replicas):

\`\`\`promql
sum(rate(finco_http_requests_total[5m]))
\`\`\`

Approximate API p95 by HTTP method (aggregate all replicas; requests with
different status classes share the same method group):

\`\`\`promql
histogram_quantile(
  0.95,
  sum by (le, method) (
    rate(finco_http_request_duration_seconds_bucket[5m])
  )
)
\`\`\`

Approximate aggregate API p99:

\`\`\`promql
histogram_quantile(
  0.99,
  sum by (le) (
    rate(finco_http_request_duration_seconds_bucket[5m])
  )
)
\`\`\`

The scrape endpoint is opt-in per environment via existing
\`METRICS_ENABLED\` and \`METRICS_TOKEN\` settings, and requires a
\`Bearer\` token. Never publish the token, expose an unauthenticated endpoint
or include request/user financial data in metric labels.

## Repeatable verification

Within the configured backend development/test environment:

\`\`\`bash
cd backend
pytest -q tests/test_performance_metrics.py tests/test_launch_hardening.py -k metrics
ruff check app/core/metrics.py app/main.py tests/test_performance_metrics.py
\`\`\`

Check real response-time behavior against a representative test deployment
before declaring any route fast. Current source-code review is *not* a real
latency benchmark, and there is no measured 10k-concurrent-user claim.

For repeatable high-cardinality finance data, the existing
\`backend/scripts/seed_perf.py\` can generate synthetic records; **its default
action resets data**. Run only on an isolated disposable database, never on a
shared/staging/production dataset that contains valuable information.

## Next measurements

1. Lighthouse/Web Vitals baseline (LCP, INP, CLS) on representative mobile/desktop
   devices, cold and warm navigation.
2. Profile dashboard API/SQL and the 500-row monthly transactions query.
3. Capture production frontend asset/chunk sizes and API request waterfall.
4. Conduct staging-only load tests with bounded concurrency and rollback plans.
5. Add carefully bounded endpoint-group latency breakdowns only after reviewing
   cardinality and privacy implications.
