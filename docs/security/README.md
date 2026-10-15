# Enterprise Security, Privacy and Legal Trust — execution checkpoint

Blueprint: supplied 21-page version 1.0 dated 15 October 2026, read completely. Scope is SEC-001 through SEC-080, separate from organic growth PR #89 and pricing PR #90.

Baseline main: `7736a24e7d520b9f08dd91d38e895b5d240f8a09`. Latest main was fetched before editing and refreshed to `e727498c9481cdcb94f06b6f429933224f9c5b08` when pricing PR #90 merged during execution; reconciled without conflict. Open PRs observed: #90 pricing, #89 growth, #85 SSO outage and #60 Clerk bridge. #88 is merged into this baseline. This branch changes privacy diagnostics and evidence only; no migrations, provider switches, authentication policy, financial records or production infrastructure writes.

This is a bounded source/test execution checkpoint, not a penetration test, production clearance, complete legal opinion or proof every endpoint is safe. Twenty-four synthetic privacy failure cases were reproduced before their fixes (eight initial cases, twelve provider-status cases, two bank-error cases and two directory visibility cases). Additional upload/executor privacy properties are also tested. The fixes remove raw upstream error bodies, endpoint credentials/paths/query strings, MCP discovery exception text, import bytes/private filenames/tracebacks and hard parser exception text from the affected diagnostics. Streaming provider errors no longer buffer untrusted error bodies. Unexpected bank errors preserve their status with generic retry messages. Transaction/asset import previews read at most the configured 10 MiB plus one sentinel byte; existing knowledge limits apply before materialization. Multipart spool/disk and parser CPU isolation still need separate limits. A read-route authentication regression contract supplements existing write-gate tests; combined read/write/directory fixtures pass 215 tests. The collaborator directory now defaults to active shared-workspace members/managers and self, excluding unrelated accounts; trusted self-hosted operators can explicitly select instance scope. Exact-email invite lookup is retained. Legitimate parser/connection behavior and CSV mapping remain covered by the existing suites.

## Verification

| Check | Observed result | Limit |
|---|---|---|
| Full backend baseline | 5,146 passed, 7 skipped; Python 3.14.8; SQLite; 4 workers | Collected before final patch tests; skips require native PostgreSQL; mock providers |
| Full frontend | Initial 920 passed; after pricing merge 935 passed with two workers | Synthetic browser DOM; no real Google/bank/card acceptance |
| Frontend production build | Passed; 214,829 gzip bytes after pricing merge vs 307,200 budget; source maps absent | Does not identify the exact running apex artifact |
| Worker privacy | 7 passed | Local Worker source, not a live cache isolation test |
| Python advisory scan | pip-audit: no known vulnerabilities reported in exported pinned runtime dependencies | Advisory database result dated to run; not absence of undiscovered issues |
| Frontend advisory scan | npm audit: 0 vulnerabilities reported | Includes dependency metadata, not runtime exploit testing |
| Focused final privacy/parser tests | 184 passed, including all eight new regression cases | Mock providers and synthetic imports; not real log-sink acceptance |
| Expanded provider/executor / banking / upload fixtures | 109 / 310 / 43 passed respectively | Includes synthetic payload disclosure checks and byte-limit rejection; no live upstream changes |
| Native PostgreSQL and Redis CI | Passed on b307407, run 38734391388 | Includes synthetic encrypted restore and seven SQLite-skipped cases; actual production restore remains unverified |
| Static Python analysis | Bandit: 30 candidates, 2 medium SQL-construction candidates reviewed | Both medium sites quote DB identifiers via identifier(); no exploit established; low findings not all dismissed |
| Lint/typecheck | Baseline whole backend Ruff/ty and frontend ESLint passed | Final changed-file rerun recorded in checks evidence |
| Source route inventory | AST decorators and 352 OpenAPI operations; 353 runtime route-method entries including schema-hidden operation | Graph categories include 128 workspace-write, 94 workspace-read, 67 explicit policies, 64 handler-review; categorization does not prove object ownership |
| Secret hygiene | Repository checker passed; 3,211 reachable UTF-8 history blobs scanned with six token-pattern families; zero matches | detect-secrets returned 1,227 candidates; redacted categorization and thirty non-obvious location reviews recorded; no all-secret-free claim |

One expanded local frontend run after the pricing merge had one existing Clerk registration test exceed its 5-second timeout (934 passed); its isolated rerun and the complete 935-test rerun passed. The timed-out attempt remains recorded. Exact final-head CI must pass before release.

Reproduce inventories with `uv run --directory backend --frozen python scripts/security_route_inventory.py` (AST) or add `--runtime` (fresh subprocess; anchored .env, secrets and Sentry disabled; no startup/query).

Latest local full backend before directory addition: **5,188 passed / 7 native-only skips**; directory plus configuration/group/workspace fixtures: **86 passed**. All seven jobs of the initial candidate CI succeeded, including native tests; the scoped-directory native PostgreSQL gate and new advisory workflow also passed on candidate 6886691. Full backend coverage and final test/documentation-head checks remain tracked on PR #91.

