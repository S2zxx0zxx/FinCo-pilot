# FinCo-Pilot Personal Account Deletion Behavior V1

**Roadmap item:** #10 — Personal account deletion behavior  
**Contract ID:** `FINCO_PERSONAL_ACCOUNT_DELETION_V1`  
**Version:** 2026-10-02  
**Status:** behavior/engineering contract only; destructive implementation and E2E acceptance remain roadmap #29.

## 1. Purpose

This contract defines exactly what FinCo-Pilot means when a user asks to delete
their personal account. It builds on the retention contract in
`FINCO_DATA_RETENTION_V1` and deliberately separates:

- deleting a person's authentication/account identity;
- deleting data that belongs only to that person;
- preserving data owned by a shared workspace;
- revoking external provider access;
- deleting object/file/vector copies as well as SQL rows;
- retaining only records whose separate #9 retention window still applies;
- waiting for bounded backup expiry before declaring the lifecycle fully
  complete.

Roadmap #10 defines behavior. It does **not** expose a production delete-account
endpoint, create a deletion job table, call providers, hard-delete workspaces,
or claim production acceptance. Those are roadmap #29 responsibilities.

## 2. Current repository reality

The current repository has an administrator-only `delete_user()` routine. It
predates newer workspace, agents, billing and retention domains and is not a
safe implementation of this contract.

Known reasons it must not become the self-service delete-account path:

1. it manually deletes only a subset of user-owned tables;
2. it can delete `TransactionAttachment` rows without deleting the
   corresponding object bytes;
3. it deletes bank-connection rows without proving upstream consent/token
   revocation;
4. it does not resolve shared-workspace owner, manager or billing-owner
   relationships;
5. it predates newer agents/knowledge/MCP/billing data;
6. a user row cascade is not equivalent to processor deletion, object deletion,
   backup expiry or evidence minimisation.

The existing workspace hard-delete problem is intentionally not hidden by this
contract. Workspace deletion itself remains roadmap #11/#30 work.

## 3. Non-negotiable user-visible behavior

A future self-service deletion flow must:

1. be available regardless of Free/Pro/Max plan;
2. require fresh authentication or another strong confirmation step before a
   destructive request is accepted;
3. show blocking workspace actions before destructive execution;
4. never imply that leaving/deleting an account destroys a shared workspace;
5. invalidate normal account access once destructive execution begins;
6. never display provider credentials, tokens or internal deletion secrets;
7. expose a stable opaque deletion reference for support/status correlation;
8. distinguish **processing** from **complete**;
9. explain that separately retained security/billing/support evidence follows
   the #9 retention contract instead of promising immediate deletion of every
   historical record;
10. explain that encrypted backups expire within the configured maximum
    retention window rather than acting as an undelete feature.

No endpoint may return “deleted” merely because the `users` SQL row is gone.

## 4. Workspace classification

### 4.1 Private personal workspace

A workspace may be implicitly destroyed with the account only when all of these
are true:

- `kind == personal`;
- the deleting user is an owner;
- the user is the sole member;
- the user is the sole owner;
- no other user has external manager access.

This is the only implicit workspace-destruction case in the #10 contract.

If this workspace has paid billing owned by the deleting user, cancellation or
termination of that personal billing relationship is part of the deletion
workflow before the user row is destroyed.

### 4.2 Shared or externally managed workspace

Every other workspace is preserved.

Examples include:

- business workspaces;
- personal workspaces with another member;
- personal workspaces with another manager;
- workspaces where the deleting user is only an editor/viewer;
- workspaces the user merely manages on behalf of somebody else.

Deleting one account must not cascade through shared financial data.

### 4.3 Sole-owner blocker

If the deleting user is the only owner of a workspace that will be preserved,
destructive account deletion is blocked until the user deliberately chooses one
of the later supported outcomes:

- transfer ownership to another eligible member; or
- explicitly choose workspace deletion through the dedicated workspace
  lifecycle once roadmap #11/#30 implements it.

There is no silent “pick another member” fallback.

### 4.4 Billing-owner blocker

If the deleting user is `billing_owner_user_id` for a workspace that will be
preserved, deletion is blocked until billing ownership is deliberately
transferred/resolved.

Creator, owner, manager and billing owner are different concepts and must not
be inferred from each other.

### 4.5 Creator and manager references

For a preserved workspace:

- membership is removed only after required owner/billing actions are resolved;
- `managed_by_user_id` must be deliberately detached or transferred;
- `created_by_user_id` is historical attribution and may become null/anonymised
  rather than keeping the deleted personal account alive;
- the workspace ledger, attachments and other shared records stay with the
  workspace.

## 5. Account-level blockers

A deletion request may be recorded while blocked, but destructive execution
must not start while any required blocker remains.

Current contract blockers are:

- the account is the last active superuser;
- the account is sole owner of a workspace that must be preserved;
- the account is billing owner of a workspace that must be preserved;
- a future legal-hold mechanism has a concrete, verified, scoped hold for the
  relevant records.

The legal-hold blocker is not permission to invent or apply a blanket hold.
The current repository has no production legal-hold registry; a future hold
must be explicit, narrow, auditable and independently implemented.

## 6. Required deletion execution order

The canonical order is:

1. **Invalidate authentication sessions/access**
   - rotate/invalidate the user's active authentication epoch/tokens;
   - prevent normal product use once destructive execution begins.

2. **Revoke personal provider access**
   - revoke bank/provider consent or tokens first;
   - erase local provider credentials after successful revocation;
   - failures remain retryable and visible.

