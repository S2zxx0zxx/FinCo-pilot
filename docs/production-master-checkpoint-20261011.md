# Production master execution checkpoint — 2026-10-11

Launch verdict: **NO GO**. This document records verified engineering and infrastructure facts, never substitutes synthetic tests for live acceptance. The 31-page master PDF was extracted and read through its final instruction; canonical continuity version 84 and current GitHub/infrastructure were reconciled before edits. Original business decisions and the 60-point roadmap remain authoritative.

## Verified starting state

- GitHub main `cf3aa603aa57e694905aabe41ba0aedc75f98d80`, tree `d1f6ec2e79aecc2f320276910a72bc0d9e43cb79`. CI run `38068550826`: all seven checks succeeded.
- Dedicated branch `fix/production-schema-safety-20261011`. Drafts #56 external MCP, #59 latency observability, #60 Clerk runtime identity probe remain reviewed but unmerged; #60 is not a complete Clerk cutover.
- Correct Vercel team `team_uMfXHmjfGpTtJIufjKEtaXV7`; frontend and API projects exist. API's only observed deployment `dpl_AAZhkt5ktTHXJ2N36Kym7qAbWN6Y` was CANCELED. No working API deployment verified.
- Public frontend `/` and `/login` returned HTML 200; `/api/info`, liveness and readiness returned 404. `/mcp` incorrectly returned frontend HTML 200. Manifest and service worker returned 200.
- Cloudflare apex/www CNAMEs point to the Vercel destination; existing email MX/SPF/DKIM/DMARC records retained. R2 `fincopilot-prod` exists, without verified authenticated storage acceptance.
- GitHub main was unprotected, rulesets empty; protection API returns 403 with current connector permission. Admin protection configuration requires repository administration access.
- API environment metadata has security/configuration flags but lacks DATABASE_URL, REDIS_URL, storage credentials, SMTP, FX, Clerk and Razorpay provider inputs. No secret values recorded here.

## Database evidence and recovery

Neon project `wispy-lab-45598548`, production branch `br-spring-pine-azhbu0wx`, PostgreSQL 18.6, six-hour history retention, production branch unprotected. This is a separate legacy manual schema, not Alembic revision 094. There are 58 public tables, 29 `schema_migrations` rows through `028_export_delivery.sql`, and no Alembic version table. Only plpgsql is installed; pgvector is absent.

Aggregate state: **3 users, 12 transactions, 7 financial_accounts, 0 source_connections**, zero orphan transaction/user links and zero orphan account references. Actual financial or identity rows were not exported into this report.

Critical incompatibilities: legacy users use user_id and Firebase/Clerk IDs instead of current users.id/password/auth_epoch; transactions use amount_paise/direction/observed_at instead of amount/date/workspace; financial_accounts has no balance column. Balances, tombstones, transfers, duplicate flags, identity ownership and encryption compatibility cannot be guessed.

Recovery branch `br-delicate-rain-azukgwvq` (`recovery-pre-production-master-20261011`) pins parent LSN `0/4182630`, timestamp `2026-10-11T07:43:45Z`, without compute. Rehearsal branch `br-snowy-hill-az6xrk9v` exists with minimum compute. Restored independent branch `br-silent-butterfly-azzushi2` was created from the recovery branch, at the same LSN. Read-only restored checks returned identical 58 tables / 29 migration rows / 3 users / 12 transactions / 7 accounts / 0 connections and zero orphan links. This proves branching and aggregate restoration, not a migrated application or encrypted backup restore.

Direct native PostgreSQL from this Work shell fails DNS/network resolution; the Neon connector can query the isolated branches. No production migrations, stamping, resets or data conversion were run. Native application/driver rehearsal remains incomplete.

## Executable changes

1. Under the migration advisory lock, refuse unmanaged application tables before Alembic can create/stamp a history. Empty and malformed history are rejected; normal managed upgrade and genuinely empty installations remain valid.
2. Production readiness now checks core columns and exactly the current Alembic head (109), in addition to connectivity. Legacy or merely stamped-incompatible schemas return sanitized 503. Liveness remains independently usable.
3. Read-only inventory script reports metadata/counts/core mismatches in a stable PostgreSQL READ ONLY snapshot without dumping user rows. Identifiers are correctly quoted.
4. Disposable native PostgreSQL CI proof injects missing history, wrong head and missing core column in rollback transactions and verifies fail-closed behavior. Never targets production; requires explicit finco_ci disposable guard.
5. All GitHub action references in eight workflows pinned to verified canonical commit SHAs; CI defaults contents:read; Renovate maintains pins.
6. Production dependency audit found six affected packages / 33 advisory entries before changes. Upgrade cryptography 50.0.2, PyJWT 2.15.1, pypdf 6.20.0 and urllib3 2.8.0. Remove python-jose and its ecdsa/rsa dependencies after migrating JWT callers to PyJWT. Preserve fixed-algorithm MCP verification and manually enforce OIDC at_hash; reject symmetric OIDC signing algorithms. Final locked production dependency audit: no known vulnerabilities found at this checkpoint.
7. Exclude both /api and /mcp path namespaces from frontend SPA fallback. A missing MCP server must not masquerade as a working protocol endpoint.

