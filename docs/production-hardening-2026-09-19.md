# Launch hardening — implementation and release gates

Repository: S2zxx0zxx/FinCo-pilot. Base: `fa599f1579e9b11e827851cd2c48225a0c7b46a4`.
Branch: `fix/production-hardening-2026-09-19`.

**This is a hardening implementation, not a declaration that the public paid/bank-connected product is ready.** No production bank, payment, SMTP, AI, object-storage account or running deployment was supplied for verification. Never substitute a sandbox response or passing mocked test for a real provider acceptance test.

## Audit disposition

| Finding | Implementation / outstanding acceptance condition |
| --- | --- |
| F01 — production boot | Compose explicitly defaults metrics off and forwards its optional token. Production settings still enforce real secrets, HTTPS, FX and SMTP requirements. |
| F02 — stale MCP membership | Every tool call checks active user, current workspace membership/archive and live capability. Writes additionally check current role. Removed-member/viewer regressions included. |
| F03 — TOTP replacement | Setup refuses to overwrite an enabled authenticator. Replacement requires disabling with password and current factor first. |
| F04 — weak passwords | Shared server user manager enforces 8–128 characters, including registration, change and reset. |
| F05 — token revocation | Durable user credential epoch plus keyed credential stamp. Logout revokes all sessions; password changes/resets invalidate prior tokens and pending second-factor challenges. |
| F06 — recovery UI | Forgot/reset pages, password confirmation, missing/expired link handling and navigation added. Actual inbox delivery remains an external gate. |
| F07 — SMTP Compose | All SMTP transport/auth/from fields forwarded; production local auth requires delivery by default. Validate real sender DNS, TLS and inbox delivery. |
| F08 — verification | Rate-limited verification request and verification routes mounted; request/consume pages added. This does not introduce a blanket verified-email login requirement. Any future payment/bank feature must explicitly require ownership where its contract requires it. |
| F09 — bootstrap | UI accepts protected setup token and honors setup availability. Disable setup after creating the first admin. |
| F10 — Indian AA | **Not implemented/blocked on provider selection and partner access.** Existing international connectors are not an Indian Account Aggregator integration. Need approved FIU/AA partner, consent/data API contract and sandbox access before implementing the adapter and production onboarding. |
| F11 — payments | **Not implemented.** No actual checkout, signed payment webhook, subscription reconciliation or cancellation is claimed. Need merchant/provider selection, enabled recurring payments, plan IDs/prices and refund/cancellation requirements. Public copy now clearly says upgrades are unavailable and no payment is collected. |
| F12 — sign contract | New/updated transaction amounts are non-negative finite magnitudes; type is debit/credit. Existing imported records remain readable (legacy signed records are not silently rewritten). |
| F13 — accounts | Supported type, three-letter currency, nonblank name, nonnegative credit terms and valid billing days checked at the API boundary. Existing wallet/investment types preserved. |
| F14 — invalid dates | Account summary/history date query parameters are parsed as dates, yielding 422 instead of 500. |
| F15 — dependencies | Frontend lockfile updated within declared ranges; npm audit reports zero known advisories at verification time. This is not a guarantee against future disclosures. |
| F16 — storage | Production Compose forwards bucket, region, endpoint and credentials and the object-storage requirement flag. Actual S3 upload/download/delete and restore test still required. |
| F17 — live AI | **Unverified external gate.** Choose actual provider/model, configure the existing connection mechanism, run streamed responses, tool approval/denial, document retrieval and failure recovery on the deployed host. No workflow green tick is treated as inference proof. |
| F18 — catalogue | Free/Pro AI action allowances set to zero to match the existing Max-only agent capability. This does not add a separate basic AI assistant. |
| F19 — external writes | Registered external tokens default read-only. Explicit write scope, live authorization and strict JSON boolean `apply` are required; OpenAI snippet also requests client-side approval. Every external write now queues an exact, ten-minute approval in Agent Connections. A logged-in user must approve it in the app; the server rechecks token, membership, capability and quota. Durable single-use claims prevent replay; uncertain execution is marked for review and never automatically retried. |
| F20 — MCP secret | Enabled production agents require a distinct configured signing secret of at least 32 characters; external token lifetime limited to 1–90 days. |
| F21 — metrics | Token-protected `/metrics`, bounded method/status labels and per-process uptime/request totals. Multiworker aggregation, alert rules, tracing and on-call routing remain operator work. |
| F22 — app fallback | Global React render error boundary and useful unknown-route screen. Existing page/network errors remain separate. |
| F23 — 2FA recovery | Ten cryptographically random one-use recovery codes; only hashes stored. Reissue requires password and current TOTP. Codes shown once. Test proves a consumed code cannot log in again. |
| F24 — policies/support/exit | **Not completed.** Need operator identity, support channel, privacy/retention/processor details, terms and a shared-workspace deletion policy. Do not publish invented legal promises or cascade-delete collaborators' financial data. |
| F25 — PWA | Existing shell/offline behavior retained. No offline financial editing/sync guarantee. Device installation, update and reconnect still require browser acceptance. |
| F26 — safe-to-spend | New workspace-scoped conservative calculation and dashboard entry. Reserves full card debt, upcoming/pending debits, recurring projections and user-entered buffers/obligations. Blocks headline on incomplete review, stale/unconfirmed provider refresh, unsupported account types or missing recent FX. See limits below. |
| F27 — loans/EMI | **Not completed.** Dedicated loan principal/interest/amortization and provider loan classification need a separate schema/ledger change and acceptance examples. Current spending plan requires users to include unrecorded loan obligations explicitly; this does not turn the existing app into a loan engine. |
| F28 — copy/localisation | Checkout messaging rewritten for users instead of implementation details. New recovery/spending-plan content is currently English; full Hindi and other-locale translation remains open. |

