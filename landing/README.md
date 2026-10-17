# FinCo-Pilot — HeroUI v3 marketing landing

The homepage uses HeroUI React and Styles 3.2.6 with React 19 and Tailwind 4. Native compound components cover Cards, Tabs, Accordion, Drawer, NumberField, ProgressBar, Alert, Chip, Button, Link, Label and Separator. Styles are compiled through the documented Tailwind-first CSS imports; there is no runtime provider or generated component stylesheet. Ant Design packages, registry, theme and extractor have been removed.

The visual system uses white, soft sage surfaces, forest accents, rounded cards, pill actions and self-hosted Open Runde. All sections have been restyled, including the application preview, local reserve illustration, six feature explanations, onboarding, sample import, privacy boundaries, ten FAQs and footer. Product captures use actual application screens with synthetic records. Motion respects reduced-motion preferences. The financial application remains separate.

## Run and verify

Use Node 22+ and `npm ci` inside `landing/`. Run `npm run dev` for development and `npm run verify` for source tests, TypeScript and production build. Against a running production build, `npm run test:browser` verifies nine widths, keyboard, demo edge states, drawer focus, FAQ, WCAG checks, product images and no external requests. `node tests/discovery-browser.mjs` covers supporting documentation. Existing CI runs Chromium, Firefox and WebKit.

The combined Vite build runs `frontend/scripts/build-marketing.mjs`, exporting this package to `/welcome/`. Keep all application CTAs in `lib/links.ts` and public asset/document paths in `lib/asset.ts`. The installed-PWA handoff remains intact. Do not configure credentials in this marketing package.

## Publication

Preview builds remain noindex, with excluded discovery inventory. Existing production publication controls, canonical URLs, root discovery, restricted crawlers and static-export gates remain unchanged. `node scripts/verify-discovery.mjs` must run with the same environment used for its build. See `lib/marketing.ts` and the existing growth evidence for release policy.

See `docs/HEROUI_REDESIGN_20261017.md` for the audit, source-backed content map, design decisions and verification evidence. Earlier Ant Design, Space UI and growth documents are historical evidence, not descriptions of the new homepage UI. Original product captures are documented in `docs/PRODUCT_CAPTURE_PROVENANCE.json`; they do not verify live authentication or bank connections.