See [dated evidence](evidence/checks.json), [all 80 controls](CONTROL_REGISTER.md), [structured register](control-register.json), [privacy/legal preparation](LEGAL_PRIVACY_REGISTER.md), [operations and risk decisions](OPERATIONS.md), [concrete approval gates](PRODUCTION_GATES.md), and [threat model](THREAT_MODEL.md).

## Current deployment evidence

Three read-only public GETs, with no authentication or customer data, found apex `/` HTTP 200 and `/api/health/ready` JSON HTTP 200 (database/Redis ok), but separate `api.fincopilot.app/api/health/ready` HTTP 503 `InvalidConfiguration`. Do not treat the second hostname's outage as proof the apex runtime is down. Actual deployment commit, provider readiness and database identity were not proved by these probes.

Apex delivered compatibility CSP with `unsafe-inline` and broad HTTPS sources, `Cache-Control: no-store`, HSTS, DENY framing, nosniff and no-referrer. Cloudflare zone API returned SSL `full`, minimum TLS `1.0`, Always Use HTTPS `off`, HSTS enabled for one year. Tunnel is healthy with four connections and ingress to an HTTP service on host.docker.internal port 3000. This does not establish origin TLS or exact process provenance. Neon account metadata shows the FinCo-Pilot project in AWS Singapore; no SQL/customer rows, passwords or connection strings were requested, and its binding to apex is unknown.

## Five priority gaps and required proof

1. Effective GitHub main protection: branch endpoint says protected=false; rulesets list empty. Need administration access and approved required checks/review policy; no protection write performed.
2. Exact production source/topology/provider mapping: apex and API subdomain diverge. Need build SHA/image provenance and runtime binding before any auth or infrastructure change.
3. Edge TLS/CSP: weak minimum TLS and compatibility policy observed. Stage TLS/origin validation and Clerk/bank/payment report-only acceptance; obtain production approval before changing enforcement.
4. Outbound requests and upload resource budgets: configurable model/bank destinations require isolated egress testing; financial import reads are now bounded, while multipart spool/concurrency and parser CPU budgets still require measured enforcement. Do not break intentional self-hosted private model endpoints with an unreviewed blanket block.
5. Privacy/legal operations: actual operator details, staffed contacts, active processor contracts, consent/deletion/backup receipts and India log residency remain unverified. Prepared registers do not replace owner/counsel confirmation.

## Release state

Keep the focused PR draft. Review the final patch tests/CI on its exact head. No automatic merge, production deployment, DNS/TLS change, database migration, key rotation, policy publication or deletion is authorized by this checkpoint. Revert the isolated diagnostic commits to roll back; no database rollback exists or is needed. Staging acceptance must cover signup/login, CSV mapping/import, LLM connection success/failure, MCP discovery/tools and sanitized telemetry before owner-approved release.


## Follow-up execution before merge — 15 October 2026

After the previous verified candidate (`9017d07`, all seven CI jobs and advisory workflow successful; local backend 5,194 passed/7 native-only skips), the remaining resource/privacy review identified and fixed additional source gaps:

- Transaction attachments, invoice attachments and invoice logos now apply the existing storage byte limit before materializing payloads. Existing 400 status/message, storage billing and service validation remain; oversized uploads never reach billing, decoding or provider upload. This is not a multipart spool/disk/concurrency guarantee.
- Knowledge ingestion no longer stores raw filesystem/provider exception strings or emits embedding tracebacks. Malformed parsers mark the document failed with a safe category instead of leaving processing state. Existing ready/no-text/retry dispatch behavior remains.
- Worker document/agent binding is validated from persisted metadata before file reads or status/chunk mutation. This is defense against mismatched internal queue arguments, not evidence of a public remote exploit.
- A new disposable native PostgreSQL proof exercises a writer waiting behind a role downgrade and a downgrade waiting behind an in-flight writer. It checks actual `pg_blocking_pids` rather than assuming a sleep proves contention. CI runs it only with explicit disposable-database gates and a generated synthetic schema; its first result is pending at this source checkpoint.

Before-fix regression run: seven test failures (storage-budget 3, ingestion privacy/status 4), plus one separate worker-binding failure. These are eight failing test cases, not eight distinct exploit classes. First focused attachment/invoice/knowledge/import rerun: **145 passed**; final small worker/budget rerun: **12 passed**. Full follow-up backend and exact-head native/coverage CI must pass; PR #91 records their final results without counting pending runs as successful.

All 80 controls remain accounted for. The register's `BLOCKED_EXTERNAL_ACCEPTANCE` status means final acceptance is open; it does **not** establish that engineering review is complete or that every blocker is merely missing permission. Explicit remaining engineering scope includes exhaustive object/property/serializer coverage, complete outbound/secret/artifact review and measured parser/ingress resource isolation. Other gates require actual provider/runtime evidence, operator/legal facts or production approval. No complete-codebase safety or 80/80 production claim is made.
