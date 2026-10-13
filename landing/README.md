# FinCo-Pilot — isolated Space UI Next.js landing

Marketing only. This package does not replace or import the authenticated Vite app, FastAPI runtime, financial data or authentication.

## Development

- Node 22; from landing/: npm install; npm run dev; npm run verify.
- Root directory for any separate preview Vercel project: landing.
- Preview builds are **noindex**. Only explicit `NEXT_PUBLIC_MARKETING_INDEXABLE=true` in a Vercel production deployment enables indexing after domain ownership and URL strategy are approved.
- The CI-generated reviewed package-lock.json is committed; CI now uses deterministic npm ci.
- Public-only environment variable NEXT_PUBLIC_FINCO_APP_URL points to the existing authenticated application origin. Default: https://fincopilot.app. Never configure secrets or provider keys here.

## Visual scope

- Responsive Next.js App Router page with navigation, Space UI motions, headline, interactive illustrative dashboard tabs, product features, access-control narrative, onboarding steps, privacy, FAQ and working anchors.
- All sign-in, sign-up, pricing, privacy, terms and support links target actual existing Vite routes via landing/lib/links.ts.
- The preview amounts and activity are illustrative; not real account data, user counts, savings promises or conversion statistics.
- No third-party analytics, fake logos, testimonial quotes, email collection, auth token handling or finance API requests.

## Space UI

Direct-source MIT adaptations from https://github.com/usespaceui/ui: Button, Badge, Card, Accordion, Spinner, Link, BlurRevealText, ProximityGrid, Animoji. Preserve SPACEUI-LICENSE.txt. Squishmoji React is the local procedural decorative avatar; not a customer identity. Tabler icons follow Space UI composed-component conventions; the original FinCo logo comes from frontend/src/components/finco-logo.tsx.

## Validation before merge or production

1. Final-head GitHub Landing Next.js CI: install, source tests, TypeScript, Next production build, npm audit; also existing repository CI.
2. Keep the reviewed npm lockfile pinned; CI uses npm ci and the exact PR head must pass.
3. Pass the actual Chromium browser job (320/375/390/768/1024/1440 responsive checks, keyboard, FAQ, menu, interactive tabs, reduced-motion); then deploy private/isolated landing preview without changing the apex domain or finance application. Verify 320/375/390/768/1024/1440 mobile and desktop layouts, actual touch and keyboard navigation, FAQ, demo tabs, CTA routing, focus management, contrast, screen readers and reduced motion.
4. Measure real performance (LCP/INP/CLS), long tasks, network requests and any third-party asset loading on representative mobile.
5. Review canonical URL, metadata, robots, domain ownership, CSP and cache policy against final deployment hostname.
6. Resolve previously verified production API readiness (503) and homepage (530) before making any conversion or login-live promise.
7. A proposed main-domain promotion must first separately migrate/verify original app origin, API proxy, OAuth callbacks, email recovery links, payments and login routes. No cutover here.

No production deployment, domain mutation, database migration or main-branch merge is part of this draft PR.


## Independent completion work

See docs/IMPLEMENTATION_BLUEPRINT.md for exact source mapping and showcase evidence, docs/CATALOG_DECISIONS.json for all 265 assessed entries, docs/PRODUCT_CAPTURE_PROVENANCE.json for actual-source sample captures, docs/PERFORMANCE_BASELINE.json for the lab run and docs/RELEASE_ACCEPTANCE.md for all thirteen requested steps and honest external gates.

Fonts are self-hosted Latin/currency subsets with next/font/local and optional display to avoid late text repaint on slow mobile links. The originals' SIL OFL notice remains. Compass artwork is Fluent/Microsoft MIT, self-hosted with its license. Sounds start off, load only on explicit user opt-in, and follow reduced motion; no delegated global sound binding.

Browser tools (Playwright, axe-core, Lighthouse) are pinned in the lockfile; CI uses npm ci and a Chromium/Firefox/WebKit matrix. Review scripts/test artifacts are not marketing customer data. The original app screenshots use synthetic fixture accounts and cannot demonstrate production authentication, bank connections or financial accuracy.

## 13 October refinement

See docs/DESIGN_SELECTION_20261013.md and docs/SPACEUI_PREVIEW_REVIEW_20261013.json for current preview outcomes and exact source selections. Meter, Timeline, Separator and callback-ref useInView are direct-source adaptations. A fresh `.next` production build is used for final acceptance; stale local route caches must not be treated as evidence for a new revision. No added runtime dependencies.
