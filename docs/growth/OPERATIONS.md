# Organic growth operations - proposed schedule

## Existing scheduling inventory

Read-only automation lookup found enabled FinCo-Pilot hourly Speed Watch and daily Full Page Audit, plus separate social watches. Their prompts include historical October 9 topology and explicitly require refresh. Do not treat those snapshots as current or create overlapping probes blindly. The existing daily Full Page Audit prompt was subsequently updated in place to refresh current source/topology and include bounded SEO checks; its daily cadence and enabled state were retained. No duplicate schedule was created. The updated schedule configuration is confirmed, but a subsequent scheduled execution/delivery has not yet been observed.

## Request and cost budgets

- Daily bounded implementation: `python3 scripts/growth_public_audit.py --core` selects five public URLs and one redirect maximum (<=10 requests). Use only after reviewing the current candidate/release source.
- Manual full script: fixed eight public URLs, one GET per URL, sequential, no retries, maximum three redirects per URL, 15-second timeout and 256 KiB response cap. At most 32 HTTP requests including redirects. No private routes, cookie jar, finance API, crawler spoofing, forms, auth or database writes.
- Default operations proposal: five representative URLs on weekday mornings, one redirect maximum (<=10 requests/run); one <=20-URL weekly sample, one redirect maximum (<=40 requests/run). Approximately <=400 scheduled requests in a four-week month if activated, excluding external service/browser resource requests. Review against actual provider quota before enabling.
- Reuse reports; do not run multiple crawlers or heavy browser/Lighthouse tests daily. Full browser tests on relevant changes only. Public marketing builds must not query financial APIs/DB.
- No new subscriptions, deployments or paid jobs authorized by this document. Existing tool/provider usage is not an audited bill; actual charges/quotas UNKNOWN until account reporting is reviewed.
- Keep sanitized technical evidence for 90 days initially; never retain recovery tokens, user data, raw cookies, private analytics rows or full headers. Review retention with owner.

## Cadence when enabled

| Cadence | Work | Output |
|---|---|---|
| Weekday morning | Refresh deployed source; bounded availability/robots/sitemap/canonical checks | New confirmed P0/P1 regression alert only |
| Daily when data available | GSC/Bing deltas; editorial queue max 1-3 evidenced opportunities | Date/lag/confidence and owner decisions |
| Weekly | Representative technical/schema checks, 3-5 competitors, funnel segments | Prioritized corrections; preserve data sufficiency caveats |
| Monthly | Indexing, brand/nonbrand, AI citations/referrals, conversions and resource spend | Outcome scorecard and next 30 days |
| After relevant deploy | Exact-source public SEO, private access/cache, CTA/auth and PWA smoke | PASS/FAIL/UNKNOWN with rollback decision |

## Alert rules

- Repeated confirmed public 5xx/404 in two bounded observations; distinguish edge/client block and origin failure.
- Any verified anonymous financial-data leak or unexpected indexable private content: immediate P0, no reproductions that expose more data.
- Approved production public route unexpectedly noindex, preview unexpectedly indexable, sitemap containing private/redirect/noindex URLs: release-blocking.
- Conversion drop: require comparable periods, consent/source stability and sufficient data; missing exports are not zero.
- Stable known failures create no repeated notifications. Report only meaningful state changes. Keep current report timestamp and last alerted state.

## Release checklist

Validate initial HTML title/H1/body, canonical host, robots/meta/header interaction, valid public-only sitemap, visible-fact schema, signed-out privacy, auth/recovery/payment continuity, no-store, mobile widths 320/375/390/768/1024/1440, keyboard/reduced motion, current tests and performance budgets. Physical-device/screen-reader acceptance and real provider flows require actual evidence. Capture lab LCP/TBT/CLS separately from field p75 LCP/INP/CLS; no invented field INP.

## Report

Date/time; repo HEAD and production SHA by origin; task IDs/PRs; source vs preview vs live status; work kept; search/AI data with reporting lag; request/cost status; risks/blockers; smallest owner action; next actions. Never call the entire project done while external acceptance remains.

## Incremental resources in PR #89

- Marketing: four statically rendered routes; zero financial API/DB calls and zero external tracking calls. Storage is static build output plus existing images/fonts. Bot/CDN bandwidth still depends on actual traffic and must be measured.
- Attribution constructor and report/dashboard: zero network calls; report export processing is manual/local. Actual analytics collection remains disabled.
- CI: one standard-library offline growth-contract job; one additional explicit-production fixture build in the landing job; documentation checks added to the existing three-engine matrix. Record real job durations/allowance before increasing cadence.
- Cheaper alternative: keep manual/offline source and export checks; run browser/Lighthouse only on relevant changes. No new paid subscription has been activated.
- Persist only public-safe receipts and aggregate sanitized reports; keep private exports outside Git and follow the 90-day proposed retention pending owner policy.
