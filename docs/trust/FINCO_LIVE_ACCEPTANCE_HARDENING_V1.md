# Live acceptance and authentication hardening

Checkpoint: 2026-10-04. Branch: `harden/live-acceptance-v1`.
Scope: outstanding first-admin, SMTP and FX acceptance, plus reproduced authentication weaknesses discovered while reviewing those gates. This is not completion of roadmap #20–#60.

## Verified access and remaining blockers

The current execution workspace has no configured production DATABASE_URL, SMTP account credentials, Open Exchange Rates App ID, deployment-secret directory or operator-selected first-admin identity. Repository documentation names `fincopilot.satzzxzxx.me`; public retrieval and DNS resolution were not successful from this environment. This does not prove that an independently managed deployment is offline. No other account, server, database or email identity is inferred from similarly named public products.

Production admin creation, setup disablement on the real host, email ownership verification, actual MFA enrollment/recovery custody, SMTP sender/DNS/inbox proof, provider-backed FX sync and controlled outage recovery remain blocked until the real target and access are available. No production account, DNS record, email or FX request has been created/sent by this work. Keep main merge on hold until these live gates are completed, as requested by the operator.

## Research, findings and decisions

| Finding | Correction and evidence |
| --- | --- |
| TOTP verifier read a challenge and later deleted it; competing TOTP/passkey verifications could both use a stale read | Shared atomic Redis GETDEL consumes and revalidates identity, allowed method and current credential stamp before JWT issuance; only one factor can win |
| A valid TOTP could sign in again through a different challenge | Atomic SET NX with a 120-second digest-only reservation spans the accepted time window; reused login codes are denied, outages fail closed |
| Enabling/disabling MFA or replacing recovery codes retained earlier sessions/challenges | Rotate the existing durable auth epoch after validated factor changes; return a replacement token to the completing caller and update the frontend session |
| TOTP seeds were stored as plaintext | Purpose-separated Fernet encryption derived with HKDF from the independent credential encryption key, plus retained-key reads; new writes are encrypted transparently |
| Existing short seed column cannot hold authenticated ciphertext | Add non-destructive migration 098 to Text, retaining existing seed bytes; bounded explicit legacy conversion; refuse a downgrade that would truncate ciphertext |
| Settings validation and passkey error logs could expose sensitive inputs | Hide settings input values in error strings and remove raw passkey credential/exception logging |
| Code/CI success could be mistaken for live acceptance | Read-only runtime audit reports individual gates and always keeps untested real login/inbox/provider/outage evidence separate |

Primary guidance consulted:
- RFC 6238 section 5.2 (successful OTP reuse must be rejected): https://www.rfc-editor.org/rfc/rfc6238
- OWASP MFA lifecycle and factor-change controls: https://cheatsheetseries.owasp.org/cheatsheets/Multifactor_Authentication_Cheat_Sheet.html
- Redis atomic GETDEL: https://redis.io/docs/latest/commands/getdel/
- Redis SET NX/expiry: https://redis.io/docs/latest/commands/set/
- Python SMTP/TLS protocol behavior: https://docs.python.org/3/library/smtplib.html
- OWASP TLS guidance: https://cheatsheetseries.owasp.org/cheatsheets/Transport_Layer_Security_Cheat_Sheet.html
- Open Exchange Rates header authentication: https://docs.openexchangerates.org/reference/authentication
- Open Exchange Rates latest/historical contract: https://docs.openexchangerates.org/reference/latest-json and https://docs.openexchangerates.org/reference/historical-json

No new account provider, paid plan, financial-data deletion or ad hoc administrator promotion is introduced. Existing independent credential-key and compatibility-key configuration remains authoritative. MFA encryption uses a separate purpose context from stored provider credentials. Missing/corrupt encryption keys do not turn an enrolled second factor into an absent factor. TOTP remains susceptible to phishing; use the existing user-verifying WebAuthn/passkey flow where supported and retain protected recovery controls.

## Implementation plan and execution record

1. Read current continuity and main; verify merged PRs #29–#31 and existing production runbooks.
2. Research official guidance and inspect bootstrap, SMTP, FX, TOTP/passkey login, recovery and storage boundaries.
3. Implement the findings on an isolated branch; retain the protected bootstrap and provider-neutral SMTP/FX contracts.
4. Verify actual ciphertext storage, legacy preservation/idempotent conversion, key rotation/missing-key failures, challenge races, OTP replay rejection and session replacement.
5. Add real disposable Redis mixed-factor concurrency and PostgreSQL migration-preservation/downgrade proofs to CI, alongside the existing first-admin concurrency proof.
6. Run local backend/frontend regression, full type/lint and migration-chain checks; verify exact PR head CI.
7. Execute the accessible no-send/read-only production probes. Missing real configuration must return failure, never simulated PASS.
8. Hold main merge until operator runtime access, identity and the real live gates are resolved. Record precise blockers and evidence in continuity.

