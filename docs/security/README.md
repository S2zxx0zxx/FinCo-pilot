# Enterprise Security, Privacy and Legal Trust — execution checkpoint

Blueprint: supplied 21-page version 1.0 dated 15 October 2026, read completely. Scope is SEC-001 through SEC-080, separate from organic growth PR #89 and pricing PR #90.

Baseline main: `7736a24e7d520b9f08dd91d38e895b5d240f8a09`. Latest main was fetched before editing. Open PRs observed: #90 pricing, #89 growth, #85 SSO outage and #60 Clerk bridge. #88 is merged into this baseline. This branch changes privacy diagnostics and evidence only; no migrations, provider switches, authentication policy, financial records or infrastructure writes.

This is a bounded source/test execution checkpoint, not a penetration test, production clearance, complete legal opinion or proof every endpoint is safe. Eight new synthetic privacy regression cases failed before the changes. Their fixes remove raw upstream error bodies, endpoint credentials/paths/query strings, MCP discovery exception text, import bytes/private filenames/tracebacks and hard parser exception text from the affected diagnostics. Legitimate parser/connection behavior and CSV mapping remain covered by the existing suites.

## Verification

| Check | Observed result | Limit |
|---|---|---|
| Full backend baseline | 5,146 passed, 7 skipped; Python 3.14.8; SQLite; 4 workers | Collected before final patch tests; skips require native PostgreSQL; mock providers |
| Full frontend baseline | 920 tests passed | Synthetic browser DOM; no real Google/bank/card acceptance |
| Frontend production build | Passed; 214,234 gzip bytes vs 307,200 budget; source maps absent | Does not identify the exact running apex artifact |
| Worker privacy | 7 passed | Local Worker source, not a live cache isolation test |
| Python advisory scan | pip-audit: no known vulnerabilities reported in exported pinned runtime dependencies | Advisory database result dated to run; not absence of undiscovered issues |
| Frontend advisory scan | npm audit: 0 vulnerabilities reported | Includes dependency metadata, not runtime exploit testing |
| Focused final privacy/parser tests | 184 passed, including all eight new regression cases | Mock providers and synthetic imports; not real log-sink acceptance |
| Static Python analysis | Bandit: 30 candidates, 2 medium SQL-construction candidates reviewed | Both medium sites quote DB identifiers via identifier(); no exploit established; low findings not all dismissed |
| Lint/typecheck | Baseline whole backend Ruff/ty and frontend ESLint passed | Final changed-file rerun recorded in checks evidence |
| Source route inventory | AST decorators and 352 OpenAPI operations; 353 runtime route-method entries including schema-hidden operation | Graph categories include 128 workspace-write, 94 workspace-read, 67 explicit policies, 64 handler-review; categorization does not prove object ownership |
| Secret hygiene | Repository checker passed; 3,211 reachable UTF-8 history blobs scanned with six token-pattern families; zero matches | detect-secrets returned 1,227 heuristic candidates; triage incomplete; no all-secret-free claim |

See [dated evidence](evidence/checks.json), [all 80 controls](CONTROL_REGISTER.md), [structured register](control-register.json), [privacy/legal preparation](LEGAL_PRIVACY_REGISTER.md), [operations and risk decisions](OPERATIONS.md), and [threat model](THREAT_MODEL.md).

## Current deployment evidence

Three read-only public GETs, with no authentication or customer data, found apex `/` HTTP 200 and `/api/health/ready` JSON HTTP 200 (database/Redis ok), but separate `api.fincopilot.app/api/health/ready` HTTP 503 `InvalidConfiguration`. Do not treat the second hostname's outage as proof the apex runtime is down. Actual deployment commit, provider readiness and database identity were not proved by these probes.

Apex delivered compatibility CSP with `unsafe-inline` and broad HTTPS sources, `Cache-Control: no-store`, HSTS, DENY framing, nosniff and no-referrer. Cloudflare zone API returned SSL `full`, minimum TLS `1.0`, Always Use HTTPS `off`, HSTS enabled for one year. Tunnel is healthy with four connections and ingress to an HTTP service on host.docker.internal port 3000. This does not establish origin TLS or exact process provenance. Neon account metadata shows the FinCo-Pilot project in AWS Singapore; no SQL/customer rows, passwords or connection strings were requested, and its binding to apex is unknown.

## Five priority gaps and required proof

1. Effective GitHub main protection: branch endpoint says protected=false; rulesets list empty. Need administration access and approved required checks/review policy; no protection write performed.
2. Exact production source/topology/provider mapping: apex and API subdomain diverge. Need build SHA/image provenance and runtime binding before any auth or infrastructure change.
3. Edge TLS/CSP: weak minimum TLS and compatibility policy observed. Stage TLS/origin validation and Clerk/bank/payment report-only acceptance; obtain production approval before changing enforcement.
4. Outbound requests and upload resource budgets: configurable model/bank destinations and unbounded transaction-preview read require isolated egress and parser-budget testing. Do not break intentional self-hosted private model endpoints with an unreviewed blanket block.
5. Privacy/legal operations: actual operator details, staffed contacts, active processor contracts, consent/deletion/backup receipts and India log residency remain unverified. Prepared registers do not replace owner/counsel confirmation.

## Release state

Keep the focused PR draft. Review the final patch tests/CI on its exact head. No automatic merge, production deployment, DNS/TLS change, database migration, key rotation, policy publication or deletion is authorized by this checkpoint. Revert the isolated diagnostic commits to roll back; no database rollback exists or is needed. Staging acceptance must cover signup/login, CSV mapping/import, LLM connection success/failure, MCP discovery/tools and sanitized telemetry before owner-approved release.
