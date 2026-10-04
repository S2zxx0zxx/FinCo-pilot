# Password reset email E2E — roadmap #23

## Contract and implementation

A valid reset link changes only the password. It never signs the user in automatically, disables MFA, deletes recovery codes, edits financial records, or changes workspace access. Normal login and configured MFA still apply. The new hash invalidates old credentials-bound sessions and registered MCP credential stamps. Reset links retain the existing FastAPI Users password-fingerprint format, so valid unexpired previously issued links remain compatible.

Reset validation now requires subject, audience, expiry and password fingerprint, pins HS256, validates identifier/fingerprint/timestamp types and maps malformed/unrecognized hashes to bounded bad-token errors. PostgreSQL locks and refreshes the user row before fingerprint verification. Concurrent attempts using the same link serialize; only the first can change the hash. Expiry is rechecked after the lock by the underlying library. A failed password-policy check does not consume the link. The existing 8–128 character password policy is retained.

The forgot-password endpoint returns generic HTTP 202 before background account lookup and SMTP submission. It means request acceptance, **not delivery**. Unknown/inactive accounts and recipient-specific SMTP failures have the same public acceptance contract. Production configuration failure and process capacity exhaustion return the same 503 for all addresses. Local-auth-disabled policy still rejects recovery routes. Required SMTP remains strict internally and emits bounded operator failures; the public endpoint does not leak provider/recipient-specific failures. This supersedes the older inline forgot-password hook behavior in the #17 SMTP checkpoint, while verification-email behavior remains separate (#24).

Existing per-IP throttling is retained. A recipient limit adds three attempts per hour across client IPs, keyed by an HMAC of the normalized address rather than raw email. Redis transactions serialize sliding-window admission; unique request members avoid timestamp collisions. A per-process limit admits at most eight simultaneous recovery tasks without an unbounded queue. Background tasks use independent database sessions; mail concurrency/socket timeout remain controlled by the SMTP service. A process crash can lose an accepted request. There is deliberately no raw-token durable outbox or automatic ambiguous-send retry; the user can request another link after the limit window.

Password-change notification contains no password/token. Notification failure is recorded separately after a successful password commit and does not misreport the reset as failed. Request/email/token/provider text is not logged by the recovery coordinator.

## Browser and edge privacy

The recovery form keeps the token in component memory and removes it from the URL with history replacement before submission, including on failed/expired-link attempts. Each recovery route has its own component key. Global early `no-referrer` meta and Nginx policy prevent URL referrer leakage. Razorpay SDK is loaded only for an explicit checkout action, with a shared bounded loader and retry after failure; it is not globally executed on reset pages. Concurrent checkout-start clicks are guarded during SDK/order setup.

Compose/image and Helm Nginx use path-only access logs without query strings/referrers. Dedicated recovery URL locations suppress error-log request URIs and serve the SPA with no-store. External ingress/CDN/provider logs must also redact recovery query values: application configuration cannot prove an independently managed edge is safe. A token exists in the initial incoming URL before the SPA runs; URL cleanup does not erase upstream or already-existing history records. Treat forwarded links, browser extensions and XSS as separate trust risks.

## Verification

Local tests run the full HTTP forgot/reset/login journey against a real synthetic TLS SMTP peer: capture mail, validate configured origin despite a forged Host header, parse link, reject weak password, reset successfully, deny replay, deny old session/password, and accept normal new-password login. Additional tests cover missing/expired/mistyped claims, wrong audience/signature, invalid fingerprint, unknown/inactive/delivery-failure acceptance, private recipient limit keys, unavailable configuration and MCP credential-stamp invalidation. Existing auth/session/SMTP/rate-limit suites remain covered.

CI runs full lint/type/build/backend/frontend checks, a dedicated PostgreSQL race proof in an isolated disposable schema, and a real Redis twenty-attempt limit proof (exactly three admitted). These are synthetic engineering proofs, not real inbox or production-deployment evidence.

## Live acceptance — still pending

No VPS, authorized production account or live SMTP inbox has been provisioned for this project. Do not mark the original live #23 acceptance done until the following evidence exists:

1. Deploy the tested backend/frontend/edge together; verify required SMTP, HTTPS canonical origin, ingress/CDN query redaction, no-store and local-auth/MFA policy.
2. Use an authorized test account and request a reset through the real public UI. Record request status and mail timestamp without copying bearer values into tickets/logs.
3. Verify actual inbox/spam delivery, From/domain authentication and the exact configured HTTPS host/path. SMTP DATA acceptance alone does not prove this.
4. Set a valid password through the received link, verify success and the change-notification email. Verify normal new-password login and MFA, old-password/session/MCP denial, replay denial and expired-link UX.
5. Verify unknown-address and recipient-rejection public behavior, real per-IP/per-recipient limits and operational SMTP failure visibility. Reconcile delivery failures without claiming the password was unchanged after successful reset.

Any result lacking real inbox/client evidence stays pending. No production account or secret was changed while building this checkpoint. Next original roadmap point is #24 Verification email E2E; it has not been completed by #23.

## Primary guidance

- [OWASP Forgot Password Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Forgot_Password_Cheat_Sheet.html): consistent account-existence responses, expiring single-use credentials, rate limits, no-referrer, no automatic login and notification.
- [OWASP WSTG reset testing](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/04-Authentication/09-Weak_Password_Change_or_Reset_Functionalities): token privacy, replay and lifecycle testing.
- Installed FastAPI Users manager/router source and its JWT decoder were inspected directly before retaining and strengthening the current fingerprint contract.

## Roadmap #24 coordinator follow-up

Verification now reuses the generic request coordinator with a separate `email_verification` recipient quota and the same eight-task per-process capacity. Reset response, legacy quota prefix, fingerprint validation and notification behavior are retained. See [verification checkpoint](FINCO_VERIFICATION_EMAIL_E2E_V1.md) for signup/ownership/compatibility decisions and live gates.
