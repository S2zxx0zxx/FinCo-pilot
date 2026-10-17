# FinCo-Pilot — organic search publication gate (16 October 2026)

This is an implementation/release audit, **not** proof of indexing, rankings, conversions or a search-platform connection. Do not place private financial data, authentication tokens or user identifiers in SEO instrumentation.

## Read-only live observations at 2026-10-16 (Asia/Kolkata)

- GitHub `main` SHA `a84f01fee920b5f8acebf3bd1d6e932a92f0a7fe` (PR #93 merged). Vercel project `fincopilot-web` has a READY production build at this SHA, with a verified rendered `/welcome/` and `/welcome/features/`; both output `noindex,nofollow`.
- The apex `https://fincopilot.app/` still serves the older authenticated SPA entry, while `/welcome/` and `/welcome/features/` render its "Page not found" screen. `/sitemap.xml` likewise returns SPA HTML, not XML. These observations are for the **apex**, not Vercel preview or `www`.
- `www.fincopilot.app/` redirects to `/welcome/` on the Vercel build, but that origin also has `noindex,nofollow` and canonical URLs on the apex. Do not submit `www` or `*.vercel.app` as canonical search properties.
- Cloudflare zone apex CNAME currently targets a Cloudflare Tunnel; `www` targets Vercel. Cloudflare Worker `fincopilot-production-frontend` exists, but the zone returned **zero Worker routes**. Its current deployment binding points to an old Vercel commit. **Do not activate this Worker without updating the immutable deploy target and confirming its safe same-origin backend pass-through.**
- Apex `/api/health/ready` returned a ready JSON response when checked, which says nothing about real login/payment completion. The `/login` page loaded, but provider-backed signup/login were not acceptance-tested.
- Root `/robots.txt` is Cloudflare-managed/augmented and contains an explicit crawler policy. Preserve the user's training/user-agent restrictions. Do not assume a static repo robots file controls the apex.

## Source changes in this PR

1. Repair home-footer links (Space UI anchors bypass Next basePath) to reach the actual `/welcome/features/`, `/welcome/how-it-works/`, and `/welcome/guides/import-transactions/` pages on a combined build. Standalone previews retain standalone paths.
2. Ensure SSR hero text is not **only** hidden inside aria-hidden spans before JavaScript hydration. Keep the same Space UI animation and outer accessible label.
3. Replace the hard-coded exported `noindex` build override with a **fail-closed** gate: ONLY the reviewed `fincopilot-web` Vercel production build, and ONLY when BOTH `FINCO_MARKETING_PUBLICATION_APPROVED=true` and `NEXT_PUBLIC_MARKETING_URL=https://fincopilot.app` are set, may generate indexable marketing. Unapproved, local, self-hosted and PR builds stay excluded. `NEXT_PUBLIC_MARKETING_INDEXABLE=true` alone fails the build. This PR does not toggle deployment variables, modify DNS, expose finance data or submit to search engines.
4. Add source, SEO-link and publication-gate regression tests.

## Production go-live order — all gates mandatory

1. Preserve the current working authentication/data origin and record rollback: current Cloudflare Tunnel CNAME, Worker bindings/route table, Vercel target SHA, and backend readiness. Confirm signing in, signing out, recovery and API routes in a private account fixture; production modifications must not touch the DB or financial records.
2. Resolve the apex routing mismatch. If using the previously reviewed Worker path, update its **verified** Vercel origin/commit binding to an immutable deployment with this change, confirm Worker routing `/api/*` and `/mcp` still pass to the same Tunnel, and run anonymous plus authenticated browser smoke checks **before enabling an apex Worker route**. Prefer a tested staging route/rollout; do not blindly repoint DNS. Confirm apex `/` redirects to `/welcome/`, the four marketing pages serve actual SSR HTML 200 and private routes remain protected.
3. Check public content/claims, accessibility, actual H1 text, unique titles/descriptions, final canonicals, social images, page performance and mobile navigation. Approve operator/legal publication where needed; do not fabricate reviews, ratings, financial claims or credentials.
4. Configure `NEXT_PUBLIC_MARKETING_URL=https://fincopilot.app` and `FINCO_MARKETING_PUBLICATION_APPROVED=true` for the **reviewed production deployment only**. Build and verify exact exported `/welcome/` HTML and `/welcome/sitemap.xml`: four canonical URLs, each HTTP 200, no `noindex` in HTML OR `X-Robots-Tag`, and root Cloudflare robots must allow Googlebot/Bingbot to reach all four. No auth, payments, private app, query/token, `www` or Vercel preview URLs may be submitted.
5. Add/verify `fincopilot.app` as a Domain property in **Google Search Console**, then submit `https://fincopilot.app/welcome/sitemap.xml` through GSC. This nested sitemap intentionally covers only the `/welcome/` subtree. Use live URL Inspection for all four and review indexing reasons; submission does NOT guarantee crawling/indexing. Set up Bing Webmaster Tools ownership for the same apex and optionally run existing `scripts/growth_indexnow.py` **once per actual approved change** after hosting/verifying the owner-authorized key at the apex root and passing the notifier's checks. Do not resubmit unchanged pages daily.
6. Connect an owner-authorized aggregate-only GSC/Bing/GA4 reporter with privacy/consent review. Baseline last 28 days: page/query impressions, clicks, CTR, average position, discovered/indexed URLs, organic landing visits and consented completed signup/activation; unknown metrics remain UNKNOWN. Follow up at 7/28/90-day checkpoints. No claimed ranking or visitor growth without source data.

## Content program after technical launch

Prioritize original product-grounded articles built from reproducible synthetic demonstrations: (a) manual expense tracking without bank sync; (b) import CSV without duplicate transactions; (c) reconcile a partial bank statement vs a current balance; (d) budget versus actual and month-end review. Every article needs an accountable editorial reviewer, tested product steps, references where appropriate, unique intent/title/description, internal links and publication date **only if genuine**. Avoid mass page generation, keyword stuffing, fake FAQ/review markup, or unsupported finance advice.

## Rollback and verification

Rollback only the **apex frontend routing or publication flags** while leaving the original Tunnel API path/DB/secrets and users untouched. Immediately recheck `/api/health/ready`, sign-in and private financial isolation, `/welcome/`, `/robots.txt`, `/welcome/sitemap.xml`, canonical consistency and search directives. For ranking or organic acquisition reports, attribute outcomes to measured GSC/Bing/GA4 data and note indexing delay.

### Reference sources

- Google Search Central: https://developers.google.com/search/docs/crawling-indexing/canonicalization
- Google sitemaps: https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap
- Google people-first content (financial YMYL): https://developers.google.com/search/docs/fundamentals/creating-helpful-content
- IndexNow key and ownership: https://www.indexnow.org/faq
