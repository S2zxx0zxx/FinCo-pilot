# Original roadmap #57 — PWA device acceptance

Engineering branch: `feat/57-pwa-browser-acceptance`, based on main `e7a35f585d008e7d04ac3014f20e48a564a44311`.

## Acceptance boundary

This milestone tests the production build in an actual Chromium engine on a
disposable localhost origin, with desktop and touch/mobile viewport contexts.
The API fixture is synthetic. Mobile emulation is **not** physical Android,
WebAPK installation, iOS Safari, or live HTTPS acceptance. Those gates remain
open until their observed results are recorded. No banking, payment, account,
Cloudflare Access, tunnel, production key or live deployment is modified.

## Audit findings and fixes

1. `android-icon-192x192.png` and `apple-touch-icon.png` had corrupt pixel streams:
   file signatures/dimensions looked valid, but Chromium image decoding and
   Pillow full decoding failed. Rebuilt both from the existing valid FinCo
   512px launcher image. This preserves the established brand geometry.
2. The fixed `finco-pwa-v4` worker/cache version did not change for frontend-only
   releases. A waiting worker could also overwrite active-release caches.
   Production builds now derive the worker version from the worker and all
   sorted build output bytes, including stable-URL icons and manifest. Waiting
   releases use separate caches; accepted activation removes earlier caches.
3. Successful navigation HTML, including recovery and proxy login pages, could
   replace the cached `/` document. Only installation writes the canonical
   public app shell. It must have the expected marker, HTML type, same-origin
   root URL and no redirect/query. Invalid shells fail installation rather than
   replace a functioning release. Query-bearing and recovery navigation,
   Authorization requests, exact `/api`, API descendants and MCP are network-only.
4. Native prompt events were reusable after dismissal and concurrent clicks
   could dispatch multiple prompts. A synchronous in-flight guard prevents
   duplicates; dismissal/failure consumes the single-use event gracefully.
5. Background worker update rejection could become an unhandled promise.
   Reconnect/visibility checks now handle failures without interrupting the app.
6. Removed conflicting white theme-color metadata; dynamic theme metadata
   remains authoritative for the existing light/dark application.

## Automated proof

`cd frontend && npm ci && npm run build && npx playwright install --with-deps chromium && npm run test:pwa`

`scripts/verify-pwa-browser.mjs` starts an ephemeral server itself and closes
browser contexts/server afterward. It uses actual built HTML, chunks, manifest,
icons, registration, browser Cache Storage and worker lifecycle. It asserts:

- desktop and mobile Chromium decode all manifest PNGs plus the Apple touch icon;
- the application login form really renders online; offline deep links render
  the public shell and connection notice without cached authentication config;
- synthetic financial/API/MCP responses and recovery query tokens never enter
  worker caches, and a route-specific proxy login page cannot poison the shell;
- a synthetic financial POST occurs once and is never queued/replayed offline;
- `/transactions` and `/reports` can load the public shell offline with a clear
  offline state (no claim that uncached finance records are available);
- a changed worker waits, preserves active caches and uses separate new caches;
- explicit acceptance changes the controller, cleans old caches and supports
  subsequent offline launch;
- an initial 200 proxy-login document is rejected as a shell.

CI runs this browser proof after the existing frontend build and unit suite.
Local final frontend regression: **862 tests / 109 files passed**; lint,
typecheck/build, npm advisory audit (0 reported), secret hygiene and the single
109-head migration chain passed. Final desktop/mobile browser proof also passed
with the actual online login-form assertion and rejected initial proxy shell.
Final publication evidence must record the exact CI head. No backend application
logic changed.

## Remaining device/release gates

| Gate | Required observed evidence | Status |
| --- | --- | --- |
| Physical Android Chrome | Real HTTPS install, launcher icon, standalone relaunch, logout, offline/reconnect and accepted update | Pending |
| Physical iPhone/iPad Safari | Share → Add to Home Screen, icon/safe areas, standalone relaunch, recovery links, offline/reconnect and update | Pending |
| Desktop Chrome/Edge install | Actual install/app-window launch and relaunch after browser restart | Pending |
| Live production origin | Correct public build/headers, reachable manifest/worker/icons and no Access HTML returned as assets | Pending |
| Authenticated device session | Real authorized user, background/resume, expired/revoked session, offline logout/cache isolation | Pending |
| Multiple open app windows | Explicit update with saved edits; old windows must not be treated as confirmed current versions | Pending |

At the last infrastructure audit the production tunnel was down and whole-domain
owner-only Access remained configured. Do not bypass that policy or pretend
localhost acceptance closes these live gates. Do not mark original #57 fully
device-accepted until the pending rows have actual evidence.

## Primary references

- https://web.dev/articles/service-worker-lifecycle — waiting/activation/cache lifecycle.
- https://web.dev/learn/pwa/update — deliberate update UX and old/new page compatibility.
- https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Guides/Caching — explicit worker cache boundaries.
- https://developer.mozilla.org/en-US/docs/Web/API/ServiceWorkerGlobalScope/skipWaiting — accepted waiting-worker activation.

Final feature CI, merge and main CI evidence must be appended here after they
are observed; a pending check is never a passed check.
