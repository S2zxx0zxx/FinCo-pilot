# FinCo-Pilot Pricing V1 — Implementation & Enforcement Map

Status: **design/logic frozen before implementation**  
Branch: `feat/pricing-entitlements-v1`  
Companion spec: `docs/pricing/FINCO_PRICING_ENTITLEMENTS_V1.md`

This document removes implementation-time guesswork. It maps the approved Free / Pro / Max product model to the existing FinCo-Pilot routes, APIs, downgrade behavior, pricing-page structure, lock states, badges, errors and tests.

---

## 1. Canonical launch prices

These values are product constants for V1 and must not be duplicated independently across UI surfaces.

| Plan | Billing interval | Price |
| --- | --- | ---: |
| Free | forever | ₹0 |
| Pro | monthly | ₹99/month |
| Pro | annual | ₹999/year |
| Max | monthly | ₹349/month |
| Max | annual | unavailable in V1 |

Computed Pro annual saving: `₹99 × 12 = ₹1,188`; `₹1,188 - ₹999 = ₹189` (~15.9%).

Rules:
- No fake list price.
- No fake countdown.
- No lifetime plan in V1.
- No forced credit card for Free.
- Max annual is not displayed as a fake disabled price; it is simply not offered in V1.
- Promotional campaigns, if added later, are separate from canonical plan prices.

---

## 2. Entitlement ownership and authority

### Source of truth

The **backend is the only authority** for a user's effective plan and usage. The browser only renders what the backend says.

Never trust any client value such as:
- `plan=pro`
- `plan=max`
- `is_pro=true`
- `is_max=true`
- localStorage/sessionStorage plan keys
- query parameters
- hidden form fields
- DOM state
- request body prices
- request body usage counters

Editing React state, DevTools, JavaScript, localStorage, URLs or network payloads must not grant access.

### Three independent checks

Paid access is intentionally separate from existing FinCo concepts:

1. **Workspace module availability** — whether the workspace kind/deployment has a module.
2. **Workspace role permission** — whether this member can write.
3. **Billing entitlement** — whether the billing owner has the paid capability/quota.

A protected action succeeds only when every applicable check passes.

---

## 3. Effective subscription state

Server model must support at least:

```text
plan: free | pro | max
status: free | active | grace | past_due | canceled | expired
billing_interval: none | monthly | annual
current_period_start
current_period_end
cancel_at_period_end
provider
provider_customer_id
provider_subscription_id
```

V1 before checkout integration may keep provider fields null. Production must never expose a normal user endpoint that directly changes `plan` or `status`.

### Effective access semantics

- `free`: Free catalog.
- `active`: paid catalog for current plan.
- `grace`: paid read/write access may remain temporarily available according to billing policy; UI shows payment warning.
- `past_due`: do not destroy data; billing-recovery state is visible. Exact grace timing is deferred to payment integration.
- `canceled`: plan remains active until paid period end when cancel-at-period-end applies.
- `expired`: downgrade rules apply.

---

## 4. V1 entitlement catalog

| Capability / quota | Free | Pro | Max |
| --- | ---: | ---: | ---: |
| Owned personal workspaces | 1 | 1 | 3 total workspaces |
| Owned business workspaces | 0 | 0 | up to 3 total workspaces |
| Manual transactions | Unlimited fair use | Unlimited fair use | Unlimited fair use |
| Accounts | 3 | 25 | 100 |
| Active budgets | 2 | 25 | 100 |
| Active goals | 2 | 25 | 100 |
| Active recurring items | 3 | 50 | 250 |
| Assets / holdings | 3 | 50 | 500 |
| Statement/CSV imports | 2/month | 30/month | 200/month |
| Rules / automation rules | Locked | 25 | 200 |
| Active split groups | 1 | 10 | 50 |
| Members per split group | 5 | 15 | 50 |
| Invoices created | Locked | Locked | 500/month |
| Business workspace creation | Locked | Locked | Included |
| AI actions | 5/month | 60/month | 300/month |
| Uploaded attachment storage | 100 MB | 1 GB | 10 GB |
| Advanced reports | Locked | Included | Included |
| Smart reconciliation | Locked | Included | Included |
| Agents / MCP / advanced automation | Locked | Locked | Included when deployment capability also enables it |
| Support | Standard | Priority | Highest priority |

