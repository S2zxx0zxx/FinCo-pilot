# Roadmap #20: production migrations 094–096

Status: engineering rehearsal in progress; actual production execution pending. No VPS/production runtime or authorized database is available. This document does not mark deployment complete. Branch: feat/migration-094-096-rehearsal-v1, based on main; pending PR #32 is not silently included.

## Reviewed scope

094 adds recovery hashes, non-null auth_epoch with an empty legacy default, and external MCP tokens. 095 adds human approvals and foreign keys/indexes. 096 adds loans with numeric/check constraints and defaults. None of these upgrades deletes existing rows. Their downgrades drop new tables/columns and can destroy security/financial records: never use production downgrade as recovery. Existing-session and old-token transition policies remain roadmap #21/#22, not inferred from schema success.

Main currently ends at 097. Pending hardening PR #32 adds 098 and encrypted MFA storage; do not deploy that code against an older schema. Always identify the actual reviewed release head rather than hardcoding 096 as the application target. Never stamp Alembic to bypass migrations or replace existing populated tables with create_all.

## Plan and implemented evidence

1. Review 094–096 and the existing Alembic transaction/advisory-lock path.
2. Keep historical upgrades unchanged; add a synthetic populated dependency fixture in a private random PostgreSQL schema.
3. Verify failed 094 DDL rolls back; then 094→096 preserves existing password/seed/workspace values and installs defaults/indexes.
4. Insert representative token, approval and loan rows; verify seven invalid FK/check writes are rejected and surviving rows remain intact.
5. Run this proof in the existing disposable PostgreSQL CI job, alongside full empty-database chain/reapply and runtime/concurrency proofs.
6. Record exact head CI. Only actual target execution and redacted evidence can close #20 production acceptance.

The new proof intentionally uses minimal pre-094 dependency tables. It is not a full historical database clone, tenant security proof, performance benchmark, session/token transition proof or backup restore test. Those require a representative restored database and separate acceptance evidence. It cleans only its own random schema; refuses execution unless CI=true and FINCO_DISPOSABLE_DB_TEST=yes.

## Actual rollout checklist (pending)

- Identify the authorized target, reviewed application commit, real Alembic current revision and single intended head. Inspect missing/divergent/multiple heads and schema drift before any write. Never infer revision from the repo alone.
- Use the existing provider's direct migration connection and verified TLS contract; runtime pooled credentials are not automatically migration credentials. Secrets remain in the deployment secret mechanism.
- Capture an encrypted backup/snapshot and verify it can restore into an isolated target. Preserve credential encryption keys separately; record provider PITR/snapshot restoration procedure. A file existing is not restore evidence. Coordinate with #25 backup/restore.
- Rehearse the exact release against an authorized sanitized/restored copy; compare existing user/workspace/financial row counts and critical values, check schema/defaults/indexes/FKs and application startup/auth/MCP/loan behavior. Measure duration and storage/locks with representative volume.
- Drain application writes and workers for the maintenance window; take the final recovery point. Prevent overlapping migration jobs. Existing Alembic uses a database advisory lock and transactional DDL, but lock acquisition currently has no bounded wait; observe/block concurrent operators rather than claiming a timeout guard exists.
- Set session-scoped lock/statement timeouts through the approved database connection configuration for the entire migration transaction, based on measured rehearsal. Do not set a global timeout or assume the proof's SET LOCAL affects a separate Alembic process.
- Run alembic current and alembic heads, then alembic upgrade head for the exact release. Do not run downgrade 093 on production; the existing CI rollback command is disposable-only.
- On failure, keep writes drained; inspect revision/schema and transaction outcome before retry. Use forward correction or tested restore, accounting for post-backup writes. Do not clear auth_epoch, recovery hashes, token registries, approvals or loans to make a check pass.
- Confirm actual revision=head and schema, startup/readiness, preserved rows and normal auth/MCP/loan behavior. Resume one release consistently across API/workers, observe errors and record timestamp/target/commit/result without credentials or personal data.
- If release includes 098, follow FINCO_LIVE_ACCEPTANCE_HARDENING_V1.md for encryption/sealing/key compatibility. Do not run old application code against encrypted seed data.

Production completion requires all actual checklist evidence. No production migration has been run by this work; main merge remains subject to the user's live-gate condition.

## Primary research

- PostgreSQL ALTER TABLE lock and constraint behavior: https://www.postgresql.org/docs/current/sql-altertable.html
- PostgreSQL transaction-local settings: https://www.postgresql.org/docs/current/sql-set.html
- Alembic revision, upgrade/downgrade and actual current state: https://alembic.sqlalchemy.org/en/latest/tutorial.html
