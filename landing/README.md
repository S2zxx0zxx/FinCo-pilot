# FinCo-Pilot — Ant Design marketing landing

The current homepage uses Ant Design 6: ConfigProvider tokens, Buttons, Cards, Tabs, Collapse, Steps, Drawer, InputNumber, Statistic, Progress, Alert, Tag, Flex and Divider. The build compiles a whitelist of Ant component CSS from the shared theme. Ant zero-runtime mode avoids regenerating component CSS during hydration; AntdRegistry includes first-screen token variables in server HTML. The authenticated Vite application remains separate.

The design is white, ink and Ant blue, with self-hosted fonts, real synthetic-data product captures, a local arithmetic illustration, six feature explanations, import guidance, privacy boundaries and ten FAQs. Motion is subtle and respects reduced-motion preferences. No homepage Space UI, sound, avatar or motion dependency is loaded. Historical component files and licenses remain for provenance.

## Run and verify

Use Node 22+ and `npm ci` inside `landing/`. Run `npm run dev` for development and `npm run verify` for source tests, TypeScript and production build. Against a running production build, `npm run test:browser` verifies nine widths, keyboard, demo edge states, drawer focus, FAQ, WCAG checks, product images and no external requests. `node tests/discovery-browser.mjs` covers supporting documentation. Existing CI runs Chromium, Firefox and WebKit.

The combined Vite build runs `frontend/scripts/build-marketing.mjs`, exporting this package to `/welcome/`. Keep all application CTAs in `lib/links.ts` and public asset/document paths in `lib/asset.ts`. The installed-PWA handoff remains intact. Do not configure credentials in this marketing package.

## Publication

Preview builds remain noindex, with excluded discovery inventory. Existing production publication controls, canonical URLs, root discovery, restricted crawlers and static-export gates remain unchanged. `node scripts/verify-discovery.mjs` must run with the same environment used for its build. See `lib/marketing.ts` and the existing growth evidence for release policy.

See `docs/ANT_DESIGN_REDESIGN_20261017.md` for the audit, source-backed content map, design decisions and verification evidence. Earlier Space UI and growth documents are historical evidence, not descriptions of the new homepage UI. Original product captures are documented in `docs/PRODUCT_CAPTURE_PROVENANCE.json`; they do not verify live authentication or bank connections.
