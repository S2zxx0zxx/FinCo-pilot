# Latest-main pre-merge recheck — 15 October 2026

Scope: the owner's five requested release checks. This records measured evidence and explicit blockers, not 80/80 production clearance.

## Source reconciliation and build

- Refreshed remote main: `ccdba0c1108e0ed29fef2447a0d956d7d1150dba`, including growth #89 and landing #92 (17 commits / 115 changed files since the previous security baseline).
- Merged into the existing security branch without conflicts. Both parent histories retained; no rebase, force push, migration, authentication cutover or feature removal. Merged tree `743ee3a91b685259ea19e1011906d1d8d1565a9e`; remote merge candidate `a273dffaac94f818980dc7dd1ab4c97eb0e207d8` matches local exactly.
- Combined CI frontend build reproduced an integration failure: Next static export rejected `/robots.txt` without a static route declaration. Both robots and sitemap metadata handlers now explicitly declare force-static. Existing environment-gated indexability, canonical URL validation and empty preview sitemap remain unchanged. Actual rebuild and Chromium/Firefox/WebKit public-entry acceptance are required; no build assertion is weakened.
- Whole backend Ruff/ty passed. Secret-hygiene checker passed. All ten updated Cloudflare Worker privacy tests and all 25 growth-script tests passed. Final full backend, frontend, build, native CI and public-entry browser outcomes are recorded on PR #91 when complete; pending checks are not passes.

## Authentication and financial isolation

Full combined backend regression includes auth/Clerk/OIDC/reset/MFA/passkey, workspace read/write contracts, scoped directory, finance ownership and accounting suites. Native CI includes role revocation contention, stale-writer/deletion fencing, payment/webhook/MCP replay safety and SQLite-skipped financial reports. These are synthetic users and test providers, not real Google/bank/payment login acceptance. Existing data, issuer/subject identity and provider configuration were not changed. Real owner-controlled staging accounts and the actual deployment binding remain required.

## Secrets, resource limits and logs

Existing before-fix privacy regressions, storage/parser byte-boundary tests, safe stream/task-result errors and application/MCP traceback contract remain in the combined source. Repository hygiene passed; prior broad heuristic/history scan limits still apply. Upload byte limits do not prove multipart disk/concurrency, PDF decompression or CPU isolation; deployment budgets need an isolated measured environment. The source's no-raw-access-log defaults do not prove actual deployed log sinks.

## Runtime, database and recovery evidence

Two fresh public read-only TinyFish fetches of apex `/api/info` and `/api/health/ready` returned HTTP **530**. This establishes those fetch outcomes, not a root cause or proof all access paths fail. Actual origin process/build/database binding is unresolved. No DNS, TLS, Tunnel or production setting was changed.

Only PostgreSQL **system metadata**, no customer rows, was queried on the named Neon FinCo-Pilot production branch `br-spring-pine-azhbu0wx`, database `neondb`. Tool inspection used `neondb_owner`; its metadata reports create-db/create-role/replication/bypass-RLS capabilities. That is the connector inspection identity, not proof the application uses that role. Managed cloud roles were not modified.

Schema metadata still shows legacy `users.user_id/firebase_uid/clerk_uid`, `transactions.transaction_id/amount_paise/direction/observed_at` and `financial_accounts`; the selected metadata query returned no `alembic_version` columns. Current ORM expects the Alembic-managed workspace/identity ledger. The legacy Neon database must not be blindly upgraded or stamped. A safe migration/recovery requires the actual app DB binding and explicit legacy identity/financial/encryption mapping. No customer balances/transactions/users were read, exported, converted or deleted.

The existing source checkpoint records an October 11 Neon branch/aggregate restoration proof; it explicitly does not establish encrypted backup recovery or application compatibility. Current native CI uses actual pg_dump, restic encryption and quarantined disposable PostgreSQL restore; production keys, object bytes, deletion/hold/payment ledgers, isolated target, measured RPO/RTO and last-good runtime image remain unverified. No live restore or rollback was executed or claimed. Need independently identified source, authorized isolated target, private backup/key custody and deployment access before a representative real drill.

## Operator, privacy, terms and legal facts

Existing publication gates require the real operator legal name, entity/country, named staffed privacy contact/email/address, processing locations/providers, current reviewed policy version and effective date. Terms additionally require reviewed contact/commercial/refund/cancellation facts and assent. These checks are tested; production values and legal approval are not supplied by source defaults or the GitHub/Neon account profile.

Do not infer legal name/address, registered status, licenses, active processors, target markets, age policy or contracts. No public notice was published, no paid lifecycle was enabled, and no statutory compliance certification is claimed. Essential owner inputs: legal/entity name and public service/contact details; active processors/regions/contracts and intended markets/age scope; approved commercial terms; counsel/applicability review where needed. Actual provider and runtime facts must agree with the published notice.

## Release state

PR #91 remains draft. Final combined checks are required. Production deployment, database conversion, identity remapping, backup copying/cutover, DNS/TLS/permission changes and legal publication remain separate reviewed actions. A passing synthetic CI run does not close these external gates.
