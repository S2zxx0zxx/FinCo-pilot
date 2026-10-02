# FinCo-Pilot Data Retention Contract V1

**Roadmap:** #9 — Data-retention policy  
**Contract:** `FINCO_DATA_RETENTION_V1`  
**Version:** 2026-10-01  
**Status:** engineering policy contract; runtime purge/deletion workflows are intentionally deferred to roadmap #10, #11, #25, #29 and #30.

This document is the canonical retention contract for FinCo-Pilot. It is not generic privacy copy and it is not a claim that every deletion path is already implemented. It maps the stores that exist in the repository today, states the intended lifecycle for each category, and records the gaps later roadmap items must close.

Roadmap #12 maintains the canonical external-service/processor register in `docs/trust/processor_inventory.v1.json` with the human-readable contract in `FINCO_THIRD_PARTY_PROCESSOR_INVENTORY_V1.md`. Any provider-side copy governed by that inventory must satisfy this retention contract before production activation.

## 1. Policy principles

1. **Purpose first.** Primary user finance/workspace data lives only while the corresponding user/workspace purpose remains active, unless a documented legal hold or contractual retention requirement applies.
2. **No invented regulatory status.** FinCo-Pilot is currently operated by an individual/solo founder. This contract does not call the operator a bank, NBFC, FIU, payment-system operator, regulated entity, company, LLP or other status that has not been established.
3. **Secrets are not records.** Passwords, OTPs, CVV/CVC, full card PAN/Card-on-File data, API keys, bearer tokens and provider client secrets must not be copied into logs, support tickets, audit payloads or analytics. Credential stores have their own narrow lifecycle.
4. **Deletion means every primary copy.** Database rows, object/file bytes, search/vector material and provider-side copies are separate deletion targets. Deleting only a SQL row is not sufficient when a file or processor copy remains.
5. **Backups expire; they are not an undelete mechanism.** Production backups have a 30-day maximum lifecycle. A disaster restore must re-apply deletion tombstones/legal holds before restored data is returned to normal service.
6. **Shared data is not personally owned data.** A user's account deletion must not silently destroy data owned by a shared workspace. Roadmap #10/#11/#29/#30 must make ownership and role transitions explicit.
7. **Legal hold is exceptional and scoped.** A legal/security/provider hold must have a reason, category, start, review/expiry and authorised actor. A hold never becomes a blanket excuse to keep unrelated product data.
8. **Processors must be deletable.** If a third-party provider cannot support the required lifecycle, that is a production contract blocker, not something the product may hide with UI copy.
9. **Unknown stores fail closed.** New persistent stores must be added to this contract before production use. `app.core.retention.get_retention_rule()` deliberately has no catch-all default.

## 2. Current legal/provider anchors — separated from operator decisions

### Current purpose-limitation anchor: IT SPDI Rules, 2011

The Information Technology (Reasonable Security Practices and Procedures and Sensitive Personal Data or Information) Rules, 2011, Rule 5(4), says that covered holders of sensitive personal data or information must not retain it longer than required for the lawful purpose for which it may be used, unless another law requires retention. Financial information is within the SPDI framework. The 2011 clarification describes Rules 5 and 6 as applying to covered body corporates/persons in India, subject to the contractual-service distinctions in that clarification.

For FinCo-Pilot V1 this is treated as a **current purpose-limitation anchor**, not as a made-up fixed-year period: active financial data is purpose-bound and longer exceptions need a documented law/provider/hold basis. Exact applicability to the present individual/solo-operator structure should be confirmed as part of legal review.

Official sources:
- https://meity.gov.in/sites/upload_files/dit/files/GSR313E_10511%281%29.pdf
- https://www.meity.gov.in/writereaddata/files/PressNote_25811.pdf

### Current cybersecurity anchor: CERT-In

CERT-In's 28 April 2022 Directions require covered service providers, intermediaries, data centres, body corporates and government organisations to enable logs of ICT systems and retain them securely for a rolling **180 days**, with those logs maintained within India. FinCo-Pilot's exact legal classification should be confirmed before public production; this contract nevertheless adopts a **365-day India-resident security-log engineering baseline** so launch architecture does not depend on a narrower interpretation.