Always available: PWA install, login/security, privacy mode, dark/light theme, viewing existing personal financial data, export/data portability, account deletion, and reading data created while formerly subscribed at a higher tier.

---

## 5. Backend enforcement primitives

Create one reusable billing package instead of scattered `if plan == ...` checks.

Suggested structure:

```text
backend/app/billing/
  catalog.py
  enums.py
  errors.py
  service.py
  usage.py
  dependencies.py
  schemas.py
backend/app/models/subscription.py
backend/app/api/billing.py
```

Required primitives:

### `EntitlementService`
Returns effective plan, status, capabilities, hard limits, current usage and reset timestamps.

### `require_capability(capability)`
For binary paid features such as Rules, Advanced Reports, Reconciliation, Business Workspace, Invoices and Agents.

### `enforce_limit(metric, increment=1)`
For Accounts, Budgets, Goals, Recurring, Assets, Imports, Groups, Group Members, Invoices, AI actions and storage.

### `EntitlementError`
Frontend-readable, stable error schema. Never rely on parsing human strings.

Recommended responses:

```json
{
  "detail": {
    "code": "ENTITLEMENT_REQUIRED",
    "capability": "rules",
    "current_plan": "free",
    "required_plan": "pro"
  }
}
```

HTTP `403` for a missing capability.

```json
{
  "detail": {
    "code": "PLAN_LIMIT_REACHED",
    "metric": "accounts",
    "usage": 3,
    "limit": 3,
    "current_plan": "free",
    "required_plan": "pro"
  }
}
```

HTTP `409` for a hard quota boundary. This distinguishes product quota from `429` rate limiting.

### Concurrency safety

Hard quotas cannot use a naive `COUNT` followed by an unprotected insert. Two concurrent requests could both see one slot left.

Implementation must use a transaction-safe strategy (row lock / serialized billing-usage row / equivalent database-safe mechanism) for metered creates. Tests must prove two concurrent requests cannot exceed the limit.

---

## 6. Exact existing API enforcement map

This is the minimum route map found in the current repository. Enforcement belongs server-side even when the frontend also locks the control.

### Accounts — `backend/app/api/accounts.py`

- `POST /api/accounts` → enforce `accounts` quota.
- PATCH/close/reopen/delete existing account → allowed after downgrade because they do not increase count.
- Reads stay available.

### Budgets — `backend/app/api/budgets.py`

- `POST /api/budgets` → enforce `active_budgets` quota.
- If an update changes an inactive/archived equivalent into an active budget, enforce before transition.
- Existing budget edits/deletes remain available after downgrade if they do not increase metered count.
- Reads/comparison remain available.

### Goals — `backend/app/api/goals.py`

- `POST /api/goals` → enforce `active_goals` quota.
- Reactivating a paused/completed/archived goal must enforce if it increases active count.
- Reads remain available.

### Recurring — `backend/app/api/recurring_transactions.py`

- `POST /api/recurring-transactions` → enforce `active_recurring` quota.
- Reactivating an inactive recurring item must enforce.
- `POST /api/recurring-transactions/generate` must never become a bypass that creates additional recurring definitions; generated transactions themselves remain ordinary financial history.
- Existing recurring items remain readable/manageable on downgrade, subject to non-increasing edits.

### Assets — `backend/app/api/assets.py`

