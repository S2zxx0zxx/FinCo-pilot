# Mobile performance: all 34 findings — 14 October 2026

Branch: `fix/mobile-performance-34-20261014`
Base: `f30f7222c00a4320b4aba42a645681dc487c662d` (latest main, Google signup PR87 merged).
Source report: https://pagespeed.web.dev/analysis/https-fincopilot-app/exsb63yjei?form_factor=mobile

This ledger preserves the user's complete 34-point scope. These are findings,
observations and acceptance checks, not 34 independent guaranteed defects.
Implementation and verification are one branch; live acceptance is tracked
separately and must not be claimed complete from unit-test success.

## Preservation contract

No page, chart, avatar, supplied artwork, locale, financial record, account,
tenant boundary or authentication requirement is removed. No database migration,
secret change, domain cutover or main-branch merge is part of this change.
Original fonts remain; disjoint font subsets retain their complete cmap coverage.
Static caches do not include financial APIs or credential-bearing recovery pages.

## Baseline and provenance

- Local latest-main production build succeeded before changes.
- Signed-out /login baseline, Chromium 141, widths 390 and 1440, synthetic GET-only
  public configuration: 2,250,986 decoded resource bytes and 49 JavaScript requests.
  This is not the 6,073 KiB development-mode PageSpeed report, and not real login.
- Vercel project fincopilot-web reports READY production deployment on exact base
  f30f722. Dockerfile also already uses production Vite build + nginx.
- Public custom domain returned Cloudflare HTTP 530 during this request.
  Read-only Cloudflare verification established the actual path: apex DNS
  points to tunnel `dc9f949a-6702-4222-844f-51e1b2f34031` (`fincopilot-origin`),
  whose version-6 ingress forwards fincopilot.app to
  `http://host.docker.internal:3000`. Tunnel status is DOWN with zero connections.
  This domain does not currently route to the READY Vercel deployment.
  Default Compose formerly exposed Vite development at host port 3000.
  This branch changes only the frontend to built nginx at the SAME host port.
  No DNS, tunnel configuration or Vercel production settings were modified.
- New dev allowed-host guard removes implicit fincopilot.app access. Deliberate
  public development needs FINCO_ALLOW_PUBLIC_DEV_SERVER=true and a specific host.
  Do not use this opt-in as the fix for production.

## Resumed completion — phase 2

The interrupted worktree was recovered without overwriting the branch. Phase 1
is commit e43a837; the changes below are the remaining implementation on the same
branch. Main is unchanged. The earlier DOWN/530 observation is historical:
during phase 2 the existing Tunnel briefly became healthy with four
connections and served HTTP 200, but its frontend still served Vite development.
The resumed Cloudflare API check now reports DOWN with zero connections again.
The existing DNS and Tunnel ingress have not been changed.

- Clerk provider and Clerk login/register/guard implementations now load at
  explicit boundaries; existing tenant and auth options are preserved. The same
  live public Clerk publishable key is configured only for this preview branch.
- Anonymous auth pages no longer fetch unused billing catalog/campaign data;
  pricing, authenticated entitlements and upgrade-dialog behavior remain tested.
  Upgrade UI loads when first requested and remains mounted for close animation.
- Desktop blur effects retain their original parameters using LazyMotion.
  A build-derived Inter Latin body-font hint reduces the text-render waterfall.
- SRI hashes are computed from final on-disk Vite bytes for entry scripts,
  modulepreloads and the hinted login chunk. The PWA hashes the finalized HTML.
  An independent build guard rejects stale integrity. Artifact-bound nginx and
  Helm strict CSP enforce/report-only profiles are available; compatibility
  remains default pending real Clerk/OAuth/payment and edge-RUM acceptance.
  Trusted Types enforcement remains off; no permissive default policy is added.
- Cloudflare scoped cache safety rules and HTTPS HSTS/nosniff have been applied
  and read back. Exact before/applied/rollback policy is in
  cloudflare-mobile-policy-20261014.json. No unrelated zone rules were replaced.
- Existing Cloudflare RUM was already enabled; it is retained. The pre-rollout
  24-hour aggregate at 2026-10-14T12:18:42.565Z contains 214 metric events,
  LCP samples 137, INP 63 and CLS 145. p75 LCP 12.416 s, INP 272 ms,
  CLS 0.003. LCP/INP API values are microseconds. Events are not visitors;
  these historical dev-origin results do not measure the optimized deployment.