Official source: https://www.cert-in.org.in/PDF/CERT-In_Directions_70B_28.04.2022.pdf

### Scheduled future DPDP requirements — not falsely treated as already effective

The Digital Personal Data Protection Rules, 2025 were notified in November 2025. The notification states that Rules 3, 5–16, 22 and 23 come into force **18 months after publication**. That means the Rule 6 and Rule 8 retention provisions are scheduled for **14 May 2027**, not October 2026.

When effective, Rule 6(e) requires one-year retention of relevant logs/personal data for security detection, investigation, remediation and continuity, unless another law requires otherwise. Rule 8(3) requires one-year retention of personal data, associated traffic data and processing logs for the purposes in the Seventh Schedule, followed by erasure unless longer retention is otherwise required. The Seventh Schedule is tied to specified governmental/lawful information purposes.

FinCo-Pilot's **365-day security-log baseline is an operator engineering decision today** and also provides runway for those scheduled future requirements. It is not recorded as an already-operative October 2026 DPDP legal minimum.

Official sources:
- https://www.meity.gov.in/static/uploads/2025/11/53450e6e5dc0bfa85ebd78686cadad39.pdf
- https://www.meity.gov.in/static/uploads/2025/11/c56ceae6c383460ca69577428d36828b.pdf

### Razorpay contractual anchor

The currently published Razorpay Payments merchant terms include a broader general obligation requiring transaction/order-related records to be retained for **10 calendar years from the relevant order date**. A separate device-specific India clause also mentions a six-month minimum for invoices/charge slips. For FinCo-Pilot's selected Razorpay payment path, the 10-year merchant-record clause is the conservative contractual anchor unless Razorpay provides a written service-specific exception. This is a provider-contract requirement, not a general Indian statutory retention rule for all FinCo-Pilot data.

Official/provider source: https://razorpay.com/terms/

### Payment-card storage prohibition

RBI's Card-on-File restriction states that entities in the card transaction/payment chain other than card issuers/card networks must not retain actual Card-on-File data after the permitted transition period. FinCo-Pilot therefore stores provider/customer/order/payment identifiers only and **must never persist full card PAN or CVV/CVC**.

Official source: https://www.rbi.org.in/scripts/NotificationUser.aspx?Id=12345

### Zoho Desk provider behavior

Zoho Desk documents that ordinary deleted records remain in its Recycle Bin for **60 days** before automatic permanent deletion, while an authorised administrator can permanently delete a record from the Recycle Bin earlier. Zoho's current data-retention table separately states that Service Data (Module Data) deleted from the UI has a **90-day backup-server tail after Trash deletion**; a record permanently deleted from the Recycle Bin is scheduled for active-database deletion within 24 hours and still has the documented 90-day backup tail.

FinCo-Pilot's operator-selected support policy is 365 days after ticket closure. At that trigger, the runbook should delete the ticket and permanently clear it from the Recycle Bin as soon as the provider/admin flow permits rather than deliberately waiting another 60 days. The remaining provider backup tail is processor-managed and must be disclosed/verified under roadmap #12. Zoho's separate provider audit-log retention is also a processor-inventory item, not FinCo-Pilot ticket-content retention.

Provider sources:
- https://help.zoho.com/portal/en/kb/desk/data-administration/recycle-bin/articles/using-the-recycle-bin
- https://help.zoho.com/portal/en/kb/desk/user-management-and-security/data-security/articles/data-retention

## 3. Canonical windows

These are FinCo-Pilot operator/engineering decisions unless described above as a legal/provider anchor.

