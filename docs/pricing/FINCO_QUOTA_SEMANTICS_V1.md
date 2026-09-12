# FinCo-Pilot Pricing V1 — Exact Quota Semantics

Status: **locked before hard-enforcement implementation**  
Branch: `feat/pricing-entitlements-v1`

This document defines exactly what every numerical plan limit means so backend enforcement, frontend usage meters and tests all count the same thing.

---

## 1. Scope / billing owner

Workspace-scoped resource quotas are charged to the workspace's explicit `billing_owner_user_id`, not necessarily the acting member.

Owner-level quotas aggregate across every non-archived workspace whose `billing_owner_user_id` is that user. Invited members do not consume their personal plan while acting inside someone else's workspace; usage belongs to that workspace's billing owner.

---

## 2. Reset window for monthly action quotas

V1 uses **UTC calendar months** for all `..._monthly` action quotas.

Window:

```text
[first day of current UTC month 00:00:00, first day of next UTC month 00:00:00)
```

Why:
- deterministic for Free, monthly Pro, annual Pro and Max alike;
- independent of payment-provider billing anchors;
- easy to explain and test;
- avoids different allowance behavior between monthly and annual subscribers.

The UI may display reset time in the user's local timezone, but the server window is UTC.

Changing subscription plan does not reset a monthly usage counter. Upgrade increases the applicable limit immediately; it does not erase already-consumed units.

---

## 3. Current-state resource quotas

These quotas describe resources that currently exist/are active. Removing/closing/archiving a resource can free capacity.

### Accounts

Count all accounts owned by the billing owner across owned workspaces where:

```text
is_closed = false
```

- Creating an account increases usage.
- Reopening a closed account increases usage and must enforce before reopen.
- Closing/deleting frees capacity.
- Closed accounts remain readable.

### Active budgets

A budget is not counted by raw `budgets` table rows because recurring budget edits intentionally create historical effective-from rows.

Count the **effective distinct budget categories for the target month**, using the same recurring-resolution semantics as `budget_service._build_budget_map`:

1. the newest recurring budget for each category effective on/before that month;
2. a month-specific override replaces that recurring value for the same category;
3. each resulting category counts once.

Quota enforcement occurs against the target month affected by create/update.

Consequences:
- adding a new category budget that increases the effective category count needs a slot;
- overriding an already-budgeted category does not consume another slot;
- historical rows never inflate quota usage.

### Active goals

Count goals where:

```text
status = "active"
```

- Creating an active goal needs a slot.
- Updating paused/completed/archived -> active needs a slot.
- Pausing/completing/archiving frees active capacity but preserves data.

### Active recurring items

Count recurring rows where:

```text
is_active = true
```

- create active -> enforce;
- inactive -> active -> enforce;
- deactivation frees capacity;
- generated financial transactions are not themselves recurring-definition quota units.

### Assets / holdings

Count asset rows where:

```text
is_archived = false
```

A non-null `sell_date` does **not** silently remove the holding from quota while it remains unarchived; the user can archive the completed holding to free capacity. This keeps usage semantics explicit and avoids invisible count changes.

- direct create -> enforce;
- a buy/import that creates a new holding -> enforce;
- adding a transaction to an existing holding does not consume another holding slot;
- archive/delete frees capacity;
- unarchive needs a slot.

### Rules

Rules are a paid capability plus a quota. For Pro/Max, count rows where:

```text
is_active = true
```

- creating an active rule needs a slot;
- activating an inactive rule needs a slot;
- deactivation frees active capacity;
- Free cannot create/activate/semantically mutate rules at all;
- historical inactive/existing rules may remain visible for portability/cleanup.

### Active split groups

Count groups where:

```text
is_archived = false
```

- create/unarchive -> enforce;
- archive/delete frees capacity.

### Members per split group

Count all persisted `group_members` rows for that group, including the self/owner member.

The published limit therefore means **total people represented in the group**, not “extra invitees”. This is deterministic and maps directly to stored split participants.

Deleting a removable member frees a slot. Existing historical split integrity rules still take precedence over deletion where the domain prevents it.

### Owned workspaces

Count non-archived workspaces where:

```text
billing_owner_user_id = user.id
```

Free/Pro:
- total owned workspaces limit = 1;
- business workspaces limit = 0.

Max:
- total owned workspaces limit = 3;
- business workspaces may be created within that same total.

Archiving a workspace frees an owned-workspace slot. Merely being invited to another workspace does not consume the invitee's quota.

---

## 4. Event/action quotas

These are **append-only usage events/counters** for the monthly window. Deleting resulting data does not refund the unit, otherwise users could delete/recreate to bypass the plan.

### Statement / CSV imports

One unit is consumed for each successfully-applied import operation:

- transaction statement import;
- asset-order import.