- A streaming Cloudflare frontend proxy is implemented and privacy-tested.
  Its immutable verified Vercel artifact serves public assets while exact
  same-origin API requests continue through the unchanged Tunnel. Frontend
  subrequests omit cookies, authorization, query tokens and private paths.
  It has no storage bindings or request logs. Rollout remains a separate
  acceptance gate: implementation is not evidence of deployment.

Phase-2 verification before interruption: 121 Vitest files / 920 tests passed,
360 UI route/viewport/theme visits passed, PWA privacy/offline/update checks passed,
and strict CSP enforcement passed eight local viewport/motion cases with zero
blocked resources and zero axe violations. Entry static graph is 214,229 gzip
bytes without Clerk config and 214,289 with the existing public Clerk config,
17 chunks, below the 300 KiB budget. Native Worker privacy tests: seven passed.
After restoring the browser removed during session interruption, the configured
Clerk anonymous UI check passed all eight viewport/motion cases, with Google and
email controls present and zero axe violations. The browser origin was the
existing authorized fincopilot.app host; only app GETs were fulfilled by the local
nginx/synthetic API fixture, while Clerk HTTPS requests used the real tenant.
The same eight configured-Clerk cases also passed strict CSP enforcement
with zero blocked resources. This is not a real sign-in, callback, bank or
payment transaction. Live edge-injected RUM still needs strict-policy acceptance.

Latest isolated phase-2 local lab (synthetic public config, not live PSI):
performance 77, accessibility 100, Best Practices 100, SEO 100, FCP 3.183 s,
LCP 4.027 s, TBT 219 ms, CLS 0, transfer 447,843 bytes. It preceded the final SRI
metadata pass; no performance claim is made for the configured provider profile.
Scores vary; LCP still exceeds 2.5 s and TBT exceeds 200 ms.

## 34-point ledger

Status: **Implemented** / ✅ means committed source and local verification, not live
production acceptance. **Measured** describes the controlled signed-out fixture.
**External** needs the disconnected origin, real providers, devices or traffic.
No claim that 34 independent issues are all resolved or that performance is 100.

