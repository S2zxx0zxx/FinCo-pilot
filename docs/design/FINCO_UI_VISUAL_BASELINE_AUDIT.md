# FinCo-Pilot UI / Visual Design Baseline Audit

**Branch:** `design/finco-identity-overhaul`  
**Baseline:** created from the current `main` product state on 2026-09-12  
**Purpose:** freeze the present UI/UX/visual identity before any identity-overhaul work begins. This file is documentation only. It intentionally does not change application behavior, API contracts, database schema, migrations, authentication, business logic, or persisted user data.

---

## 1. Why this baseline exists

FinCo-Pilot already has a functioning visual system, but future work is expected to make the product feel substantially more original and internally consistent. Before redesigning anything, this document records the present appearance, geometry, assets, layout structure, recurring UI patterns, responsive behavior, motion, iconography, chart colors, image treatment, and notable inconsistencies.

The goal of the redesign is not a blind theme swap. The high-recognition fingerprints are structural: sidebar composition, page hierarchy, card shells, auth layouts, dashboard information hierarchy, control shapes, chart treatment, spacing rhythm, empty states, and repeated component geometry. Those are documented here so redesign work can be deliberate and reversible.

---

## 2. Frontend architecture and visual surface map

### Core stack

- React 19.2
- React Router 7.13
- Vite 8.2
- TypeScript
- Tailwind CSS 4.3
- shadcn 4 / Radix UI primitives
- Lucide React icons
- Recharts for charts
- d3-sankey for Sankey reporting
- Sonner for toast feedback
- cmdk for command palette
- next-themes for light/dark mode
- TanStack Query for server-state loading/error states

### Global provider/shell order

`ThemeProvider -> QueryClientProvider -> TooltipProvider -> BrowserRouter -> AuthProvider -> WorkspaceProvider -> Suspense/Routes`.

Protected application pages render through `ProtectedRoute -> CollectionFilterProvider -> AppLayout`.

### Routed visual surfaces

| Route | Main visual family |
|---|---|
| `/setup` | branded onboarding / first-run form |
| `/login` | centered authentication card |
| `/register` | authentication/account creation |
| `/auth/oidc/callback` | auth transition/loading |
| `/i/:token` | public shared invoice |
| `/` | financial dashboard |
| `/transactions` | transaction list/calendar/workflows |
| `/accounts` | accounts list/summary |
| `/accounts/:id` | account detail |
| `/import` | import/upload/mapping/review |
| `/rules` | automation rules list/editor |
| `/categories` | categorized icon/color management |
| `/collections` | account/wallet collection management |
| `/budgets` | budget planning/progress |
| `/goals` | goal planning/progress |
| `/recurring` | recurring transactions |
| `/assets` | investment/assets dashboard |
| `/reports` | reporting/charts/Sankey analysis |
| `/payees` | payee management |
| `/groups` | split groups |
| `/groups/:id` | split group detail |
| `/invoices` | invoice list/status management |
| `/invoices/:id` | invoice detail/document workflow |
| `/workspace/settings` | workspace configuration |
| `/admin` | global/admin settings including theme colors |
| `/agents` | AI agent management |
| `/agents/connections` | agent/tool connections |
| `/agents/:id` | agent detail/configuration |

A legacy `/assets/import` route redirects to `/import?tab=investments`.

---

## 3. Global typography

### Font family

Primary application font stack:

```css
'Geist', 'Inter', system-ui, -apple-system, sans-serif
```

Google Fonts loads Geist at weights 400, 500, 600, 700, 800.

Font feature settings:

```css
"cv02", "cv03", "cv04", "cv11"
```

Global antialiasing is enabled for WebKit and macOS.

### Heading treatment

`h1`, `h2`, `h3` globally use `letter-spacing: -0.035em`.

The shared `PageHeader` uses:

- section/eyebrow: 12 px, medium, muted
- page title: 24 px, semibold, tight tracking
- responsive layout: stacked on small screens, title and action aligned to bottom on `sm+`
- common bottom spacing: 24 px

