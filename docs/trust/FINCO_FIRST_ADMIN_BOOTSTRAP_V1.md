# First admin bootstrap v1 — roadmap 19

## Scope and completion gates

Create the first local administrator deliberately, once, with the existing password hasher and RBAC. Do not promote a public signup, infer an operator identity, or mark an unverified email verified. No real production administrator has been created by this implementation. Actual operator-selected identity, production execution, login, administrative authorization and MFA evidence remain deployment gates.

## Provisioning contract

The protected setup API and operator CLI share one provisioning service. The caller commits the user, owner workspace/membership, free subscription, wallet, category/rule seeds and `security.first_admin_bootstrap.v1` completion record in one transaction. Seed helpers retain their historical commit behavior for other callers. JWT generation also precedes API commit, so a signing failure does not strand bootstrap.

The fixed AppSetting primary key arbitrates concurrent bootstrap requests across processes. A conflicting insert waits for transaction completion and fails closed after a committed winner. A failed winner releases its claim on rollback. A second user-count check follows the claim. The committed record permanently closes bootstrap even when users are removed. Preserve this record in backups and restores; never delete or rewrite it to reopen setup. Existing deployments with users also close setup without attempting a role promotion.

Public registration in production requires an existing active administrator, preventing public signup from taking the empty database before bootstrap. Bootstrap should be performed before exposing OIDC callbacks or other identity-creation surfaces. OIDC-only administrator provisioning requires an explicit trusted identity-provider role policy; it is not silently converted to local authentication.

Production/staging API setup requires a token of at least 32 characters. Production configuration rejects whitespace and short tokens. Configure a cryptographically random token through the existing secret mechanism. Disabled or invalid-token endpoints return 404. Local authentication must be enabled. The status endpoint advertises the environment's password minimum and closes when setup is unavailable. API requests use the existing login rate limiter. Never put the setup token in a URL.

Passwords use the existing password helper. Development retains the 8-character compatibility minimum; staging and production require 15–128 characters. The frontend obtains the minimum from the API. Currency must be supported. Successful audit logging includes only user UUID; completion metadata contains event/version/UUID/UTC time, never email, password or setup token.

## Operator execution

1. Verify migrations, database target, secret configuration and backup readiness. Keep public traffic closed until bootstrap completes. Select the real administrator email explicitly.
2. Temporarily enable `SETUP_ENABLED=true` with local authentication and a strong setup token. Prefer the protected setup UI over any ad hoc SQL role update, or run the CLI inside the trusted backend environment:

   ```sh
   python -m scripts.bootstrap_first_admin --email YOUR_OPERATOR_EMAIL --currency INR --language en
   ```

   It prompts twice without echo. Automated execution may supply `--password-file` referencing a regular private file (0600 or stricter); symbolic links and group/world permissions are rejected. No password or token CLI flags are provided. Noninteractive execution without a private file fails closed. Store the file through your deployment's secret mechanism, not source control.
3. Confirm the CLI PASS result or successful setup response. A replay must fail with setup completed; `/api/setup/status` must show setup unavailable.
4. Set `SETUP_ENABLED=false`, remove the temporary setup token, restart/redeploy, and confirm the create-admin endpoint returns 404.
5. Verify actual administrator login and permitted admin actions; verify an ordinary user receives 403 on administrator endpoints. Complete MFA enrollment and email verification through their real flows. Record redacted evidence, never credentials or bearer tokens.
6. If setup fails, diagnose safely and retry after rollback. If users already exist, stop and investigate their legitimate origin; the bootstrap service does not promote or delete them.

## Validation

Focused tests cover existing setup/wallet compatibility, seed failure rollback and retry, password hashing, unverified-email preservation, completion-record replay protection and private password files. Disposable PostgreSQL CI adds a real concurrent different-email proof in a unique schema, requiring both CI and explicit disposable-test opt-in; it does not modify application schema data. Full backend regression, type/lint checks and frontend type checks must pass on the final reviewed tree before merge. CI or local fixtures are not production execution evidence.

## Research basis

- SQLAlchemy transaction boundaries: https://docs.sqlalchemy.org/en/20/orm/session_transaction.html
- PostgreSQL locking/concurrency: https://www.postgresql.org/docs/current/explicit-locking.html
- NIST SP 800-63B password guidance: https://pages.nist.gov/800-63-4/sp800-63b.html
- OWASP logging guidance: https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html

Use explicit transaction ownership and database uniqueness rather than process-local locks. Avoid logging authentication secrets. Keep production identity and execution claims separate from implementation tests.

## Post-bootstrap security acceptance

Follow `FINCO_LIVE_ACCEPTANCE_HARDENING_V1.md` for migration 098, encrypted MFA seeds, bounded legacy conversion, one-use login challenges, factor-change session revocation and read-only final runtime gates. This does not claim that the live deployment has completed those steps.
