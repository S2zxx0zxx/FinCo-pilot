# FinCo-Pilot → Clerk Auth Migration — Architecture & Release Contract (v1)
Status: **DESIGN + FOUNDATION ONLY**. Branch: \`feature/clerk-auth-migration\`. Do not deploy, switch auth providers, import user records, or disable legacy auth without the cutover gates below.

## Decision / boundaries
- Clerk owns authentication: primary sign-in/sign-up, credentials, recovery, MFA, passkeys, and session lifecycle.
- Existing FinCo-Pilot branded React UI remains the visual contract. Use supported Clerk React custom-flow APIs after confirming versions and complete MFA/first-factor requirements; do not paste or store passwords in FinCo-Pilot APIs.
- FastAPI owns resource authorization, role/tenant/workspace membership, subscription entitlements, account deletion/retention, fraud/abuse policy, bank permissions, and financial data.
- PostgreSQL \`users.id\` (UUID) **never changes**. Financial foreign keys stay intact. Clerk \`sub\` is an external identity, not a local user ID.
- **Never link by email alone**. Neither unverified Clerk email, frontend userId, JWT custom \`external_id\`, nor a webhook payload is sufficient ownership proof.
- **No production behavior changes on this foundation commit.** Existing password/passkey/TOTP routes remain intact until deliberate, tested cutover.

## Reviewed repository architecture (main at 3718e3f3249d41c5be7120b3cdca09bbac7aed89)
- \`frontend/src/App.tsx\`: React Router, \`AuthProvider\`, protected routes, account recovery.
- \`frontend/src/contexts/auth-provider.tsx\`: localStorage bearer JWT; \`frontend/src/lib/api.ts\`: central Axios bearer interceptor.
- \`backend/app/core/auth.py\`: FastAPI Users \`current_active_user\` + credential-stamped, revocable JWT. Used across many domain endpoints.
- \`backend/app/api/custom_auth.py\`, \`two_factor.py\`, \`passkeys.py\`, \`oidc_auth.py\`: local password, MFA, WebAuthn, external OIDC.
- \`backend/app/models/user.py\`: UUID user PK, financial/workspace links, existing OIDC issuer+subject. One OIDC identity slot is not sufficient as a universal multi-provider map.
- \`backend/app/core/config.py\`: legacy auth and OIDC settings. Do not set \`LOCAL_AUTH_ENABLED=false\` with missing OIDC configuration: current validation rejects it.
- \`backend/app/main.py\`: routes and FastAPI Users routes (including user updates/deletions) need separate cutover review.
- Key issue outside Clerk migration: demo Docker config previously used development debug/default secret, published DB/backend, and Vite dev server. Clerk does NOT fix these deployment issues.

## Target data-plane / control-plane
React original UI → Clerk React SDK (asynchronous session token; no localStorage bearer persistence) → Axios auth-adapter / dynamic \`getToken()\` → FastAPI JWT verification (RS256, known issuer, explicit authorized-parties, exp/iat/nbf, Clerk session) → **server-side external-identity map** → \`users.id\` → current authorization guards → workspace-scoped data.
Clerk backend operations (admin imports, revocations, webhooks) use server-side credentials **only** and never expose \`CLERK_SECRET_KEY\` to browser/GitHub.
Do not trust Clerk Organizations, profile public metadata, email, or subscriptions as authority for FinCo-Pilot financial tenant permissions; use local workspace membership and billing entitlements.

## Identity mapping
New table \`external_auth_identities\`:
- provider='clerk', issuer, provider_subject, user_id (FK users.id), timestamps.
- UNIQUE(provider, issuer, provider_subject); UNIQUE(provider, issuer, user_id).
- Enforce case-sensitive external subjects and exact issuer separation between dev/prod.
- New users: transactionally create local User + personal workspace/defaults + link once; unique violation -> idempotent lookup, never duplicate wallets. Confirm local registration policy and email-verification policy; disable signups during initial migration if needed.
- Existing users: **explicit one-time reauth** using local verified session + Clerk verified session, with anti-CSRF one-time nonce (Redis), recent-auth, explicit consent, and atomic unique-constraint conflict checks. No automatic account linking on email equality.
- Migration from existing password hashes only if exact hasher + digest format supported by Clerk (e.g. supported Argon2/bcrypt). No plaintext export, no logs. MFA/passkeys are not assumed transferable. Cohort test first.
- Legacy deleted/deactivated accounts cannot be resurrected by Clerk login/webhook. Fail closed if no local active mapping.
- Run dry-run import counts + signed-off snapshot, batch rate-limit/backoff, immutable audit report (no PII/passwords), reconcile all IDs. No email/financial-data dump to ChatGPT.

## Phases & strict go/no-go gates
0. **Baseline**: backup PostgreSQL + attachments, test restore; record counts/hash, active users, audit current flows; verify dev and release CI. Set an immutable main commit SHA. Check Clerk plan limits and availability of every desired factor.
1. **Isolation**: this branch only; compare HEAD to main. Feature flag default OFF; no production domain/keys. Prepare isolated Clerk Development instance and integration fixtures.
2. **Backend foundation**: verify Clerk RS256 session tokens (issuer, signature, time, authorized party, optional audience); reject malformed and impersonation/pending sessions; map by stable DB link; reject disabled/deleted users, unlinked identities; preserve existing authorization dependency contracts.
3. **Frontend**: add ClerkProvider behind explicit mode flag; preserve same visual login/register layout. Use supported *current* Clerk custom flows (including social sign-in, password, email verification, MFA, passkey, forgotten password, recovery). Ensure no credential POST to legacy endpoints in Clerk mode. Use getToken() per request, never persist Clerk session token in localStorage.
4. **User lifecycle**: implement secure explicit existing-account linking and idempotent new-user provisioning with workspace/wallet defaults; webhook events signature/timestamp verification, dedupe/out-of-order protections, deprovisioning, deletion and tenant rules.
5. **Account operations**: switch email/password/MFA/passkey management and reset/change-credential screens to Clerk flows; review users/me FastAPI Users routers, local-admin/create-user paths, invitation workflows, billing and support; prevent dual-auth confusion and accidental account takeover.
6. **Migration**: export only required local identities securely, choose Clerk supported password digest import or forced secure reset, process staging test cohorts, reconcile IDs, verify recovery and MFA re-enrollment. No production import without owner-approved schedule.
7. **Threat model / testing**: unit JWT fake RSA and malformed tokens; integration unauthorized/unlinked/disabled/deleted/link races; tenant cross-account BOLA/IDOR; CSRF and XSS; webhook forgery/replay; MFA recovery; role escalation; stale JWT after lock/revoke; browser E2E; load tests with measurable targets.
8. **Controlled rollout**: local → disposable staging → owner-only → small pilot → production; deploy prepared Clerk production instance with domain/redirects; configure fail-closed flag; collect auth failure rates, latency, signup conversions, errors.
9. **Cutover**: stop new legacy credential signups/changes; verify Clerk sign-ins, mappings, admin-only operations; expire/revoke legacy sessions deliberately; monitor. Only after an agreed rollback window retire legacy auth code/routes and remove obsolete credential data per approved retention plan.

## Test matrix / release gates
- Success: password and social sign-in, signup, forgot/reset password, verification, MFA enrollment and recovery, passkey flows where supported, logout-all-devices, inactive/locked user refusal, user profile update, signup-disabled, new-user defaults, account re-link denial, role and workspace access, financial data unchanged.
- Security: wrong issuer, invalid signature/alg, missing/invalid azp, expired/future tokens, wrong audience, pending session, impersonation, attacker-chosen subject, expired nonce, replayed linkage, forged webhooks, two simultaneous provision requests, 401/403 distinction.
- Regression: routes protected by \`current_active_user\`; BI/reporting/AI tasks, MCP, account deletion, payment webhook and billing roles; tests unchanged in legacy mode.
- Operational: explicit rollback drill in staging; feature flag OFF defaults to legacy behavior; backup/restore proof; no unencrypted secrets in repository; no public database/backend ports; suitable environment URLs, CORS and CSRF guards.
- **GO** only after all critical security tests pass, migration reconciliation matches expected records, owner authorizes final rollout, and production environment is separately hardened. Any missing prerequisite = **NO-GO**.

## Integration configuration (future phase; DO NOT set in main/production yet)
Frontend publishable key: \`VITE_CLERK_PUBLISHABLE_KEY\` (public).
Backend: \`CLERK_JWT_PUBLIC_KEY\` (PEM public; never signing private key); \`CLERK_ISSUER\` (exact HTTPS issuer); \`CLERK_AUTHORIZED_PARTIES\` explicit origins; optional \`CLERK_AUDIENCE\`; \`CLERK_SECRET_KEY\` (server only for backend management/import).
Mode flag \`AUTH_PROVIDER=legacy|clerk\` requires explicit validated full-stack implementation; **not yet wired**.
Development and production must have separate Clerk instances and keys.
Current foundation token verifier is deliberately unconnected to live routes until tested.

## Rollback & destructive-operation controls
- Before cutover: toggle **legacy** mode and redeploy; ensure legacy credential accounts still work. Feature flags do not reverse a completed Clerk migration by themselves if password paths have been retired.
- After migrations: schema changes are additive; do not automatically drop identity links or user data. Never downgrade schema automatically on production failure.
- Do not modify/update/delete external Clerk users without an owner-approved migration batch and reversible reconciliation.
- Run no bulk password resets, account imports, auth deletion, or data change during architecture/foundation stage.
- Existing Cloudflare Access owner-only investor demo remains separate from product authentication.

## Verified references
- https://clerk.com/docs/guides/sessions/session-tokens
- https://clerk.com/docs/guides/sessions/manual-jwt-verification
- https://clerk.com/docs/guides/development/migrating/overview
- https://clerk.com/docs/reference/backend/user/create-user
- https://clerk.com/docs/react/guides/development/custom-sign-in-or-up-page
- https://clerk.com/articles/how-to-add-authentication-to-a-python-backend