| Policy key | V1 window / trigger |
|---|---|
| Security/request/access logs | rolling 365 days |
| Production backups | rolling maximum 30 days |
| Unreferenced object/file sweep | within 24 hours after a deletion lifecycle marks the blob orphaned |
| Closed support tickets | 365 days after closure, then provider deletion + prompt permanent Recycle Bin purge where permitted; current Zoho docs list a 90-day backup tail after Trash deletion |
| Abandoned/expired checkout reservation | 30 days after terminal expiry/abandonment |
| Successful payment/subscription evidence | 365 days after the payment/service relationship ends for ordinary internal evidence; Razorpay transaction/order records that fall under the current merchant contract use 10 calendar years from the relevant order date |
| Pricing/security/MCP minimal approval evidence | rolling or terminal-state + 365 days; minimise actor/content fields when no longer required |
| Exact MCP approval argument payloads | 30 days after terminal state, then redact/remove while preserving only minimal approval evidence |
| AI usage telemetry | rolling 365 days |
| Active primary finance/workspace data | while purpose/account/workspace remains active; user/workspace deletion contract controls end-of-life |
| AI conversations | until user deletes the conversation or parent account/workspace reaches deletion |
| AI knowledge | until user deletes the document/agent or parent account/workspace reaches deletion |
| Bank credentials | revoke upstream then delete immediately on disconnect/deletion |
| Redis auth/OAuth/rate-limit state | existing explicit TTL; no backups |
| User-generated ZIP exports | not persisted server-side |

The executable constants and category registry live in `backend/app/core/retention.py`. A new persistent category must be added there and here together.

## 4. Repository data map

