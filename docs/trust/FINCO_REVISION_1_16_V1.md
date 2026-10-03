# FinCo-Pilot roadmap #1–#16 engineering revision

Baseline: main `843d86ebbe1a1a51b5350c549edb912a607e021b`, 2026-10-03.
This revision preserves existing tables, record IDs, conversation histories,
issued invoices, uploaded files and product/pricing features. It does not run
any production deletion, credential rotation or provider provisioning.

## Findings and implemented corrections

| Finding | Correction | Regression evidence |
| --- | --- | --- |
| JWT key rotation strands stored provider credentials | Independent encryption key; explicit read-only legacy key ring; both historical KDF salts remain readable | Session rotation and pre-rebrand compatibility tests |
| JWT rotation turns Core Copilot into an editable shared agent | Independent identity key; verified compatibility signatures; signed rows are protected even when verification fails; fail-closed access and provisioning | Per-user protection, missing-key quarantine, migration tests |
| Production settings can bypass external DB/Redis security flags | Runtime requires external encrypted PostgreSQL and external authenticated TLS Redis | Production settings tests |
| Helm can expose API before migration; readiness only checks liveness | Init gate on backend, worker, Beat and MCP; advisory-lock migrations; production Postgres, Redis, object-storage acceptance and data-key dry run; dependency readiness | Release gate unit tests and Helm CI |
| Compose health check targets the wrong Celery hostname | `worker@$$HOSTNAME`, matching the worker command and avoiding host-side interpolation | Compose CI |
| Redis result backend ignores canonical finite timeouts/pool limits | Explicit backend connect/read timeouts, health checks, maximum connections and visibility timeout | Actual Celery backend parameter assertions |
| Support diagnostic fields can carry secrets or external-looking paths | Scan every forwarded caller diagnostic; reject protocol-relative/backslash paths; validate request references; preserve provider response compatibility | Zoho provider contract, support API/service tests |
| S3 downloads allocate an unbounded response body | Reject oversized declared length, bounded streaming, early close and checksum verification | Oversized declared and chunked stream tests |
| S3 canonical path is double encoded | Sign the exact once-encoded wire path for headers and presigned URLs | Spaces, percent, plus and Unicode path regression |
| Upload failures can leave or remove inconsistent files | Include primary promotion/flush in guarded invoice upload; compensate new uploads only after rollback/reference verification; preserve bytes when state cannot be verified; logo persistence guarded across commit | Storage compensation, invoice, logo and attachment tests |
| Legacy production user deletion ignores retention and shared-workspace policy | Both the custom admin route and framework-generated user route refuse unsafe deletion before any row is removed; development implementation retained; actual retention-aware execution remains #29/#30 | Both API routes preserve user data; service refusal and existing admin tests |

## Required key rollout for an existing installation

Do this in a maintenance window, with a verified encrypted backup. Keep every
old application consumer stopped while rewriting data. Do not paste key values
into commands, terminal output, logs, issues or committed files.

1. In the external secret manager, generate three independent high-entropy
   values of at least 32 characters. `SECRET_KEY` authenticates application JWTs;
   `CREDENTIAL_ENCRYPTION_KEY` encrypts stored provider credentials;
   `CORE_COPILOT_SIGNING_KEY` authenticates system-agent identity. Keep the
   current JWT key initially if session invalidation is not yet desired.
2. Before switching the two data keys, put the **previous SECRET_KEY** in
   `LEGACY_DATA_KEYS`. If data keys have already been separated, include their
   previous values under the appropriate purpose only. This is a JSON secret
   with separate `credentials` and `copilot` arrays (at most eight keys each),
   never a JWT verification key ring. For the initial migration, the previous
   shared SECRET_KEY goes in both arrays. For subsequent rotations, previous
   encryption keys go only in `credentials`, and previous identity keys go only
   in `copilot`. This prevents an encryption key from authenticating an agent.
3. Compose secret-file names are `credential_encryption_key`,
   `core_copilot_signing_key`, `legacy_data_keys`, alongside existing
   `secret_key`. Helm's `global.existingSecret` contains the corresponding
   uppercase environment names. Do not inject production values through the
   committed values file or plaintext Compose mappings.
4. With the new build and all required secrets loaded, run from `/app`:

   ```sh
   python scripts/rotate_data_keys.py
   python scripts/rotate_data_keys.py --apply
   ```

   The first command validates only. The second locks relevant rows, validates
   **every** known encrypted value and signed agent before changing anything,
   then atomically re-encrypts/re-signs. Any unreadable value aborts the entire
   transaction. Only aggregate counts are printed. No row is deleted, no
   provider is contacted and IDs/history are unchanged.
5. Restart all consumers on the new build. Test the affected LLM, SimpleFIN,
   EnableBanking and Core Copilot flows with the legacy ring still available.
   Remove the legacy ring in a maintenance window and rerun the dry run. Restore
   it immediately if validation fails. Retain retired keys in the protected
   backup secret store while backups encrypted with them remain restorable.
6. JWT rotation can now invalidate sessions without touching data keys.
   After data re-encryption, rollback must use a build that understands the new
   data keys, or restore the verified database backup and matching old secrets.
   Rolling back to a pre-revision build alone will strand new ciphertext.

New installations need no legacy ring. Development retains the historic
`SECRET_KEY` fallback when independent keys are absent. Production requires
independent keys and fails startup rather than quietly using a shared key.

## Deployment and acceptance

Helm init containers run `python scripts/prepare_release.py` before the service
container starts. PostgreSQL migrations serialize with the existing database
advisory lock. Production gates verify schema/TLS/pgvector, decryptability and
Core identities, Redis, and private object-storage round trips. A failure keeps
the pod unready; no `--wait` dependency on the post-install migration hook is
needed. The retained hook repeats the idempotent release gate. Provider probe
objects are isolated temporary acceptance objects; existing user data is never
removed. The hook and init checks do not exercise live Celery work: use the
existing Redis acceptance command with `--require-worker` after rollout.

Readiness is `/api/health/ready`; liveness remains `/api/health` so dependency
outages do not cause a restart storm. Migrations must remain compatible with
the previous build during rolling upgrades, or use a maintenance window.

## Completion boundaries

Code and regressions are reviewable in this revision. Actual hosting/domain
setup (#1/#2), FIU/AA onboarding (#5), approved live AI inference (#6), Zoho
credential rotation/live ticket and reply (#7), and live Neon/Redis/R2
acceptance (#14–#16) require their operator accounts and deployed environment.
Their existing release gates remain in force; unit tests are not production
acceptance. Full personal/shared deletion execution and durable orphan
reconciliation still belong to #29/#30. Failed compensation is logged without
secrets and preserves bytes when database state is unknown; it is not a claim
that a durable cross-system deletion workflow already exists. Payment
activation and webhook lifecycle work remain #31–#39; no gate is bypassed.