| # | Issue / location | Why / engineering action | Evidence and remaining acceptance |
|---|---|---|---|
| 1 | Dev assets served by default Compose frontend | Dockerfile.dev + source mounts exposed Vite through host:3000. Default now builds production Dockerfile/nginx, host port stays 3000; explicit dev override retains development. | ✅ Implemented; Compose configurations validated. CI production build and real nginx-container proofs pass. Owner-hosted frontend rebuild and Tunnel restart remain external.|
| 2 | HMR/WebSocket errors on public domain | Development client expected a local HMR socket. Production HTML has no Vite client/source entry; public dev host requires explicit opt-in. | ✅ Implemented; build gate and nginx browser checks pass. Live retest external.|
| 3 | Unminified JavaScript | Vite production already minified; wrong serving mode caused the source report. Enforce actual production output rather than add redundant minifier. | ✅ Build passes; hashed JS, no public sourcemaps or dev HTML.|
| 4 | Excessive initial transfer | Private shell, desktop decoration, locales and whole fonts loaded initially. Split actual import boundaries and fonts. | ✅ Measured signed-out payload reduction; comparison below. No resource deleted.|
| 5 | Unused initial JavaScript | Signed-out page statically imported private application code. Lazy AppLayout remains inside ProtectedRoute. | ✅ Phase-2 entry graph 214,229 gzip bytes, 17 chunks; 300 KiB gate. Remaining library overhead retained.|
| 6 | Recharts on login | AppLayout pulled chart modules into public entry. Preserve charts, load after authenticated shell. | ✅ Build traversal/browser resource checks exclude CartesianChart/private shell from signed-out login.|
| 7 | Motion/decorative loading | Hidden desktop brand still imported effects on mobile. Load AuthBrandPanel only at existing 1024px breakpoint. | ✅ 390/768px checks exclude brand chunk; effects remain on desktop. Shared form Motion retained.|
| 8 | Icon library overhead | Import graph rather than deleting icons; retain Vite tree-shaking and private shell isolation. | ✅ Build gate, 360 route checks pass. No claim that every used icon byte can be removed.|
| 9 | Markdown/chat overhead | Private shell imports markdown/chat dialogs. Move shell to lazy protected boundary. | ✅ Browser checks exclude chat-panel; all private components remain in repository/build.|
| 10 | Locale bytes | Portuguese was eager alongside English. Load selected non-English locale before i18nReady. | ✅ Locale tests pass, all 15 locale files preserved; Portuguese nav labels retained.|
| 11 | Slow LCP | Development delivery + excess bytes + dependent loading. Production serving, route hint, font subset and import isolation. | ✅ Local LCP measured below; live PageSpeed external. No promised production score.|
| 12 | Delayed LCP paragraph / configuration card shift on login | Text waited for JS/font/render and a short card grew when auth methods arrived. Build-derived public login/font hints start early; reuse existing route loader during actual auth-config wait, then render final controls. | ✅ Delayed-config regression test added; no artificial delay or changed auth admission. Settled content unchanged; final local LCP/CLS below.|
| 13 | Slow Speed Index | Late first useful public rendering. Reduce initial code/font work while preserving UI. | ✅ Controlled local Speed Index below; no deleted UI.|
| 14 | Main-thread work | Parsing/evaluation of heavy private dependencies. Code splitting at actual boundaries. | ✅ Lighthouse main-thread comparison recorded below; retained provider/runtime overhead remains.|
| 15 | TBT / long tasks | Excess initial evaluation blocked main thread. Keep optional Sentry/vitals lazy; split shell. | ✅ Local TBT measured below; field INP requires real traffic.|
| 16 | Critical dependency chain | Login is a lazy route reached after entry. Build-derived public module/font hints reduce waterfall. | ✅ Production hint targets actual hashed outputs; dependency chain still exists, not claimed eliminated.|
| 17 | Full heading fonts | Whole 162,732-byte semibold font on Latin login. Disjoint Latin/Europe/other WOFF2 subsets, hashed asset caching. | ✅ Latin semibold 67,648 bytes; generator checks all 2,512 codepoints, outlines and advances for all 4 weights. Originals/OFL retained.|
| 18 | Cache/compression policy | Static content and credentials need different policies; nginx add_header inheritance could drop security. | ✅ Actual nginx checks: hashed assets immutable, HTML/SW/recovery/API no-store, missing files 404; gzip enabled. Helm/Vercel source validated; live edge external.|
| 19 | Forced reflow | Browser layout work must be measured, not blindly rewrite UI. Preserve behavior and inspect lab trace. | ✅ Latest local forced-reflow audit passes; this does not certify all interactions/routes.|
| 20 | Cloudflare legacy beacon | Source report includes edge-injected external analytics. Not application code; removal would change analytics. | ⚠️ Provider retained; existing Cloudflare RUM collector/rules verified enabled. Historical field aggregates recorded above. No claim of controlling the vendor’s legacy bundle.|
| 21 | Missing main landmark | AuthShell used a div. Replace outer element with semantic main without changing classes/layout. | ✅ One main; axe WCAG AA zero violations across 8 screen/motion cases.|
| 22 | Missing description | index.html lacked summary metadata. Add honest app description. | ✅ Production HTML guard and local SEO audit pass.|
| 23 | robots timeout/invalid discovery | Missing static file/fallback and unavailable origin. Add robots, block private endpoints, keep catalog discovery in HTML. | ✅ Actual nginx text/plain 200; local Lighthouse robots audit passes. Live timeout requires restored tunnel.|
| 24 | llms.txt timeout | Static public app description absent/unavailable. Add factual llms text without private data. | ✅ Actual nginx text/plain 200; no SPA HTML fallback. Live fetch external.|
| 25 | Catalog HTML/schema error | Machine route returned shell/incorrect content. Add well-known static ARD v1 catalog + alias, entries=[] for no verified public capability. | ✅ Actual Lighthouse 13.5 schema validator accepts; nginx application/json 200. No fake agent API advertised.|
| 26 | CSP missing | Add enforced compatibility baseline, object/base/frame restrictions, provider HTTPS access. | ✅ Headers verified. Default compatibility policy retains unsafe-inline/https. Artifact-bound strict profile passes eight default and eight configured-Clerk anonymous cases; real callbacks/payments and edge RUM acceptance remain. Not a strict-XSS certification.|
| 27 | HSTS missing | Add max-age=31536000 on trusted forwarded HTTPS; no indiscriminate subdomain/preload changes. | ✅ Actual nginx HTTPS-forwarded header pass; absent on plain HTTP. Cloudflare HTTPS HSTS/nosniff policy applied and read back; frontend rollout acceptance tracked separately.|
| 28 | COOP missing | same-origin-allow-popups protects baseline while allowing existing OAuth/payment popups. | ✅ Actual header pass; full cross-origin isolation not enabled. Real Google/Clerk/payments external.|
| 29 | Frame/clickjacking protection | Add X-Frame-Options DENY and CSP frame-ancestors none across locations. | ✅ Actual HTML/JS/SW/discovery header tests pass; embedding deliberately disallowed.|
| 30 | Trusted Types missing | Enforcement can break provider/editor/PDF DOM sinks. Add explicit nginx/Helm opt-in report-only staging mode; default off to avoid unsolicited inspector issues. | ⚠️ Reporting configuration present; NO enforcement/completion claim. Real compatibility and reviewed policy external.|
| 31 | Filter/blur animation observation | Deleting effects would change UI. Preserve animation and load hidden desktop component only when displayed. | ✅ Settled before/after screenshot comparison 0 differing pixels at 390/1440; reduced-motion browser checks pass.|
| 32 | Keyboard/assistive technology | Preserve visible tab sequence; animated heading generic aria-label caused a desktop axe issue. Use sr-only text + aria-hidden animated words. | ✅ 8 axe cases zero violations, keyboard order pass. Physical TalkBack/VoiceOver external.|
| 33 | Structured data | Add factual WebApplication JSON-LD, no invented prices/reviews. | ✅ Build JSON parse/type/name checks and local SEO pass; rich-result eligibility not promised.|
| 34 | No field vitals / CrUX | Traffic cannot be simulated into CrUX. Add explicit opt-in lazy CLS/INP/LCP local summary events without URL/query/account/financial data. | ⚠️ Unit tests pass; no collector/network destination invented. Existing Cloudflare RUM verified and pre-rollout p75 aggregates recorded above. New-deployment field acceptance and CrUX require subsequent real traffic.|