| Data category | Source | Storage location | Purpose | Owner / scope | Current deletion behavior | Required / proposed retention | Deletion / anonymisation method | Exceptions / hold | Backup expiry | Third-party processor |
|---|---|---|---|---|---|---|---|---|---|---|
| Account identity & preferences | registration/settings/OIDC | PostgreSQL `users` | authentication, profile, locale/preferences | personal user | admin delete exists; self-service deletion is not complete | active purpose; #10 defines end-of-life | hard-delete account identity after dependency resolution; retain only scoped hold evidence | security/legal hold only | max 30d | OIDC IdP if configured |
| Password/recovery/TOTP/passkeys | auth flows | PostgreSQL `users`, `user_passkeys`; Redis challenges | account security | personal user | passkey delete exists; user deletion dependency handling is incomplete | credential lifetime; Redis TTL 5–10 min or current auth TTL | revoke/invalidate then hard-delete | incident preservation only | max 30d for DB; Redis none | WebAuthn authenticator ecosystem |
| Workspaces & memberships | workspace API | PostgreSQL `workspaces`, `workspace_members`, `workspace_tax_ids` | tenancy, ownership, issuer/tax metadata | workspace, potentially shared | **archive only**; no production hard-delete workflow | active purpose; shared deletion defined by #11/#30 | explicit ownership transfer/archive/delete plan; never cascade shared data from a member account blindly | legal/tax hold if actually applicable | max 30d | none |
| Financial ledger & planning | manual/import/bank sync | PostgreSQL accounts, transactions, categories, rules, budgets, recurring items, goals, loans, assets/values/trades, collections, groups/settlements, reconciliation | core finance product | workspace | mixed per-entity hard delete/archive; workspace archive preserves data | active purpose | workspace-scoped hard delete or anonymisation only when ownership/hold checks pass | documented legal hold | max 30d | bank providers for synced subset |
| Payees & fiscal identifiers | user/invoice flows | PostgreSQL payees, payee tax IDs | transaction and invoice context | workspace | cascades vary; not covered by old manual admin delete completely | active purpose | workspace lifecycle | actual tax/legal obligation only; no invented statutory duration | max 30d | none |
| Invoices & fiscal documents | user/provider import | PostgreSQL invoice tables + object storage | billing/document tracking | workspace | invoice attachment service deletes object + row; parent cleanup is best-effort | active purpose; longer only when actual tax/provider obligation is established | delete DB + object bytes together | documented tax/legal/provider hold | max 30d | object-storage provider; source provider |
| Transaction attachments | user upload | PostgreSQL `transaction_attachments` + local/S3 object storage | receipts/supporting docs | workspace | direct attachment delete removes object + row; transaction cleanup is best-effort | parent transaction/workspace lifecycle | object delete + DB delete; orphan sweep <=24h | legal hold if scoped | max 30d | S3-compatible provider when enabled |
| Workspace invoice logo | user upload | object storage + invoice settings logo id | document branding | workspace | replacement/read implemented; lifecycle cleanup must be verified in later deletion work | workspace active purpose | delete derived object key when replaced/workspace deleted | none normally | max 30d | S3-compatible provider |
| Import metadata | CSV/OFX import | PostgreSQL `import_logs` | import trace, counts, source name | workspace | admin delete includes old import-log path; shared lifecycle incomplete | active purpose; source files should not be retained after parse unless explicitly required | hard-delete metadata with workspace; no raw upload archive by default | incident hold only | max 30d | none |
| User-generated backup/export | export API | in-memory response stream; user device after download | portability/user backup | user/workspace | server does not persist generated archive | **no server retention** | N/A after response | none | none | destination chosen by user |
| Bank provider credentials & consent state | connection/OAuth | PostgreSQL `bank_connections.credentials/settings`; Redis OAuth state | bank access/sync | user + workspace | local row delete exists in some paths; upstream revocation is not a proven universal invariant | only while connection active; OAuth state 10 min | revoke provider consent/token first, then erase local credential | provider/legal incident hold only; never copy secret to audit | max 30d for DB; Redis none | Pluggy / Enable Banking / SimpleFIN / future AA |
| Bank-synced financial data | bank provider | PostgreSQL accounts, transactions, institutions, card bills, raw provider metadata | ledger and Safe-to-Spend inputs | workspace | tied to financial entity deletion/cascades | active purpose | delete workspace/account rows and raw provider payloads when lifecycle ends | documented legal hold | max 30d | bank-data provider |
| Checkout reservations | pricing/checkout | PostgreSQL `checkout_reservations` | reserve offer position/order flow | user | expiration state exists; automatic purge is not implemented | 30d after terminal expiry/abandonment | hard-delete unsuccessful terminal reservation after audit evidence separation | fraud/security dispute hold | max 30d | Razorpay when live |
| Successful payments/subscriptions/founder evidence | verified payment lifecycle | PostgreSQL subscription/founder/reservation fields; provider | entitlement, billing evidence | user | paid lifecycle is not yet fully live; user FK cascades currently exist | active relationship + 365d after end for ordinary internal evidence; Razorpay transaction/order records covered by current merchant terms retain 10 calendar years from relevant order date | minimise identifiers; delete/anonymise after window/holds | chargeback, tax, legal hold | max 30d | Razorpay |
| Pricing audit events | pricing admin/offer engine | PostgreSQL `pricing_audit_events` | campaign integrity/audit | operational | append-only; actor FK can SET NULL; no purge job | rolling 365d | detach/anonymise actor where possible then purge after window | security/legal hold | max 30d | none |
| Support tickets | authenticated support form/email/portal | Zoho Desk; app logs contain references, not ticket body | customer support/security escalation | personal user + support case | provider owns ticket; app does not persist local ticket body | 365d after closure, then provider deletion | delete ticket and permanently purge Recycle Bin promptly where permitted; current Zoho docs still list a 90d backup-server tail after Trash deletion | unresolved dispute/security/legal hold | provider-managed: current Zoho service-data backup tail is 90d after Trash delete | Zoho Desk |
| Request IDs & application/security logs | API/middleware/process | deployment log sink/stdout | debugging, security response, support correlation | operational; may reference user/request | logging exists but production sink/TTL/residency not yet proven | rolling 365d engineering baseline | automatic log-store expiry; redact secrets/body; access-restrict | active incident/legal hold | not in app DB backups | hosting/logging provider |
| Redis rate limits | login/register/reset/support | Redis | abuse prevention | IP/user bucket | explicit expiry 60s–1h + buffer | existing TTL only | TTL expiry | none | none | Redis host |
| OAuth state | bank connection redirect | Redis `oauth_state:*` | bind callback to user/workspace/provider | user/workspace | GETDEL one-shot; 10 min TTL | 10 min maximum | consume once or TTL | none | none | Redis host |
| WebAuthn/2FA temporary challenges | login/passkey flow | Redis | authentication ceremony | personal user | one-shot/delete + TTL; passkey challenge default 5 min | existing TTL only | consume/delete or TTL | none | none | Redis host |
| AI agents & configuration | user/Max agent setup | PostgreSQL agents/tools/LLM connections | custom AI features | user + workspace | agent deletion cascades child rows; archive also exists | active purpose | hard-delete/connection secret erase with parent lifecycle | security hold only for event evidence, not secret | max 30d | OmniRoute/upstream LLM |
| AI provider credentials | user/instance connection | PostgreSQL encrypted key or deployment secrets | route model calls | user/instance | connection deletion path exists; exact upstream lifecycle varies | only while connection/provider enabled | revoke upstream then delete encrypted local secret | incident-only hold where safe | max 30d for encrypted DB copy | OmniRoute/upstream provider |
| AI conversations/messages/tool results | chat/tool calls | PostgreSQL conversation/message tables | user history and product function | user + workspace | explicit conversation hard delete cascades messages | until user deletes or parent lifecycle ends | hard-delete conversation/messages | narrowly scoped legal hold | max 30d | OmniRoute/upstream LLM for request copies |
| AI knowledge raw files/chunks/embeddings | knowledge upload | local agent-knowledge volume + PostgreSQL chunks/pgvector | RAG | user/agent/workspace | doc row deletion then best-effort filesystem delete; no orphan reconciler | document/agent/workspace lifecycle | delete raw file + chunks + embeddings; orphan sweep <=24h | narrowly scoped legal hold | max 30d | embedding/LLM provider depending configuration |
| AI usage telemetry | AI runtime | PostgreSQL `llm_usage` | quota/cost/latency operations | user + agent | user FK cascade; no age purge | rolling 365d | purge or anonymise actor ids after window | billing/security hold | max 30d | upstream LLM may hold own logs |
| External MCP tokens | MCP issuance | PostgreSQL token metadata; bearer token itself not stored | external integration auth | user + workspace | revoke/delete endpoints exist; token metadata/approvals persist by lifecycle | expiry/revocation + 365d evidence | never store bearer token; detach/purge metadata after evidence window | incident hold | max 30d | external MCP client/server |
| MCP approvals/tool arguments | MCP mutations | PostgreSQL `mcp_approvals` | exact human-approved mutation/replay protection | user + workspace | terminal states/expiry exist; pruning is partial/on-submit and exact arguments share the row | exact argument payload: terminal state + 30d; minimal decision/evidence: up to 365d | redact/null exact arguments after 30d while retaining only non-sensitive decision/result evidence needed for the 365d window | incident/legal hold must be scoped to the necessary evidence | max 30d | none |
| Production DB/object backups | infrastructure | database/object backup service | disaster recovery | system | actual production backup/restore is roadmap #25; not yet acceptance-tested | rolling max 30d | encryption + automatic expiry; restore must reapply deletion tombstones | explicit legal hold backup copy only, separately controlled | 30d | hosting/backup provider |

