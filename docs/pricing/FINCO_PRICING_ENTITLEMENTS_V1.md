# FinCo-Pilot Pricing & Entitlements V1 — Build Specification

Status: planning / no checkout integration yet
Branch: `feat/pricing-entitlements-v1`

## 1. Locked launch pricing

| Plan | Monthly | Annual | Positioning |
| --- | ---: | ---: | --- |
| Free | ₹0 | ₹0 | Everyday manual finance tracking |
| Pro | ₹99/month | ₹999/year | Personal-finance power users |
| Max | ₹349/month | Not offered in V1 | Freelancers, creators, businesses, automation-heavy users |

Pro annual saves ₹189 versus 12 monthly payments (₹1,188 → ₹999, ~15.9%).

No fake crossed-out list price, no lifetime plan, no forced card trial, no ads, and no client-side self-activation of paid plans.

## 2. Product entitlement matrix

Limits are server-authoritative. UI labels are a reflection of backend entitlements, never the source of truth.

| Capability | Free | Pro | Max |
| --- | ---: | ---: | ---: |
| Personal workspaces owned | 1 | 1 | 3 |
| Business workspaces owned | 0 | 0 | 3 (within 3 total) |
| Manual transactions | Unlimited* | Unlimited* | Unlimited* |
| Accounts | 3 | 25 | 100 |
| Active budgets | 2 | 25 | 100 |
| Active goals | 2 | 25 | 100 |
| Active recurring items | 3 | 50 | 250 |
| Assets / holdings | 3 | 50 | 500 |
| Statement / CSV imports | 2/month | 30/month | 200/month |
| Rules / automations | 0 | 25 | 200 |
| Split-expense groups | 1 active | 10 active | 50 active |
| Members per split group | 5 | 15 | 50 |
| Invoices | 0 | 0 | 500/month |
| Business workspace features | Locked | Locked | Included |
| AI actions | 5/month | 60/month | 300/month |
| User-uploaded attachment storage | 100 MB | 1 GB | 10 GB |
| Advanced reports | Locked | Included | Included |
| Smart reconciliation | Locked | Included | Included |
| Agents / MCP / advanced automation | Locked | Locked | Included when deployment capability is enabled |
| Priority support | Standard | Priority | Highest priority |

`*` Manual transactions remain unlimited for normal human use because locking a user's financial history behind a quota harms trust. Abuse is handled by rate limits and fair-use safeguards rather than a marketing quota.

### Always available regardless of plan

- PWA installation and core app shell.
- Login, security, passkeys/2FA where deployment supports them.
- Viewing and exporting the user's own existing data.
- Reading data created while previously subscribed to a higher tier.
- Dark/light theme and privacy mode.
- Account deletion / data portability paths.

## 3. Downgrade semantics

Never delete or hide financial records merely because a subscription ends.

If a Pro/Max user exceeds a Free quota after downgrade:

- existing records remain readable;
- edits that do not increase the metered resource count remain allowed where safe;
- creation of additional metered resources is blocked until usage is below the current-plan limit or the user upgrades;
- Max-only modules such as business invoicing become read-only where practical instead of deleting data;
- exported data remains available.

## 4. Security model — paid access cannot be bypassed from the browser

### Non-negotiable rule

The frontend must never decide whether a paid action is authorized. It may hide, disable, lock, decorate, or explain a capability, but the backend must independently reject every disallowed operation.

### Required backend primitives

1. `Subscription` / billing-state record keyed to the billing owner.
2. `PlanId`: `free | pro | max`.
3. `SubscriptionStatus`: at minimum `free | active | grace | past_due | canceled | expired`.
4. `EntitlementCatalog`: immutable server-side mapping from plan → capability + limit.
5. `EntitlementService`: returns effective plan, access flags, limits, current usage, and reset times.
6. `require_entitlement(capability)` dependency/helper for binary paid features.
7. `enforce_limit(metric)` helper for quota-bearing create/import/upload operations.
8. A server endpoint such as `/api/billing/entitlements` for the UI to render current-plan state.
9. Audit log entries for plan/status changes.