## Spending-plan contract

`POST /api/dashboard/spending-plan` is a read-only, authenticated workspace calculation. Viewers can calculate within workspaces they can read. Inputs: horizon 1–90 days, emergency buffer, goal reserve, other obligations and explicit obligation review. Financial JSON values are decimal strings.

The headline is the nonnegative difference between current liquid cash and all reserves. Negative results also expose a shortfall. Daily allowance rounds down. Investment holdings, credit limits and future income do not fund the allowance. Matched future cash-to-cash transfers are excluded; already-settled incoming transfers do not hide a future outgoing payment. The shared recurrence projector suppresses already materialized occurrences.

Conservative limitations are visible in the UI: full card debt is reserved even outside the horizon; pending debits and future card repayments can duplicate an amount already included in a bank snapshot/reserve, reducing the estimate. Manual balances require user reconciliation. Mixed-currency manual ledger entries block the headline. FX uses cached USD cross-rates no older than seven days; no 1:1 fallback or provider call occurs in this calculation. Bank freshness requires an actual provider refresh timestamp within 24 hours, not merely a successful cached ingestion. Providers that cannot prove freshness will require reconciliation rather than receiving a misleading spendable number. Calendar boundaries currently use server dates.

This first version does not persist a personal plan, optimize debt schedules or infer missing loans/taxes. User-entered obligations are necessary. Do not market it as a guarantee that every liability has been discovered.

## Required operator inputs

Set secrets in the deployment secret manager / environment, **not in source control or a public issue**.

