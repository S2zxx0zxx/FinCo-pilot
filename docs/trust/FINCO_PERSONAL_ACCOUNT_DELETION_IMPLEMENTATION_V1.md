# Personal account deletion — roadmap #29

This implementation consumes the #10 contract in `app/core/account_deletion.py`. It implements a real, operator-reviewed workflow, **not unattended deletion or a claim that live provider accounts/backups have already been erased**. Shared-workspace hard deletion is roadmap #30. Public legal publication remains deferred until after #60.

## Audit and design decisions

The legacy admin/fastapi-users deletion routes use user cascades and cannot safely distinguish shared financial rows from personal data. Production continues to refuse those routes. The new workflow never calls ORM `delete(User)` or bulk financial deletion by `user_id`.

The audited schema inventory is explicit and checked against both registered metadata and actual database tables/columns before destructive work. New tables, drift, unknown legacy scope, cross-workspace foreign-key references and cross-workspace transfer pairs block execution until reviewed. Agent tables are audited even when their routes are disabled.

Only a personal workspace with exactly one member, one active owner and no other manager is removed with its account. Business/shared workspaces survive. The last active owner, shared payer, last active superuser and verified holds block execution. Archived workspaces are included. Ownership/holds are rechecked at execution, not trusted from the request.

An inactive pseudonymous user row is deliberately retained: numerous existing financial foreign keys require its UUID. Its email, password, MFA seed/recovery codes, preferences, OIDC identifiers and privileges are erased/disabled. This is pseudonymization, not irreversible anonymization. Shared authored records and payment/hold evidence remain under the reviewed retention decision; no blanket legal retention period is invented. Personal LLM keys are removed and dependent shared agents are archived rather than silently falling back to instance credentials.

## Authentication and consent

`/account-deletion` supports logged-in request/cancel and receipt-based tracking after sign-out. The exact confirmation is `DELETE MY ACCOUNT`.

Request/cancel and operator mutations require a full authentication result no older than five minutes. Only successful password login without pending MFA, completed TOTP/recovery/passkey second-factor login, or verified user-present/user-verified passkey login receives `auth_time`. Token minting during settings changes does not grant fresh authentication.

OIDC uses `/api/auth/oidc/login?reauthenticate=true`, requesting `prompt=login` and `max_age=0`. The callback requires recent integer `auth_time` from the verified ID token; issuing a new local token after silent SSO is insufficient. Ordinary OIDC login does not grant deletion freshness. Existing credential-stamp checks bind freshness to the current password and auth epoch.

A random 256-bit receipt secret is returned once; only its SHA-256 is stored. Tracking uses `X-Deletion-Receipt`, never a query parameter/cookie. The UI keeps the secret in memory. Save it before leaving. All deletion API responses are `no-store`; the existing service worker never caches API responses.

## Durable execution

1. Fresh authenticated user submits consent. One active request per user is enforced by a user lock and database uniqueness. A blocked request can be recorded. Cancellation is possible only before an execution lease exists.
2. A different active operator executes the request. Operators must freshly authenticate and review current retention/hold/provider/processor/backup facts. A review is bound to a complete inventory fingerprint and expires after 24 hours. Re-review invalidates earlier receipts.
3. Required receipts include verified off-system hold/retention review, actual processor inventory and actual backup inventory . Existing bank connections, personal LLM credentials, provider billing identifiers/non-free subscription state and S3 object versions require additional exact receipts.
4. Receipts are **operator attestations with hashes of actual evidence**, not automatic provider verification. Keep the real evidence in the operator's protected evidence store; never submit secrets, identity documents, raw payment payloads or unreviewed fabricated hashes. These checks cannot be satisfied merely because newly created ledger tables are empty.
5. A renewable ten-minute execution lease prevents competing/resumed executors from acting on the same request. A crashed process can resume after lease expiry. SQL failures are sanitized and purge-precondition failures release the lease without partial deletion.
6. On PostgreSQL, the rare destructive transaction takes a bounded-timeout `EXCLUSIVE` lock over the audited tables. Workspace write requests first hold a `KEY SHARE` lock through upload calls. The fence deliberately pauses writes and waits for existing writers/locked upload readers while the exact manifest, session rotation/deactivation, private graph purge and shared-reference detachment commit atomically. Schedule this operation in a maintenance window. A five-second lock timeout fails closed; retry later. It is not a high-throughput bulk-deletion worker.
7. Migration 099 installs database guards against new rows referencing a deleted actor and against modifying/reactivating a tombstone. Unchanged actor references in surviving shared rows remain editable. Application admin/user update paths also refuse tombstone edits. Database guards cover stale authenticated requests and queued jobs after the transaction fence is released.
8. Exact attachment keys, current/frozen invoice logos, replaced/orphan files in private UUID workspace namespaces and knowledge paths are saved durably before their database rows disappear. Each confirmed deletion is checkpointed. Provider/path changes, surviving references, permission/provider failures or unsafe paths lead to `external_retry`, retaining the manifest. Retry does not depend on already-erased attachment rows.
9. Local deletion uses directory descriptors and no-follow opens; traversal, symlink files/directories and nonregular targets are refused. Missing bytes are idempotent success. S3 inventory uses bounded, authenticated, paginated ListObjectsV2 and rejects malformed XML, escaped namespaces and pagination loops. S3 deletion uses the existing authenticated, bounded-timeout adapter; versioned copies require separate evidence. Do not treat a delete marker as erasure.
10. Processor cleanup and unmapped legacy-storage checks **must be evidenced after** the fenced primary purge. S3 per-key and whole-workspace namespace checks also happen after logical deletion, so retained versions, delete markers and in-progress multipart uploads cannot be declared erased prematurely. Until those actual external actions finish the request stays `external_retry` with `post_primary_reconciliation_required`; pre-execution receipts for these checks are rejected. The fresh-authenticated operator detail endpoint exposes the protected exact-key manifest needed to reconcile versions; do not share it publicly. After all primary database/object cleanup and post-purge checks finish, sensitive manifest paths are discarded and state becomes `backup_expiry_pending`. It becomes `complete` only after a fresh operator submits real evidence and an earliest recoverable-data timestamp later than primary deletion. A calendar expiry date alone is insufficient. Snapshot/object versions, replicas, exports and restore copies must all be covered. Restore reconciliation must apply the latest deletion ledger before reopening restored data.