### Anti-bypass enforcement

- Direct API calls from DevTools/cURL must receive 403/402-style product errors when the entitlement is missing.
- Client-supplied `plan`, `is_pro`, `is_max`, price, billing interval, or usage values are never trusted.
- Paid plan mutation is never exposed through normal user-update endpoints.
- When payment is added, only verified provider webhooks may activate/renew paid status.
- Webhook events must be signature-verified, idempotent, and persisted by provider event id.
- Quota checks and resource creation must be transaction-safe so two concurrent requests cannot exceed a hard limit by racing each other.
- Usage counters are server-owned. The browser cannot decrement/reset them.
- Cache invalidation occurs immediately after verified subscription changes.
- Workspace access inherits the billing owner's entitlements where appropriate; workspace membership itself must not mint a paid plan.
- Admin/dev override, if ever added, must be explicit, audited, and disabled by default in production.

## 5. Billing ownership model

V1 entitlement ownership is user/account based.

- A user starts on Free automatically.
- Owned personal/business workspaces consume that owner's plan quotas.
- Max may own business workspaces.
- Members invited into a Max-owned business workspace may use the workspace capabilities granted by that workspace owner's Max entitlement, subject to workspace role permissions.
- A member cannot use another owner's Max subscription to create their own Max workspace.

This separates billing entitlement from the existing workspace module resolver and existing write permissions. Module visibility, role permissions, and paid entitlement are three independent checks that must all pass where relevant.

## 6. Payment-provider boundary

This branch builds the pricing page and entitlement foundation before checkout.

Until a real payment provider is integrated:

- the production client cannot activate Pro/Max;
- CTA may route to a future checkout entry point / wait state, but must not flip plan state locally;
- test fixtures may create paid subscription states only in backend tests or explicit local-development tooling.

Later checkout integration must add provider customer/subscription ids, current period timestamps, cancel-at-period-end, grace period, verified webhooks, invoice/payment history, and reconciliation jobs.

## 7. Pricing-page UX — FinCo-native, reference-inspired, not a visual clone

The supplied X pricing screenshots are used for hierarchy and interaction inspiration only. The page must use FinCo-Pilot's existing monochrome design language, F mark, spacing, radii, typography, and motion.

### Mobile/PWA structure

1. Compact close/back control + FinCo F mark.
2. Original FinCo hero visual using monochrome depth/orbit/particle treatment rather than X artwork.
3. Headline: clear value, not a fake discount countdown.
4. Three-plan segmented control: `Free | Pro | Max`.
5. Selected-plan feature panel with simple icons and short labels.
6. Locked features remain visible with a lock icon and the required-plan capsule.
7. Billing selector below features:
   - Pro: Monthly ₹99 / Annual ₹999 with `Save ₹189`.
   - Free: no interval selector.
   - Max: Monthly ₹349; annual cell absent or marked `Not available yet`, never fake-disabled pricing.
8. Sticky safe-area-aware CTA at the bottom.
9. Full comparison section and FAQs below the primary decision surface.

### Desktop/tablet structure

- Hero + monthly/annual control.
- Three concise plan cards with Pro visually emphasized as `Most Popular`.
- Feature comparison below.
- No huge marketing gradients; use true-black/white, subtle graphite borders, depth, blur, and restrained semantic colors only.

## 8. Pro / Max Dynamic-Island plan badges

Create one reusable badge component, not ad-hoc pills.

Visual requirements:

- small capsule / Dynamic-Island silhouette;
- subtle 3D depth via border, inner highlight, shadow, and transform only;
- monochrome FinCo styling, with semantic distinction via text/icon treatment rather than loud gradients;
- variants: `PRO`, `MAX`;
- responsive down to narrow mobile widths;
- accessible text, not color-only meaning;
- reduced-motion safe.