### Common micro-type sizes

- 10 px: tiny role/type labels, some sidebar metadata
- 10.5-11 px: uppercase section labels, status/detail microcopy
- 12 px: sidebar account values, captions, filters
- 13 px: main sidebar navigation
- 14 px: normal app body/control text on desktop
- 16 px: mobile input text and common body-size fallback
- 18 px: desktop sidebar brand wordmark
- 20 px: auth card titles
- 24 px: page titles
- 30 px: dashboard headline balance
- ~41.6 px: auth brand-panel headline (`2.6rem`)

---

## 4. Global color system

### Light theme tokens

| Token | Current value |
|---|---|
| background | `#F8F9FB` |
| foreground | `#0F172A` |
| card | `#FFFFFF` |
| popover | `#FFFFFF` |
| sidebar | `#FFFFFF` |
| primary | `#F97316` |
| primary foreground | `#FFFFFF` |
| secondary | `#F1F5F9` |
| muted | `#F1F5F9` |
| muted foreground | `#64748B` |
| accent | `#FFF1E8` |
| accent foreground | `#C2410C` |
| destructive | `#F43F5E` |
| border/input/sidebar border | `#E8ECF1` |
| ring | `#F97316` |

Light chart tokens:

`#F97316`, `#FB7185`, `#10B981`, `#F59E0B`, `#F43F5E`.

### Dark theme tokens

| Token | Current value |
|---|---|
| background | `#0C0D12` |
| foreground | `#F0F0F5` |
| card | `#16171F` |
| popover | `#16171F` |
| sidebar | `#16171F` |
| primary | `#FB7A5B` |
| primary foreground | `#FFFFFF` |
| secondary | `#252836` |
| muted | `#252836` |
| muted foreground | `#8A8F9E` |
| accent | `#3A1F18` |
| accent foreground | `#FDBA9A` |
| destructive | `#FB7185` |
| border/input/sidebar border | `#2A2D3A` |
| ring | `#FB7A5B` |

### Semantic colors repeatedly used outside the token layer

- positive/income/success: emerald (`#10B981` family)
- expense/negative/error: rose (`#F43F5E` family)
- warning/pending: amber (`#F59E0B` family)
- some progress/on-track states: blue
- split/shared states: violet
- search entity accents: indigo, emerald, sky, fuchsia, amber, rose

### Agent/report chart palette

Current multi-series palette:

1. `#6366F1` indigo
2. `#10B981` emerald
3. `#F59E0B` amber
4. `#F43F5E` rose
5. `#8B5CF6` violet
6. `#06B6D4` cyan
7. `#EC4899` pink
8. `#84CC16` lime

### Runtime theme override behavior

Admin settings can override the light and dark primary color. `theme-utils.ts` then updates `--primary`, `--ring`, and `--sidebar-primary`, and derives accent/muted colors through CSS `color-mix()`. Any future brand system must account for this runtime customization instead of assuming the hard-coded coral/orange primary will always be present.

---

## 5. Radius, geometry, border and shadow language

### Global radius scale

Base radius is `0.625rem` = **10 px**.

Derived Tailwind tokens:

- sm: base - 4 px
- md: base - 2 px
- lg: base
- xl: base + 4 px
- 2xl: base + 8 px
- 3xl: base + 12 px
- 4xl: base + 16 px

### Most common product fingerprint

A very large part of the product repeats this shell:

```text
bg-card + rounded-xl + border/border-border + shadow-sm + often overflow-hidden
```

It appears across dashboard blocks, budgets, recurring, goals, categories, invoices, rules, groups, imports, reconciliation, agents, and empty states. This is one of the strongest current cross-product visual fingerprints and should be treated as a high-impact redesign lever.

### Shared Card primitive

- `rounded-xl`
- `border border-border/80`
- extremely light shadow: `0 1px 2px rgba(0,0,0,0.03)`
- CardHeader/CardContent/CardFooter horizontal padding: 24 px

### Dialog shell