Preview does not consume quota.

Failed validation / rejected pre-write import does not consume quota.

Undoing/deleting imported data later does not refund the unit.

Retries must use an idempotency key so the same logical applied import cannot consume twice due to client/network retry.

### Invoices created

One unit is consumed when the Max-only invoice create operation successfully creates a **local FinCo invoice**.

- deleting/voiding the invoice does not refund the monthly unit;
- draft creation counts because a persisted invoice resource was created;
- imported/synced external invoices are not automatically charged to this V1 user-created-invoice allowance unless a future import product rule explicitly says so.

### AI actions

V1 product allowance is one metered **assistant run**, not one internal tool call/token chunk.

The exact charging point will be finalized when the actual model/provider billing integration is wired. Until then:
- never trust browser-reported action count;
- do not count every streamed token or internal tool invocation as a user-visible action;
- failed-before-start requests do not count;
- provider-side cost telemetry may later refine this policy without changing the plan UI wording.

No implementation may label AI “unlimited”.

---

## 5. Storage quota

Storage is current-state bytes, not a monthly action counter.

Count the sum of `size` from persisted user-uploaded attachments across billing-owner workspaces, including:
- transaction attachments;
- invoice attachments.

Before accepting a new upload:

```text
current_server_owned_bytes + incoming_actual_bytes <= plan.storage_bytes
```

- enforce after reading/verifying actual payload length and before durable storage/database commit;
- client `Content-Length` is not trusted as the source of truth;
- deleting an attachment frees storage capacity;
- generated ephemeral render/cache files that are not stored as user attachments do not consume this user quota unless explicitly persisted as such.

---

## 6. Binary capabilities with no numerical quota

These do not use current-row counters:

- `advanced_reports`: Pro/Max.
- `smart_reconciliation`: Pro/Max.
- `business_workspaces`: Max.
- `invoices`: Max, with monthly create quota in addition.
- `agents_automation`: Max plus deployment capability flag.

Both capability and workspace-role/module rules must pass where applicable.

---

## 7. Quota concurrency strategy

### Guaranteed billing row

Every user must have exactly one server-owned subscription row, including Free users. The row is the serialization anchor for current-state quota mutations.

Existing users are backfilled as Free by migration; registration creates the Free billing row server-side.

### Current-state resources

Before a create/reactivate/reopen/unarchive that may increase usage:

1. resolve the workspace billing owner;
2. lock that owner's subscription row with `SELECT ... FOR UPDATE` in the same DB transaction;
3. recompute authoritative usage from persisted rows;
4. reject if `usage + increment > limit`;
5. perform domain mutation;
6. commit mutation and release lock together.

This closes the classic “two requests see one remaining slot” race in production PostgreSQL.

### Monthly action counters

Use a server-owned usage-counter/event structure keyed by billing owner + metric + UTC month. Increment atomically and idempotently only at the successful apply boundary.

A normal browser endpoint can never set/decrement/reset this counter directly.

### Service commits

Where an existing domain service calls `commit()` internally, the entitlement lock/check and the domain write must share the same session/transaction so the service commit releases the lock only when the protected mutation is committed. Do not perform quota checking in a separate request/session.

---

## 8. Upgrade / downgrade behavior

### Upgrade

- effective limit increases immediately after verified server billing state changes;
- existing usage is preserved;
- monthly counters do not reset;
- UI refetches/invalidate entitlements.

### Downgrade / expiry

- never delete resources;
- existing data remains readable/exportable;
- actions that reduce usage remain available where domain-safe;
- actions that increase a metered resource are denied while usage is at/above the new limit;
- paid automation execution stops;
- Max business/invoice history remains readable even when new Max-only mutations are locked.

---

## 9. Usage response semantics

`GET /api/billing/entitlements` eventually reports authoritative usage using these exact definitions.

Important UI rule: a missing usage metric means “not loaded/not applicable”, **not zero**. Frontend must not invent usage.

For a resource quota display, use:

```text
usage / limit
```

Examples:
- `2 / 3 accounts`
- `2 / 2 imports this month`

For binary features show only lock/unlock state and required plan badge.

---

## 10. Required boundary tests

For each current-state quota:
- below limit -> grow succeeds;
- exactly last available slot -> succeeds;
- one above -> stable `PLAN_LIMIT_REACHED` response;
- close/archive/deactivate/delete reduces capacity where defined;
- reactivate/reopen/unarchive enforces again;
- two concurrent last-slot requests cannot both succeed in PostgreSQL integration validation.

For monthly counters:
- preview/failure does not count;
- successful apply counts once;
- retry with same idempotency key does not double-count;
- delete/undo does not refund;
- UTC month rollover exposes fresh allowance;
- upgrade raises limit without resetting used count.
