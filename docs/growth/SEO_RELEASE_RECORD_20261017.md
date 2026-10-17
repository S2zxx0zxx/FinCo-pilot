# Reviewable release record — 17 October 2026

## State and scope

Production was not changed by this run. Latest independently fetched main and observed web production SHA: `264a6ad75ef588f70402a7b1a44ca9b167840262`. Existing draft PR95 was reconciled to that main without force push or merging unrelated PRs. Engineering candidate: `cd652108f6e3438e7cc716b7019b246e7785af1a`; subsequent ledger/lab/release-probe updates are separately reviewable in the PR head. Inspect the latest head/checks before any release.

Baseline production deployment: `dpl_xEssQgKSs3a99ZasGGrpGVdoHW5W`, fincopilot-web, READY, https://fincopilot-m57nmre68-s2zxx0zxxs-projects.vercel.app . This is the rollback reference, not the candidate preview.

Candidate preview: `dpl_JAjw4YXj8x6VzTB39rU28gf1U3Xa`, READY at exact engineering SHA, https://fincopilot-pw9v5jprv-s2zxx0zxxs-projects.vercel.app . Actual preview browser confirms repaired footer navigation, source-backed import article, correct canonical and noindex. Further head deployments/checks must be matched by SHA.

## What changes

1. Preserve PR95 links and accessible SSR H1; keep the branded layout and financial application.
2. Generate root robots and root sitemap from the same four-page export. Approved production gets the exact public inventory; preview gets disallow-all and empty inventory. Preserve private/training/user-agent restrictions. No invented lastmod.
3. Require explicit approval, actual production environment and exact apex for combined publication. Prevent direct export bypass. Add final artifact gates, production-fixture CI and bounded release observer.
4. Permanent root/public alias redirects and public-only www canonical redirects in source config. No live DNS/proxy mutation or auth/API host redirect.
5. Enrich the existing import guide with source-authenticated QIF/dedupe limitations and a synthetic INR sample. No additional public route or financial write.
6. Port the one-line Sentry contextual typing fix already present in separate PR96, because main lint fails on explicit-any. No Sentry sanitization/runtime/collection change; no other PR96 patch imported.
7. Persist all53 blueprint tasks, provider/search/HTTP receipts, keyword/content/AI research and monitoring checkpoints.

## Local acceptance

- Landing18 contracts; growth29 offline contracts; all pass.
- Frontend939 tests /122 files, lint and TypeScript pass. Original main lint failure and its scoped correction are retained in the ledger.
- Combined excluded-preview build and approved-production fixture build pass, including final HTML canonicals, metadata, source H1, links, exact root/export sitemap, root robots, private app noindex, SRI/CSP, no public sourcemaps and PWA identity/start route. App entry graph214922 gzip bytes against307200 budget.
-175 synthetic account/import backend regressions pass with warnings as errors. No production DB or provider write; this is not an entire backend suite or native production isolation acceptance.
- Chromium homepage9 widths,8 axe sample-state scans; documentation12 viewport-page checks plus3 no-JS pages. Zero reported violations/external requests.
- Actual Nginx synthetic public entry/login12 cases pass with strict CSP and privacy/cache/header checks. It is synthetic GET-only config, not Google OAuth/payment/session acceptance.
- Independent local Firefox execution hit its150-second outer resource cap during newPage, with no product assertion failure. Do not label that local run passed. Remote engine CI is distinct evidence.
- Two mobile and two desktop Lighthouse samples for each of three URLs are recorded. Plain uncompressed local serving makes these diagnostic, not live CWV or a transport-equivalent before/after improvement. Live browser certificate refusal and PageSpeed429 remain explicit limitations.
- Secret hygiene and whitespace checks pass. GitHub Backend Tests job may scope-skip unchanged backend; its green wrapper is not a full-suite claim.

## Before/after acceptance matrix

| Contract | Fresh production before | Candidate proof | Remaining live gate |
|---|---|---|---|
| Four public pages |200 HTML; unique metadata; noindex |Production fixture:200/indexable intended metadata; preview:noindex |Approved exact-SHA production |
| Root sitemap |404 |Root XML copied from export;4 production/0 preview |Root200 XML on apex |
| Root robots |200; private rules; no sitemap |Generated authoritative file; restrictions retained; one directive when approved |Final HTTP policy at apex |
| Home footer |Wrong unprefixed marketing URLs |Actual preview clicks resolve /welcome/... |Release exact candidate |
| H1 |Source static tokens aria-hidden |Readable initial heading and no-JS browser pass |Release exact candidate |
| www |Duplicate200 canonical-to-apex |Public-only host redirects in Vercel config |Verify actual308 and no session effect |
| Missing welcome route |True404 already |Preserved; no new SPA catch-all |Recheck after release |
| Login/register/app policies |200 noindex |Private shell still noindex; synthetic UI pass |Real authorized provider E2E |
| API readiness |Transient tunnel down, later healthy; both public readiness URLs200 ready |API routing unchanged |Exact backend SHA/provider acceptance unknown |

