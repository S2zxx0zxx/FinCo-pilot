# Landing implementation blueprint and source map

Scope: existing PR #81 / feature/nextjs-spaceui-landing-20261012. Baseline 70ec9bf. Product captures pin the earlier finance tree ee1427a501b908806c0007c82bc7e57091d5ecd2 at main dde45d0. Latest main 8779483 (PR #82 manual cash confirmation) was inspected and merged into this landing branch without changing its financial implementation. Dashboard/Accounts capture source is unchanged by that main update. No financial runtime or customer data is embedded in marketing.

## Visitor journey

1. Identify the product and its everyday finance purpose.
2. Explore a clearly labelled illustrative overview/budget/activity specimen.
3. Understand accounts, plans, reporting and optional AI.
4. Inspect actual app Dashboard and Accounts screenshots with synthetic fixtures.
5. Understand control, onboarding and privacy boundaries.
6. Read FAQ and follow original app or legal/support routes.

## Source-to-section mapping

Official Space UI upstream: https://github.com/usespaceui/ui/tree/6489d244d1652470efdc810a79a289ebd966c177/src/registry

| Area | Source artifact | Adaptation and exception |
|---|---|---|
| Navigation/CTAs/footer | primitives/button, primitives/link | FinCo labels and original app links; mobile Escape closes disclosure and restores focus |
| Feature/product surfaces | primitives/card; primitives/badge | Brand-specific copy, responsive grid and colors |
| All three tab groups | primitives/tabs + lib/segmented-control | Automatic focus activation; roving focus and linked panels; old panels leave layout immediately |
| Preview profile | primitives/avatar | Explicit synthetic FC initials, not a real person |
| Headline | components/spaceui/blur-reveal-text | Visible matching server markup, no opacity hiding, static reduced-motion output |
| Hero geometry | blocks/interactive-grid-hero/.../proximity-grid | Optional desktop-only lazy decoration; static cells allocate no per-cell Motion subscriptions |
| Preferences | hooks/browser/use-media-query | Official reactive hook; conservative server fallback for motion/sound |
| Privacy illustration | @usespaceui/squishmoji/react | Original seed; decorative, not social proof |
| Compass punctuation | components/spaceui/animoji + @usespaceui/emoji | Fluent assets self-hosted with Microsoft MIT notice; animation loads on viewport entry, static reduced-motion asset; unused generic resolver lazy-loads |
| Optional sounds | @usespaceui/sounds 0.1.4; official sound-provider pattern | Explicit session opt-in, engine lazy-loaded, quiet tap at least 1.5s apart, automatic suppression with reduced motion |
| Icons | @tabler/icons-react and upstream Lucide Accordion indicator | Same icon families used by Space UI |
| Fonts | existing Open Runde assets, SIL OFL | Self-hosted Latin/currency subsets; next/font/local; consistent body/headings; retained license |
| Actual product evidence | original frontend pages/dashboard.tsx, pages/accounts.tsx | Isolated browser fixture capture, never a live customer session; source tree and hashes recorded |
| Original logo/icons | original frontend FinCo mark / existing icon assets | Intentional product identity exception; not replaced by a library logo |
| Share card | original FinCo mark + native SVG rendering | Brand asset, not a Space UI stock template or AI-generated imagery |

Native semantic sections, picture elements and original finance screenshots are composition, not claims of exact upstream page duplication. This is a custom FinCo landing composed from source-adopted Space UI building blocks.

## Design decisions and alternatives

- Interactive Grid Hero: retain restrained desktop geometry; reject mobile cell animation work.
- Card Info: use official Card primitive for product-specific information rather than transplanting unrelated block copy.
- Eleven Labs / Smooth Orb: evaluated; reject artificial real-time AI status and heavier decorative centerpiece.
- Carousels/WebGL galleries: evaluated; two explicit product tabs are easier to read and operate by keyboard/touch.
- Stats/community/rating/testimonial blocks: reject absent real evidence; do not invent customers, financial outcomes or certificates.
- Sign-in/upload/payment blocks: reject in marketing; original app owns those flows.
- Full template clone: reject changing FinCo branding and publishing template banking claims.
- Optional sounds: add an explicit off-by-default switch; never autoplay or collect persistent user preference data.

## Product-copy evidence

Accounts/transactions/budgets/goals/reports routes and capability guards are in frontend/src/App.tsx. Dashboard source composes account balances, monthly income/expenses and reports. Workspace permissions/auth safeguards exist in backend source; their existence is not an assurance that production is configured correctly. Optional AI and bank connections retain availability caveats. Manual account specimen has no integration logos or bank-certification claims.

## Catalog coverage and honesty

CATALOG_DECISIONS.json assesses all 265 historical entries for this landing and inventories local official docs/source files. Historical web status is preserved: 264 detail reads, plush source-only after timeout. Current local documents found for 256 entries; nine tool entry points use tool implementation paths rather than library MDX. This automated inventory is not presented as a new human line-by-line read of all source or a new bulk website crawl.

## Verified showcase research

TinyFish runs:
- https://agent.tinyfish.ai/runs/4ab7b75e-4b57-43d6-a5a7-816547554371 — blocks and official showcase discovery.
- https://agent.tinyfish.ai/runs/0636edc1-35fd-4c6a-ba93-bcc7d232e0e4 — relevant official showcase examples.

| Official example | Primary reference | Useful observation | Excluded claims/assets |
|---|---|---|---|
| Rival | https://www.spaceui.one/templates/rival ; https://github.com/adrielzimbril/rival-landing | Product console adjacent to a clear benefit; compact mobile disclosure; product/security/FAQ rhythm | No banking, card issuance, currency exchange or certification claims imported; no template code copied |
| Sunabase | https://www.spaceui.one/templates/sunabase | Concrete product explanation and feature hierarchy | Backend performance claims and badges excluded |
| Oleap | https://www.spaceui.one/templates/oleap | Problem → product → explanation → FAQ/CTA sequence | Customer adoption/AI outcome claims excluded |
| Twelve AI / Netra | official template MDX in upstream source | Secondary conceptual positioning references | Unrelated generated visuals and facility metrics excluded |

These are official conceptual starter/showcase entries, not proven successful paying customer sites. Upstream Rival README calls itself MIT but its checked tree has no standalone LICENSE; we copied no source/assets from it. Space UI registry files used here retain the existing MIT notice.

## Responsive and motion rules

Main CTAs stay 50px high; interactive preview tabs at least 44px; product tabs 48px. Mobile specimen hides decorative sidebar/floating note to make content readable. Actual product screens use matching 390px captures on narrow screens instead of shrinking a desktop capture. Dynamic number widths are tabular. Text balances/pretty wraps; no arbitrary counters or endless hero text swaps. User motion preference updates reactively. H1 exists and is visible without JS. No external assets, analytics, auth or finance API requests from marketing.

## Post-merge refinement — 13 October

New branch starts from main 75df7e8, which includes the merged landing and later authentication/Sentry/FX work. See DESIGN_SELECTION_20261013.md for exact Meter/Timeline/Separator/useInView mapping, Motion playground findings and typography refinement. SPACEUI_PREVIEW_REVIEW_20261013.json records all 831 attempted unique demo URLs; 189 visual snapshots, 26 loading snapshots, 10 failed captures and 606 HTTP 429 responses. Full interactive/video inspection is incomplete. Contact-sheet review is not a substitute for exercising every interaction. No gated Pro source was adopted.
