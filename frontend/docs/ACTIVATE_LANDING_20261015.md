# Connect the existing landing to the actual app — 15 October 2026

## Why users saw no landing

Base: main `e727498c9481cdcb94f06b6f429933224f9c5b08`, including merged pricing PR #90 and landing PRs #81/#86. The marketing implementation existed in `landing/`, but the deployed finance application routed `/` to its protected Dashboard. Its Docker/Vercel output contained only Vite. Merging a design PR therefore never made that marketing implementation the public entry.

This branch packages the **existing Next.js landing**, not a replacement design, into the finance frontend's production artifact. It adds no always-running marketing service, preview-origin proxy or new application dependency. Backend/data/schema/tenant permissions, payment order handling and provider credentials are unchanged.

## Requested light appearance

The latest requested appearance changes only marketing colors: white page/header/mobile navigation, light neutral cards, dark headings/body/links, visible dark focus rings and brand mark. Green accents and section colors, component/layout/animation behavior, actual product captures and the finance application theme remain intact. The landing browser theme color is white. Mobile and desktop contrast/overflow are checked against the rebuilt artifact.

## Route contract

| Request / action | Result |
|---|---|
| Public `/` | Temporary redirect to `/welcome/`; Nginx/Worker use a **relative** Location and drop the incoming query. Vercel controls platform redirect normalization/query handling; its existing no-referrer policy remains in place. Relative Location preserves HTTPS behind the existing Tunnel. |
| `/welcome/` | Exported Next.js landing HTML and hydration; no finance SPA, auth SDK or financial API bootstrap. |
| `/welcome/_next/static/*` | Namespaced content-hashed scripts, CSS and fonts; actual files only, missing files 404. |
| `/welcome/product/*`, `/welcome/emoji/*` | Existing self-hosted, licensed product screenshots and emoji, namespaced to avoid app asset conflicts. |
| Landing login/register/pricing/privacy/terms/support | Relative same-origin links into the existing real finance application. |
| `/dashboard` | Existing Dashboard, inside the unchanged ProtectedRoute / workspace layout. Anonymous users still go to login. |
| Successful local/Clerk/OIDC signup/login, setup completion | Protected `/dashboard`, or the existing validated internal `next` destination. A legacy explicit `next=/` maps to Dashboard. |
| Sidebar logos, command palette, denied module/admin/Agents routes | Protected Dashboard, rather than marketing. |
| Pricing's public Home action / client navigation to `/` | Crosses out of the SPA into the public landing. |
| Installed PWA | Same install identity (`id=/`, scope `/`), new start URL `/dashboard`. Old standalone installations launching `/` hand off to protected app after marketing hydration; no token or storage inspection and no auth bypass. |
| `/api`, `/mcp`, recovery/verification, SSO callback, invoice sharing | Existing application/proxy routes and guards retained. |

The public URL deliberately uses `/welcome/` so Next.js owns a clean asset/router namespace without moving the entire finance app or changing its API/callback origin. It is a real same-origin page, not an iframe or hosted demo.

## Build and deployment wiring

- `frontend/scripts/build-marketing.mjs` installs the existing pinned landing lockfile, builds Next.js with static export/basePath `/welcome`, and copies output to generated `frontend/public/welcome`. The normal frontend build includes it in `dist/welcome`; missing marketing output fails the build. Generated bundles/images are not committed.
- Normal standalone landing preview build remains supported. Export-mode app links are relative; public assets use the same explicit namespace. Product captures remain labelled synthetic sample data.
- Default Compose, dev/QA images and release workflow use **repository-root Docker context** with `frontend/Dockerfile` / `frontend/Dockerfile.dev`. The source stage copies only the two relevant source trees; root `.dockerignore` excludes environments, dependencies and generated builds.
- Nginx, Helm, Vite dev/preview, Vercel static routing and the existing optional Cloudflare Worker understand marketing versus app paths. Vercel also accepts the slash-normalized `/welcome` spelling without a loop. No DNS, Worker pin/route, deployment protection or production environment mutation is performed.
- Successful hashed marketing assets receive status-aware immutable caching in nginx/Worker; 404/error assets get no-store. Public HTML and all app/API privacy boundaries remain conservative. Vercel retains its existing no-store header; no broad rule that accidentally caches error responses is added.
- Existing strict CSP remains artifact-bound: exact Next.js inline script hashes and SRI on executable/preloaded scripts are included, alongside existing finance script integrity. No unsafe-eval or permissive Trusted Types policy is introduced. PWA release digest includes final marketing bytes.
- Marketing is excluded from authenticated app-shell navigation caching. The service worker installs only the validated `/index.html` finance shell, never the public landing, proxy login or recovery HTML. Explicit update approval and API/write exclusions remain intact.

## Verification

Local acceptance before publication:

- Combined Next.js export + Vite production build, TypeScript, whole-frontend zero-warning lint and final artifact/SRI/discovery/source-map checks.
- Full frontend suite: **939 tests / 122 files passed**. Navigation checks include default Dashboard, legacy root return, preserved annual pricing return, blocked protocol-relative external return, Clerk callback replay, and denied module/role behavior.
- Existing four landing source contracts and eight Worker privacy/path tests passed. All generated public marketing assets are covered by Worker path tests.
- Real nginx strict-CSP Chromium: marketing and existing login at 320/390/768/1024/1440 combinations; landing FAQ hydration, same-origin CTAs, pricing handoff, anonymous dashboard gate, no marketing API requests, zero overflow/axe violations and no blocked scripts. Legacy standalone handoff is checked after its final build.
- Actual Chromium service worker: desktop/mobile emulation icons, offline deep links, API/token/document cache exclusion, update isolation/approval and rejection of proxy-login HTML passed.
- Signed-in contract smoke renders Dashboard, Transactions and Pricing without boundary errors/overflow. These responses are local synthetic fixtures; they are never bundled as product data.
- Dedicated `Connected Public Landing` workflow verifies production nginx + strict CSP in Chromium, Firefox and WebKit, and uploads screenshots/receipts. General repository CI still verifies PWA, recovery/MCP proxy privacy, secret hygiene, migrations and applicable Helm checks. Final links/conclusions are recorded on the PR.

Preview/browser checks do not certify real Google/MFA/bank/payment/provider operations, physical iPhone/Android or VoiceOver/TalkBack. Previous all-demo Space UI review limits remain recorded in landing docs; this integration does not claim a new exhaustive video review.

## Activating the deployed site after merge

Merging source alone cannot replace an owner-hosted running container. Deploy/rebuild **only the frontend** in its existing deployment context, preserving current Compose project, environment, public keys and backend/Tunnel configuration.

For the existing default Compose checkout, from repository root with its original project/env flags:

```sh
docker compose up -d --build --no-deps frontend
```

For the hardened production stack using a pinned GHCR image, build/publish an immutable frontend release through the existing release workflow and update only that frontend image through the established deployment procedure. Do not launch a new Compose project or recreate backend/data volumes. If the optional Worker becomes the frontend entry, its immutable deployment pin must point to this combined artifact; do not keep a pre-integration pin. Existing Vercel project uses root `frontend/` and `npm run build`; the sibling `landing/` source is required in the repository checkout.

Read back `/` → public marketing, all namespaced asset MIME/404s, login/register/Pricing/support/legal links, protected Dashboard, recovery and API readiness after deployment. Keep a known previous frontend image/deployment for rollback. No production cutover is executed by this PR.

Preview/noindex defaults are retained; this is routing activation, not a search-indexability or legal/provider readiness declaration. For local Vite development, run `npm run build:marketing` once before `npm run dev` (the dev Compose override prepares it automatically).
