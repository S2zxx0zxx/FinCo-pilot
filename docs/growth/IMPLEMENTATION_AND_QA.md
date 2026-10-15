# Candidate implementation and acceptance

15 October 2026. Same draft PR #89, reconciled with main `e727498c9481cdcb94f06b6f429933224f9c5b08` (pricing PR #90). This is a branch implementation report, not a certificate that all 52 roadmap tasks or production outcomes are complete. TASK_REGISTER.csv accounts for every task individually.

## Concrete behavior

Four initial-HTML marketing pages provide distinct brand, feature, first-session and import-review intent. Canonical, social metadata, safe WebSite/BreadcrumbList, restricted-crawler policy and an eligible-only XML sitemap use one explicitly validated owned HTTPS origin. Indexability requires both production environment and explicit opt-in. Preview builds remain noindex with an empty sitemap. `discover.fincopilot.app` in CI is a fixture, not a registered/released host.

The financial Vite app shell gains noindex, including its current client-rendered pricing and policy utility routes. This is a material indexing change: public indexable equivalents need a reviewed marketing/runtime strategy before release. App journeys and authentication are preserved. Nginx/Helm/Vercel/Worker sitemap routing no longer serves a misleading app shell; missing app sitemap returns 404. Worker keeps upstream X-Robots-Tag and adds noindex to private/app responses while retaining no-store controls.

Reporting accepts authorized aggregate exports locally, rejects unexpected personal/financial columns and malformed cohorts, and outputs sanitized aggregate JSON. A local dashboard starts with 14 UNKNOWN values and has no network/storage. The consented fixed-ID attribution constructor is deliberately not wired to a collector. No private report, financial record or secret is committed.

Source-backed editorial drafts, claim review, official competitor text research, intent ownership, distribution drafts, citation protocol and conditional IndexNow/translation/experiment procedures are recorded. No placements, outreach, ranking results, customer outcomes, AI citations or IndexNow submissions are claimed.

## Verification recorded locally

| Check | Observed result / limitation |
|---|---|
| Full frontend suite after PR90 integration | 935/935 passed across 122 files with two bounded workers |
| Initial default-concurrency full run | Two existing timing timeouts; both affected files passed unchanged in focused run; bounded full rerun passed. No assertion weakened |
| Frontend lint / TypeScript / production build guards | Passed |
| Landing TypeScript / unit tests / build | Passed; 10 unit tests |
| Actual built discovery bytes | Preview: noindex and zero eligible URLs; explicit production fixture: four canonical URLs and valid metadata |
| Existing homepage Chromium acceptance | Passed existing responsive/accessibility suite |
| New pages Chromium and Firefox | Each: 3 pages x 4 widths (320/390/768/1440), keyboard/axe and 3 no-JS cases passed |
| Visual inspection | Representative new feature mobile and import guide desktop screenshots inspected; readable layout, no clipping observed |
| WebKit locally | Launch blocked by missing host OS libraries; requires CI browser job with installed dependencies. No local pass claimed |
| Local dashboard Chromium | 390/1440 widths, import/reset, hostile text, axe and no-network checks passed |
| Python probe/report privacy contracts | 12 passed |
| Worker privacy contracts | 9 passed |
| Secret hygiene and migration chain | Passed; chain head 109 |
| Workflow YAML | Parsed locally |
| Performance | Single local lab run: performance 86, accessibility 100, best practices 100, SEO 69; intentional preview noindex affects SEO. LCP 3438ms, TBT 267.7ms, CLS 0. Shared runtime, not a matched before/after or field result |

Firefox local execution required host sandbox environment overrides; CI retains its normal browser settings. Full screenshots are transient test artifacts; small dated JSON receipts are retained under evidence/. Failed official competitor browser captures are explicitly unavailable; text citations are not a substitute for a claimed screenshot review.

New-head GitHub CI is a separate gate. Historical green checks on the initial ledger commit do not validate this candidate. Record the candidate SHA and terminal workflow results in PR metadata once available. Backend provider/live tenant, exact origin deployment and real customer flow acceptance are outside these local passes.

## Release and rollback sequence

1. Re-read current main, concurrent landing/security PRs and deployment routing. Preserve newer work; no automatic merge of other drafts.
2. Confirm exact owner-hosted runtime/source and final public origin. Coordinate with the existing landing workstream; do not activate a competing host.
3. Pass relevant candidate CI including three browser engines, frontend/Worker and container/Helm routing checks. Review indexing effect on app pricing/policies.
4. Verify product/claims/legal/support and isolated signup/login/checkout/activation. Obtain actual authorized property/report access. Account creation alone is not a successful integration read.
5. Owner reviews one PR #89 and authorizes release. Deploy exact immutable source with indexability still disabled; verify preview/private routes and canonical destinations.
6. Only after signed-off routing and public acceptance enable the chosen production origin's indexing. Recheck HTTP/content type/canonical/robots/sitemap/noindex boundaries on exact host. Submit only eligible URLs if explicitly approved.
7. Roll back to the prior immutable deployment/config if guards fail; disable public indexability first. Do not alter identity, DNS or data opportunistically.
8. Observe real indexing and cohort outcomes over reported periods; do not equate deploy success with indexing or growth.

Owner-reported Windsor setup is recorded. Current tools still lack an authenticated Windsor operation/property read; GSC/Bing/GA4 status remains unknown. Existing daily full-page watch was updated in place; its subsequent scheduled delivery is not yet observed. These external gates remain open while independent implementation continues.

## Further continuation — source and review artifacts

The initial final-candidate receipt is in PR89 for `d43ffc4`: all five workflows passed, including all three browser engines and native service checks; the broad backend suite was scope-skipped. Do not apply that green status automatically to a later commit.

Continuation adds the inactive bounded IndexNow implementation, guarded matched-period outcome comparison and dashboard view, and a dedicated CI job running existing synthetic manual-account/transaction-import tests. Offline growth suite now has 25 tests passing locally. Source product-proof acceptance must be read from the continuation's actual CI result. Dashboard import/reset/hostile-input/zero-baseline comparison/axe/no-network checks pass locally at390/1440 widths.

Three official competitor viewport screenshots (Actual, Monarch, YNAB) were successfully captured and visually inspected using the cloud browser after earlier local attempts failed. The Monarch/YNAB consent panels remain visible. PocketGuard displayed a region restriction in that browser; no bypass or global/user-country availability conclusion. Original comparison draft and source matrix are in COMPARISON_EDITORIAL_DRAFT.md. Research captures are not assets to reuse in product marketing.

The manual IndexNow notifier remains offline by default; no live key installation or submission. Maximum seven requests only after explicit approved release and successful preflight. Reports refuse unsupported comparisons, zero-baseline percentages, malformed cohorts and unsafe numeric precision. No real account exports or resource costs were supplied. Source implementation completion does not close these live/evidence gates.

Initial continuation product-proof CI stopped before test collection because its app DATABASE_URL was incorrectly set to SQLite, which the runtime guard correctly rejects. The dedicated job was corrected to keep the valid default PostgreSQL app configuration while conftest overrides test sessions with disposable in-memory fixtures. No runtime guard or product assertion was weakened. Final product-proof result must come from the corrected candidate.