- `POST /api/assets` → enforce `assets` quota.
- `POST /api/assets/buy` may create a holding when ticker/wallet has no existing holding, so it must enforce before a new holding is created.
- `POST /api/assets/import` → enforce monthly import quota and resulting holding quota transaction-safely.
- `POST /api/assets/import/preview` remains preview-only; it must not consume quota.
- Existing asset transaction/value edits remain usable after downgrade when no new holding is created.
- Market search/quote are not themselves paid-plan switches in V1; provider rate/cost policy may change later.

### Statement imports — `backend/app/api/import_transactions.py`

- `POST /api/transactions/import/preview` remains free/read-only and does not consume import quota.
- `POST /api/transactions/import` → atomically consume one monthly import unit only when the import is actually accepted/applied.
- Failed validation must not consume the monthly quota.
- Retry idempotency must prevent one logical import from being double-counted if payment/network/client retry behavior is introduced later.

### Rules — `backend/app/api/rules.py`

Free: entire mutating Rule feature is locked.

- `POST /api/rules` → require `rules` + enforce rule quota.
- `POST /api/rules/import` → require `rules`; enforce resulting quota before writes.
- `POST /api/rules/packs/{pack}/install` → require `rules`; enforce resulting quota.
- PATCH/DELETE existing rules after downgrade: deleting is allowed; edits that keep a previously-created rule should be read-only/disabled unless the product explicitly permits cleanup. V1 safest behavior: allow delete, block create/reactivate/semantic mutation while Free.
- `GET /api/rules`, export and preview of existing historical rules can remain readable after downgrade to avoid hiding user data, while execution of paid automations must be disabled.

### Split groups — `backend/app/api/groups.py`

- `POST /api/groups` → enforce active group quota.
- `POST /api/groups/{id}/members` → enforce members-per-group quota.
- Reactivating/unarchiving a group must enforce active group quota.
- Existing group balances/transactions/settlements stay readable.
- Delete/archive remains available for cleanup after downgrade.

### Workspaces — `backend/app/api/workspaces.py`

- `POST /api/workspaces` is a critical bypass surface.
- Free/Pro: must reject any additional workspace beyond their owned-personal limit and reject `kind=business`.
- Max: enforce total owned workspace quota; only Max may create a business workspace in V1.
- User-supplied `kind=business` must never be accepted merely because the UI hid the option.
- Member invitation does not transfer/mint the invited member's personal subscription.
- A member can use capabilities of a Max-owned business workspace only within that workspace and only with their role permission.

### Invoices — `backend/app/api/invoices.py`

Current invoice APIs already use workspace module read/write gates. Billing is an additional gate, not a replacement.

- Creating/issuing/voiding/editing invoice data on an active Max business workspace → require Max invoice entitlement.
- `POST /api/invoices` → enforce `invoices_monthly` before creation.
- After Max expires/downgrades, previously-created invoices and archived documents remain readable/exportable.
- Mutating/issuing new business invoice actions become locked/read-only after downgrade.
- Never delete business records because billing ended.

### Attachments — `backend/app/api/attachments.py` and invoice attachment paths

- Before accepting bytes, compute current user-owned storage usage + incoming size and enforce storage quota server-side.
- Reject oversized uploads before persisting file or DB metadata.
- Existing attachment download/rename/delete remains available after downgrade; delete helps the user get under quota.
- Storage usage is computed from server-owned metadata, never client headers alone.

### Advanced reports — `backend/app/api/reports.py`

V1 split:
- Free keeps basic dashboard summaries and normal transaction/account views.
- The dedicated `/reports` advanced analysis surface is Pro/Max.
- `GET /api/reports/net-worth`, `/income-expenses`, `/cash-flow` therefore require `advanced_reports` in V1.
- If later a small Free report preview is desired, create an explicit limited endpoint/parameter policy rather than trusting frontend controls.

### Smart reconciliation

All mutation/accept/link operations that constitute Smart Reconciliation must require `smart_reconciliation` (Pro/Max). Historical reconciliation data may remain readable after downgrade.