Minimal append-only application events retain reviewed fingerprints, actor IDs, state changes and evidence hashes. They contain no object paths, raw authentication factors or provider secrets. Holds retain verifier/releaser and both evidence hashes. Migration rollback refuses nonempty deletion/hold/event tables.

## Operator API

Detailed file inventory and all mutation routes below require current superuser + fresh full authentication; use a different operator from the deletion target for execution. Never execute against real accounts during acceptance testing.

| Operation | Route | Body |
| --- | --- | --- |
| List latest requests | `GET /api/account-deletion/operator/requests` | — |
| Inspect requirements/receipts | `GET /api/account-deletion/operator/{id}` | — |
| Add verified hold | `POST /api/account-deletion/operator/holds` | `user_id`, `reason` (`legal`, `tax`, `dispute`, `fraud`, `retention`), `evidence_sha256` |
| Release hold | `POST /api/account-deletion/operator/holds/{hold_id}/release` | `evidence_sha256` |
| Review current inventory | `POST /api/account-deletion/operator/{id}/review` | `evidence_sha256` |
| Record exact external check | `POST /api/account-deletion/operator/{id}/receipt` | `requirement` as returned by inspection, `evidence_sha256` |
| Execute/resume | `POST /api/account-deletion/operator/{id}/execute` | — |
| Confirm actual backup expiry | `POST /api/account-deletion/operator/{id}/backup-proof` | `evidence_sha256`, timezone-aware `verified_after` |

The user screen includes request/cancel/receipt tracking and a superuser panel for review, required receipts, execute/resume and backup evidence. Hold administration also has the explicit API above. No provider cancellation/refund is fabricated by deleting a local subscription row. Existing live paid billing gates remain closed.

## Validation

Meaningful SQLite/API/browser tests cover blockers, private cleanup, shared preservation, stale inventory/expired review, new holds, fresh-auth expiry/malformed claims, receipt authorization, cancelled requests, resume after failure, duplicate execution leases, local symlink/traversal safety, tombstone edit refusal, redacted audit events, request errors and separate English/Hindi screens.

`python -m scripts.verify_account_deletion_postgres` runs only with **both** `CI=true` and `FINCO_DISPOSABLE_DB_TEST=yes`, creates a synthetic isolated schema, exercises migration 099 and native foreign keys, deletes actual temporary bytes, proves another writer waits on the table fence, preserves editable shared rows, refuses stale-actor insertion/reactivation, rejects backup shortcuts and refuses a destructive downgrade. It drops only its own generated schema. It is part of the existing PostgreSQL CI job.

All existing CI jobs must pass on the final commit before merge. Live deployment, real provider revocation, verified legal/payment facts and actual recoverable-backup expiry still require the operator's real environment/evidence; this implementation does not certify those facts.

## Primary research

- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html): recent reauthentication for destructive/sensitive actions and session invalidation.
- [OWASP MFA Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Multifactor_Authentication_Cheat_Sheet.html): sensitive actions must preserve the account's authentication strength.
- [SQLAlchemy cascade documentation](https://docs.sqlalchemy.org/en/20/orm/cascades.html): ORM cascade and bulk SQL deletion have different semantics; foreign-key behavior must be tested on the real database.
- [OpenID Connect Core](https://openid.net/specs/openid-connect-core-1_0.html): `max_age`, `prompt=login` and verified `auth_time` distinguish new token issuance from fresh authentication.
- [AWS S3 version deletion](https://docs.aws.amazon.com/AmazonS3/latest/userguide/DeletingObjectVersions.html): ordinary DELETE may retain earlier versions behind a delete marker.

- [AWS ListObjectsV2](https://docs.aws.amazon.com/AmazonS3/latest/API/API_ListObjectsV2.html): exact prefixes, URL-encoded keys and continuation-token pagination.
