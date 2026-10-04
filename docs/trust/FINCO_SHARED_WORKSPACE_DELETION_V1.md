# FinCo-Pilot Shared-Workspace Deletion Policy V1

**Roadmap item:** #11 — Shared-workspace deletion policy  
**Contract ID:** `FINCO_SHARED_WORKSPACE_DELETION_V1`  
**Version:** 2026-10-02  
**Status:** policy/engineering contract only; destructive implementation and E2E acceptance remain roadmap #30.

## 1. Purpose

This contract defines when a FinCo-Pilot workspace may be irreversibly deleted,
who may authorize it, what must be resolved first, what data is in scope, and
what “complete” means.

It builds directly on:

- `FINCO_DATA_RETENTION_V1` (#9);
- `FINCO_PERSONAL_ACCOUNT_DELETION_V1` (#10).

Roadmap #11 is not a hard-delete implementation. The current application only
archives workspaces. Roadmap #30 owns the durable destructive workflow,
provider/object cleanup, SQL deletion, retries and production acceptance.

## 2. Current repository reality

The current workspace lifecycle is deliberately non-destructive:

- `POST /api/workspaces/{workspace_id}/archive` flips `is_archived=true`;
- it requires effective owner access;
- it refuses to archive the requester's last accessible workspace;
- there is no production workspace hard-delete endpoint;
- workspace rows have multiple user relationships with different meanings:
  `created_by_user_id`, `managed_by_user_id`, `billing_owner_user_id`,
  and `workspace_members`.

The database contains many workspace-scoped rows with
`ON DELETE CASCADE`, but a relational cascade alone is not sufficient for
hard deletion because object/file bytes, provider consent/tokens, processor
copies, vector/knowledge files and backup copies have independent lifecycles.

Therefore the existing archive endpoint must remain archive-only. It must never
be silently reinterpreted as destructive deletion.

## 3. V1 authorization rule

Irreversible workspace deletion requires an **actual owner membership**.

A user whose only access comes from `managed_by_user_id` receives a virtual
`manager` role for normal operation, but that role is not sufficient authority
to destroy shared financial data.

V1 intentionally does not invent multi-party deletion approval. Instead, before
hard deletion can become READY:

- the requester must be an actual `owner` member;
- the requester must be the sole remaining member;
- the requester must be the sole remaining owner;
- any other external manager must already be detached;
- the workspace billing owner must be resolved and must be the requester.

This is an operator safety decision, not a statutory claim.

If a future product adds multi-owner approvals, it must be a new explicit
contract version rather than silently weakening this rule.

## 4. Archive-before-delete boundary

A workspace must be archived before hard deletion.

Archive and delete remain distinct:

- **archive** hides/stops normal active use without destroying records;
- **hard delete** irreversibly destroys the workspace's primary records and
  owned object/file/vector copies subject to documented retention exceptions.

This staged boundary provides a deliberate decommissioning step and prevents a
single ordinary workspace-settings action from becoming irreversible data loss.

Roadmap #30 may add a dedicated deletion center for archived workspaces; it must
not overload the existing archive endpoint.

## 5. Preconditions and blockers

A hard-delete request may be recorded while blocked, but destructive execution
must not start until all blockers are resolved.

### Requester is not an actual owner member

Editors, viewers, users with no membership, and manager-only users cannot
authorize hard deletion.

### Workspace is not archived

The user must archive/decommission first.

### Other owners remain

A workspace with another owner cannot be deleted. Ownership must be deliberately
resolved first.

### Other members remain

Editors/viewers/other members must be removed or otherwise resolved before
irreversible deletion. This makes collaborator impact explicit instead of
silently deleting shared records underneath them.

### Another external manager remains

If `managed_by_user_id` references another user, that management edge must be
detached/transferred before deletion.

If the requester is both the actual owner and the same external manager, the
execution workflow may detach that same-user management edge as part of the
deletion process.

### Billing owner unresolved or different

`billing_owner_user_id` is not inferred from creator/manager/owner roles.

- null/unresolved billing owner fails closed;
- a billing owner different from the deleting owner fails closed.

The billing relationship must be explicitly repaired/transferred first.

### Requester's last accessible workspace

A standalone workspace-delete flow must not leave the user with no accessible
workspace. If this is the requester's last accessible workspace, deletion is
blocked.

Deleting the account itself is a separate #10/#29 flow and may intentionally
remove the final private personal workspace.

### Verified legal hold

A concrete, scoped, auditable hold may block only the affected records.

The current repository has no production legal-hold registry. This policy does
not invent one and does not authorize blanket indefinite retention.

## 6. Billing behavior

Deleting a workspace does **not** cancel the user's global FinCo-Pilot
subscription.

Current subscriptions are user-level. Workspace deletion may reduce usage and
workspace counts, but it must not silently:

- cancel Pro/Max;
- terminate the user's unrelated billing relationship;
- refund a subscription;
- change plan;
- destroy separately retained payment evidence.

Payment/subscription evidence continues to follow the #9 retention contract and
the later payment-lifecycle roadmap items.

## 7. Canonical deletion execution order

Roadmap #30 must implement an idempotent workflow with this order:

1. **Freeze workspace writes**
   - once destructive execution starts, normal writes stop;
   - no new transactions, files, agents or provider sync writes may race the
     deletion manifest.

2. **Capture a deletion manifest**
   - enumerate workspace-scoped SQL identities and every object/file/vector key
     needed for cleanup;
   - persist only bounded non-secret retry metadata;
   - never copy provider secrets into the manifest.

3. **Cancel pending invitations / membership-side pending actions**
   - no new collaborator should join a workspace being destroyed.

4. **Revoke workspace provider access**
   - revoke bank/provider consent/tokens before local credential destruction;
   - uncertain external results remain retryable.

5. **Detach same-requester external-manager edge when present**
   - only after preflight proved no other manager remains.

6. **Delete workspace object/file/vector bytes**
   - transaction attachments;
   - invoice attachments;
   - invoice/logo branding objects;
   - AI knowledge raw files;
   - extracted chunks/embeddings/vector material;
   - any other object key owned by the workspace.

   Object deletion occurs while the manifest/storage keys still exist. A
   durable reconciliation path must handle partial provider/storage failures.

7. **Delete primary workspace database rows**
   - delete the workspace and all scoped relational data only after provider and
     object cleanup has either succeeded or durable retry state is safely
     persisted.

8. **Delete or anonymise processor copies**
   - use the processor-specific #12 contract;
   - failures remain visible/retriable.

9. **Write a minimal deletion tombstone**
   - sufficient to stop a later backup restore from resurrecting the deleted
     workspace;
   - no raw financial data, credentials or unnecessary personal identifiers.

10. **Wait for bounded backup expiry**
    - normal encrypted backup copies expire within the #9 maximum window;
    - a restore must re-apply deletion tombstones before serving restored data.

## 8. Data categories in scope

Workspace deletion targets the workspace-owned primary copies, including as
applicable:

- workspace row and memberships;
- workspace tax IDs and fiscal configuration;
- accounts and bank-synced records;
- transactions, splits, categories, budgets, recurring data and rules;
- assets and asset values;
- goals and planning data;
- loans and loan-plan records;
- payees/mappings;
- reconciliation state and overrides;
- groups/collections scoped to the workspace;
- invoices, lines, allocations, settings and workspace fiscal documents;
- transaction attachments;
- invoice attachments;
- invoice logo/branding objects;
- import metadata;
- workspace bank connections after upstream revoke;
- workspace AI agents;
- conversations/messages owned by those workspace agents;
- AI knowledge raw files/chunks/embeddings;
- workspace-scoped MCP approval/token metadata where its parent lifecycle ends;
- other future persistent workspace categories only after they are added to the
  #9 retention registry.

Unknown workspace-owned persistent categories fail closed; they must not inherit
an unreviewed delete default.

## 9. Records not blindly destroyed by workspace deletion

Some records have a separate retention purpose/window under #9 and therefore
must be minimised/detached rather than blindly cascaded:

- security/request/access logs;
- successful payment/subscription evidence;
- pricing/security audit events;
- minimal MCP approval/security evidence;
- support tickets;
- legally held records;
- deletion workflow/tombstone evidence;
- normal encrypted backup copies until bounded expiry.

This is not permission to retain the deleted workspace indefinitely. It means
the narrower evidence record follows its own documented lifecycle.

## 10. Member and actor references

For shared data:

- uploader/creator/actor IDs are not ownership;
- removing a user account must not destroy a workspace merely because that user
  created a row;
- deleting the entire workspace may remove workspace-owned rows regardless of
  which member authored them once all deletion preconditions are met;
- separately retained evidence should detach/anonymise actor identifiers when
  its narrower purpose no longer requires them.

## 11. User-visible behavior for roadmap #30

A future hard-delete UI/API must:

1. be reachable only through a dedicated destructive flow;
2. require fresh authentication or another strong confirmation;
3. clearly state that archive is reversible/non-destructive while hard delete
   is irreversible;
4. show blockers before destructive execution;
5. identify member/owner/manager/billing-owner conflicts without leaking
   unrelated account details;
6. require exact explicit confirmation of the target workspace;
7. expose a stable opaque deletion reference;
8. distinguish `processing`, `external retry`, `primary deleted`,
   `backup expiry pending` and `complete`;
9. never claim complete because a SQL `DELETE` succeeded;
10. never expose storage keys, provider tokens, OAuth secrets or internal
    deletion credentials.

## 12. Lifecycle states

The behavior contract uses:

`requested -> blocked | ready -> executing -> external_retry -> primary_workspace_deleted -> backup_expiry_pending -> complete`

A request may move to `cancelled` only from `requested`, `blocked` or
`ready`.

After `executing` begins, destructive external/data operations may already
have started, so the product must not offer a false safe cancellation.

## 13. Idempotency and failure semantics for #30

The implementation must be restart-safe and idempotent:

- retrying a completed blob deletion must not recreate the file;
- provider revocation must be reconciled before retrying uncertain outcomes;
- a DB cascade must not erase the only copy of storage/provider cleanup keys;
- failed object/processor cleanup stays pending;
- workers can resume after restart from bounded durable state;
- completing one target cannot implicitly mark all other targets complete;
- the final state requires every mandatory target plus the backup-expiry
  condition.

## 14. Relationship to other roadmap items

- **#9** defines retention windows/categories.
- **#10** defines personal-account deletion behavior.
- **#12** inventories third-party processors and processor-specific lifecycle.
- **#25** proves real backup + restore behavior.
- **#27/#28** publish Privacy Policy / Terms.
- **#29** implements personal-account deletion.
- **#30** implements shared-workspace deletion safeguards and destructive E2E.

## 15. Acceptance for roadmap #11

Roadmap #11 is policy/engineering-contract complete only when:

- machine-readable preflight policy is merged;
- tests prove manager-only access cannot hard-delete;
- tests prove archive-before-delete;
- tests prove other owners/members block;
- tests prove external-manager and billing-owner conflicts block;
- tests prove last-accessible-workspace and verified-hold blockers;
- tests prove workspace deletion does not cancel global user subscription;
- tests prove provider/object cleanup and manifest capture precede primary SQL
  deletion;
- tests prove lifecycle cannot jump directly from primary deletion to complete;
- hardening documentation records runtime implementation remains #30;
- final PR-head CI and post-merge main CI are green.

Production workspace hard-delete acceptance is **not** claimed by #11.

## Original #30 implementation follow-up

The original policy/history above is preserved. Original #30 now implements the separate durable deletion workflow and safety gates; see [Shared deletion implementation](FINCO_SHARED_WORKSPACE_DELETION_IMPLEMENTATION_V1.md). Archive remains non-destructive. Real provider/processor/version/legacy storage and backup-expiry evidence are operational gates; code/test completion does not certify them.