### AI / Agents — `backend/app/agents/...`

- `POST /api/agents/{agent_id}/chat` currently has workspace write permission because tools may write financial data. Billing must additionally require the appropriate AI/agent capability.
- Max-only Agents/MCP routes require `agents_automation` **and** the existing deployment feature flag. A plan cannot turn on a deployment-disabled capability.
- AI-action usage must be counted server-side at the action boundary selected for billing. Client-reported token/action counts are never trusted.
- Free/Pro AI allowance and Max Agent access are separate concepts; a simple assistant action must not accidentally grant full Agent/MCP capability.

---

## 7. Downgrade/read-only rules

The subscription system must never ransom existing financial history.

When usage is above the new plan limit:

- keep all existing data visible;
- allow delete/archive/close actions that reduce usage;
- allow safe edits that do not create/increase a metered resource;
- block create, duplicate, unarchive/reactivate or other actions that increase a metered count;
- business invoices/documents remain readable/exportable after Max ends;
- paid automation stops executing once its entitlement is gone;
- no background job may continue a paid capability simply because it was scheduled while paid.

Example: user has 12 accounts on Pro, then becomes Free. All 12 remain visible. They cannot create account 13 (or any additional account) until usage is below the Free limit or they upgrade. Closing/deleting accounts is allowed.

---

## 8. Pricing page — exact screen anatomy

The user's supplied X screenshots are **reference for hierarchy, density and interaction only**. Do not copy X artwork, text, branding or proprietary decorative assets. FinCo uses its own F mark, monochrome palette and motion language.

### Mobile / installed PWA primary decision screen

Order from top to bottom:

1. **Top bar**
   - back/close control at top-left;
   - centered/subtly offset FinCo F identity;
   - safe-area aware.

2. **FinCo hero motion**
   - original F mark with restrained depth/orbit/particle treatment matching existing route loader;
   - no stock illustration required;
   - CSS/SVG first, no heavy video dependency;
   - reduced-motion fallback.

3. **Headline + one-line value statement**
   - concise; no fake urgency.

4. **Plan segmented tabs**
   - `Free | Pro | Max`;
   - selected tab has crisp underline/raised-state inspired by reference hierarchy;
   - keyboard and screen-reader accessible.

5. **Selected-plan feature panel**
   - graphite/true-black card, large radius, short icon-led rows;
   - first 5–7 decision-driving benefits visible without cognitive overload;
   - additional details available via comparison section;
   - info icon only where explanation materially helps.

6. **Locked feature rows**
   - visible but muted;
   - lock icon on the row;
   - required plan shown using the reusable tiny Dynamic-Island `PRO` / `MAX` badge;
   - locked row itself never runs the protected action.

7. **Billing choice card**
   - Free: simple `₹0 forever` state, no fake interval cells.
   - Pro: two cells like the reference hierarchy — Monthly `₹99` and Annual `₹999/year`; annual shows computed `Save ₹189`.
   - Max: one real monthly option `₹349/month`; no invented Max annual price.
   - selected price option gets subtle white/black outline + depth, not neon.

8. **Primary CTA**
   - wide, high-contrast FinCo button.
   - Free logged-out: `Start free` → registration.
   - Pro/Max logged-out: authenticate first; never set plan locally.
   - Logged-in Free: `Choose Pro` / `Choose Max` routes to future checkout boundary.
   - Current plan: `Current plan`, non-purchase state.
   - No payment provider yet: CTA must go to a clearly defined coming/checkout boundary and must not fake success.

9. **Renewal/legal microcopy region**
   - shown when a paid billing option is selected;
   - exact renewal/cancel language will be finalized with real provider/payment terms, not guessed now.

10. **Below primary fold**
    - full feature comparison;
    - quota/usage explanation;
    - downgrade/data-safety explanation;
    - FAQ;
    - trust copy (`No ads`, privacy/data principle only if accurate to product policy).