- dark overlay at 50% black
- centered panel
- maximum width `sm:max-w-lg`
- 24 px padding
- rounded-lg
- border + shadow-lg
- fade + 95% zoom transition
- ~200 ms motion

---

## 6. Main application shell

### Desktop sidebar

- fixed left sidebar
- width: **240 px** (`w-60`)
- full viewport height
- card-like sidebar background token
- right border
- desktop content is offset by `lg:ml-60`

#### Desktop brand header

- height: **64 px**
- horizontal padding: 20 px
- FinCo mark: **24 px**
- wordmark: 18 px, bold, tight tracking
- privacy / AI / theme icon actions: 16 px icons

#### Sidebar command/search trigger

- outer horizontal padding: 12 px
- top margin/padding: 12 px
- rounded-lg
- border
- subtle sidebar-accent background
- internal padding roughly 12 px x 8 px
- text: 12.5 px
- search icon: 13 px
- keyboard hint: 17 px high, 9.5 px monospace text

#### Navigation

- link text: 13 px medium
- icons: 17 px
- link padding: 12 px horizontal, 8 px vertical
- rounded-lg
- section labels: 10 px uppercase, semibold, `0.12em` tracking
- active state: faint primary fill + primary text/icon + 3 px primary left rail

#### Sidebar account list

- title: 11 px uppercase, `0.12em` tracking
- account row: 12 px primary text with 10 px type metadata
- negative balances use rose
- first 3 accounts shown by default
- expand control reveals remaining accounts

#### Bottom identity area

`WorkspaceSwitcher` is the merged workspace + account identity control. Below it sits a centered 11 px version label.

### Mobile header/sidebar

- sticky mobile header: **56 px** (`h-14`)
- horizontal padding: 16 px
- mobile FinCo mark: **22 px**
- search/privacy/theme/AI actions: 18 px icons
- user avatar trigger: 32 px
- sidebar becomes an off-canvas 240 px panel
- mobile sidebar backdrop: `bg-black/50`

### Main content canvas

- desktop left offset: 240 px
- inner page padding: **24 px**
- content max width: Tailwind `max-w-7xl` (~1280 px)
- horizontally centered
- horizontal overflow suppressed at main level

---

## 7. Primary navigation information architecture

There is currently **no dedicated Dashboard navigation row**. The FinCo-Pilot logo/wordmark routes to `/`.

### Accounts group

- Transactions — ArrowLeftRight
- Invoices — Receipt
- Accounts — Building2
- Import — Upload

### Analysis group

- Reports — BarChart3
- Assets — Landmark

### Setup group

- Budgets — PiggyBank
- Goals — Target
- Recurring — Repeat
- Categories — Tag
- Payees — Users
- Split Groups — Split
- Rules — SlidersHorizontal

The entire navigation icon vocabulary is currently Lucide-based.

---

## 8. Brand mark, wordmark and browser assets

### React application mark

`frontend/src/components/finco-logo.tsx`

The current mark is a square 32x32 SVG viewBox containing:

- four vertical finance bars
- an upward/rising finance path
- a circular “pilot beacon” endpoint
- muted bars at 42% opacity
- main path stroke width 2.8
- beacon outer radius 3.1
- beacon white center radius 1.1
- uses `currentColor`, so placement determines color

### Current mark sizes and placements

| Surface | Mark size / treatment |
|---|---|
| desktop sidebar | 24 px |
| mobile header | 22 px |
| setup mobile card | 22 px inside 44x44 tile |
| login / 2FA card | 22 px inside 44x44 tile |
| auth brand-panel wordmark | 20 px inside 36x36 translucent tile |
| auth decorative background | 640 px, 6% white, rotated -8° |

### Documentation wordmark asset

`docs/logo.svg`:

- viewBox: **520 x 160**
- dark rounded rectangle, radius 32
- mark accent: `#FF7A59`
- wordmark text: 50 px bold
- documentation font declaration: `Inter, Geist, Arial, sans-serif`
- README displays it at width **260 px**

### Browser/app icons

`frontend/public` contains:

- favicon.ico
- favicon-16x16.png
- favicon-32x32.png
- favicon-96x96.png
- apple-touch-icon.png
- android-icon-192x192.png

`frontend/index.html` references all favicon variants and sets the document title to `FinCo-Pilot`.

### Brand consistency note

The current app has several near-but-not-identical brand corals:

- docs logo: `#FF7A59`
- dark UI primary: `#FB7A5B`
- light UI primary: `#F97316`

The docs SVG also places `Inter` before `Geist`, while the application places `Geist` before `Inter`. These are minor individually, but they are useful cleanup targets during a deliberate identity system rebuild.

---

## 9. Authentication and onboarding visual language

### Setup / first-run

Desktop uses a 2-column split layout:

- left: `AuthBrandPanel`
- right: centered setup form

The form card:

- max width: **400 px**
- subtle border and shadow
- internal horizontal padding: 32 px
- 20 px semibold title
- 14 px muted description
- mobile-only logo tile: 44x44, rounded-xl, primary at 10% background, logo 22 px
- language and theme controls at top
- name, email, password, confirmation, currency fields
- full-width primary submit button

### AuthBrandPanel

Visible only at `lg+`.

- padding: 48 px
- background:
  `linear-gradient(150deg, #0B0B0F 0%, #171217 52%, #2B1711 100%)`
- white text
- 640 px decorative FinCo mark positioned beyond bottom-right edge
- decorative mark opacity: 6%
- decorative mark rotation: -8°
- radial vignette from upper-right area
- animated coral/orange/amber aurora blobs
- top wordmark: 36x36 translucent tile + 20 px mark + 18 px semibold text
- headline: ~41.6 px, semibold, line-height 1.08
- body copy: 16 px
- metadata row: 12 px

Aurora colors and motion:

- coral `#fb7185`
- orange `#fb923c`
- amber `#fdba74`
- blur 72 px
- durations 24s / 29s / 33s
- disabled when `prefers-reduced-motion: reduce`

### Login / 2FA

Login is currently **not** using the branded split-screen panel. It is a centered card:

- max width: **380 px**
- 44x44 logo tile with 22 px mark
- 20 px title
- standard 36 px inputs
- full-width primary button
- optional passkey and OIDC actions
- simple horizontal divider

2FA uses the same centered 380 px card visual family.

### Current auth identity inconsistency

Setup has a distinctive branded split experience while login/2FA are generic centered cards. This is a clear opportunity to unify the product’s first impression during identity redesign.

---

## 10. Dashboard baseline

### Header

- eyebrow = time-of-day greeting, optionally followed by user `display_name`
- title = selected month
- month selector has 32x32 previous/next buttons
- central month control minimum width ~180 px

### Main hero card

Current hero shell:

- card background
- rounded-xl
- border
- shadow-sm
- margin-bottom 20 px
- padding ~20 px

Primary balance:

- 12 px semibold muted label
- 30 px bold amount
- neutral foreground when non-negative
- rose when negative

Account chips below balance:

- 11 px pill treatment
- border + background
- tiny institution/account icon
- hover scale ~1.05
- name + amount in one chip

Secondary metric grid:

- 2 columns mobile
- 4 columns at `sm+`
- Income: emerald
- Expenses: rose
- Net worth: neutral unless negative
- Savings rate: semantic state color

### Categorization state banner

- uncategorized state: amber-tinted clickable banner
- all-categorized state: emerald success banner

### Dashboard charts

- one column small screens; two columns at `lg+`
- 20 px gap
- row minimum around 380 px
- chart cards roughly max 420 px height
- chart section headers generally 20 px horizontal / 16 px vertical padding
- title text around 14 px semibold

Balance flow chart:

- current series: `#10B981`
- previous series: `#94A3B8`
- current series includes soft area gradient
- axis labels: 10 px
- tooltip radius: 12 px
- tooltip shadow: `0 4px 12px rgba(0,0,0,.08)`

### Goals widget

- same rounded-xl card shell
- goal icon tile: 32x32 rounded-lg
- icon background uses user-defined goal color
- progress line height: 6 px
- progress colors use emerald/blue/amber/muted semantics

