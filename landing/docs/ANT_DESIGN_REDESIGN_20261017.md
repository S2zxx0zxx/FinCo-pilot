# Ant Design landing redesign — 17 October 2026

## Audit and scope

Started from main `887eaee578c8766b5757c057473ed20c7ab6c52e` (PR #98 merged). Inspected recent PR descriptions, open work (#96/#94/#85/#60), full homepage and its imported UI, product captures, supporting public content, route/link helpers, metadata, publication policy, combined Vite export and CI. This branch does not pull unrelated open PR code.

TinyFish inspected `https://www.fincopilot.app/welcome/`, resolving to the apex welcome page. The previous page used Space UI, a generic headline, illustrative overview tabs, four feature cards, orbit art, avatar, opt-in sound and five FAQs. Product screenshots already existed and their capture provenance remains unchanged. Source was read before replacing the public page.

Provider reads confirmed Vercel `fincopilot-web` owns apex/www and its current production deployment was READY; Cloudflare zone is active and apex/www CNAMEs both point to `70e8c4aa1f97e5a4.vercel-dns-017.com`, DNS-only. No DNS, production environment, credentials, API, auth, billing or database changes are needed for this UI PR.

## Research

Reviewed official Ant Design introduction, theme tokens, Next.js integration and SSR documentation through TinyFish:

- https://ant.design/
- https://ant.design/docs/react/customize-theme/
- https://ant.design/docs/react/use-with-next/
- https://ant.design/docs/react/server-side-rendering/

Installed pinned `antd@6.6.6`, `@ant-design/icons@6.3.4` and `@ant-design/nextjs-registry@1.3.0`. Confirmed API types in installed packages. AntdRegistry extracts first-screen CSS into static/server HTML; ConfigProvider scopes tokens to public homepage. The layout uses CSS for page composition and responsive breakpoints; interactive UI primitives come from Ant, with no homepage Space UI or Motion imports.

## Design and implementation

White/ink/Ant-blue palette, self-hosted existing font, restrained 12px component corners, 44px controls and 8px-derived spacing. No neon wash, generated pictures, invented testimonials or unsupported certification claims. Native Ant components handle drawer, keyboard tabs, expandable FAQs, numeric input, cards, steps, alert, statistics and progress.

Replaced the entire homepage composition: wordmark navigation, hero, contextual balance illustration, capability strip, six feature cards, actual-product tab showcase, interactive reserve example, onboarding steps, import guide/sample callout, permission/privacy explanations, ten FAQs, final CTA and footer. Replaced homepage CSS and refreshed the social card/generator. Supporting public documents retain their content and usable styles.

The arithmetic illustration is deliberately labeled synthetic: 62,000 cash −22,000 bills/EMI −5,000 goal −chosen buffer. It supports empty, zero, positive and shortfall states, reads no account and makes no API request. It is not presented as the application's complete spending engine. No bank support, price, number of customers or financial outcome is invented.

## Content evidence map

| Homepage claim | Reviewed source |
| --- | --- |
| Manual accounts, account types/currency | `frontend/src/pages/accounts.tsx`, existing features guide |
| Safe-to-spend review/blocked estimates | `frontend/src/pages/spending-plan.tsx` |
| Recurring transactions | `frontend/src/pages/recurring.tsx` |
| Goals and dashboard context | `frontend/src/pages/dashboard.tsx` |
| Loan/EMI planning | spending-plan link to `/loans`, existing loan implementation |
| File formats, preview and QIF/duplicate limitations | `frontend/src/pages/import.tsx`, `backend/app/services/import_service.py`, existing import guide |
| Product captures contain synthetic records | `landing/docs/PRODUCT_CAPTURE_PROVENANCE.json` |
| Optional providers/modules depend on configuration and plan | existing public feature/how-it-works content and app modules |

All existing app destinations remain in `lib/links.ts`; docs/assets use `landingAsset`. PWA installed-app handoff, four-page canonical inventory, noindex/publication controls and crawler policy are preserved. Historical unused source components/licenses remain for provenance, but are not imported into the new homepage.

## Verification

See the final verification receipt below (updated before delivery). Browser test assertions were migrated from removed Space UI tabs/sounds/orbits to the new Ant interactions, retaining nine widths, CTA checks, keyboard, FAQ, accessibility, synthetic screenshots, no-JS, reduced motion and no-third-party-request boundaries. Added empty/zero/shortfall demo checks and CSV download acceptance. Supporting-document browser checks remain intact.

A local initial browser setup required browser downloads and a fresh Next cache; attempts were not counted as successful acceptance. The first tab test exposed decorative icon accessible names; icons are now hidden from assistive technology. No test timeout, retry or accessibility threshold was weakened.

## Release

Owner reviews and merges. PR preview is review-only; do not change production hosting or enable indexing for this redesign. Production sign-in, data isolation and separate security blockers are not certified by marketing QA. Revert this scoped landing commit and rebuild to roll back; no schema/data migration exists.