Usage:

- locked navigation items;
- locked feature controls;
- comparison table;
- upsell modal/sheet;
- current-plan indicator in billing settings.

## 9. Locked-feature behavior

Locked features must be discoverable but unusable.

- Show lock icon + required plan badge.
- Use `aria-disabled` / disabled semantics where appropriate.
- Do not execute the feature action when clicked/tapped.
- A tap may open an informational upsell sheet explaining `Requires Pro` or `Requires Max`; it must never invoke the protected action.
- Route-level paid pages must be protected both in frontend routing for UX and backend APIs for security.
- Deep links to a paid route must resolve to an upgrade/locked state, not the protected feature content.

## 10. Pricing data architecture

Do not hardcode pricing independently across cards, settings, lock sheets, and checkout.

Create a single typed frontend pricing catalog populated from a backend public billing catalog endpoint when checkout arrives. Until then, one canonical frontend config mirrors this document and is covered by tests.

Canonical values:

```text
FREE:  ₹0
PRO_MONTHLY: ₹99
PRO_ANNUAL: ₹999
MAX_MONTHLY: ₹349
MAX_ANNUAL: unavailable in V1
```

All savings copy must be computed, not typed manually.

## 11. Required application wiring

### Frontend

- `/pricing` route (accessible logged-in and in an intentional logged-out presentation).
- `PricingPage` responsive layout.
- `PlanBadge` component.
- `LockedFeature` / `EntitlementGate` components for UX only.
- Entitlements context/query sourced from backend.
- Upgrade sheet/modal.
- Sidebar/nav lock state derived from entitlements.
- Settings/Billing entry showing current plan and usage.
- PWA-safe-area handling and route-loader integration.

### Backend

- billing/subscription model + migration;
- entitlement catalog/service;
- read endpoint for effective entitlements and usage;
- server-side gates on every paid capability;
- hard quota enforcement for create/import/upload paths;
- tests for direct-API bypass attempts, downgrade, expiry, grace, and concurrency;
- no payment-provider activation endpoint until provider integration is implemented.

## 12. Validation gates before merge

Must all pass before this branch is considered complete:

- backend unit tests;
- backend API entitlement tests;
- direct-request bypass tests;
- quota boundary tests (`limit-1`, `limit`, `limit+1`);
- concurrent-create quota test for hard limits;
- downgrade/read-only preservation tests;
- frontend lint;
- frontend typecheck;
- frontend production build;
- existing Vitest suite;
- new pricing/plan-badge/locked-feature tests;
- mobile narrow viewport test;
- desktop test;
- PWA standalone/safe-area smoke test;
- dark and light theme screenshots/manual review;
- keyboard + screen-reader semantics for locked controls;
- no paid state can be produced by localStorage, query params, DOM edits, or request-body plan fields.

## 13. Build order

1. Audit existing routes/modules/permissions and all candidate paid feature mutation paths.
2. Add backend plan catalog and entitlement data model.
3. Add entitlement read endpoint + backend enforcement helpers.
4. Wire quotas into resource creation/import/upload paths.
5. Add frontend entitlement client/context.
6. Add reusable lock UI and Pro/Max Dynamic-Island badges.
7. Build pricing page using the approved FinCo-native layout.
8. Wire sidebar/pages/settings locked states.
9. Add tests and bypass/security cases.
10. Run full CI and responsive/PWA review.
11. Only after this is stable, start payment/checkout provider work on a separate branch.

## 14. Decisions intentionally deferred

These are not guessed during implementation:

- Max annual price: unavailable in V1 until explicitly approved.
- Bank-sync quotas: deferred until actual provider pricing is known.
- Team-seat pricing beyond any included Max workspace access: deferred until collaboration billing is designed.
- AI overage/top-up price: deferred until real model/token cost data exists.
- Launch coupons / first-two-month promotion: optional later campaign, not baked into base plan price.
