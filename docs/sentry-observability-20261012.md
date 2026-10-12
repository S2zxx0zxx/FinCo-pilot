# Sentry observability — staged integration and production acceptance

**Baseline:** `S2zxx0zxx/FinCo-pilot` main at `dde45d069e57e3fc3c37eb1f26477356332515de`.
**Isolation:** Feature branch only, no production migration, no financial-data changes.
**Current status:** Code integration staged; Sentry organization/project/DSN/alerts **not verified or configured**. Sentry plugin available in this session is read-only and `SENTRY_AUTH_TOKEN` was not present. DO NOT mark live monitoring as activated.

## What the code instruments

- FastAPI unhandled errors and Celery worker exceptions through the official pinned Python SDK.
- Browser/React unexpected errors and existing application error boundary through the official pinned React SDK.
- Separate `api`, `worker`, `web` component tags, production/preview labels and deploy release naming.
- Server error sampling 100% when explicitly enabled. Browser errors only when enabled.
- Private JavaScript source maps uploaded at build time *only* when all three Sentry build inputs are present. Vite uses hidden source maps, deletes artifacts after upload and fails the configured build on upload failure.
- No session replay, screenshot/DOM capture, personally identifiable users, financial payloads, local variables, cookies, authorization headers, breadcrumbs, request context, user IDs or query strings; tracing and profiling are disabled by default because route/span payloads can include confidential finance data.

This implementation deliberately does **not** add a public error-test endpoint, inject synthetic financial data or replace the existing authenticated Prometheus counters.

## Real account prerequisites — not guessed

Use only the owner's **actual** Sentry organization and projects. Ideally create separate React and Python projects, with the API and workers sharing a backend project and a `component` label. Do not invent a DSN, email or project. Review organization retention, data processing agreements, sampling and membership before enabling.

### Vercel production `fincopilot-api` (server-side only)

Configure through Vercel protected settings (never commit or paste secrets):

- `SENTRY_ENABLED=true`
- `SENTRY_DSN` = **actual Sentry Python project HTTPS DSN**, stored as sensitive server-only variable
- `SENTRY_ENVIRONMENT=production`
- `SENTRY_RELEASE` = the actually deployed Git SHA (if unset, Vercel commit SHA is used)

### Vercel production `fincopilot-web`

- `VITE_SENTRY_ENABLED=true`
- `VITE_SENTRY_DSN` = **actual Sentry React project HTTPS public ingestion DSN**
- `VITE_SENTRY_ENVIRONMENT=production`
- Build-only variables: `SENTRY_ORG`, `SENTRY_PROJECT` and **secret** `SENTRY_AUTH_TOKEN` with project/release upload privileges. The build token must **never** use a `VITE_` or `NEXT_PUBLIC_` prefix.
- Build must upload private, release-matched hidden source maps; public `.map` files must not ship. Inspect the deployment *after* build.

### Self-hosted Compose and Kubernetes

- Development Compose may pass an opt-in local DSN through environment; do not commit it.
- Production Compose: place the backend Sentry DSN in a restricted file `${FINCOPILOT_SECRETS_DIR}/sentry_dsn` mounted read-only as `/run/secrets/sentry_dsn`; set `SENTRY_ENABLED=true`. Never interpolate a production DSN into Compose yaml.
- Helm: place `SENTRY_DSN` and optionally `SENTRY_ENABLED` in the existing *operator-owned Kubernetes Secret* referenced by `global.existingSecret`; workload `envFrom` already injects this. Do not inject secrets in ConfigMaps.

### Acceptance before enabling real notifications

1. Verify actual organization ownership, backend and web projects, valid HTTPS DSNs, access scopes and privacy/retention settings.
2. Confirm Vercel's **frontend** production commit matches reviewed main/merge commit; do not confuse READY deployments with healthy API. Existing PostgreSQL legacy schema and HTTP 503 readiness must be fixed independently before launch.
3. Run locked CI: secret hygiene, full backend tests, TypeScript, lint, npm audit, frontend/browser/PWA acceptance, schema checks and Redis worker checks.
4. With a safe non-sensitive QA-only exception, verify web error and backend/worker error appear in their correct project with environment and matching release; inspect the **actual event JSON** to ensure no financial values, email, IP, cookies, URL token, local variables or headers are present. Confirm sourcemap frame mapping and that public `.map` URLs return 404.
5. In Sentry account, add owners/teams and mobile/email alerts for **new issues, regressions, repeated backend exceptions and availability/error-rate thresholds**; test notification delivery on your phone. Do not claim an alert rule exists without querying it.
6. Verify inbound volume/rate limits, data retention and operational response procedure. Existing Prometheus metrics remain authoritative for server availability until a proven external monitor is configured.

## Rollback

Set `SENTRY_ENABLED=false` on backend and `VITE_SENTRY_ENABLED=false` on frontend, then redeploy. Existing finance routes, data, auth, billing and migration state remain unchanged. Disable Sentry ingestion/alert rules separately if desired. Never expose or rotate app authentication/database secrets merely for observability.

## Reason release is blocked

The Sentry plugin installed for this session supports **read-only issue/event API requests** and requires an externally configured `SENTRY_AUTH_TOKEN`; none was available. It cannot create Sentry projects, DSNs or alert rules. The connected Vercel projects do not currently expose the verified Sentry project/credential inputs. Application observability is therefore **code-staged, not live-active**.