## Final paired local laboratory result

Latest-main production baseline and final branch were measured sequentially with
the SAME synthetic public GET API, local nginx templates, Lighthouse 13.5.0,
Chromium 141, mobile emulation, default simulated throttling (CPU 4x/network RTT
150ms). These are single-run laboratory measurements; scores vary with runtime
conditions. They are NOT the saved PageSpeed development-mode score of 37 and
NOT a live-domain result. This pair does not test configured external providers.

| Metric | Latest-main production baseline | Final branch |
|---|---:|---:|
| Performance | 32 | 71 |
| Accessibility | 98 | 100 |
| Best Practices | 100 | 100 |
| SEO | 82 | 100 |
| FCP | 14.40 s | 3.62 s |
| LCP | 14.80 s | 4.43 s |
| TBT | 1,142 ms | 265 ms |
| CLS | 0 | 0 |
| Speed Index | 14.40 s | 3.62 s |
| Network payload | 2,283,677 bytes | 488,777 bytes (~79% less) |
| Main-thread work | 7610 ms | 1405 ms |

A preceding optimized run exposed intermittent CLS=0.126 during auth-config
arrival; the final change retains the existing route loader during that real
wait, then renders the actual selected sign-in methods. Final run CLS=0; one run
does not certify every provider/network scenario. Final LCP remains above 2.5 s,
TBT above 200 ms and performance below 90: residual framework/provider/runtime
and network work remains. Critical dependency-chain/unused-JS opportunities are
not asserted eliminated. A more aggressive rewrite of auth/providers requires
its own compatibility evidence rather than deleting UI or disabling features.

Machine-readable summary: [mobile-performance-20261014-lab.json](mobile-performance-20261014-lab.json).
Reproduce using the production build and `scripts/verify-nginx-browser.mjs` with
NGINX_BIN plus optional PERF_TOOLS_ROOT/LIGHTHOUSE_CHROME_PATH. For the baseline,
set FINCO_PERF_DIST and FINCO_PERF_TEMPLATE to preserved base production output
and nginx template; FINCO_PERF_LAB_ONLY=true skips browser/header assertions and
is labeled accordingly. Run full browser/header checks separately.

## Engineering decisions and research

- Vite production builds already minify. Lazy-load the private AppLayout at the
  protected route rather than force manual vendor chunks that can preload charts.
  Build manifest traversal follows static imports only; a 300 KiB gzip entry
  budget and forbidden private/decorative entry dependencies fail the build.
- AuthShell keeps the actual UI and uses a main landmark. Desktop brand content
  loads only at its existing lg breakpoint; all supplied effects/avatar remain.
- English fallback remains immediate. Selected locales, including Portuguese,
  finish loading before i18nReady; all 15 locale files and picker options remain.
