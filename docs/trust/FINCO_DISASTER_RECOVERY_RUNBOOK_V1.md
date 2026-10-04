# Roadmap #26 — disaster recovery runbook

Contract: `FINCO_DISASTER_RECOVERY_RUNBOOK_V1`. Scope: loss/corruption of database, primary objects, knowledge files, host or credentials. Engineering procedures and isolated CI rehearsal are available; no production VPS, offsite repository or representative live recovery is claimed. [#25 backup contract](FINCO_BACKUP_ACTUAL_RESTORE_V1.md) supplies the tools. This runbook supplies incident ownership, containment, dependencies, evidence, gated cutover and rollback.

## 1. Declare and classify

Assign an incident lead, infrastructure operator and evidence reviewer; one person may hold these roles for a small deployment, but record that limitation. Use opaque operator IDs, not names/emails, in the machine-readable case. Record incident start in UTC, observed last known good point, affected systems and whether this is a **synthetic drill** or a **live incident**. A security compromise requires preserving restricted forensic evidence and revoking exposed access; restoring vulnerable code or compromised keys is not recovery. Provider/network outages with intact data may need repair rather than an older restore. Corruption needs a known-good point before corruption, not blindly `latest`.

| Failure | Initial action | Recovery choice / stop condition |
| --- | --- | --- |
| Host lost | Block ingress; stop surviving schedulers/writers | Clean replacement, pinned images/code, isolated DB/objects/Redis and separately recovered keys |
| DB lost/corrupt | Fence surviving writer identities; preserve original if reachable | Verified full logical checkpoint or separately tested provider PITR; choose pre-corruption point |
| Object/knowledge loss | Stop destructive jobs; preserve surviving bytes | Consistent #25 DB+file checkpoint; don't mix newer DB with arbitrary older files |
| Redis lost | Stop Beat/workers and reject old pending auth flows | Fresh authenticated TLS Redis; reconcile durable records, do not restore challenges/queues |
| Secret compromised/lost | Restrict access; inventory affected consumers | Retain required old data decryption keys securely, rotate compromised online credentials; missing decryption keys block restore |
| Backup unreadable/missing | Retain failure evidence, try another authorized point | Never invent successful recovery or initialize over the only repository; escalate lost-data estimate |

This product has no general maintenance/read-only switch. Enforce containment at ingress and process/network/DB identity layers. Health liveness does not imply recovery readiness.

## 2. Contain before recovering

These are **operator commands**, not commands automatically executed by the evidence CLI. Run only on the verified intended Compose project with the protected production environment already configured; inspect project/service identity first. Keep configuration and diagnostics private; do not paste `docker compose config`/environment/credential output into tickets.

```sh
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml --profile cloudflare-edge stop cloudflared
docker compose -f docker-compose.prod.yml stop celery-beat
docker compose -f docker-compose.prod.yml stop --timeout 120 celery-worker backend
docker compose -f docker-compose.prod.yml --profile agents stop mcp-server
```

If using a different edge, deny traffic there first. Stop all deployments/replicas on other hosts and disable restart/orchestrator rollout paths; Compose `stop` alone cannot fence another operator or cluster. Verify in-flight workers finish or identify interrupted side effects, then fence old DB/provider writer identities at the infrastructure boundary. Do not use `down -v`, purge Redis queues, remove old volumes, downgrade migrations or delete the original database. Keep old stack fenced throughout recovery. Pause backup/expiry/check timers during active repository use; preserve the 30-day expiry backlog and resume it promptly, rather than creating an indefinite retention exception. Don't `restic unlock` while another operation is active.

For Helm, preserve current release/values/replica counts privately, disable external routing, scale application/MCP/worker/Beat deployments to zero using **observed deployed names**, and prevent controllers/GitOps from undoing the fence. Don't guess resource names or uninstall PVCs. Exactly one Beat may eventually resume; multiple schedulers can duplicate tasks.

## 3. Inventory dependencies and select a point

| Dependency | Required recovery evidence |
| --- | --- |
| Release | Exact 40-character source commit and immutable backend/frontend image digests; matching Python/Alembic head, PostgreSQL server/client and vector extension versions |
| Database | Trusted full checkpoint, source capture time, complete snapshot ID, all table checks; separate managed roles/extensions/server configuration |
| Files | Referenced attachments, invoice/current historical logos, raw knowledge bytes; isolated bucket/prefix and knowledge mount paths |
| Secrets | Restic password, data encryption current/legacy keys, Copilot current/legacy signing keys, app signing/provider/OIDC/SMTP/FX/storage credentials from separate access-controlled escrow |
| Transient state | Fresh TLS/auth Redis; no old sessions/challenges/broker/result state; stopped Beat/workers and provider side-effect inventory |
| External current facts | Latest deletion tombstones/verified legal holds and payment-provider subscription/settlement/webhook state obtained **outside the historical backup** |
| Edge | Correct public hostname/TLS, auth redirects, ingress/query-log redaction and ability to route back while writers remain fenced |

Never place secret values, user/financial rows, raw provider responses or backup contents in Git/chat/public issues. Keep case artifacts minimal/private and in a separate durable operator store with controlled retention. Hashes provide binding, not encryption or reviewer authenticity. The case checker does not inspect an artifact's meaning or scan it for secrets.

Use the protected backup environment and tested compatible client, from `backend/`:

```sh
umask 077
pg_dump --version
pg_restore --version
restic version
restic snapshots --tag finco-dr-v1 --host fincopilot --json > /private/incident/snapshots.json
python -m scripts.disaster_recovery check
```

`/private/incident` must already be an operator-created mode-0700 directory. Set `RESTIC_REPOSITORY` and mode-0600 `RESTIC_PASSWORD_FILE` through protected configuration. Full repository check can be expensive; record size/duration and provider limits. Select the exact 64-character snapshot ID; verify host/tag, ownership, capture point, known-good corruption boundary and key availability. Repository snapshot creation time is upload completion, not the database point. #26 manifests record time immediately **before snapshot export** for a conservative capture point. Clock synchronization remains an operator prerequisite. Pre-#26 reports lack measurable timing/binding fields: repeat the isolated rehearsal with current tooling instead of manufacturing fields.

Initial RPO target is 24 hours; calculate incident start minus selected database capture time, report any breach and lost-write range. End-to-end RTO target is 4 hours; measure incident start through successful required product service restoration, including containment, provisioning, reconciliation, cutover and validation. `restore_elapsed_seconds` is only the isolated command duration, **not RTO**. Targets aren't production SLAs. Provider PITR/WAL is a separate recovery path needing its own measured DB+object consistency proof.

## 4. Provision a clean target

Use a separate authorized recovery project/network where possible. The restore role must not access the original database or original object write namespace. An administrator provisions a fresh database from `template0`, restricted restore role, required vector extension and marker. Configure credentials through the provider/secret manager; do not put a password in SQL command history or arguments.

The following is a **psql template**, with non-secret identifiers supplied via `-v restore_role=... -v restore_db=...`. Database name is exactly `finco_restore_<32 lowercase UUID hex>`; role identifiers are generated/verified by the operator. Connect to an administrative database through private libpq/secret settings; `CREATE DATABASE` runs outside a transaction. No original DB is dropped or modified.

```sql
CREATE ROLE :"restore_role" LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION;
CREATE DATABASE :"restore_db" OWNER :"restore_role" TEMPLATE template0;
COMMENT ON DATABASE :"restore_db" IS 'FINCO_ISOLATED_RESTORE_V1';
```

Connect as the administrator to this **new target**, install `CREATE EXTENSION IF NOT EXISTS vector`, and verify no application relations exist. Provide the restricted role password out of band and place its URL in `FINCO_RESTORE_DATABASE_URL`. Check actual target host/port/name independently; the production source Settings must stay distinguishable from it. Use verified TLS/CA; system CA mode uses hostname verification. Isolated restore doesn't bypass production settings validation. Match extension/server versions; unsupported clients/extensions are a stop, not a reason to grant superuser or skip integrity checks.

```sh
python -m scripts.disaster_recovery restore --snapshot <exact-64-character-id> --destination /private/new-recovery
```

Destination must not exist. The command creates a persistent quarantine before restoring, checks encrypted bundle/keys/table fingerprints/migration heads/file bytes, rotates user auth epochs, revokes MCP inventory, remaps knowledge paths and stages object bytes. It neither uploads to the original bucket nor releases the target. On failure preserve the failed isolated target/output for diagnosis; provision another **fresh** target for retry. No `--clean`, destructive downgrade or ignoring restore errors. Private plaintext staging can survive process/host crashes; secure cleanup is an operator responsibility, not a secure-erasure promise.

## 5. Create and review the recovery case

Current restore writes `restore-report.json` with snapshot/target hash, capture/start/end timestamps and monotonic duration. Initialize a fresh case; substitute actual incident timestamp/ID and pinned commit. A drill must use `synthetic`:

```sh
python -m scripts.recovery_evidence init --restore-report /private/new-recovery/restore-report.json --case-directory /private/new-case --incident-id incident-opaque-id --app-commit <40-character-commit> --incident-at <UTC-ISO-timestamp> --exercise-kind live
python -m scripts.recovery_evidence evaluate --case-directory /private/new-case
```

`init` never marks a gate passed. `evaluate` returns exit **2** for incomplete gates, **1** for invalid input, **0** only for all documented gates. It is offline and has no database/provider/ingress access. Even exit 0 is explicitly `documented_gates_complete_not_promoted`, not permission, proof of live deployment or automatic release. It reports capture-point age/isolated duration and always `rto_measured=false`, `automatic_release=false`.

Edit `case.json` in the private case directory to add these **ten** attestations. Each gate requires a distinct basename-only mode-0600 artifact, SHA256, timezone timestamp after restore completion and opaque reviewer ID. Artifact content must identify this case/snapshot/target/commit and the observed check outcome; the hash binds the reviewed bytes. Updating artifacts requires review and hash refresh. The tool rejects unknown fields/gates, altered report/artifacts, traversal/symlink/public files, naive/future/stale timestamps, wrong chronology and payloads over 1 MiB. Keep evidence templates pending until observed facts exist.

```json
{"keys": {"verified_at": "<UTC-ISO-timestamp>", "reviewer_id": "operator-opaque-id", "artifact": "keys.txt", "sha256": "<64-character-sha256>"}}
```

Insert this member under `gates`; repeat using the exact gate names below. This is a schema example, not valid completed evidence. Preserve other case/report fields. Do not write actual encryption keys into `keys.txt`.

| Gate | What the reviewer actually checks |
| --- | --- |
| `recovery_inventory` | Pinned commit/images/versions, intended source capture, complete DB/file coverage, backup and target identity, extension compatibility |
| `containment` | Ingress denied, every old writer/Beat/worker/MCP fenced, in-flight side effects recorded; restart controllers can't undo fence |
| `keys` | Independent escrow recovery/decryption plus current/legacy credential and protected-agent signing compatibility; compromised online credentials rotated |
| `deletion_holds` | Fresh externally held deletion/hold facts reconciled into DB/object/knowledge scope without deleting shared survivors; unresolved requests block release |
| `payments` | Current provider settlements/subscriptions/pending checkout/webhooks reconciled; avoid duplicate charge/refund or stale paid entitlement |
| `objects` | Fresh private bucket/prefix populated using reviewed storage tooling; preserve logical keys/content types/SHA metadata, download **every referenced object** and match size/SHA; knowledge mount/path/permissions verified |
| `redis` | Fresh authenticated TLS target, no copied queues/auth state, old tokens/MCP invalidated, duplicate tasks reconciled, planned single Beat |
| `runtime` | Quarantine blocks ordinary factory even after rename; isolated SQL/schema/ownership/financial precision/MFA/protected-agent/attachment evidence and validated recovery config; required post-release probes specified |
| `cutover_rollback` | New endpoint/secret/volume/image plan, maintenance boundary, old stack fenced, rollback criteria and data-divergence decision; operator availability |
| `operator_review` | All preceding evidence independently checked where possible; case hashes/current observations reviewed and limitations recorded |

**Deletion/hold reconciliation is currently a hard live blocker** if no current external records exist. Roadmaps #29/#30 own durable executors/ledger; #10/#11 are side-effect-free policies. Don't replace missing facts with an empty historical table or a “not applicable” guess. A reviewer may document a genuinely empty history only after checking the current authoritative process. Payment/secret/processor checks likewise remain real operational work. No synthetic artifact substitutes for a live gate.

## 6. Controlled release and cutover

This phase is manual infrastructure work after documented gates and the incident lead's recorded decision. The evidence CLI **cannot** release a DB. Keep public ingress denied and all side-effecting jobs stopped. Operator prepares the isolated object namespace, knowledge mount and fresh Redis, sets recovery-only secret/config paths and immutable release, then uses the restricted administrative session on the independently verified **new** target to set the single quarantine row `released=true` and rename it to a reviewed non-`finco_restore_` name. Preserve the marker table/audit evidence. Renaming alone cannot release it; setting the marker alone leaves the name guard. Don't point old running consumers at the new target, and don't use an automated one-line release script.

Rebind private DB/Redis/storage secrets/config to the intended recovered identities and mounts; validate the exact release without public traffic. Compose backend startup runs migrations and dependency probes, so use the matching backup release initially; upgrades require separately reviewed forward migration compatibility. A downgrade is not rollback. Run only behind network isolation:

```sh
python -m scripts.verify_production_postgres
python -m scripts.verify_production_redis --redis-only
python -m scripts.verify_production_object_storage
```

The object probe writes/deletes only random acceptance objects in the **recovery namespace**; it is not a substitute for checking restored files. Start backend/frontend privately with workers/Beat/MCP still stopped. Check `/api/health/ready` returns 200; `/api/health/live` is insufficient. With an authorized harmless test account, verify login/MFA, old-token rejection, workspace/role isolation, account/transaction currency precision, actual attachment/invoice/knowledge reads, protected Copilot integrity if enabled, email/reset/verification redirects and edge header/query-redaction. No real billing action is needed for this smoke. Readiness alone doesn't test object storage, payments or provider reachability.

If all product checks pass, enable required worker(s), run `python -m scripts.verify_production_redis --require-worker`, and only then enable **one** Beat after task replay decisions. Reconcile webhook events from their authoritative provider under the existing idempotency boundaries; do not blindly resend old queues. Enable MCP/provider integrations individually, then switch edge routing last. Monitor financial duplicates/missing bytes/auth/privacy/errors and record actual service-restored time/RTO. Cutover config and provider DNS/tunnel commands depend on the deployed host/account and remain deliberately unexecuted until those exist.

## 7. Rollback, failure and closure

Before recovered writes or external side effects begin, failed acceptance can return routing/config to the **known-good fenced** original only after verifying its integrity and keys; otherwise stay in maintenance and choose another point. After recovered writes/charges/jobs occur, reverting endpoints would create split history: immediately fence both stacks, preserve both datasets/provider state, select one authority and reconcile deltas. Never merge by summing balances or automatically re-enable the old Beat. Rollback does not drop recovery/original data.

Stop for any restore/checksum/key/schema failure, unavailable current deletion/hold/payment facts, wrong target, unexpected old token validity, uncontrolled writers, missing references, or unverified cutover. Full read check failure is not repaired with `restic repair`/forced unlock without a separate reviewed repository-preservation plan. Record incomplete/failed status and actual data-loss estimate.

After stable monitored service, preserve minimal access-controlled incident evidence separately, revoke temporary admin/restore/provider credentials, close public recovery access, reconcile old resources/staging under approved retention, and resume backup/expiry/check timers against the selected live authority. Take and actually rehearse a new checkpoint; check retention backlog and fresh key escrow. Keep ordinary backup max 30 days; any verified legal hold copy must be separately scoped. Don't retain unbounded plaintext case dumps or extend all backups indefinitely for an incident.

Exercise at least quarterly and after restore tooling/storage/key/schema/topology changes, using synthetic data unless a separately authorized representative live drill exists. Record incident/capture/restoration times, data size, full phases, failure paths, findings, owners and follow-up dates; rehearse lost key, corrupted bytes, missing reference, stale deletion/hold evidence and rollback after divergence. CI proves tools and missing-evidence blocking on real disposable PostgreSQL/Restic; it doesn't simulate host loss, prove provider access or measure production RTO.

## 8. Research and validation boundary

- [NIST SP800-34 Rev1](https://csrc.nist.gov/pubs/sp/800/34/r1/final): contingency priorities, responsibilities, recovery/reconstitution and exercises. Used as procedural guidance, not a compliance certification.
- [PostgreSQL16 SQL dump](https://www.postgresql.org/docs/16/backup-dump.html), [pg_restore](https://www.postgresql.org/docs/16/app-pgrestore.html), [CREATE DATABASE](https://www.postgresql.org/docs/16/sql-createdatabase.html), [ALTER DATABASE](https://www.postgresql.org/docs/16/sql-alterdatabase.html): version/extension compatibility, trusted-source SQL, fresh template, transaction/error semantics and rename restrictions.
- [Restic restore](https://restic.readthedocs.io/en/stable/050_restore.html), [repository operations](https://restic.readthedocs.io/en/stable/045_working_with_repos.html): exact snapshot selection, encrypted repository checks and controlled recovery. Use maintained open-source tooling; versions must be recorded.
- [Docker Compose stop](https://docs.docker.com/reference/cli/docker/compose/stop/) and [up](https://docs.docker.com/reference/cli/docker/compose/up/), [Celery periodic tasks](https://docs.celeryq.dev/en/stable/userguide/periodic-tasks.html): stop without volume deletion, dependency startup and one scheduler.
- [Cloudflare R2 upload](https://developers.cloudflare.com/r2/objects/upload-objects/): use supported S3 tooling, correct metadata and private target; no automatic original-bucket recovery writes.

Engineering acceptance: complete procedure, measurable/bound restore report, offline strict evidence checker with failure tests, real disposable restore/evidence integration and all seven final-head CI jobs. Live acceptance still needs real infrastructure/current ledger/holds/provider state, representative complete exercise, recorded service RPO/RTO and reviewed cutover. #27 is Privacy policy publish; do not count its work as part of #26.