## Dependency-ordered execution plan and release evidence

| Master steps | Work / required gate | Checkpoint |
| --- | --- | --- |
| A1 database forensics | Inspect metadata, historical schema and aggregate invariants; preserve recovery point | Completed read-only inventory and recovery branches |
| A2 rehearsal | Explicit legacy identity/ledger/workspace/encryption mapping, isolated conversion, native application tests and recovery | Blocked by missing mapping/encryption context and native database access; no guessed conversion |
| A3 cutover | Verified rehearsal, preservation checks, secret injection, rollback and approval gates from master | Not attempted |
| A4–A10 runtime | API, Redis, storage, email, Clerk identity transition, canonical routing and real frontend/backend E2E | Backend/schema/provider credentials unresolved; routing fail-closed fix prepared |
| B11–B17 product | Worker/scheduler, Razorpay success/failure matrix, FX, authorized bank, OmniRoute and deterministic Safe-to-Spend E2E | Provider/runtime acceptance remains pending; preserve existing engineering |
| C18–C21 operations | Founder legal details, deletion acceptance, encrypted backup restore and incident drill | Recovery clone proof completed; remaining live operations blocked |
| C22–C23 security | GitHub required checks, least privilege/pins, dependency/secret/code audit | Pinning/audit fixes implemented; admin-only protection unresolved |
| D24–D29 reliability | Observability draft, physical/browser devices, load, failure injection, fresh-user end-to-end | Existing drafts reviewed; full production acceptance remains pending |
| E30 final gate | Reconcile original roadmap and issue GO only from verified live evidence | NO GO |

Validation: frontend 862 tests / 109 files passed; frontend lint/build and npm audit passed (zero known npm advisories). Initial schema/runtime/migration-chain focused suite: 40 passed. JWT/provider/schema focused suite: 170 passed. Ruff and ty passed. Final expanded targeted and full backend suites and seven-check candidate CI are recorded in the durable final checkpoint when complete. An earlier full backend run was canceled after dependencies changed and is not claimed as final acceptance.

Security guard limits: the core-column gate detects critical compatibility failures, not every possible schema drift. Valid nonempty Alembic history still relies on Alembic's revision validation. Neither gate constitutes a legacy data migration, provider acceptance, complete Clerk conversion or release approval.

## Original 60-point reconciliation

Engineering, synthetic acceptance and live acceptance are separate. Historical merged work below is preserved, not newly certified as live. #52–56 are not silently promoted by #57.