Full response metadata is in evidence/2026-10-17/production-http.json and preview-http.json. Public readiness alone does not prove auth, payments or financial correctness.

## Required release decision

The blueprint chapter04 and existing project review instructions retain owner merge approval. No merge, production environment switch, DNS/Tunnel/Worker change, database change or public indexing activation was performed. Main protection details could not be read (GitHub integration403); do not change protection settings to bypass checks.

After required exact-head CI and maintainer content review, approve this PR and the public-only publication separately from real finance/provider acceptance. Production env scope on **fincopilot-web only**:

```
FINCO_MARKETING_PUBLICATION_APPROVED=true
NEXT_PUBLIC_MARKETING_URL=https://fincopilot.app
VERCEL_ENV=production # provider-owned value, verify rather than override
```

Do not set approval on Preview, API, landing's separate project or private-QA projects. Build with the scoped settings; identify exact deployment SHA and verify qualified responses before search submission. Missing approval keeps indexing closed. Reverting approval requires a rebuild; it is not a runtime toggle.

## Discovery/provider actions

HYPD connected property `sc-domain:fincopilot.app`, siteOwner. Four inspections: home excluded by noindex, last crawled16Oct10:21:52Z; three other URLs unknown. Submitted sitemap list empty. Final web performance aggregate and country/device query17Sep–14Oct have no rows; not proof of zero visitors.

Do not submit the current404/empty sitemap or request indexing of excluded pages. After qualified production, submit https://fincopilot.app/sitemap.xml once and read back the provider record and errors. HYPD is read-only. Browser Search Console account currently lacks FinCo property access; its access to another property is irrelevant. Use an authorized property account when completing submission. Bing is signed out: ownership, import, sitemap processing and URL inspection remain unverified; no duplicate account created. IndexNow remains optional/disabled without validated published key and eligible changed URLs. No Google Indexing API for ordinary finance pages.

Google Rich Results URL test on candidate preview is expected to be blocked by preview robots. Code-only JSON-LD validation, where reported, is separate from live eligibility. No removal of preview controls to satisfy a validator.

Code-mode result from actual deployed guide JSON-LD: **one valid Breadcrumb item detected**, receipt https://search.google.com/test/rich-results/result?id=bjcIZ__CZD2L5fMvpzDheg . URL-mode separately confirmed preview robots block; this does not certify production eligibility.

First engineering CI also exposed the old recovery fixture's root sitemap404 expectation; it is changed to200 XML/zero eligible preview URLs. Remote Firefox public-entry timed out at the1024px reduced-motion cold-login phase, after earlier cases passed. This remains a recorded intermittent harness/browser concern, not a claimed product fix. No timeout/assertion weakening is included. Final exact-head checks must pass independently.

## Rollback and stop conditions

- No schema/financial-data rollback is needed: no financial writes or migrations are in scope.
- On public routing/CTA/auth/cache/privacy regression, restore the identified prior web deployment; verify alias points to its exact SHA and run public readiness/auth entry smoke. Do not reroute API, reactivate stale Worker, change DNS, restore an old DB or weaken authentication.
- Revert scoped publication approval and rebuild when indexing must close. Keep disallow/noindex on previews and private app; never globally emit index,follow.
- On malformed sitemap, private URL inclusion, preview indexing or missing security headers, stop release and revert the scoped code/config candidate.

## Monitoring and next evidence

Existing daily **FinCo-Pilot Full Page Audit** was updated in place; its enabled state and schedule are preserved. No duplicate automation. It refreshes main/deployment/PR95 and bounded public discovery evidence; weekly connected GSC checks use finalized data and remain read-only.7/14/28-day outcome checkpoints start from first *verified public indexable release*, not PDF date. Actual future delivery, engine indexing, rankings, AI citations, conversions, field CWV and costs are pending independent evidence.

All53 task statuses are in seo-inventory.csv. DONE denotes the named bounded artifact/assessment only. Tasks whose acceptance requires production, authenticated providers, verified business facts or future outcomes remain BLOCKED/UNVERIFIED. The PR checks and description carry the final exact-head CI/deployment receipt; this record does not turn source readiness into a live-completion claim.