### Period transactions

Supports list/calendar view through a segmented control. Mobile renders stacked transaction rows; desktop uses a table. Amounts use emerald for positive/credit and rose for negative/debit.

---

## 11. Shared cards, sections and lists

The following recurring structures appear across most feature pages:

### Section cards

Typical feature section:

```text
bg-card
rounded-xl
border border-border
shadow-sm
overflow-hidden
```

Typical section heading:

- 16-20 px horizontal padding
- 16 px vertical padding
- bottom border
- 14 px semibold title
- optional action aligned right

### Tables

Common table header typography:

- 12 px
- medium
- muted foreground
- around 12 px vertical padding

Rows generally use subtle border separators and muted hover fills rather than elevated row cards.

### Segmented controls

Common segmented shell:

- rounded-lg
- border
- muted/card background
- ~2 px internal inset
- active tab uses card/secondary fill and subtle shadow

### Status pills

Common status badge:

- rounded-full
- 11-12 px type
- semibold/medium
- small horizontal/vertical padding
- semantic tint background + border + text

Invoice states use:

- partial: amber
- paid: emerald
- overdue: rose
- draft/open/void/uncollectible: primarily neutral/muted

---

## 12. Core controls and exact sizes

### Button

Base:

- rounded-lg
- 14 px medium text
- 8 px icon/text gap
- 2 px focus ring

Sizes:

| Variant | Height / size |
|---|---|
| default | 36 px |
| xs | 24 px |
| sm | 36 px |
| lg | 44 px |
| icon | 40x40 px |
| icon-xs | 24x24 px |
| icon-sm | 32x32 px |
| icon-lg | 40x40 px |

### Input

- height: **36 px**
- rounded-md
- border + card background
- horizontal padding: 12 px
- mobile text: 16 px
- desktop text: 14 px
- subtle shadow
- 2 px focus ring

### Badge

- rounded-full
- 12 px medium text
- 8 px horizontal padding
- very small vertical padding
- internal icons: 12 px

### Generic dialog

- centered
- 24 px padding
- rounded-lg
- `sm:max-w-lg`
- overlay `black/50`
- fade + zoom animation

---

## 13. Iconography system

### Product-wide icon language

The interface is predominantly Lucide. Main navigation, actions, status affordances, category fallbacks, onboarding controls, dialogs, search, agents, settings and utility actions all rely on the same outline icon family.

This gives consistency, but also makes the product visually close to many shadcn/Lucide-based applications. A future identity overhaul can keep Lucide for ordinary semantic utility icons while reserving custom iconography/illustration for brand-defining surfaces.

### Category icon tiles

Exact sizes:

| Size | Tile | Icon |
|---|---:|---:|
| xs | 16x16 | 10 px |
| sm | 24x24 | 14 px |
| md | 32x32 | 16 px |
| lg | 40x40 | 20 px |
| xl | 44x44 | 22 px |

Tile radius grows with size from `rounded` through `rounded-xl`.

Category background color is stored/configured dynamically. The Lucide glyph is rendered white. Emoji values are still supported for backwards compatibility.

### Account / institution icons

Exact sizes:

| Size | Tile | Fallback icon |
|---|---:|---:|
| xs | 20x20 | 11 px |
| sm | 24x24 | 12 px |
| md | 32x32 | 14 px |
| lg | 40x40 | 18 px |

If an institution logo exists, the tile uses white background + border and the image is `object-contain`; failed logo loads fall back to the account-type icon.

Bank-connection logo tile: 32x32 with a 14 px generic bank fallback.

---

## 14. Images and media placement inventory

The application is not heavily illustration-driven. Most imagery is functional/user/provider content.

### Current image contexts

- institution logos on accounts
- bank/OAuth provider logos
- market asset/company logos
- invoice business logos
- invoice logo upload preview
- invoice attachments/documents
- transaction attachment previews
- favicon/app icons
- documentation logo

### Invoice logo preview

Current preview tile is approximately:

- width: **96 px**
- height: **56 px**
- rounded-md
- border
- muted background
- centered/contained image

### Attachment/document media

- image thumbnails commonly use square/aspect-square containers
- full attachment previews use contained/full-width images depending on component
- invoice document iframe is around 1123 px requested height but capped at 78vh

### Identity observation

There are currently no strong product-owned illustration families, empty-state illustrations, branded photography systems, or custom data-art motifs. This leaves substantial room to build a unique FinCo-Pilot visual signature later without touching financial logic.

---

## 15. Workspace and collection identity

### Workspace switcher

Bottom-sidebar trigger:

- full width
- rounded-lg
- 12 px horizontal / 10 px vertical padding
- workspace icon: 24x24
- workspace name: 12 px semibold
- email/role metadata: 10 px
- up/down chevron: 13 px

Menu:

- width: **256 px**
- opens above the bottom trigger
- most action icons: 14 px
- language submenu width: **160 px**

Default workspace fallback color is `#6366F1`.

### Global collection filter

Header variant is used in the app shell:

- sticky top, z-30
- full-bleed across the page’s 24 px inner padding
- blurred/translucent background
- 48 px bar height
- bottom border
- micro-label: 11 px uppercase, `.1em` tracking
- collection selector is a pill with 13 px text
- color dot: 10 px
- active collection applies the collection’s own color at low-opacity background/border
- optional compact clear-filter pill
- dropdown width: 240 px

---

## 16. Command palette

Shortcut: **Cmd/Ctrl + K**.

- overlay: background tint + 3 px backdrop blur
- panel top position: ~22% of viewport
- width: 92vw
- max width: **640 px**
- rounded-2xl
- border
- card background
- large soft shadow
- ~150 ms fade/zoom/top-slide animation

Search entity accent colors:

- transactions: indigo
- accounts: emerald
- payees: sky
- categories: fuchsia
- goals: amber
- assets: rose

Recent selection storage key: `fincopilot.cmdk.recent`, maximum 5 records.

---

## 17. Global AI chat

Shortcut: **Cmd/Ctrl + J**.

- overlay matches command palette: subtle background tint + 3 px blur
- right-side slide-over
- full width on mobile
- **440 px** at `sm`
- **480 px** at `md+`
- full viewport height
- left border + shadow-xl
- ~200 ms slide animation

Header uses compact icon buttons and an agent selector. Agent identity is represented by an 8 px color dot and small status/default badges.

Conversation preference storage key: `fincopilot.global-chat`.

---

## 18. Onboarding tour

Current onboarding spotlight:

- overlay z-index: 10000
- tooltip z-index: 10001
- overlay opacity: black 50%
- spotlight padding around target: 6 px
- spotlight border: 2 px primary at 50%
- transition: 300 ms
- tooltip max width: **320 px**
- typical offset from target: 16 px right / 12 px below fallback
- tooltip shell: rounded-xl, border, shadow-lg, 20 px padding

### Audit issue

The tour still includes a target for `[data-tour="nav-dashboard"]`, while the dedicated Dashboard nav item was removed and the dashboard is now reached from the logo/wordmark. This target should be corrected in future work.

---

## 19. Motion and interaction language

Current motion is restrained and mostly functional:

- `transition-colors` / `transition-all` on controls and nav
- sidebar slide transform on mobile
- dialog fade + zoom
- command palette fade + zoom + vertical slide
- AI chat horizontal slide
- account chips hover scale to ~1.05
- onboarding spotlight 300 ms movement
- auth ambient aurora 24-33 second loops
- row-highlight flash 2.4 seconds

Reduced-motion support explicitly disables the auth aurora animation.

Recharts wrapper/surface focus outlines are intentionally suppressed because chart selection is conveyed visually in-chart.

---

## 20. Responsive behavior baseline

Main recurring breakpoints/patterns:

- mobile uses sticky 56 px header + off-canvas sidebar
- `lg+` uses permanent 240 px sidebar
- setup becomes a two-column branded layout at `lg`
- page headers stack on mobile and align horizontally on `sm+`
- dashboard summary metrics move from 2 to 4 columns at `sm`
- dashboard charts move from 1 to 2 columns at `lg`
- transaction presentation switches between mobile stacked rows and desktop tables
- AI chat expands from full-width mobile to fixed 440/480 px side panel
- command palette remains width-responsive with 92vw cap at 640 px

---

## 21. Loading, feedback, empty and error language

### Loading

- global lazy-route fallback: centered 32 px spinner using primary border color
- page/module loading frequently uses rectangular Skeleton blocks
- sidebar module loading uses dedicated skeleton nav rows

### Feedback

- Sonner toasts are used for mutation success/error feedback
- destructive/negative messaging consistently uses rose/destructive tones
- warning and pending states commonly use amber
- success states commonly use emerald

### Empty states

Many feature empty states currently use the same rounded-xl bordered card vocabulary, often with a 48x48 muted circular/icon container and centered copy/action. This is another area where custom FinCo-Pilot illustration/voice could create meaningful identity separation later.

---

## 22. Strongest current visual fingerprints

These are the elements most likely to make two products feel related even if the logo/name differs:

1. fixed 240 px left sidebar with grouped 13 px Lucide navigation
2. 64 px sidebar brand header and command-search field directly below
3. ubiquitous `rounded-xl + border + shadow-sm` section cards
4. page-title eyebrow/title/action composition
5. dashboard balance-first hero followed by 4 compact financial metrics
6. two-column analytical card grid
7. highly standard shadcn/Radix control geometry
8. repeated muted-table/segmented-control patterns
9. Lucide-only navigation/action language
10. centered generic login card while setup uses a separate branded split panel
11. broad use of tiny uppercase section headings
12. semantic emerald/rose/amber palette repeated across finance rows and status widgets

These should be evaluated before changing minor decoration. Structural changes here will create more product identity than simply changing colors.

---

## 23. Baseline inconsistencies / future cleanup targets

### A. Setup vs login identity

Setup has a rich branded split panel; login and 2FA are centered generic cards. First-run and returning-user experiences do not currently feel like one designed system.

### B. Brand coral mismatch

Docs logo, light UI and dark UI use three neighboring but different orange/coral values.

### C. Font-order mismatch

App prefers Geist then Inter; documentation logo declares Inter before Geist.

### D. Hard-coded visual palettes outside tokens

Dashboard charts, agent charts, command palette search entities, status badges and various feature progress states contain hard-coded semantic hues. A future design system should decide which are semantic and which should become brand tokens.

### E. Card shell overuse

The same rounded-xl bordered card appears almost everywhere. This increases consistency but reduces hierarchy and distinctiveness.

### F. Tour target drift

Onboarding still targets the removed dashboard nav item.

### G. Auth panel exists only on setup

`AuthBrandPanel` is currently not shared by login/2FA, producing an inconsistent branded-auth experience.

### H. Product-owned illustration layer is nearly absent

Most visuals are Lucide icons or third-party/user-provided logos. There is no unique FinCo illustration/empty-state/data-art family yet.

### I. Dynamic theme overrides can dilute brand identity

Admin-customizable primary color is a useful feature but future branding must keep shape, typography, motion, composition and iconography distinctive even when primary hue changes.

---

## 24. Identity-overhaul priority map (no implementation yet)

The safest redesign sequence for future work is:

**Foundation:** design tokens, typography, radius, elevation, spacing, primary/semantic palette.  
**Shell:** desktop/mobile navigation, brand placement, global search, workspace/account identity.  
**Page grammar:** PageHeader, section containers, tables/lists, controls, empty states.  
**Dashboard:** information hierarchy, hero treatment, analytical modules, chart visual system.  
**Auth/onboarding:** setup/login/register/2FA unified visual story.  
**Brand assets:** custom mark/wordmark rules, favicon set, documentation lockups.  
**Icon/illustration:** custom brand-level symbols/illustrations while preserving semantic utility icons.  
**Motion:** transitions, loading, overlays, page feedback.  
**Feature pass:** transactions, accounts, budgets, goals, assets, reports, invoices, groups, AI, admin/settings.  
**Responsive pass:** mobile/tablet/desktop density and hierarchy.  
**Accessibility pass:** contrast, focus, reduced motion, keyboard states, readable financial density.  
**Final identity QA:** screenshots at every major route and breakpoint, brand-color consistency, stale assets/text, browser icons, docs.

