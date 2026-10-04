# Roadmap #21: existing-session migration

Scope: interactive API sessions and frontend transition. External MCP token migration is #22. Actual production acceptance remains pending without a deployed authorized target. No user records, password hashes, factor seeds, recovery codes or financial rows are rewritten by this migration.

## Decision and compatibility matrix

| Existing state | Release behavior |
| --- | --- |
| Pre-credential-stamp JWT | 401; authenticate again using normal password/OIDC/passkey and required MFA. No automatic conversion or grace period |
| Current stamped JWT with required exp/sub/aud, supported signature and matching current password/epoch | Accepted while unexpired and user active, including empty legacy auth_epoch |
| Missing/invalid expiry, wrong audience/algorithm/signature or malformed/non-ASCII stamp | 401, no server exception/token logging |
| Session issued before password change, logout-all or MFA lifecycle epoch rotation | Rejected using refreshed current DB state |
| Old in-flight request rejects after a new token was installed | Only that request fails; the replacement session is preserved |
| Current session rejects in same tab, other-tab sign-out or storage clear | Clear local identity and private query cache; require login |

No broad forced auth_epoch rewrite is needed to reject unstamped sessions. It would unnecessarily revoke valid current sessions. Stateless JWTs cannot provide an inventory of all browser sessions; do not claim a database audit counted or converted them. Signing secrets are not rotated just to implement this transition; key rotation is a separate release decision with its own session impact. No refresh-token endpoint, background JWT exchange or trust of browser-decoded claims is introduced.

## Findings, plan and implementation

1. Read actual installed FastAPI Users JWT strategy and application issuance/verification, MFA/logout/password paths, Axios interceptors and cross-tab cache behavior.
2. Enforce server-issued session claim shape: sub/aud/exp/stamp required, pinned algorithm/audience, expiry validation and lowercase 64-hex HMAC stamp. Catch invalid input before DB reads; refresh current password/epoch/activity before stamp comparison. Existing current issuance remains compatible.
3. Bind frontend 401 invalidation to the rejected request's actual Authorization header and current local token. Preserve explicit headers for logout so replacement login does not change which token is sent.
4. Notify the same-tab auth provider when current-token rejection occurs. Clear private query cache on rejection, token/account adoption and cross-tab sign-out/storage clear. Use a cancellable token probe; stale responses never install another account's identity. Authenticated same-account MFA replacement responses explicitly retain the current identity during revalidation so recovery-code screens stay mounted; generic account adoption clears it.
5. Regression matrix covers real API rejection and logout/re-login, real Axios interceptor behavior, cross-tab/current-token cache isolation and late account probes. Run full existing CI before finalizing reviewed branch.

## Rollout and real acceptance (pending)

- Identify reviewed release commit and confirm application schema including auth_epoch; coordinate #20. Existing main head requires 098 when encrypted-seed code is included.
- Drain old replicas and deploy the same release/signing configuration to every API instance. An old instance accepting unstamped tokens invalidates the migration guarantee. Do not roll back to permissive code while claiming enforcement complete.
- Communicate that legacy sessions require re-login. Confirm the actual operator can authenticate and recover using already established identity/provider/MFA custody. Never mark an email verified or bypass MFA to resolve a migration failure.
- In authorized staging, use synthetic accounts to exercise pre-stamp rejection/current session preservation, password/MFA/logout-all revocation, ordinary-user/admin boundaries and rejection after restart across replicas. Never capture real tokens in reports.
- With controlled browser tabs, confirm migration redirect/login flow, financial cache clearing, cross-tab sign-out and a delayed old request after re-login. Network failure alone does not prove server revocation.
- Preserve redacted timestamp/target/commit/status evidence. Real production deployment/session acceptance is separate from unit/API/CI proof. User instructed reviewed code may merge before hosting exists.

## Limits

Existing localStorage token storage is retained, not changed into an HttpOnly cookie design; XSS/session theft is a separate remaining architecture risk. Logout remains all-sessions, and offline failure cannot guarantee immediate server revocation. A request already authorized before a concurrent revocation may finish; this is not a retroactive cancellation guarantee. Provider/session checks do not prove absence of every vulnerability or replace #22 external token migration. Browser extension state, service-worker caches and arbitrary third-party persistence are not enumerated by TanStack query-cache clearing.

## Primary research

- RFC 8725 JWT best current practices: https://www.rfc-editor.org/rfc/rfc8725
- OWASP JWT validation/revocation: https://cheatsheetseries.owasp.org/cheatsheets/JSON_Web_Token_Cheat_Sheet.html
- OWASP session lifecycle: https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html
- Installed FastAPI Users JWT strategy was inspected directly; application-specific required claims are enforced above its generic validation.