| Area | Required configuration or decision |
| --- | --- |
| Host | Actual domain/HTTPS URL, hosting account or server access, immutable image version, public frontend URL and trusted proxy chain. |
| Core | Strong unique `SECRET_KEY`, PostgreSQL URL, Redis service, backups and a tested restore procedure. |
| Setup | Temporarily `SETUP_ENABLED=true`, strong `SETUP_TOKEN`; disable after first admin creation. |
| Mail | `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL`, correct STARTTLS/SSL mode. Keep `EMAIL_DELIVERY_REQUIRED=true` for production local login. |
| FX | `OPENEXCHANGERATES_APP_ID`; production keeps `FX_ALLOW_UNSAFE_1TO1_FALLBACK=false`. |
| Attachments | Durable local volume plus backups, or `STORAGE_PROVIDER=s3`, bucket, region, endpoint if applicable and scoped access/secret key. For required object storage set `REQUIRE_OBJECT_STORAGE=true`. |
| Metrics | Optional `METRICS_ENABLED=true` plus unique `METRICS_TOKEN`, protected scrape target and operator alerts. |
| Agents | `AGENTS_ENABLED=true` only after configuring the real AI connection. Unique `AGENTS_MCP_JWT_SECRET`; public HTTPS `AGENTS_EXTERNAL_MCP_URL` if external access is wanted. Read-only external credentials are the default. |
| International banks | Credentials and redirect URLs for whichever existing supported connectors will actually be offered. Each needs connect, refresh, expired consent, retry, disconnect and duplicate-sync acceptance tests. |
| India | Actual approved AA/FIU partner and sandbox/production access. A generic bank API key alone does not establish this integration. |
| Billing | Merchant account/provider, recurring-payment enablement, exact monthly/annual plans, webhook secret, tax/refund/cancellation policy and test acceptance cases. |
| Customer trust | Operator/company details, privacy/terms, support address, retention and user/shared-workspace deletion rules. |

## Deployment and rollback

1. Back up the database and attachment volumes; rehearse restoring them into an isolated environment.
2. Build immutable backend/frontend images from the reviewed commit. Existing Compose release-image variables must reference these images; changing a Git branch does not update deployed containers.
3. Configure the production environment. Validate Compose and Settings with real configuration before starting services; never disable protective validation merely to get a green boot.
4. Run `alembic upgrade head` against the intended database. Revision 094 adds credential epoch/recovery-code columns and the external MCP credential registry; revision 095 adds exact-action approval records. Deploy backend, workers and MCP together so every process shares the new authorization contract.
5. Existing app JWTs, pending login challenges and old unregistered external MCP tokens deliberately require re-login/reissue. Notify users before release. Logout now signs out all devices. Offline local logout cannot contact the server to revoke a session until connectivity returns.
6. Verify health, real account registration/recovery/verification, secure admin bootstrap, no tenant crossover, 2FA recovery, real bank sync and actual AI behavior. Exercise browser navigation on mobile and desktop; inspect console/network errors.
7. Enable paid/India marketing claims only after their missing integrations and provider tests pass. Do not merge/deploy this branch as evidence of those features.

Rollback should restore the prior application images and a compatible backup in a controlled maintenance window. **Do not blindly downgrade the production database**: dropping credential history can undo revocation guarantees. The CI downgrade exercise runs only against its disposable database.

## Verification evidence

- Frontend: 743 tests across 82 files passed after recovery and spending-plan additions; production build passed; ESLint passed.
- Backend security/account tests: 294 targeted tests passed before the additional spending-plan cases. Full final regression result is recorded below when complete.
- Ruff and ty passed after the approval implementation.
- Migration chain: 95 revisions, single head `095`.
- Added a real PostgreSQL/pgvector CI job to apply all migrations, roll back new migrations 094–095 on an empty disposable database, and reapply. A chain check alone is not execution evidence.
- Browser click-through in this environment was blocked from the local application URL. Browser/device/live-provider acceptance is **not** marked passed.

## September 20 continuation

The initial PR run passed frontend checks, Helm checks, migration chain and the real PostgreSQL upgrade/rollback/reapply job. Backend had 3,859 passing tests, seven PostgreSQL-specific skips and one failing recovery-code fixture. That fixture fabricated a stale credential challenge; it now obtains real password-login challenges and verifies a consumed recovery code fails even with a fresh challenge. The corrected recovery/passkey/spending group passed all 59 tests.

Server-mediated external-action approvals are now implemented, including exact stored arguments, user/workspace/token binding, expiry, explicit rejection, current-role revalidation, token revocation and durable single-use execution. Approval history is visible in Agent Connections. Requests are bounded to 16 KiB and 50 per credential per hour; old expired records are pruned on subsequent submissions. A failed/uncertain execution requires inspection rather than automatic replay. Added a PostgreSQL concurrency CI test that sends two simultaneous approval requests and verifies exactly one financial mutation.

Local approval/security/route regression: 198 passed. Approval UI: two interaction tests passed. Full final PR CI is being re-run on the updated commit; do not infer success from earlier commits.
