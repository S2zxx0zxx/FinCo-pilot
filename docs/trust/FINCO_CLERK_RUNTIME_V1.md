# Clerk runtime bridge — Phase 2 (disabled by default)

Source branch: `feature/clerk-auth-runtime-v1`

## What is implemented

- GET `/api/auth/clerk/me` is **404** until the backend flag `CLERK_BRIDGE_ENABLED=true` is set.
- When explicitly enabled, it validates a Clerk-issued RS256 session token using the pinned public key, HTTPS issuer, expiry/not-before, exact browser origin (`azp`), and session claims. It rejects impersonation/pending sessions.
- It maps only the token's signed `sub` + `iss` to `external_auth_identities`; no email-based linking or silent registration.
- Linked local User must be active and must not be in deletion execution/tombstone states.
- The endpoint only returns the existing `UserRead` identity; **it does not grant financial routes access via Clerk yet**. Existing FastAPI Users JWT login, React UI and financial routes stay unchanged.
- Tests use fake RSA keys and test DB accounts, no real Clerk traffic.

## Not enabled / missing by design

- Clerk publishable key / real issuer/public verification key must come from a trusted **Development** Clerk instance.
- No browser SDK, no passwords, no MFA or passkeys migrated, no existing account linking API, no new user onboarding, no webhooks, no auth cutover.
- Do not set `LOCAL_AUTH_ENABLED=false` or deploy a partial bridge to production as "completed Clerk auth."

## Configuration for future isolated development test (never commit secrets)

```ini
CLERK_BRIDGE_ENABLED=false
CLERK_ISSUER=https://YOUR-DEV-ISSUER.clerk.accounts.dev
CLERK_JWT_PUBLIC_KEY="-----BEGIN PUBLIC KEY-----..."
CLERK_AUTHORIZED_PARTIES=http://localhost:3000
CLERK_AUDIENCE=
```

Do **not** turn the flag on without configuring the real issuer and public key; startup validates these. Never put `CLERK_SECRET_KEY` in React or GitHub. Production must use distinct keys/instance, https origins and approved operational changes.

## Next engineering tasks

1. Confirm Clerk Development application's publishable key (safe to share), issuer, chosen sign-in methods, and a supported `@clerk/react` version.
2. Add Clerk SDK and re-generate/commit npm lockfile; introduce independently tested frontend auth adapter behind feature flag OFF.
3. Implement explicit dual-proof linking (signed local recent-auth + signed Clerk session, one-time CSRF nonce, uniqueness and audit), signup provisioning, migration and recovery workflows.
4. Centralize FastAPI `current_active_user` / superuser dependencies to accept Clerk sessions only in a strict cutover mode, preserve financial policy, disable legacy mutation/auth routes; test all protected routes.
5. Complete custom original login UI flows including Device Trust, MFA, passkeys and account recovery. Plan import/re-enrollment and outage rollback.
6. Enforce lifecycle/webhook anti-replay, account deletion/revocation and session invalidation, with full staging/E2E and migration reconciliations.

Read `docs/trust/FINCO_CLERK_AUTH_MIGRATION_V1.md` for full go/no-go and roll-back plan.