- Open Runde is partitioned by disjoint Unicode ranges, preserving all 2,512
  original cmap codepoints for each weight. Latin semibold becomes 67,648 bytes
  from 162,732 bytes. Hashed CSS font outputs receive immutable caching.
- Discovery files are static and excluded from HTML fallbacks. Catalog uses the
  actual Lighthouse 13.5 ARD schema specVersion=1.0 and entries=[] because there
  is no verified unauthenticated agent capability to advertise. This does not
  grant access to authenticated financial APIs.
- Docker/nginx, Helm and Vercel receive compatible hardening and cache policies.
  Nginx location-level add_header inheritance is explicitly handled. COOP is
  same-origin-allow-popups for OAuth/payment compatibility. HSTS on nginx is
  emitted only behind an HTTPS forwarded scheme, without blindly including
  every subdomain/preloading HSTS.
- CSP retains HTTPS provider compatibility and existing inline-script behavior;
  an enforced policy alone is not a strict-XSS-policy certification.
  Trusted Types reporting is opt-in (default off) pending real Clerk/bank/PDF/editor acceptance.
  No permissive default Trusted Types policy is introduced to silence warnings.
- Web-vitals is explicit opt-in and lazy. Only bounded metric summaries are
  dispatched locally through finco:web-vital; no URL/query, DOM entries,
  financial/account data or stable session identifiers. Collector integration
  and field sample collection remain required; CrUX cannot be manufactured.
- Sentry stays opt-in/lazy and keeps existing financial privacy scrubber. Fix
  statically analyzable import so production can resolve its package chunk.

Primary sources:
- https://vite.dev/guide/build
- https://vite.dev/config/build-options
- https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Cross-Origin-Opener-Policy
- https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Security-Policy
- https://developer.mozilla.org/en-US/docs/Web/API/Trusted_Types_API
- https://developer.chrome.com/docs/lighthouse/agentic-browsing/llms-txt
- Lighthouse 13.5.0 npm package, third-party/ard/spec/schemas/ai-catalog.schema.json
  (upstream schema pinned b76f235a8f461876ad4f1e77abd0eb0eb302b48d)
- https://web.dev/articles/vitals

## Remaining external acceptance

Restore the existing Cloudflare Tunnel connector and update its frontend before benchmarking the live domain. Its current DOWN/zero-connection state cannot be repaired by changing browser code; the origin operator must run the connector. Do not switch apex DNS to the unrelated Vercel frontend as a shortcut.
Verify real Google/Clerk login and bank/payment flows with the deployed configuration.
Strict CSP and Trusted Types enforcement require provider-specific acceptance.
Physical Android/iPhone and TalkBack/VoiceOver checks require actual devices.
Connect a reviewed telemetry collector and collect real traffic for field metrics.
No improved production score is asserted until the changed branch runs at that origin.


## Verification and safe rollout

- Frontend Vitest: 119 files / 912 tests passed; typecheck, production build and
  zero-warning lint passed. Full dependency audit: zero vulnerabilities.
- UI: 45 routes × 4 viewport widths × 2 themes = 360 visits, no failures.
- Actual nginx: 8 viewport/reduced-motion cases, zero WCAG A/AA violations;
  header/cache/discovery/404 assertions and preserved keyboard order passed.
- PWA browser suite: desktop/mobile emulation, real service worker, cache privacy,
  offline deep links, waiting update isolation and accepted update passed.
  Synthetic public API fixtures do not certify real authentication/bank/payment.
- Compose default/dev/QA/production configs and Helm lint/render validated; rendered Helm nginx syntax passes. Recovery/MCP CI containers now mount the shared header include; their actual Docker checks run in GitHub CI.
  This host has no Docker daemon: an actual image build remains origin acceptance.
- No files are deleted, financial/backend data/schema unchanged. Browser screenshot
  comparison verifies settled login appearance; it cannot promise zero bugs in
  every provider/device/session.

On the **existing origin**, preserve its current environment/public provider keys,
checkout this branch, then rebuild **only** frontend:

```sh
docker compose up -d --build --no-deps frontend
```

This retains host port 3000, backend and data volumes. Do not run `down -v` or
migrations for this frontend change. Run/restore the existing cloudflared connector
using the origin's existing service configuration; no token is embedded here.
Check public HTML has hashed `/static/` files and no `@vite/client`; check API,
real Google/Clerk signup/login/callback, banks/payments, PWA update and recovery.
Then rerun the supplied mobile PageSpeed URL. Rollback: restore the previous
frontend checkout/image without changing data volumes. Main is not merged by this
branch implementation.