3. **Cancel/end personal subscription**
   - stop future personal billing through the verified payment-provider
     lifecycle;
   - do not destroy payment evidence whose #9 window still applies.

4. **Resolve verified holds**
   - apply only documented record-specific holds.

5. **Delete primary database data**
   - delete user-only records;
   - delete truly private personal workspaces selected by the preflight;
   - remove the user's membership/references from preserved workspaces;
   - preserve shared workspace rows.

6. **Delete object/file/vector copies**
   - transaction attachments;
   - invoice/logo objects where owned by the deleted private workspace;
   - agent knowledge raw files;
   - chunks/embeddings/vector material;
   - any other user/private-workspace object key.

7. **Delete or anonymise processor copies**
   - processor lifecycle follows the #9/#12 contract;
   - failures are retried and do not silently become “complete”.

8. **Write the minimal deletion tombstone**
   - enough to prevent a later restore from resurrecting deleted data;
   - no email, password, bank credential, raw financial records or provider
     secret in the tombstone.

9. **Wait for bounded backup expiry**
   - normal encrypted backup copies expire within the #9 maximum window;
   - a restore must re-apply deletion tombstones before restored data can
     re-enter service.

## 7. Deletion states

The behavior contract uses these lifecycle states:

`requested -> blocked | ready -> executing -> external_retry -> primary_data_deleted -> backup_expiry_pending -> complete`

Important semantics:

- `blocked`: user action is required; destructive deletion has not started.
- `external_retry`: one or more provider/object/processor operations failed or
  are uncertain; never report complete.
- `primary_data_deleted`: live primary application data is gone, but the
  lifecycle still has backup/provider-tail obligations.
- `backup_expiry_pending`: the account is no longer usable and primary data is
  deleted; bounded encrypted backup copies are aging out.
- `complete`: every required primary/provider action is verified and the
  contract's backup-expiry condition is satisfied.

The eventual implementation may persist more detailed sub-states, but it must
not weaken these meanings.

## 8. Category-by-category outcome

| Category | Account deletion outcome |
|---|---|
| Authentication credentials/passkeys | hard-delete with account after access invalidation |
| Redis auth/OAuth/rate-limit challenges | expire/delete by existing TTL; never backed up |
| Private personal workspace finance data | hard-delete with the private workspace |
| Shared workspace finance data | preserve; remove only the deleting user's membership/references |
| Transaction/invoice/knowledge objects | delete bytes and metadata when owned by deleted private scope |
| Bank credentials/consent | revoke upstream first, then erase local credentials |
| Bank-synced private finance rows | delete with private workspace |
| AI conversations/messages | delete user/private-workspace content unless a preserved shared lifecycle explicitly owns it |
| AI knowledge/chunks/embeddings | delete raw bytes + rows + vectors for deleted private scope |
| AI usage telemetry | retain/anonymise only according to #9 rolling window |
| MCP exact approval arguments | follow #9 short payload window; do not preserve them merely because account was deleted |
| Minimal MCP/security evidence | retain/anonymise only according to #9 evidence window |
| Successful payment/subscription evidence | minimise and retain only for #9 billing/legal/dispute window |
| Support tickets | follow #9 closed-ticket/provider lifecycle; account deletion does not falsify immediate provider purge |
| Security/request/access logs | follow #9 rolling window with actor minimisation where possible |
| Generated export archives | FinCo-Pilot has no server-retained copy |
| Production backups | expire within #9 maximum; restore must replay deletion tombstone |

## 9. Idempotency and failure rules for roadmap #29

The future implementation must be idempotent:

- repeating a deletion step must not recreate data;
- successful provider revocations must not be blindly retried as new grants;
- uncertain external outcomes must be reconciled before retry;
- every step records bounded non-secret status;
- a failed blob/provider cleanup remains pending and visible;
- no worker may mark `complete` from a partial SQL cascade;
- the request must survive worker restart without losing the remaining work.

## 10. Security and privacy boundaries

The deletion system must never:

- log passwords, OTPs, API keys, bank/provider tokens, full card data or raw
  provider credentials;
- use support tickets as a deletion job queue;
- let a viewer/editor delete a workspace they do not own;
- let account deletion bypass workspace ownership checks;
- silently transfer ownership or billing to an arbitrary member;
- keep a hidden “undelete” copy outside the documented backup window;
- restore deleted account data from backup without replaying deletion
  tombstones;
- report processor deletion as successful without provider evidence when the
  integration supports such evidence.

## 11. Relationship to later roadmap items

This #10 contract intentionally leaves these gates open:

- **#11** shared-workspace deletion policy;
- **#12** third-party processor inventory and processor-specific delete/retain
  behavior;
- **#25** real backup + restore acceptance;
- **#27/#28** published Privacy Policy / Terms;
- **#29** personal deletion implementation + E2E tests;
- **#30** shared-workspace deletion safeguards.

Roadmap #29 should consume this module/contract rather than inventing a second
set of deletion semantics.

## 12. Acceptance for roadmap #10

Roadmap #10 is behavior-contract complete only when:

- the machine-readable preflight contract is merged;
- tests prove private-personal vs shared-workspace classification;
- tests prove sole-owner and shared billing-owner blockers;
- tests prove manager/creator references do not imply workspace destruction;
- tests prove authentication/provider revocation steps precede primary DB
  deletion in the canonical execution order;
- the hardening report records that runtime deletion remains unimplemented;
- CI is green on the final branch head and post-merge main.

Production account-deletion acceptance is **not** claimed by this roadmap item.