---

## 25. Safety / change-control rules for the redesign branch

Until a specific redesign task is approved:

- do not alter backend behavior
- do not alter database schema/migrations
- do not delete or rename API contracts
- do not alter authentication semantics
- do not alter financial calculation logic
- do not remove user data compatibility
- do not overwrite unrelated local changes
- keep changes scoped to `design/finco-identity-overhaul`
- preserve a working baseline at every logical commit
- prefer shared primitives/tokens over one-off page-specific hacks
- verify responsive behavior and existing tests after every structural UI phase

The AGPL license and required legal/source obligations remain part of the project and are not a visual-branding target.

---

## 26. Source-of-truth files for future visual work

### Global foundation

- `frontend/src/index.css`
- `frontend/src/components/theme-provider.tsx`
- `frontend/src/lib/theme-utils.ts`
- `frontend/index.html`
- `frontend/package.json`

### Shell / navigation

- `frontend/src/components/app-layout.tsx`
- `frontend/src/lib/nav-items.ts`
- `frontend/src/components/workspace-switcher.tsx`
- `frontend/src/components/collection-selector.tsx`
- `frontend/src/components/command-palette.tsx`
- `frontend/src/components/global-chat-panel.tsx`

### Brand

- `frontend/src/components/finco-logo.tsx`
- `frontend/src/components/auth-brand-panel.tsx`
- `docs/logo.svg`
- `frontend/public/*favicon*`
- `frontend/public/apple-touch-icon.png`
- `frontend/public/android-icon-192x192.png`

### Shared UI primitives

- `frontend/src/components/ui/button.tsx`
- `frontend/src/components/ui/card.tsx`
- `frontend/src/components/ui/input.tsx`
- `frontend/src/components/ui/dialog.tsx`
- `frontend/src/components/ui/badge.tsx`
- `frontend/src/components/page-header.tsx`
- `frontend/src/components/transactions-view-switcher.tsx`
- `frontend/src/components/invoice-ui.tsx`

### Visual data / icon systems

- `frontend/src/components/account-icon.tsx`
- `frontend/src/components/category-icon.tsx`
- `frontend/src/lib/category-icons.ts`
- `frontend/src/components/agents/agent-chart.tsx`

### High-impact pages

- `frontend/src/pages/dashboard.tsx`
- `frontend/src/pages/login.tsx`
- `frontend/src/pages/setup.tsx`
- `frontend/src/pages/register.tsx`
- `frontend/src/pages/transactions.tsx`
- `frontend/src/pages/accounts.tsx`
- `frontend/src/pages/account-detail.tsx`
- `frontend/src/pages/budgets.tsx`
- `frontend/src/pages/goals.tsx`
- `frontend/src/pages/recurring.tsx`
- `frontend/src/pages/assets.tsx`
- `frontend/src/pages/reports.tsx`
- `frontend/src/pages/invoices.tsx`
- `frontend/src/pages/invoice-detail.tsx`
- `frontend/src/pages/groups.tsx`
- `frontend/src/pages/group-detail.tsx`
- `frontend/src/pages/admin/settings.tsx`
- `frontend/src/pages/agents-list.tsx`
- `frontend/src/pages/agent-detail.tsx`

---

## 27. Baseline status

At the time this document was created:

- the new design branch exists separately from `main`
- the visual audit is documentation-only
- no product UI component has been redesigned on this branch yet
- no backend/database changes were introduced by this audit
- existing FinCo-Pilot brand assets and behavior remain untouched

This document should be updated whenever a major visual system decision is approved so future work always has a current reference rather than relying on memory or screenshots alone.