## Final publication and owner handoff

- Source commit: 6bcb6584afaa3468337284b5226bb957961e200a; all seven CI
  jobs passed, plus the separate Frontend Edge Privacy workflow. Frontend CI
  includes zero-warning lint, dependency audit, build/tests, real Chromium PWA,
  real nginx-container recovery privacy and MCP forwarding proofs. The Backend
  Tests job correctly skipped its suite because no backend code changed.
- Vercel deployment dpl_BFvXna1Bc1CkUcvfgo8fsK8yKJ92 is READY on that exact
  source SHA in fincopilot-web, as a preview with the existing public Clerk key.
  https://fincopilot-61zf7hlwz-s2zxx0zxxs-projects.vercel.app
  Direct HTTP checks verify actual script SRI and public-file MIME types. This
  preview is not a functioning production backend or a new Clerk-authorized
  hostname; full flows must be checked at the existing app host.
- Cloudflare Worker fincopilot-production-frontend is uploaded and pinned to
  that immutable artifact. workers.dev and preview URLs are disabled, it has
  no secrets/storage/logging bindings, and zone routes remain empty. No live
  cutover was performed: the existing Tunnel has zero active connections.
- Deployment receipt: mobile-performance-20261014-deployment.json. Source and
  receipt commits intentionally differ; only the tested source SHA is pinned.

| Owner-required acceptance | Exact remaining action | Reason it cannot be certified here |
|---|---|---|
| ❌ Existing origin availability (#1–2, #11, #18, #23–25) | Restart the existing cloudflared service/container with its current configuration; keep backend and origin running. | Cloud API cannot execute on host.docker.internal or start the owner machine's connector. |
| ❌ Origin frontend rollout (#1–2) | Apply this branch in the existing deployment context, preserve Compose project/env/public Clerk keys, then rebuild ONLY frontend with `docker compose up -d --build --no-deps frontend`. Check host port3000 before publishing traffic. | No remote host shell is connected. Do not use compose down/volumes, start a new backend, migrate a DB or replace provider secrets. |
| ❌ Real provider flows (#26, #28, #30) | Test existing Google signup/login/callback, local auth/MFA/recovery, bank connect and test-mode payment with owned test accounts. | Anonymous UI and fixtures cannot certify account/provider transactions; no real money operation was performed. |
| ❌ Strict CSP / Trusted Types rollout (#26, #30) | Use artifact-bound strict/report-only profiles on staging, retain RUM, inspect provider/editor/PDF/payment violations, review sink policies before enforcement. | Anonymous strict Clerk passes; financial flows and edge-injected RUM are not fully certified. TT remains explicit report-only opt-in, default off. |
| ❌ Physical accessibility/PWA (#32) | Test real Android/iOS installation, TalkBack/VoiceOver and keyboard through authenticated pages. | Browser emulation does not replace physical assistive technology. |
| ❌ Field outcomes (#11, #15, #20, #34) | After origin rollout, run live mobile PageSpeed and collect post-rollout RUM/CrUX traffic. | No fabricated score/INP/CrUX sample; historical RUM is from the former dev origin. Vendor legacy beacon implementation is outside app control. |

If the edge-proxy rollout is chosen instead of rebuilding the origin frontend,
first restore and verify that SAME backend/Tunnel, then bind only the documented
Worker Route. The uploaded Worker alone does not serve fincopilot.app. Do not
move DNS to the Vercel preview: its standalone API rewrite is not the existing
Tunnel backend. Existing optional MCP availability must be checked on the
origin; HTML fallback is rejected rather than advertised as a working API.

A final HTTP probe found Vercel's broad `/static/(.*)` immutable header also
applied to nonexistent JS 404s. Commit 6bcb658 removes that broad preview header
and makes the default no-store. Status-aware immutable caching remains in nginx
and the Worker. This change prevents a missing deployment chunk from being
retained for a year. It changes caching, not UI or features.

Final cache acceptance on 6bcb658: live preview index/recovery/SW and missing
static 404 are no-store; all 17 entry/modulepreload SRI resources match delivered
bytes and the deployed public Clerk key matches the existing tenant. The Worker
is re-pinned to this final READY artifact; readback confirms empty zone routes
and disabled workers.dev/preview URLs. All seven CI jobs and the separate Worker
privacy workflow pass for this final source SHA. No live-domain score is claimed.
