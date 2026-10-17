# HeroUI experience upgrade — 17 October 2026

This extends the initial HeroUI migration in PR #99. The design uses HeroUI 3.2.6 with a white/charcoal foundation, restrained green actions, local Open Runde, varied feature specimens and concise product explanations.

## Approved scope and implementation

| Improvement | Implementation |
| --- | --- |
| Signature financial hero | A visible, sequential balance → commitments → reserves → illustrative remainder story; native Meter; reduced motion |
| Product before features | Six-view application explorer immediately after the hero |
| Deeper local example | Three NumberFields, matching Sliders, reset and an explanation Popover; positive, zero, empty and shortfall states |
| Mobile legibility | Main body 15–16px, helper copy around 12–13px, 44px controls and 48px mobile actions |
| Varied feature layouts | Two opening cards, three smaller specimens and a wide capabilities card |
| More original app views | Dashboard, Accounts, Budgets, Goals, Recurring and Reports; responsive WEBP captures |
| Screen zoom | Full-screen native Modal with close/focus handling |
| Guided first look | Three-step native Modal using original application captures |
| Example scenarios | Everyday, bills-heavy and savings-goal presets; entirely synthetic |
| Import walkthrough | Native Tabs from sample CSV through mapping to an accessible Table review; no writes |
| Adaptive mobile actions | IntersectionObserver visibility; hidden in hero, at/past final CTA and while entering values; safe-area spacing |
| Concrete trust details | Authentication/workspace roles, optional bank/AI configuration, reviewed inputs and policy links |
| Standard plan preview | Free, Pro, Max; monthly/annual controls; no invented Max annual price |
| Progressive FAQs | Five common questions plus five additional native Disclosure/Accordion questions |
| Human product story | Everyday decisions, manual starting point and reviewed inputs; no invented founder quotes, users or testimonials |

## Evidence and content boundaries

- The finance app's routes, modules and source were reviewed before writing the specimens and copy. Original dashboard/accounts provenance remains in `PRODUCT_CAPTURE_PROVENANCE.json`.
- `PRODUCT_CAPTURE_EXTENDED.json` records eight additional responsive captures and SHA-256 hashes. They use the original Vite application and synthetic loopback-only API fixtures. `frontendAppTree` identifies the reviewed source tree; the existing built application's older visible version label is explicitly recorded. These are screenshots, not a claim that a real account is connected.
- Reports' sample historical series is made up and labelled synthetic. Capture waits for the chart's SVG data to render before taking a screenshot.
- `scripts/marketing-content.mjs` derives the standard INR plan amounts from `backend/app/billing/pricing.py` and checks them against `frontend/src/billing/catalog.ts`. It runs before development/production build. This is a build-time standard catalog preview, not a quote of runtime campaigns, taxes, checkout availability or per-user offers.
- The spending illustration is ₹62,000 minus three chosen reserves. It does not reproduce the application's full spending-plan engine. Empty/invalid inputs withhold a number; oversubscribed reserves show a shortfall. The explanation names omitted debt, timing, interest and records.
- The sample CSV illustration uses the shipped two-row synthetic file. Nothing is uploaded or submitted. Net flow is explicitly distinguished from an account balance.
- Genuine testimonials and founder quotations require actual approved source material and are not fabricated as part of this implementation.

## Verification

Meaningful source tests cover the calculation boundaries and presets, authoritative standard catalog consistency, and hashes/error-free captures. Browser acceptance exercises nine widths, actual touch on small widths, keyboard controls, responsive image selection, all six product tabs, zoom, guided tour, presets/reset/sliders/Popover, import mapping/review, billing intervals, additional FAQs and mobile action visibility. Axe scans cover both mobile and desktop including open overlays and the import Table.

Existing authentication, registration, pricing, privacy, terms and support destinations remain on the application. Supporting marketing pages, consent-gated attribution, installed-PWA handoff and publication/noindex rules remain covered by existing checks. No production promotion or merge is included.

### Issues resolved during acceptance

- Increased NumberField steppers to 44px and matched all three grid columns, preventing the right control from escaping the field at 320px.
- Made the horizontally scrolling CSV specimen and the scrolling guided-tour body keyboard focusable, with visible focus indicators and accessible region names.
- Kept the zoom dialog outside the Tabs keyboard scope and used separate native HeroUI overlay states. A combined popover → tabs → zoom test exposed an exit lifecycle that could leave the dismissed modal mounted. Modal dismissal now completes immediately, while entry motion remains enabled and reduced motion remains supported. Escape, close-button and focus-return assertions remain strict.
- Browser assertions use the actual native `radiogroup`/`radio` semantics of single-selection ToggleButtonGroup. Accessibility scans wait for native entering animations to settle within five seconds.

The shipped eight extended captures have a build/source tree match verified against the visible `42af20b` build label, the reviewed main revision and this branch's unchanged `frontend/src` tree (`b446a85d982b8b8d113d53225d4319c9e8467317`).
