# Pricing completion and continuity — 15 October 2026

## Refreshed scope

Base main: `7736a24e7d520b9f08dd91d38e895b5d240f8a09`. Landing PRs #81/#86 were merged; auth #87 and production/mobile work #88 were subsequently merged. The pricing work from the previous session was not published. This branch finishes the existing finance application's `/pricing`; the separate Next.js landing remains intact. Open growth PR #89 is a separate docs/tooling proposal and is not incorporated.

No backend, financial records, authentication policy, database, migrations, infrastructure or live payment configuration changes. No application dependencies added. Do not replace the Vite application's real checkout with an independent Next.js payment implementation.

## Research and selection

Official source: https://github.com/usespaceui/ui at `6489d244d1652470efdc810a79a289ebd966c177`; fresh upstream checkout confirmed unchanged. MIT notice retained in `SPACEUI-LICENSE.txt`, with attribution on adapted primitives. The prior complete category/source inventory is `spaceui-catalog.json`; landing research/preview limits are recorded in `../../landing/docs/`. Those records are reused, not represented as a fresh successful video review of every demo. Prior preview review hit HTTP 429; full interactive review of all demos remains incomplete.

TinyFish public pricing review: https://agent.tinyfish.ai/runs/dfa3d5c7-ad3e-4bb5-bf1f-233db915d9ee. Observed Community, highlighted Pro annual, Lifetime; FAQ and calculator; **no monthly/annual toggle**. This is reference-site evidence, not a FinCo business model. Adopt three-card hierarchy, differentiated middle tier, clear billing suffix and objection-handling FAQ. Reject Lifetime, discounts, urgency and developer-time savings calculator because FinCo has no corresponding verified offer or ROI. No paid/gated source copied.

| Supplied category | Pricing decision |
|---|---|
| Docs / skills / typography | Reuse local Inter, readable hierarchy, tabular prices; Space Motion/Interactions references in `spaceui-reference`; Vercel React Best Practices applied to component separation and derived URL state. |
| Primitives | Official Card, Badge, RadioGroup, Tabs, Accordion, Separator and segmented-control helper adapted directly. Existing source-adapted Button retains application `asChild` compatibility. |
| Components | Existing original FinCo mark retained. Prefer functional pricing primitives over unrelated shader/showpiece components. |
| Tools / avatars / Squishmoji | Existing local IdentityAvatar as a decorative FAQ guide, not a customer identity/testimonial. No remote identity requests. |
| Motion tool / interactions | 180–200ms state/accordion transitions, no price obscuring reveals or autoplay. Scoped reduced-motion rule disables transitions/animation. No simulated agent data or autonomous workflows. |
| Blocks | Three-tier composition informed by the official pricing reference. Preserve real app management cards instead of copying another product's checkout. |
| Hooks | Existing useMediaQuery in avatar respects reduced motion; URL state supplies plan/period across navigation. No unnecessary new global listeners. |
| Animoji / sound | Not added: avoid distracting motion/audio next to financial commitments. Existing licensed avatar is sufficient. |

## Source-to-section map

| Source | Destination | Adaptation |
|---|---|---|
| registry/primitives/card | `pricing-card.tsx` | Import paths; named article and summary section through upstream render API. |
| registry/primitives/tabs + lib/segmented-control | `pricing-tabs.tsx`, `pricing-segmented-control.ts` | Import paths; inactive tab contrast override in scoped CSS; mobile plan tabs with real associated panels, roving keyboard behavior. |
| registry/primitives/radio-group | `pricing-radio-group.tsx` | Import path; labelled monthly/annual billing group. Radio semantics, not false content tabs. |
| registry/primitives/accordion | `pricing-accordion.tsx` | Import path; six real FAQ disclosures. |
| registry/primitives/badge | `pricing-badge.tsx` | Import path; variant helper made internal for React Refresh. |
| registry/primitives/separator | `pricing-separator.tsx` | Import path; structural dividers. |
| Existing Button / Squishmoji | `pricing-experience.tsx` | Functional actions, decorative FAQ guide. |

`pricing-experience.css` scopes the composition to `.finco-pricing`, uses two-tone surfaces and no decorative gradients. Desktop shows three cards; <=920px uses plan tabs; comparison becomes a selected-plan definition list without horizontal table scrolling. Prices remain visible and finite; touch targets >=44px. Light and dark preserve Pro's readable green surface.

## Authoritative product truth

Sources: `backend/app/billing/pricing.py`, `backend/app/billing/catalog.py`, `backend/app/billing/usage.py`, frontend catalog and current management modules. Display metadata is in `src/billing/pricing-presentation.ts`.

| Plan | Real standard price | Billing |
|---|---|---|
| Free | ₹0 | None |
| Pro | ₹99 | Monthly |
| Pro | ₹999 | Annual upfront; ₹189 saving vs 12 standard monthly payments |
| Max | ₹349 | Monthly only |

No Max annual or lifetime. Standard cards do not substitute a founder campaign price for eligibility. FounderOfferCard retains server-backed campaign state/capacity and appears only for Pro monthly, the eligible billing interval. Exact quote and tax remain server-authoritative. Missing/negative/foreign-currency price options show Unavailable and disable continuation; no fabricated paid ₹0 fallback. Catalog fetch failure retains the pre-existing approved fallback catalog, with tax unavailable disclosure and backend fail-closed checkout.

