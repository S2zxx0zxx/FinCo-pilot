# Production sign-in redirect incident — 2026-10-12

## Evidence (read-only)

- `https://fincopilot.app/login` renders a Clerk Google sign-in control.
- `https://api.fincopilot.app/api/health` returned `{"status":"alive","application_ready":false}` during the incident.
- `https://api.fincopilot.app/health` returned `application_not_ready`.
- Vercel `fincopilot-api` grouped **39** `API bootstrap blocked by invalid configuration` errors across the last 24 hours (observed 2026-10-12).
- `backend/app/vercel_entry.py` intentionally serves only diagnostics and 503 on application routes if Pydantic settings validation fails.
- Frontend rewrites `/api/*` to `https://api.fincopilot.app/api/*`. Clerk OAuth can return to `/sso-callback` without the necessary API token exchange succeeding.

**Confirmed blocker:** production API configuration validation is failing. Do not infer that the OAuth provider or the financial database is faulty solely from the redirect.

## Production API environment gap (project-scoped Vercel variables)

A read-only list of `fincopilot-api` project environment variable *names* (not decrypted secrets) shows hardening flags but no project-scoped values for these dependencies:

| Dependency | Required variables to verify and configure securely |
| --- | --- |
| Neon PostgreSQL | `DATABASE_URL` (the existing approved production branch, asyncpg-compatible DSN) |
| Managed Redis | `REDIS_URL` (authenticated `rediss://` endpoint) |
| Cloudflare R2 | `STORAGE_S3_ACCESS_KEY`, `STORAGE_S3_SECRET_KEY` |
| FX provider | `OPENEXCHANGERATES_APP_ID` (`REQUIRE_FX_PROVIDER=true`) |
| Transactional email | `SMTP_HOST`, `SMTP_FROM_EMAIL` (also the provider's required credentials, since `EMAIL_DELIVERY_REQUIRED=true`) |
| Clerk API bridge | `CLERK_ENABLED`, `CLERK_ISSUER`, `CLERK_SECRET_KEY`, `CLERK_JWT_PUBLIC_KEY`, `CLERK_AUTHORIZED_PARTIES` (only after approved identity linking) |

Vercel shared variables, environment integrations, deployment-specific inherited values or another secret source may exist. The list alone does not prove a specific value is missing *from every source*. However, live `application_ready:false` proves the effective production configuration is currently unusable.

Production variables already configured include `DATABASE_EXTERNAL_REQUIRED=true`, `REDIS_EXTERNAL_REQUIRED=true`, `REDIS_TLS_REQUIRED=true`, `REDIS_AUTH_REQUIRED=true`, `STORAGE_PROVIDER=s3`, `REQUIRE_OBJECT_STORAGE=true`, and `REQUIRE_FX_PROVIDER=true`. Their checks are deliberate. **Never** set these to false to bypass bootstrap.

`fincopilot-web` exposes no project-scoped production `VITE_CLERK_PUBLISHABLE_KEY` in the same API read; independently verify its build-time source and the **currently aliased deployment**, since the live UI displays Clerk.

## Critical Neon schema mismatch — do not connect blindly

The connected Neon `FinCo-Pilot` project, branch named `production`, was inspected **read-only**. Its public schema has `financial_accounts`, `schema_migrations`, and `users.user_id` as the primary key. It does **not** have the `accounts`, `external_auth_identities`, `alembic_version`, or `users.id` required by this GitHub FastAPI backend's models/Alembic migrations.

Therefore **do not** automatically configure `DATABASE_URL` with that Neon branch. It appears to belong to a different application schema or revision. The correct current FastAPI production data source must first be identified and verified without modifying any records. Never run an Alembic upgrade against an unknown financial database.

## Safe operator recovery order

1. **Freeze deployment and back up:** record current Vercel deployment IDs, config *names and scopes* (not secret values), and the Neon production branch snapshot. Do not reset tables, issue replacement JWT signing secrets, or re-link existing financial users by email.
2. **Resolve infrastructure:** confirm which schema-compatible PostgreSQL database/branch, Redis instance, R2 bucket/prefix, FX provider, and SMTP identity are the approved live resources. Confirm availability and permission before referencing any of them.
3. **Set real secrets securely:** supply the missing environment settings to `fincopilot-api` production through Vercel encrypted/sensitive variables or approved integration; do not put values into Git, logs, PRs, or the frontend. Retain existing `SECRET_KEY`, `CREDENTIAL_ENCRYPTION_KEY`, `CORE_COPILOT_SIGNING_KEY`, and object prefix exactly unless an independently planned rotation is approved.
4. **Redeploy API only**, then independently check `/api/health/ready` for HTTP 200 (not just a successful build or `/api/health` liveness). Inspect server logs for config faults without logging credential values.
5. **Verify Clerk identity bridge:** frontend publishable key from the same Clerk instance, backend `CLERK_ISSUER` / public verifier / authorized parties / secret, live Google redirect allowlist, and mapping of existing financial account UUIDs. An unknown legacy user should remain blocked (`403 Existing account requires an approved identity mapping`) until a separately reviewed migration links the identity.
6. **Test an isolated approved test identity:** Google redirect `/sso-callback` → frontend `/api/auth/clerk/exchange` success → `/api/users/me` success → dashboard, refresh and logout. Verify correct workspace isolation and no regressions in email/password or MFA.
7. **Only then promote UI fixes:** frontend changes in this branch distinguish 5xx from 401/403, fail closed when `/users/me` cannot verify the user, and prevent retries that flood `/auth/clerk/exchange`.

## Why frontend fix alone cannot restore login

`/api/auth/clerk/exchange` is an application route. While Vercel bootstrap returns `application_not_ready`, every exchange fails regardless of the frontend redirect strategy. Any PR may improve failure handling, but **live login is not fixed until the API is ready and the end-to-end callback succeeds**.
