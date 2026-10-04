# Verification email E2E — roadmap #24

## Current repository inventory and decisions

The repository already had the FastAPI Users verification routes, signed one-hour links, canonical-origin SMTP templates, resend and verification screens, a stored `is_verified` ownership flag, OIDC verified-email policy, and admin/programmatic verified-account paths. Roadmap #23 already supplied URL cleanup, no-referrer/no-store edge protection, delayed checkout SDK loading, bounded TLS SMTP, and a generic reset-request coordinator. This checkpoint extends those components rather than replacing them. No database migration or financial-data deletion is required.

Verification is ownership evidence for the current account email. It does not issue a login token, grant roles/workspace/paid access, disable MFA, change password or auth epoch, or auto-activate an inactive account. Existing local login accepts active unverified users; this compatibility policy remains unchanged. OWASP recommends gating account use until ownership verification. That stronger product policy is **not implemented or claimed** here: blanket gating would lock out existing users and requires a separately planned adoption/exception policy. OIDC issuer/email linking controls remain unchanged. Verification is not a strong second factor.

## Backend contract

`POST /api/auth/request-verify-token` accepts a valid email with generic HTTP 202 before background account lookup and SMTP submission. Known eligible, unknown, inactive, already-verified and recipient-specific SMTP failure cases have the same public acceptance body. A 202 means accepted, not delivered. Invalid request shape/email remains 422. Missing required SMTP configuration and shared process-capacity exhaustion return identical 503 behavior for every address. Existing local-auth-disabled and per-IP throttling dependencies remain attached.

Reset and verification requests share the existing coordinator's maximum eight active background tasks per process and independent task database sessions. Each purpose has a separate three-attempt/hour recipient quota; HMAC keys avoid storing email addresses in limiter keys. The legacy reset quota prefix is retained. SMTP's existing bounded concurrency, TLS and socket timeouts continue to apply. A process crash can lose an accepted request. No token-containing durable outbox, unbounded queue or ambiguous-send retry is introduced.

Normal HTTP registration schedules an initial verification request after committed account/workspace/category/rule creation. A configuration/capacity/limiter refusal cannot misreport the committed account as a failed registration. Recipient/provider failures are bounded operator warnings; users can use manual resend. Programmatic/admin registration and OIDC flows retain their existing behavior. Signup guidance describes verification without promising inbox delivery.

`POST /api/auth/verify` retains the installed library's response and error contract. Validation pins HS256 and requires `sub`, `aud`, integer `exp` and a well-formed string `email`; malformed, expired, wrong-audience/signature/identifier/email tokens receive bounded bad-token errors. The user row is locked and refreshed before current active-state and ownership checks. The installed library rechecks expiry after lock acquisition, matches the current email according to its existing SQLAlchemy comparison policy, checks the matching subject and rejects already-verified users before changing only `is_verified`.

PostgreSQL serializes competing attempts: one succeeds and the other observes already-verified state. Valid unexpired links issued by the previous library format remain compatible. No provider-specific dot stripping or new local-part normalization is introduced. Existing email updates reset ownership; a pre-change link fails while the current address differs. This uses existing flag/current-email lifecycle semantics, not a permanent consumed-token ledger: changing away and back to an equivalent address can make an old unexpired link eligible again. Link expiry still bounds that compatibility window. Do not claim permanent nonce revocation, reauthentication-gated email change or a new two-address-confirmation workflow from this checkpoint.

## Frontend and edge

Verification requires an explicit form action; merely opening a link does not consume it, which avoids automated mail scanners verifying accounts. Tokens are removed from navigation through history replacement and retained only in component memory. Missing and expired/reused links show resend guidance. Success updates only the ownership flag of the matching currently signed-in account, guarded by account ID and the still-current stored session token. A late response cannot adopt another identity, create a session or restore logged-out state. Anonymous verification remains supported.

The #23 no-referrer, no-store, path-only access logs, recovery error-log suppression and explicit-action checkout SDK loader apply to `/verify-email` as well. Real Nginx proof covers Compose/image and Helm recovery locations. Independently managed ingress/CDN logs still require deployment verification; SPA URL cleanup cannot erase the original incoming request or upstream logs.

## Acceptance and engineering evidence

Tests cover the HTTP resend → real synthetic TLS relay → canonical-origin link → successful verify → replay rejection journey, no token/recipient public logs, fresh ownership state and preserved credentials/session; strict malformed claims; inactive/current-email mismatch; indistinguishable acceptance; private separate-purpose recipient quotas; unavailable configuration/shared capacity; initial signup mail scheduling, provider failure and successful resend; actual email-update ownership reset; MFA preservation and normal MFA login requirement. Frontend tests cover anonymous success, resend guidance, matching-account flag updates, wrong-account rejection and late-session/logout rejection, alongside existing recovery/privacy and session regressions.

CI runs the full backend/frontend lint/type/build/test gates plus an isolated disposable PostgreSQL two-session verification race. Existing Redis admission and recovery-edge proofs remain applicable to the reused coordinator and `/verify-email`. Final PR evidence records exact final-head run results; a local SQLite test cannot prove row locking and a synthetic SMTP relay cannot prove real inbox arrival.

## Live acceptance — pending

No VPS or authorized live SMTP inbox has been supplied. To close the original live #24 gate later:

1. Deploy tested backend/frontend/edge together with canonical HTTPS frontend URL, required SMTP TLS, sender-domain authentication and ingress/CDN token-query redaction.
2. Register an authorized synthetic test account through the public UI. Record acceptance and actual inbox/spam arrival without copying bearer values into logs/tickets.
3. Verify correct configured host/path and expiry; complete explicit verification and confirm current-email ownership state. Confirm no automatic session/role/paid/MFA changes, replay rejection and expired-link resend UX.
4. Exercise resend and unknown/inactive/already-verified behavior, recipient/IP limits, SMTP rejection/configuration/capacity failure visibility and committed-signup recovery.
5. Confirm real browser no-referrer/no-store behavior and upstream log redaction. Keep real deployment/inbox evidence pending until actually observed.

Next original roadmap item after this engineering checkpoint is #25 Backup + actual restore. This document does not mark #25 completed.

## Primary sources

- [OWASP Email Validation and Verification Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Email_Validation_and_Verification_Cheat_Sheet.html): identity comparison policy, expiring single-use ownership proof, anti-enumeration, and verification versus authentication. The stronger account-use gating recommendation is explicitly distinguished above from current compatibility policy.
- [FastAPI Users UserManager](https://fastapi-users.github.io/fastapi-users/latest/configuration/user-manager/): lifecycle hooks and token settings. Installed manager/router/JWT/database adapter source was inspected directly for actual behavior and retained-format compatibility.