| # | Original requirement | Verified status / remaining gate |
| --- | --- | --- |
| 1 | Production hosting provider/project select | Projects exist; API deployment canceled. Runtime acceptance blocked. |
| 2 | Production domain + HTTPS | Apex/www DNS and HTTPS frontend observed; API routing not live. |
| 3 | Payment provider choose | Razorpay decision preserved; no live payment acceptance. |
| 4 | Provider mapping for ₹99/₹999/₹349 | Merged engineering; provider plan objects and real captures unverified. |
| 5 | Indian AA/FIU partner select | Intentionally deferred; compliant partner/legal acceptance unresolved. |
| 6 | Production AI provider/model | OmniRoute architecture preserved; hosted model/credential acceptance unresolved. |
| 7 | Support email/channel | Email DNS exists; support delivery/owner acceptance unverified. |
| 8 | Operator/business identity | Operator identity/legal details require founder input. |
| 9 | Data-retention policy | Merged policy engineering; live lifecycle acceptance unverified. |
| 10 | Personal account deletion behavior | Merged behavior; real authenticated deletion not exercised. |
| 11 | Shared-workspace deletion policy | Merged policy; live workspace deletion not exercised. |
| 12 | Third-party processor inventory | Merged inventory; production processor reconciliation pending. |
| 13 | Production secret management | Vercel metadata checked; critical runtime credentials absent. |
| 14 | Prod PostgreSQL | Neon PostgreSQL 18.6 exists with incompatible legacy schema; no cutover. |
| 15 | Prod Redis/workers | No verified production Redis or worker runtime. |
| 16 | Object storage | R2 bucket exists; credentials and authenticated roundtrip unverified. |
| 17 | SMTP | Email DNS exists; SMTP API credentials/delivery absent. |
| 18 | FX provider | Real FX key absent from API deployment metadata. |
| 19 | First admin bootstrap | No compatible production schema; bootstrap not run. |
| 20 | Migrations 094–096 prod | Current head 109; legacy manual schema has 29 history rows. Conversion not run. |
| 21 | Existing-session migration | Legacy Firebase/Clerk IDs require explicit auth mapping; no session migration. |
| 22 | Old MCP token migration | Merged engineering; production MCP token acceptance unresolved. |
| 23 | Password reset email E2E | Merged tests; production reset email E2E blocked by SMTP/backend. |
| 24 | Verification email E2E | Merged tests; production verification email E2E blocked by SMTP/backend. |
| 25 | Backup + actual restore | Recovery branch restored into independent branch; counts/FKs checked. Encrypted backup/object restore drill still pending. |
| 26 | Disaster recovery runbook | Merged runbook; production incident drill pending. |
| 27 | Privacy policy publish | Legal publication/identity acceptance pending. |
| 28 | Terms publish | Legal publication/identity acceptance pending. |
| 29 | Personal deletion implementation/test | Merged engineering/tests; production deletion acceptance pending. |
| 30 | Shared-workspace deletion safeguards | Merged safeguards/tests; production acceptance pending. |
| 31 | Payment checkout/order creation | Merged payment lifecycle engineering/tests; provider-backed production acceptance pending. |
| 32 | Signed payment webhook | Merged payment lifecycle engineering/tests; provider-backed production acceptance pending. |
| 33 | webhook idempotency/event persistence | Merged payment lifecycle engineering/tests; provider-backed production acceptance pending. |
| 34 | payment→subscription activation | Merged payment lifecycle engineering/tests; provider-backed production acceptance pending. |
| 35 | renewal lifecycle | Merged payment lifecycle engineering/tests; provider-backed production acceptance pending. |
| 36 | failed/past-due/grace | Merged payment lifecycle engineering/tests; provider-backed production acceptance pending. |
| 37 | cancellation | Merged payment lifecycle engineering/tests; provider-backed production acceptance pending. |
| 38 | refunds | Merged payment lifecycle engineering/tests; provider-backed production acceptance pending. |
| 39 | payment failure scenarios | Merged payment lifecycle engineering/tests; provider-backed production acceptance pending. |
| 40 | AA consent/onboarding | Intentionally deferred AA integration; no consent onboarding acceptance. |
| 41 | AA account+transaction fetch | Intentionally deferred AA fetch; no live data. |
| 42 | liability classification | AA-dependent liability acceptance deferred. |
| 43 | AA refresh/expiry/revoke/reconnect | AA-dependent consent lifecycle deferred. |
| 44 | retry+dedupe | AA-dependent retries/dedupe live acceptance deferred. |
| 45 | Indian bank→Safe-to-Spend E2E | AA bank to Safe-to-Spend live acceptance deferred. |
| 46 | international bank provider live acceptance | User-paused international banking live acceptance. |
| 47 | Enable Banking liability mapping | Merged Enable Banking classification; real provider account acceptance pending. |
| 48 | SimpleFIN classification | Merged SimpleFIN classification; real provider account acceptance pending. |
| 49 | real AI connection | Actual production AI connection unresolved. |
| 50 | AI streaming/tools/RAG/error QA | Production streaming/tools/RAG/error acceptance unresolved. |
| 51 | External MCP HTTPS acceptance | Draft PR #56; public /mcp currently frontend HTML. HTTPS protocol/auth acceptance unresolved. |
| 52 | floating loan rates/daily interest/fees | Remaining engineering; not marked complete by milestone #57. |
| 53 | partial loan payments | Remaining engineering; not marked complete by milestone #57. |
| 54 | principal prepayment | Remaining engineering; not marked complete by milestone #57. |
| 55 | bank-verified loan repayments | Remaining engineering/provider acceptance; no bank-verified repayments proof. |
| 56 | duplicate EMI detection | Remaining engineering/provider acceptance; no duplicate EMI live proof. |
| 57 | PWA device testing | Merged engineering (PR #61); physical iOS/Android install and live gates pending. |
| 58 | full browser/mobile/desktop + production E2E + provider failure + load | Full live E2E, device and production load/failure proof pending. |
| 59 | operational polish | Observability draft #59 reviewed; operational live acceptance pending. |
| 60 | hardening report current status + final release gate | This checkpoint is NO GO; final launch gate remains open. |

## Unresolved concrete inputs and next action

- Secure native access to the rehearsal database and the legacy migration source/identity/encryption context. Define preservation mappings before any conversion; do not assign zero balances or invent passwords/provider ownership.
- Backend runtime and Redis/worker provisioning with protected DATABASE_URL/REDIS_URL and verified platform architecture. Current Vercel Services supports Celery; this project's Redis/Beat transport still needs explicit compatibility proof rather than assuming an old platform limitation.
- R2 service credential, authenticated SMTP sender/provider, FX key, Clerk production instance/auth transition, fresh Razorpay plan/keys/webhook input, AI routing host/provider input. Secure secret injection only.
- Founder operator/legal/support identity and applicable policy decisions; physical iOS/Android devices and genuinely authorized provider accounts.
- Repository administration capability for protected main and required checks; provider protection/backup retention settings need owner review.

Next engineering gate: verify this exact branch's full candidate tests and all seven CI jobs, then merge only the tested expected head, verify main CI/tree and deployment behavior. Next launch gate: explicit old-manual-schema conversion rehearsal with financial/identity preservation. No launch GO until fresh-user and provider-backed production journeys pass.

Primary references: GitHub secure-use documentation (immutable action SHAs, least privilege), official PyJWT usage documentation (OIDC at_hash requires caller validation), official cryptography/pypdf/PyJWT release notes, Neon branching documentation and current Vercel Celery documentation. No universal security guarantee is implied by a point-in-time package audit.
