# Post-merge release check — 17 October 2026

Owner merged PR95 at07:09:32 UTC (12:39:32 IST). Main52a471327b9fc00cee6a925c660b61ce2f574384 has the exact reviewed tree24ce2e54afd30b563f00c56ef63d70ac66118175. Vercel web production dpl_5HNYU7gNNLvdc2TMkdFddXVnpVz6 is READY at this SHA with apex/www aliases. Earlier unmerged/main264a6ad records are historical snapshots.

## Live discovery and scoped fix

Four public apex pages return200/noindex. Private signed-out app pages retain noindex. Root sitemap now returns200 XML but empty inventory; publication variables are absent. Root redirects308 to /welcome/ and synthetic missing marketing route returns404. This is a deployed excluded build, not an indexable release.

All four www marketing canonical paths with trailing slash return200; slashless variants redirect308. www robots/sitemap redirect308. Cache-busting homepage query still returns200. No assumption that cache expiration fixes it.

This follow-up adds exact host-scoped redirects for four approved slash paths before the existing wildcard. No global host/auth/API redirect. The bounded observer now checks all four www paths and rejects anything except308 to the exact apex path.31 offline growth tests and18 landing contracts pass, including negative fixtures for the observed200, temporary redirects and wrong destinations. Existing Node module-type warnings remain. Hosted acceptance is pending; this is not a claimed live fix.

## Full main CI release blocker

Run39012585198, Backend Tests job117338064737:5,212 passed;7 skipped;1 failed in513.70s. Failure: tests/test_clerk_exchange_safety.py::test_verified_email_does_not_implicitly_link_existing_user expected403, got200. Full backend runs on main push; earlier22/22 PR checks can scope-skip unchanged backend and do not certify this full suite.

PR96 already proposes identity binding/isolation fixes. Review its current source/checks against latest main before owner-approved merge. Do not silently duplicate or merge separate security work. This follow-up changes no backend identity handling; no blanket production-ready claim.

Cloudflare tunnel dc9f949a-6702-4222-844f-51e1b2f34031 is healthy with four connections. Dedicated readiness returned200 ready in the first sweep; subsequent apex/dedicated probes timed out. Tunnel health does not establish OAuth/session acceptance; timeout cause unresolved.

## Execution ownership

| Step | Autonomous work | Owner needed only for |
|---|---|---|
| 1 Release review | Main/PR/diff/checks and fixes | Final merge approval for follow-up/security PRs |
| 2 Deployment | Exact source/settings/rollback verification and authorized release | Explicit public-indexing release decision under retained publication policy |
| 3 Live SEO | HTTP/browser/schema/canonical/robots/sitemap checks | No routine input |
| 4 App regression | Synthetic tests, signed-out smoke, authorized isolated provider tests | Account handoff/OTP or disposable provider/test identity when unavailable |
| 5 GSC | Inspect; submit/read back where writable access exists | Authorized FinCo property account; HYPD is read-only |
| 6 Bing | Existing property setup, sitemap, inspection | Login/ownership challenge |
| 7 Content/trust | Source-backed drafts, links and examples | Verified operator/legal/retention facts, real proof and required editorial approval |
| 8 Analytics | Existing property inventory, minimum consent-compatible funnel | Property access/selection or required policy choice |
| 9 Performance | Reliable live baseline, measured fixes and comparisons | Only actual access gaps; no paid purchase implied |
| 10 AEO/monitoring | Actual accessible observations, evidence panel and existing schedule | Unavailable account access; elapsed7/14/28-day time |

## Concrete publication proposal

Only fincopilot-web production: FINCO_MARKETING_PUBLICATION_APPROVED=true and NEXT_PUBLIC_MARKETING_URL=https://fincopilot.app. Verify provider-owned VERCEL_ENV; do not override it. Four eligible paths: /welcome/, /welcome/features/, /welcome/how-it-works/, /welcome/guides/import-transactions/. Previews/private app stay excluded. Resolve live release blockers and verify exact deployment before search submission. This post-merge run performed no env/indexing/provider write.

Rollback reference: dpl_xEssQgKSs3a99ZasGGrpGVdoHW5W. Withdrawing publication requires removing scoped approval and rebuilding. No financial-data rollback, DB migration or API DNS change to ship SEO.

The53-task inventory remains authoritative; do not mark all G1 tasks done merely because PR95 merged. Raw bounded GET evidence: evidence/2026-10-17/postmerge-http.json. Main CI: https://github.com/S2zxx0zxx/FinCo-pilot/actions/runs/39012585198