### Desktop/tablet

Do not enlarge the mobile sheet blindly.

- centered max-width layout;
- hero + billing interval control;
- three plan cards visible together;
- Pro is the recommended/most-popular visual anchor;
- feature comparison below;
- sticky CTA only when useful, never covering content;
- keyboard focus order follows visual order.

---

## 9. Reusable 3D Dynamic-Island plan badges

One component: `PlanBadge`.

Variants:
- `PRO`
- `MAX`

Shape/style:
- very small capsule / Dynamic-Island silhouette;
- near-black surface in light context / elevated light or graphite treatment as appropriate in dark context;
- inner 1px highlight;
- subtle outer shadow and inset depth;
- tiny F/lock/spark glyph optional when it remains legible;
- no rainbow or gaming gradient;
- transform/opacity only for motion;
- reduced-motion safe.

Behavior:
- decorative label is never the authorization mechanism;
- use beside sidebar entries, buttons, locked rows, settings, upsell sheets and current-plan status;
- `PRO` badge means minimum Pro; `MAX` badge means Max only.

---

## 10. Lock UX contract

Reusable frontend abstraction: `EntitlementGate` + `LockedFeature`.

### Locked navigation item

- item remains discoverable when product strategy wants discoverability;
- lock + plan badge rendered at trailing edge;
- click opens a plan explanation/upgrade sheet instead of navigating to protected content;
- direct URL still meets a route gate and backend gate.

### Locked button/control

- visually disabled but readable;
- lock + plan badge;
- `aria-disabled=true` when using a discoverable button pattern;
- intercept activation and open upsell sheet;
- must never call the protected API.

### Quota reached

Different from binary lock. Show:

```text
3 of 3 accounts used
Upgrade to Pro for up to 25 accounts
```

Existing resources remain usable.

### Deep links

A user pasting a paid route URL must see a proper locked/upgrade state. It must not mount paid content and rely on hidden controls.

---

## 11. Frontend data contract

Add a server endpoint such as:

`GET /api/billing/entitlements`

Response shape should be stable and sufficient to render all locks without embedding business logic in components:

```json
{
  "plan": "free",
  "status": "free",
  "billing_interval": "none",
  "current_period_end": null,
  "capabilities": {
    "advanced_reports": false,
    "rules": false,
    "smart_reconciliation": false,
    "business_workspaces": false,
    "invoices": false,
    "agents_automation": false
  },
  "limits": {
    "accounts": 3,
    "active_budgets": 2,
    "active_goals": 2,
    "active_recurring": 3,
    "assets": 3,
    "imports_monthly": 2,
    "split_groups_active": 1,
    "group_members": 5,
    "ai_actions_monthly": 5,
    "storage_bytes": 104857600
  },
  "usage": {
    "accounts": 2,
    "active_budgets": 1
  },
  "resets_at": {
    "imports_monthly": "...",
    "ai_actions_monthly": "..."
  }
}
```

Frontend may cache this with React Query, but entitlement state must be invalidated immediately after any verified billing-state change.

---

## 12. Navigation wiring in current frontend

Current main navigation is centralized in `frontend/src/lib/nav-items.ts` and route protection in `frontend/src/App.tsx`.

Do not rewrite module visibility logic. Add pricing state as a distinct layer:

- `visibleNavItems(...)` continues answering workspace module visibility.
- a new entitlement decorator determines `unlocked | locked-pro | locked-max | quota-reached`.
- `ModuleRoute` remains module-aware.
- add `EntitlementRoute` only for true paid route boundaries such as advanced Reports/Rules/Agents/Max business surfaces.
- quota-based pages such as Accounts/Budgets/Goals/Assets remain navigable; only their create/increase actions lock when usage reaches the plan limit.

This prevents the common mistake of hiding an entire page just because creation is capped.

---

## 13. Pricing page visual language