All 15 quota metrics are represented, plus advanced reports and Agents capability. MiB/GiB match binary byte allowances. Max personal/business workspace sublimits share the total of three. Monthly usage resets at calendar-month boundaries in UTC, not annually or on the subscription anniversary. Max AI allowance is conditional on deployment enablement; no unconditional AI claim.

## Behavior changes and preserved boundaries

- One shared URL-driven Pro billing interval; desktop cards, mobile card, summary and login return agree. Max still submits monthly even while Pro annual is selected.
- Selecting a card/tab never starts payment; a single selected-plan action does. Current plan is disabled.
- Paid customers choosing Free go to existing subscription management instead of an inert downgrade button. No invented immediate downgrade/refund operation.
- Stable Home link replaces history-dependent back navigation. Privacy, Terms and Support remain real routes.
- Existing Razorpay SDK loading, server-owned order validation, modal/verification fences, retry=false, cancellation reservation reconciliation, duplicate callback guard and support request references preserved. SDK remains lazy on paid continuation.
- Usage, renewal enrollment, cancellation, refunds, checkout status and refund operator modules retained, visible only to signed-in users. Their endpoints/mutations/permissions are unchanged.

## Thirteen-step execution ledger

| # | Requirement | Evidence / status |
|---|---|---|
| 1 | Recover current branch/main/PR state | Fresh main + #86 merged confirmation; #87/#88 preserved. |
| 2 | Understand current architecture | Pricing controller, billing provider/catalog, backend prices/limits/usage and six management modules inspected. |
| 3 | Research supplied Space UI categories | Existing complete source/category ledger + fresh pinned upstream inspection; all-demo live preview limits explicit. |
| 4 | Study product/pricing references | TinyFish pricing review above; prior landing showcase ledger reused. No unsupported competitor conversion claims. |
| 5 | Write source-to-section plan | Selection table and implementation map above. |
| 6 | Preserve approved product truth | Standard prices, 15 limits, capability and founder/tax caveats checked against backend. |
| 7 | Build responsive composition | Source primitives, desktop cards, mobile tabs/list, scoped CSS. |
| 8 | Complete action/navigation paths | Plan-only selection, one continuation action, annual login return, real management and legal/support links. |
| 9 | Preserve payment/data safety | Existing order/verification/cancellation fences unchanged; synthetic regression suite expanded. |
| 10 | Accessibility and motion | Real tab panels/radio group, heading/region/table semantics, FAQ controls, focus treatment, reduced motion. |
| 11 | Responsive visual verification | Automated browser report and screenshots; final results added after execution. |
| 12 | Engineering verification | Lint, types, production build/budget, complete frontend suite and dedicated browser workflow. Exact results below. |
| 13 | Reviewable delivery | Isolated branch based on latest main; final PR after local acceptance; no merge or production cutover. |

## Verification receipt

- Complete frontend Vitest suite: **934 passed / 122 files**; after adding the Max annual regression, affected pricing/billing suite: **49 passed / 10 files** (one additional test; full suite not redundantly rerun).
- Zero-warning whole-frontend ESLint and TypeScript pass. Production build and artifact/SRI/discovery check pass; entry graph 214,843 gzip bytes versus 307,200 budget; no public source maps.
- Chromium local contract acceptance: **36 visits**, widths 320/375/390/620/768/920/921/1024/1440, light/dark, guest/signed-in. No horizontal overflow. Annual Pro ₹999 and Max monthly ₹349, tab ArrowRight, FAQ, annual auth handoff and management anchor pass; **8 axe scans**, zero violations. External requests/mutations blocked.
- Browser review found and fixed inactive mobile tab contrast (3.02:1 before fix) and 2px signed-in Refunds action overflow at 320px. No hidden overflow workaround; button rows wrap and retain >=44px targets.
- Inspected rendered 390px light guest and 1440px dark guest screenshots; signed-in dark 390px reviewed separately. CI uploads final screenshots for each engine.
- Initial remote CI exposed an ANSI-coloured Vite log readiness hang in the verification harness, not the product. The runner now strips ANSI control sequences, drains stderr, prints visit progress and fails readiness after 20 seconds; browser steps have a five-minute deadline. Forced-colour GitHub Actions environment was reproduced locally; corrected harness completed 18 signed-in visits with clean accessibility checks.
- Local Firefox failed with sandbox/runtime library error; WebKit requires absent OS libraries. System package install is unavailable in this workspace. These are not product test passes; the dedicated GitHub workflow installs required dependencies and must verify both engines before final handoff. Browser responses are local synthetic contract fixtures, with external requests and mutations blocked. They do not certify provider payments or production readiness.

## Remaining external acceptance

Real payment/provider reconciliation, live account eligibility/renewal/refund operations, physical iPhone/Android and VoiceOver/TalkBack are not exercised by these fixtures. A test order must use authorized isolated provider resources; no real charge is initiated here. Marketing hostname/cutover and historical dedicated API readiness are separate deployment concerns. Do not claim they are solved by this pricing UI PR. No exhaustive-video-review or 13/13 production-completion claim.
