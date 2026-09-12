# FinCo-Pilot Billing Ownership Decision V1

Status: **locked before implementation**

## Why an explicit billing owner is required

The existing workspace model has `created_by_user_id`, `managed_by_user_id`, and role-based `workspace_members`. None is a safe substitute for subscription ownership:

- `created_by_user_id` is audit history and does not change when workspace ownership changes.
- `managed_by_user_id` represents an external manager, not necessarily the subscriber paying for the workspace.
- there may be multiple members with owner-level authority, so deriving a payer from membership is ambiguous.

Therefore paid entitlement must not be inferred from any of those fields.

## V1 decision

Add an explicit nullable-then-backfilled `workspaces.billing_owner_user_id` foreign key to `users.id`.

After migration it is non-null for active application workspaces. This user is the subscription whose plan supplies workspace-level paid capabilities and consumes owner-scoped quotas.

### Creation

Every newly-created workspace gets:

```text
billing_owner_user_id = creator.id
```

The user's automatic Personal workspace follows the same rule.

### Existing workspace migration

Backfill in this order:

1. `created_by_user_id` when present;
2. otherwise `managed_by_user_id` when present;
3. otherwise one deterministic existing `owner` membership;
4. only if historical malformed data has none of those, leave temporarily nullable and surface it for repair rather than assigning a random user.

Do not silently pick an arbitrary member.

### Membership

Inviting a member does **not** change billing ownership and does not grant that member the billing owner's plan outside this workspace.

Example: a Free user invited as an editor to a Max-owned business workspace can use Max workspace features there when their workspace role allows it. They remain Free in their own Personal workspace.

### Workspace ownership/role changes

Changing `workspace_members.role` does not automatically move the subscription. Billing ownership transfer is a distinct future billing action because it can change who is charged and whose quotas are consumed.

V1 does not expose a normal end-user billing-owner transfer endpoint until checkout/subscription transfer rules exist.

### Entitlement resolution

Workspace-scoped request:

```text
Workspace.billing_owner_user_id
    -> Subscription(user_id)
    -> effective Plan
    -> EntitlementCatalog
```

User-scoped actions such as creating a new workspace use the acting user's own subscription.

### Security invariant

No request body may choose `billing_owner_user_id`. It is server-assigned. A user cannot point a new workspace at another user's Max subscription through DevTools/cURL.

### Downgrade

If the billing owner's paid subscription ends, the workspace remains intact. Historical paid data remains readable according to the downgrade rules in the main pricing specification; creation/paid mutations are gated by the owner's new effective entitlement.