## Safe production rollout and acceptance sequence

Run these only in the authorized target backend environment with secrets supplied by its existing secret mechanism. Never send passwords, SMTP keys, App IDs, authenticator seeds or recovery codes in chat or commit them.

1. Identify the actual deployment and database; verify backup/restore readiness and preserve the current credential encryption key plus required compatibility keys separately from the DB backup. Keep UTC/NTP accurate across API replicas.
2. Drain old application replicas during rollout. Upgrade the schema before deploying code that writes encrypted seeds:
   ```sh
   alembic upgrade head
   ```
   Required head is 098. The widening migration preserves existing seeds and limits PostgreSQL lock wait to five seconds. If migration fails, diagnose rather than disabling protection. Do not roll encrypted data back into a 32-character column or run old code against newly encrypted seed values.
3. Deploy the reviewed code consistently to every API replica, preserving the independent credential key. Existing plaintext seeds remain readable for compatibility, but they are not accepted as a completed release gate. Inspect, then explicitly seal bounded batches:
   ```sh
   python -m scripts.seal_legacy_mfa_seeds
   python -m scripts.seal_legacy_mfa_seeds --execute --batch-size 100
   ```
   Repeat controlled batches until `legacy_rows_remaining=0`. The command preserves seed identity, enabled state, recovery hashes and auth epoch. A failed batch rolls back. No seed is printed. The default is inspection only. For later credential-key rotation, the existing `python -m scripts.rotate_data_keys --apply` now also re-encrypts MFA seeds atomically with LLM/bank credentials and Copilot identities. Preserve the old credential ring through conversion and verification; never remove retained keys before every affected encrypted record has been resealed and verified.
4. If the first administrator has not yet been created, choose the real operator identity explicitly and follow `FINCO_FIRST_ADMIN_BOOTSTRAP_V1.md`. Do not infer it from the repository author. If users already exist without the expected bootstrap record, investigate their origin; no public signup is promoted.
5. Disable SETUP_ENABLED and remove the temporary SETUP_TOKEN, restart/redeploy, and verify the actual create-admin endpoint returns 404. Verify real admin login and authorized admin action; an ordinary user must receive 403 on admin endpoints. Complete actual email verification, MFA enrollment and operator custody of unused recovery codes. Factor changes revoke earlier sessions; preserve only the completing caller's new token. An old session/challenge must fail after the change.
6. Complete SMTP provider activation, real verified sender and exact provider-returned domain records. Follow `FINCO_PRODUCTION_SMTP_V1.md`; run the no-send TLS/AUTH/NOOP probe first. Send harmless tests only to explicitly selected controlled inboxes; verify provider delivered status, two independent inboxes and DKIM/DMARC alignment. SMTP acceptance alone is not inbox delivery. Exercise real verification/reset journeys without logging auth links.
7. Complete the selected FX provider account/terms/quota and inject its real credential. Follow `FINCO_PRODUCTION_FX_V1.md`: latest and historical read-only probes, scheduled sync, common-date currency coverage, exact database upsert/idempotency and worker/Beat consistency. No mock snapshot establishes provider coverage.
8. Run controlled staging outage/429/Redis recovery drills, preserving truthful cached-rate behavior and blocking unavailable conversion; do not disrupt live financial traffic to manufacture an outage proof.
9. Run the final read-only runtime audit:
   ```sh
   python -m scripts.verify_live_acceptance
   ```
   It checks production mode, setup/token removal, first admin activity/email verification/MFA, encrypted seed storage, SMTP/FX release settings, current migrations and a valid recent common-date provider cache. It never writes rows, sends email or requests a provider. Exit 0 means only its automated runtime gates passed. `live_acceptance_complete` deliberately remains false because inbox delivery, actual login/recovery custody, quota/outage acceptance and provider rights cannot be proved from configuration/DB state alone.
10. Preserve redacted evidence for each actual live gate, including target, timestamp, reviewed commit and observed result. Only then merge/release. Never edit a JSON boolean or mark an email verified to replace the real verification journey.

## Test scope and limits

Unit/API/database regressions and disposable CI proofs validate the implemented behavior; they do not establish production account ownership, DNS propagation, real inbox placement, live migration completion or the absence of every possible vulnerability. TOTP nonce expiry assumes healthy Redis and synchronized clocks; Redis authentication outages intentionally deny new MFA login rather than bypass it. A challenge/code may be consumed if a later commit/signing step fails; request a new login challenge/code, with no automatic replay. Recovery-code consumption is committed only with a successfully generated token, and competing attempts remain protected by the user-row lock plus atomic challenge consumption.

Legacy plaintext compatibility exists only for controlled transition. The runtime audit detects remaining legacy rows; a completed release requires them to be sealed. Retained key removal must be coordinated with all other credentials sharing the existing key-ring settings.