## 5. Current deletion gaps discovered during #9

These are facts from the current repository and must remain visible until later items close them:

1. **The admin user-delete routine predates multiple newer domains.** It manually deletes a subset of finance rows and then the user. It is not a safe personal-account deletion implementation for the current workspace/agents/billing model.
2. **Admin user deletion can orphan attachment bytes.** It deletes `TransactionAttachment` rows directly without invoking `cleanup_attachment_files()`, so object-storage bytes can survive the SQL deletion.
3. **Workspace deletion is not implemented.** The current workspace endpoint archives by setting `is_archived`; it does not hard-delete a workspace or its blobs.
4. **File cleanup is partly best-effort.** Transaction/invoice/knowledge cleanup catches storage/filesystem failures. There is no durable orphan reconciliation queue proving eventual deletion.
5. **Production log retention is not enforced by application code.** Request IDs are logged, but the hosting/log sink, India residency, access policy and automatic 365-day expiry are an external deployment requirement.
6. **Backup expiry is not an active production control yet.** The 30-day window is a contract for #25; it is not proof that production backups are currently configured.
7. **Third-party deletion is not centrally orchestrated.** Zoho, Razorpay, bank providers, OmniRoute/upstream model providers and hosting/object storage need verified processor deletion behavior in #12 and their integration roadmap items.
8. **Bank credential disconnect must prove upstream revocation.** Local row deletion alone is not enough for OAuth/consent providers.
9. **AI knowledge raw-file deletion is best-effort.** SQL deletion can succeed before filesystem deletion, requiring an orphan sweeper/reconciler later.
10. **No legal-hold registry exists.** Later deletion work must not invent one ad hoc; it must be a narrow auditable mechanism tied to this policy.
11. **MCP approval arguments and evidence currently share one row.** The V1 contract now gives exact tool arguments a 30-day terminal-state window but keeps minimal approval/security evidence for up to 365 days. Later lifecycle work must redact/null the argument payload without destroying the narrower replay/security evidence.

