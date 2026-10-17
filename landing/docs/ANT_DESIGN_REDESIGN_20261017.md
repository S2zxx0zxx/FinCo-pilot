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

Installed pinned `antd@6.6.6`, `@ant-design/icons@6.3.4` and `@ant-design/nextjs-registry@1.3.0`. Confirmed API types in installed packages. Ant component CSS is compiled before dev/build from a whitelist through the official static-style-extract package. AntdRegistry retains first-screen token variables in static/server HTML; ConfigProvider scopes tokens to public homepage. The layout uses CSS for page composition and responsive breakpoints; interactive UI primitives come from Ant, with no homepage Space UI or Motion imports.

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

The verification receipt below distinguishes source validation from live application acceptance. Browser test assertions were migrated from removed Space UI tabs/sounds/orbits to the new Ant interactions, retaining nine widths, CTA checks, keyboard, FAQ, accessibility, synthetic screenshots, no-JS, reduced motion and no-third-party-request boundaries. Added empty/zero/shortfall demo checks and CSV download acceptance. Supporting-document browser checks remain intact.

A local initial browser setup required browser downloads and a fresh Next cache; attempts were not counted as successful acceptance. The first tab test exposed decorative icon accessible names; icons are now hidden from assistive technology. No test timeout, retry or accessibility threshold was weakened.

## Release

Owner reviews and merges. PR preview is review-only; do not change production hosting or enable indexing for this redesign. Production sign-in, data isolation and separate security blockers are not certified by marketing QA. Revert this scoped landing commit and rebuild to roll back; no schema/data migration exists.

### Verification receipt

- Functional source: `16e1f410dc9ddfd8a1f4acc520c82a84a86e33c5`, based on main `887eaee`. Later evidence-only edits do not alter its application code.
- Local: 18 source/publication tests passed; TypeScript and frontend ESLint passed. Normal Next and combined Vite builds passed. Combined verification confirmed `/welcome/`, same-origin destinations, marketing SRI/CSP, PWA identity/start URL, no source maps and 214,911-byte finance-app entry gzip against 307,200 budget.
- Actual local Chromium: nine widths (320/375/390/620/768/920/921/1024/1440), seven WCAG AA scans with zero violations, demo positive/zero/shortfall/empty states, keyboard tabs, drawer Escape/focus, FAQ open/close, responsive product images, sample CSV download, reduced motion, no-JS heading/style, skip link and no third-party requests passed. Supporting documents: 12 viewport/page checks plus three no-JS pages passed. Desktop/mobile full-page captures visually reviewed, including loaded real product screenshots.
- CI functional predecessor `9e3ac9`: combined CI [39030818134](https://github.com/S2zxx0zxx/FinCo-pilot/actions/runs/39030818134) passed; strict-Nginx public-entry Chromium/Firefox/WebKit [39030817964](https://github.com/S2zxx0zxx/FinCo-pilot/actions/runs/39030817964) passed. The first standalone drawer scan measured an opening transition and failed; wait for actual animation completion, preserving all contrast/focus assertions. Theme now uses a stable CSS-variable key and direct Ant module imports. Initial default Statistic contrast failure is corrected through description/tertiary theme tokens.
- Final functional-source CI: [Landing Next.js](https://github.com/S2zxx0zxx/FinCo-pilot/actions/runs/39031071342), [Combined CI](https://github.com/S2zxx0zxx/FinCo-pilot/actions/runs/39031071262), [Public entry](https://github.com/S2zxx0zxx/FinCo-pilot/actions/runs/39031071303). Consult the actual run conclusions and PR checks; these links are not claims that an in-progress run has finished.
- Live production baseline and PR preview are distinct. Initial web preview `645c1408` was READY and TinyFish confirmed the new homepage content at its exact preview URL. Final preview/build status remains independently visible in the PR checks; no production promotion or indexing switch is authorized by this receipt.
- Local mobile Lighthouse samples varied under concurrent testing (76 and 51 performance, zero CLS; corrected accessibility 100). This is a lab/environment observation, not a field speed improvement, and no 90+ or Core Web Vitals pass is claimed. Preview noindex lowers its SEO score by design. Real-user mobile performance remains a release measurement.

### Static CSS refinement

Mobile lab main-thread work prompted adoption of Ant 6's documented `zeroRuntime` mode. `lib/ant-theme.ts` is shared between build and runtime, with a stable CSS-variable key and hashed classes disabled. The pinned dev-only `@ant-design/static-style-extract@2.1.0` compiles only the 13 imported component families as explicit prefixes of the build/dev commands (not optional npm lifecycle hooks). It produces a reproducible ignored stylesheet; Next emits its optimized cacheable CSS. The first-screen HTML fell from roughly 288 KB to 90 KB, with inline style bytes falling from about 220 KB to 21 KB. These are local artifact sizes, not field speed claims.

An isolated static-CSS lab sample measured performance 60, accessibility 100, best practices 100, preview SEO 69 (deliberate noindex), LCP 3.49s, TBT 3.88s and CLS 0. Earlier runtime samples ranged 43–76. Samples are not controlled causal comparisons; mobile performance is not certified 90+ and remains a production measurement. No check or threshold was removed to improve the report.

Drawer accessibility now waits for the component's actual `afterOpenChange` lifecycle via `aria-busy`, instead of guessing from visibility or a fixed delay. This preserves focus and contrast checks across browser engines. Final PR checks/preview must correspond to the final branch head; older CI links above remain historical evidence.

The combined frontend deliberately inherits `ignore-scripts` from its npm policy. CI caught that this skips prebuild hooks, so stylesheet generation is now explicit inside `build`/`dev`; dependency lifecycle scripts remain disabled. This preserves the security policy and ensures clean clones produce the CSS.