Must feel native to current FinCo-Pilot:

- true black / white primary system;
- graphite cards;
- existing FinCo F mark;
- same typography scale and radii family as the app;
- semantic colors only where they encode status;
- premium depth using border, blur, shadow and perspective rather than bright gradients;
- no orange/coral brand accent reintroduction;
- existing route-loader motion language reused where appropriate;
- 44px+ touch targets;
- narrow mobile width tested down to 320px;
- PWA safe area (`env(safe-area-inset-*)`);
- no horizontal overflow;
- reduced-motion support.

No generated image/video is required for V1 because a lightweight original F-mark hero will load faster, remain theme-responsive and integrate better with PWA/offline behavior. If later creative testing shows a media hero materially improves conversion, add it as an optional optimized asset rather than a blocking dependency.

---

## 14. Security/bypass test matrix

These tests are mandatory, not optional polish.

### Client tampering

Prove Free cannot gain access by:
- localStorage edits;
- sessionStorage edits;
- query params;
- modifying DOM disabled state;
- changing React state in DevTools;
- direct navigation to paid URL;
- manually adding `plan`, `is_pro`, `is_max`, price or usage values to request bodies.

### Direct HTTP

For every paid mutation path:
- call API directly as Free → denied;
- call as Pro when Max required → denied;
- call as correct plan → allowed if role/module also allows;
- caller with paid plan but read-only workspace role → still denied for writes.

### Quotas

For every hard metric:
- `limit - 1` create succeeds;
- reaching `limit` succeeds when exactly one slot remains;
- `limit + 1` is rejected;
- two concurrent last-slot requests result in exactly one success;
- failed request does not consume monthly quota;
- delete/archive lowers usage as expected;
- downgrade over-limit retains data but blocks growth.

### Background paths

Check scheduled/background/agent/import paths as well as normal REST UI endpoints. A paid restriction is incomplete if a worker, Agent tool or alternate import API can still perform the same operation.

---

## 15. Build sequence — no guessing during implementation

### Phase A — entitlement foundation
1. Add subscription model/migration.
2. Add enums/catalog/errors.
3. Add entitlement service and usage calculators.
4. Add `GET /api/billing/entitlements`.
5. Add backend tests for effective-plan resolution.

### Phase B — hard enforcement
6. Accounts, budgets, goals, recurring quotas.
7. Assets + imports + storage quotas.
8. Rules, advanced reports, reconciliation capabilities.
9. Groups/member quotas.
10. Workspace/business creation and invoice Max gates.
11. AI/Agents/MCP gates and usage meter.
12. Concurrency/bypass tests.

### Phase C — frontend entitlement layer
13. API types/query/provider.
14. `PlanBadge`.
15. `LockedFeature` / `EntitlementGate`.
16. quota meter / upgrade sheet.
17. nav/action/route wiring.

### Phase D — Pricing UI
18. `/pricing` public/auth-aware route.
19. mobile/PWA reference-inspired decision surface.
20. desktop/tablet layout.
21. comparison + FAQs + downgrade/trust explanation.
22. responsive/accessibility/motion tests.

### Phase E — validation
23. backend test suite.
24. frontend lint/typecheck/build/tests.
25. direct API bypass suite.
26. dark/light visual review.
27. 320px mobile + typical phone + tablet + desktop.
28. installed-PWA safe-area/offline smoke test.

### Phase F — only after the above is green
29. Payment/checkout provider work starts on a **separate branch**.

---

## 16. Decisions explicitly not guessed in this branch

- Max annual price.
- payment gateway/provider selection and its checkout UI;
- GST display/legal invoice treatment;
- exact cancellation/refund/grace-period legal policy;
- bank-sync limits until provider cost is known;
- AI top-up/overage price until real model usage cost is measured;
- promotional 50%-off campaign from the visual reference.

Those require separate product/payment decisions. The Pricing/Entitlements foundation must be correct without them.