## 6. Deletion state machine required by later roadmap items

Roadmap #10/#11/#29/#30 should implement a common lifecycle rather than scattered `DELETE` calls:

```text
requested
  -> ownership/member impact resolved
  -> provider revocations requested
  -> legal/provider holds evaluated
  -> primary DB delete/anonymise
  -> object/file delete
  -> processor delete
  -> deletion tombstone recorded (minimal, no restored content)
  -> backup expiry window
  -> verified complete
```

A failed external deletion remains visible/retriable to operators. It must never be silently reported to the user as complete.

Shared-workspace rules:
- deleting a member account removes personal membership/auth data, not the shared workspace's ledger;
- sole-owner deletion must force an explicit ownership transfer or workspace-deletion choice;
- `managed_by_user_id`, `created_by_user_id`, `billing_owner_user_id`, invitations and actor references must be resolved deliberately;
- workspace hard deletion must remove SQL rows and every object/knowledge file key under that workspace.

## 7. Logging and data-minimisation rules

Security/request logs may include: request ID, time, HTTP method, route template, status, service instance, coarse security outcome and pseudonymous/internal actor id where needed.

They must **not** include:
- passwords, OTPs, recovery codes, TOTP seeds;
- Authorization headers/JWTs/MCP bearer tokens;
- provider OAuth/client secrets or refresh/access tokens;
- full bank credentials;
- full payment-card PAN or CVV/CVC;
- raw support ticket descriptions;
- raw uploaded document/file contents;
- full AI prompt/tool payloads by default;
- full provider response bodies that may echo personal or financial data.

Application metrics remain aggregate and must not carry email/user IDs or other personal labels.

## 8. Backup contract

- Maximum normal production backup retention: **30 days**.
- Backups must be encrypted and access-restricted.
- Backup media is not queried for product features.
- Deletion does not require destructive surgery inside immutable point-in-time backups; instead the deleted data expires with the backup window.
- A restore into production must replay a minimal deletion-tombstone set before users can access restored data.
- A legal hold, if genuinely required, creates a separately controlled hold copy with explicit scope/review; it does not extend every backup.
- #25 must prove an actual backup **and restore** against this contract.

## 9. Processor obligations carried into roadmap #12

The processor inventory must record for each provider:
- data categories sent;
- region/residency;
- purpose;
- sub-processors;
- default retention;
- configurable retention;
- deletion API/manual procedure;
- backup deletion lag;
- account termination behavior;
- security logs;
- DPA/terms/privacy version/date;
- evidence of production configuration.

Known processor candidates from the current code/config include Zoho Desk, Razorpay, bank/open-banking providers, OmniRoute/upstream model providers, SMTP, S3-compatible object storage, production database/Redis/hosting and any observability/log sink. Listing a candidate here does not prove it is enabled in production.

## 10. Acceptance criteria for roadmap #9

#9 is code-complete only when all of these are true:

- this contract is committed on a dedicated branch;
- the machine-readable registry exists and fails closed for unknown categories;
- tests prove the policy invariants;
- legal/provider anchors are sourced and clearly distinguished from operator choices;
- current deletion gaps are recorded rather than mislabeled complete;
- CI passes on the branch;
- the diff contains no secrets/unrelated product changes;
- the hardening report and durable continuity checkpoint are updated.

Even after #9 merges, **production retention enforcement is not fully accepted** until the relevant hosting/logging/backups/processors and later deletion roadmap items are implemented and externally verified.
