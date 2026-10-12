# Space UI frontend redesign — source and adoption ledger

Target: `S2zxx0zxx/FinCo-pilot`, frontend only. Base: `cbfa98eb06ae4d981df0b0c8d38cc92891f370ee`.

The user supplied ten entry links. Docs, skills and typography were read first. TinyFish fetched the seven catalogs and all 265 discovered detail URLs: 264 completed; Plush timed out on three attempts and was inspected in the official source instead. The official source commit is `6489d244d1652470efdc810a79a289ebd966c177`.

## Integration rules

- Use the best-fitting published source/variant; do not force unrelated shaders, games, media tools, demo agent telemetry or self-playing workflows into finance screens.
- Source-first adapters preserve current React Router, Radix asChild/ref, React Hook Form, query scoping, server pagination, billing gates, roles, precision and SSE contracts.
- Space Motion and Space Interactions references are vendored under `spaceui-reference/`, with upstream MIT attribution. Film/export-only rules are recorded but do not add a film player to this finance app. Existing Lucide icons stay coherent with the app and published primitive guidance; this is not a wholesale import of flagship demo interaction code.
- Local Open Runde/Inter fonts, CSS continuous corners with fallback, two-tone surfaces, bounded panel motion and reduced motion are used throughout. Financial amounts remain tabular and use existing formatting.
- Procedural avatars use local identifiers; no user email is sent to an avatar service. Emoji are self-hosted, static, decorative and licensed.
- No backend files, database migrations, API payloads or production authentication policies changed. Browser fixtures live only in the QA script, which refuses mutations.

## Source integration locations

| Source | App integration |
|---|---|
| Primitives: button/card/input/table/badge/dialog/menu/select/tabs/switch | Compatibility adapters in `src/components/ui/` |
| Primitives: Empty, Frame, Meter | Copied licensed source, used for retries and real billing usage |
| Sidebar/Sheet patterns | Responsive application shell and accessible mobile navigation |
| Theme Toggle | `components/spaceui/theme-toggle.tsx` |
| Blur Reveal Text | `components/spaceui/blur-reveal-text.tsx`, real auth panel |
| Squishmoji tools/package | Local account, workspace, Copilot and usage identities |
| Emoji tool | Self-hosted coin/target assets; coin used in spending-plan header; target in goal empty state |
| Sign-in block | AuthShell composition with real existing forms |
| Stats block | Dashboard metric hierarchy, no sample statistics |
| Agent Usage Card interaction | Frame/Meter composition driven by actual entitlement counts |
| useMediaQuery/useClipboard | `hooks/spaceui/`, mobile detection and invoice share feedback |
| Typography / Motion | `styles/spaceui.css`, local fonts, panel timing and reduced-motion behaviour |

## Route coverage

Every route inherits the new typography, surfaces and shared controls. Existing feature-specific data/calendar/chart layouts are retained. This distinction is intentional: source adapters and theme changes are not a rewrite of financial business logic.

| Page | Redesign coverage |
|---|---|
| `src/pages/account-deletion.tsx` | Shared typography/control/token redesign; specialist layout preserved |
| `src/pages/account-detail.tsx` | Direct feature surface/composition change + shared system |
| `src/pages/account-recovery.tsx` | Direct feature surface/composition change + shared system |
| `src/pages/accounts.tsx` | Direct feature surface/composition change + shared system |
| `src/pages/admin/settings.tsx` | Direct feature surface/composition change + shared system |
| `src/pages/agent-connections.tsx` | Direct feature surface/composition change + shared system |
| `src/pages/agent-detail.tsx` | Shared typography/control/token redesign; specialist layout preserved |
| `src/pages/agents-list.tsx` | Direct feature surface/composition change + shared system |
| `src/pages/assets.tsx` | Shared typography/control/token redesign; specialist layout preserved |
| `src/pages/budgets.tsx` | Direct feature surface/composition change + shared system |
| `src/pages/categories.tsx` | Direct feature surface/composition change + shared system |
| `src/pages/collections.tsx` | Shared typography/control/token redesign; specialist layout preserved |
| `src/pages/dashboard.tsx` | Direct feature surface/composition change + shared system |
| `src/pages/goals.tsx` | Direct feature surface/composition change + shared system |
| `src/pages/group-detail.tsx` | Direct feature surface/composition change + shared system |
| `src/pages/groups.tsx` | Direct feature surface/composition change + shared system |
| `src/pages/import.tsx` | Direct feature surface/composition change + shared system |
| `src/pages/invoice-detail.tsx` | Direct feature surface/composition change + shared system |
| `src/pages/invoices.tsx` | Direct feature surface/composition change + shared system |
| `src/pages/loans.tsx` | Direct feature surface/composition change + shared system |
| `src/pages/login.tsx` | Direct feature surface/composition change + shared system |
| `src/pages/oauth-callback.tsx` | Shared typography/control/token redesign; specialist layout preserved |
| `src/pages/oidc-callback.tsx` | Shared typography/control/token redesign; specialist layout preserved |
| `src/pages/payees.tsx` | Direct feature surface/composition change + shared system |
| `src/pages/pricing.tsx` | Direct feature surface/composition change + shared system |
| `src/pages/privacy.tsx` | Direct feature surface/composition change + shared system |
| `src/pages/recurring.tsx` | Direct feature surface/composition change + shared system |
| `src/pages/register.tsx` | Direct feature surface/composition change + shared system |
| `src/pages/reports.tsx` | Direct feature surface/composition change + shared system |
| `src/pages/rules.tsx` | Direct feature surface/composition change + shared system |
| `src/pages/setup.tsx` | Shared typography/control/token redesign; specialist layout preserved |
| `src/pages/shared-invoice.tsx` | Shared typography/control/token redesign; specialist layout preserved |
| `src/pages/spending-plan.tsx` | Direct feature surface/composition change + shared system |
| `src/pages/support.tsx` | Shared typography/control/token redesign; specialist layout preserved |
| `src/pages/terms.tsx` | Direct feature surface/composition change + shared system |
| `src/pages/transactions.tsx` | Direct feature surface/composition change + shared system |
| `src/pages/workspace-deletion.tsx` | Shared typography/control/token redesign; specialist layout preserved |
| `src/pages/workspace-settings.tsx` | Direct feature surface/composition change + shared system |

## Complete catalog decisions

Variant headings, acquisition status, dependency/file metadata references and acquisition status are indexed in `spaceui-catalog.json`. The table records every discovered item, including those deliberately not imported.

| Section | Item | Acquisition | Decision |
|---|---|---|---|
| primitives | [accordion](https://www.spaceui.one/primitives/accordion) | TinyFish detail read | Reviewed; no direct replacement needed for current frontend. Existing specialist behaviour remains; shared typography/tokens apply where relevant. |
| primitives | [alert](https://www.spaceui.one/primitives/alert) | TinyFish detail read | Reviewed; no direct replacement needed for current frontend. Existing specialist behaviour remains; shared typography/tokens apply where relevant. |
| primitives | [alert-dialog](https://www.spaceui.one/primitives/alert-dialog) | TinyFish detail read | Reviewed; no direct replacement needed for current frontend. Existing specialist behaviour remains; shared typography/tokens apply where relevant. |
| primitives | [aspect-ratio](https://www.spaceui.one/primitives/aspect-ratio) | TinyFish detail read | Reviewed; no direct replacement needed for current frontend. Existing specialist behaviour remains; shared typography/tokens apply where relevant. |
| primitives | [autocomplete](https://www.spaceui.one/primitives/autocomplete) | TinyFish detail read | Reviewed; no direct replacement needed for current frontend. Existing specialist behaviour remains; shared typography/tokens apply where relevant. |
| primitives | [avatar](https://www.spaceui.one/primitives/avatar) | TinyFish detail read | Existing Radix image/fallback API retained; procedural Squishmoji added to account/workspace/Copilot identities. |
| primitives | [badge](https://www.spaceui.one/primitives/badge) | TinyFish detail read | UI adapter: squircle status styling with existing variants. |
| primitives | [breadcrumb](https://www.spaceui.one/primitives/breadcrumb) | TinyFish detail read | Reviewed; no direct replacement needed for current frontend. Existing specialist behaviour remains; shared typography/tokens apply where relevant. |
| primitives | [button](https://www.spaceui.one/primitives/button) | TinyFish detail read | UI adapter: Space UI squircle geometry, press feedback; keep Radix asChild/ref/form contracts. |
| primitives | [calendar](https://www.spaceui.one/primitives/calendar) | TinyFish detail read | Reviewed; no direct replacement needed for current frontend. Existing specialist behaviour remains; shared typography/tokens apply where relevant. |
| primitives | [card](https://www.spaceui.one/primitives/card) | TinyFish detail read | UI adapter: two-tone, continuous corners; preserve existing content slots. |
| primitives | [checkbox](https://www.spaceui.one/primitives/checkbox) | TinyFish detail read | Reviewed; no direct replacement needed for current frontend. Existing specialist behaviour remains; shared typography/tokens apply where relevant. |
| primitives | [checkbox-group](https://www.spaceui.one/primitives/checkbox-group) | TinyFish detail read | Reviewed; no direct replacement needed for current frontend. Existing specialist behaviour remains; shared typography/tokens apply where relevant. |
| primitives | [collapsible](https://www.spaceui.one/primitives/collapsible) | TinyFish detail read | Reviewed; no direct replacement needed for current frontend. Existing specialist behaviour remains; shared typography/tokens apply where relevant. |
| primitives | [combobox](https://www.spaceui.one/primitives/combobox) | TinyFish detail read | Reviewed; no direct replacement needed for current frontend. Existing specialist behaviour remains; shared typography/tokens apply where relevant. |
| primitives | [command](https://www.spaceui.one/primitives/command) | TinyFish detail read | Existing cmdk actions and shortcuts retained; source shell styles adopted. |
| primitives | [context-menu](https://www.spaceui.one/primitives/context-menu) | TinyFish detail read | Reviewed; no direct replacement needed for current frontend. Existing specialist behaviour remains; shared typography/tokens apply where relevant. |
| primitives | [date-picker](https://www.spaceui.one/primitives/date-picker) | TinyFish detail read | Reviewed; no direct replacement needed for current frontend. Existing specialist behaviour remains; shared typography/tokens apply where relevant. |
| primitives | [dialog](https://www.spaceui.one/primitives/dialog) | TinyFish detail read | UI adapter: 350ms arrival / 220ms close, bounded scrolling, continuous corners. |
| primitives | [drawer](https://www.spaceui.one/primitives/drawer) | TinyFish detail read | Reviewed; no direct replacement needed for current frontend. Existing specialist behaviour remains; shared typography/tokens apply where relevant. |
| primitives | [empty](https://www.spaceui.one/primitives/empty) | TinyFish detail read | Copied official primitive; report/goals/invoice error/retry presentation. |
| primitives | [field](https://www.spaceui.one/primitives/field) | TinyFish detail read | Reviewed; no direct replacement needed for current frontend. Existing specialist behaviour remains; shared typography/tokens apply where relevant. |
| primitives | [fieldset](https://www.spaceui.one/primitives/fieldset) | TinyFish detail read | Reviewed; no direct replacement needed for current frontend. Existing specialist behaviour remains; shared typography/tokens apply where relevant. |
| primitives | [form](https://www.spaceui.one/primitives/form) | TinyFish detail read | Reviewed; no direct replacement needed for current frontend. Existing specialist behaviour remains; shared typography/tokens apply where relevant. |
| primitives | [frame](https://www.spaceui.one/primitives/frame) | TinyFish detail read | Copied official primitive; real billing usage card. |
| primitives | [group](https://www.spaceui.one/primitives/group) | TinyFish detail read | Reviewed; no direct replacement needed for current frontend. Existing specialist behaviour remains; shared typography/tokens apply where relevant. |
| primitives | [input](https://www.spaceui.one/primitives/input) | TinyFish detail read | UI adapter: rounded surface, mobile 16px text; preserve native field/ref behaviour. |
| primitives | [input-group](https://www.spaceui.one/primitives/input-group) | TinyFish detail read | Reviewed; no direct replacement needed for current frontend. Existing specialist behaviour remains; shared typography/tokens apply where relevant. |
| primitives | [kbd](https://www.spaceui.one/primitives/kbd) | TinyFish detail read | Shortcut typography adapted in navigation. |
| primitives | [label](https://www.spaceui.one/primitives/label) | TinyFish detail read | Existing association preserved, inherited source typography. |
| primitives | [link](https://www.spaceui.one/primitives/link) | TinyFish detail read | Reviewed; no direct replacement needed for current frontend. Existing specialist behaviour remains; shared typography/tokens apply where relevant. |
| primitives | [menu](https://www.spaceui.one/primitives/menu) | TinyFish detail read | UI adapter: rounded menu surfaces; fixed two-child Slot crash and desktop/mobile deletion parity. |
| primitives | [menubar](https://www.spaceui.one/primitives/menubar) | TinyFish detail read | Reviewed; no direct replacement needed for current frontend. Existing specialist behaviour remains; shared typography/tokens apply where relevant. |
| primitives | [meter](https://www.spaceui.one/primitives/meter) | TinyFish detail read | Copied Base UI primitive; real entitlement usage, no fake metrics. |
| primitives | [navigation-menu](https://www.spaceui.one/primitives/navigation-menu) | TinyFish detail read | Reviewed; no direct replacement needed for current frontend. Existing specialist behaviour remains; shared typography/tokens apply where relevant. |
| primitives | [number-field](https://www.spaceui.one/primitives/number-field) | TinyFish detail read | Reviewed; no direct replacement needed for current frontend. Existing specialist behaviour remains; shared typography/tokens apply where relevant. |
| primitives | [otp-field](https://www.spaceui.one/primitives/otp-field) | TinyFish detail read | Reviewed; no direct replacement needed for current frontend. Existing specialist behaviour remains; shared typography/tokens apply where relevant. |
| primitives | [pagination](https://www.spaceui.one/primitives/pagination) | TinyFish detail read | Reviewed; no direct replacement needed for current frontend. Existing specialist behaviour remains; shared typography/tokens apply where relevant. |
| primitives | [popover](https://www.spaceui.one/primitives/popover) | TinyFish detail read | UI adapter: source surface and timing language; existing position/focus logic retained. |
| primitives | [preview-card](https://www.spaceui.one/primitives/preview-card) | TinyFish detail read | Reviewed; no direct replacement needed for current frontend. Existing specialist behaviour remains; shared typography/tokens apply where relevant. |
| primitives | [preview-link-card](https://www.spaceui.one/primitives/preview-link-card) | TinyFish detail read | Reviewed; no direct replacement needed for current frontend. Existing specialist behaviour remains; shared typography/tokens apply where relevant. |
| primitives | [progress](https://www.spaceui.one/primitives/progress) | TinyFish detail read | Reviewed; no direct replacement needed for current frontend. Existing specialist behaviour remains; shared typography/tokens apply where relevant. |
| primitives | [radio-group](https://www.spaceui.one/primitives/radio-group) | TinyFish detail read | Reviewed; no direct replacement needed for current frontend. Existing specialist behaviour remains; shared typography/tokens apply where relevant. |
| primitives | [segmented-control](https://www.spaceui.one/primitives/segmented-control) | TinyFish detail read | Reviewed; no direct replacement needed for current frontend. Existing specialist behaviour remains; shared typography/tokens apply where relevant. |
| primitives | [scroll-area](https://www.spaceui.one/primitives/scroll-area) | TinyFish detail read | Reviewed; no direct replacement needed for current frontend. Existing specialist behaviour remains; shared typography/tokens apply where relevant. |
| primitives | [select](https://www.spaceui.one/primitives/select) | TinyFish detail read | UI adapter: rounded controls/popups; retain Radix selection and portal behaviour. |
| primitives | [separator](https://www.spaceui.one/primitives/separator) | TinyFish detail read | Reviewed; no direct replacement needed for current frontend. Existing specialist behaviour remains; shared typography/tokens apply where relevant. |
| primitives | [sheet](https://www.spaceui.one/primitives/sheet) | TinyFish detail read | Source-informed mobile sheet; existing Radix modal provides focus/Escape/scroll behaviour. |
| primitives | [sidebar](https://www.spaceui.one/primitives/sidebar) | TinyFish detail read | Source-informed shell: 264px navigation, grouped links, source style; API/module filtering retained. |
| primitives | [skeleton](https://www.spaceui.one/primitives/skeleton) | TinyFish detail read | Existing loader kept with shared tokens/reduced-motion safety. |
| primitives | [slider](https://www.spaceui.one/primitives/slider) | TinyFish detail read | Reviewed; no direct replacement needed for current frontend. Existing specialist behaviour remains; shared typography/tokens apply where relevant. |
| primitives | [spinner](https://www.spaceui.one/primitives/spinner) | TinyFish detail read | Reviewed; no direct replacement needed for current frontend. Existing specialist behaviour remains; shared typography/tokens apply where relevant. |
| primitives | [switch](https://www.spaceui.one/primitives/switch) | TinyFish detail read | Existing controlled API retained; source timing/surface language applied. |
| primitives | [table](https://www.spaceui.one/primitives/table) | TinyFish detail read | UI adapter: source spacing, header/body states; preserve scroll and table semantics. |
| primitives | [tabs](https://www.spaceui.one/primitives/tabs) | TinyFish detail read | UI adapter: rounded segmented surface; retain Radix keyboard selection. |
| primitives | [textarea](https://www.spaceui.one/primitives/textarea) | TinyFish detail read | Reviewed; no direct replacement needed for current frontend. Existing specialist behaviour remains; shared typography/tokens apply where relevant. |
| primitives | [toast](https://www.spaceui.one/primitives/toast) | TinyFish detail read | Reviewed; no direct replacement needed for current frontend. Existing specialist behaviour remains; shared typography/tokens apply where relevant. |
| primitives | [toggle](https://www.spaceui.one/primitives/toggle) | TinyFish detail read | Reviewed; no direct replacement needed for current frontend. Existing specialist behaviour remains; shared typography/tokens apply where relevant. |
| primitives | [toggle-group](https://www.spaceui.one/primitives/toggle-group) | TinyFish detail read | Reviewed; no direct replacement needed for current frontend. Existing specialist behaviour remains; shared typography/tokens apply where relevant. |
| primitives | [toolbar](https://www.spaceui.one/primitives/toolbar) | TinyFish detail read | Reviewed; no direct replacement needed for current frontend. Existing specialist behaviour remains; shared typography/tokens apply where relevant. |
| primitives | [tooltip](https://www.spaceui.one/primitives/tooltip) | TinyFish detail read | Reviewed; no direct replacement needed for current frontend. Existing specialist behaviour remains; shared typography/tokens apply where relevant. |
| components | [avatar-extended](https://www.spaceui.one/components/avatar-extended) | TinyFish detail read | Procedural local identity avatars via official Squishmoji package; no remote identity requests. |
| components | [avatar-group](https://www.spaceui.one/components/avatar-group) | TinyFish detail read | Reviewed; not imported. Showcase/decorative or domain-mismatched behaviour is not required for the finance frontend. |
| components | [frost-blurred](https://www.spaceui.one/components/frost-blurred) | TinyFish detail read | Reviewed; not imported. Showcase/decorative or domain-mismatched behaviour is not required for the finance frontend. |
| components | [bouncy-accordion](https://www.spaceui.one/components/bouncy-accordion) | TinyFish detail read | Reviewed; not imported. Showcase/decorative or domain-mismatched behaviour is not required for the finance frontend. |
| components | [detachable-accordion](https://www.spaceui.one/components/detachable-accordion) | TinyFish detail read | Reviewed; not imported. Showcase/decorative or domain-mismatched behaviour is not required for the finance frontend. |
| components | [smooth-slider](https://www.spaceui.one/components/smooth-slider) | TinyFish detail read | Reviewed; not imported. Showcase/decorative or domain-mismatched behaviour is not required for the finance frontend. |
| components | [slosh-slider](https://www.spaceui.one/components/slosh-slider) | TinyFish detail read | Reviewed; not imported. Showcase/decorative or domain-mismatched behaviour is not required for the finance frontend. |
| components | [tick-slider](https://www.spaceui.one/components/tick-slider) | TinyFish detail read | Reviewed; not imported. Showcase/decorative or domain-mismatched behaviour is not required for the finance frontend. |
| components | [liquid-switch](https://www.spaceui.one/components/liquid-switch) | TinyFish detail read | Reviewed; not imported. Showcase/decorative or domain-mismatched behaviour is not required for the finance frontend. |
| components | [theme-toggle](https://www.spaceui.one/components/theme-toggle) | TinyFish detail read | Adapted circle View Transition toggle; next-themes, reduced-motion and unsupported-browser fallback. |
| components | [liquid-sortable-list](https://www.spaceui.one/components/liquid-sortable-list) | TinyFish detail read | Reviewed; not imported. Showcase/decorative or domain-mismatched behaviour is not required for the finance frontend. |
| components | [interactive-checklist](https://www.spaceui.one/components/interactive-checklist) | TinyFish detail read | Reviewed; not imported. Showcase/decorative or domain-mismatched behaviour is not required for the finance frontend. |
| components | [team-roster-selector](https://www.spaceui.one/components/team-roster-selector) | TinyFish detail read | Reviewed; not imported. Showcase/decorative or domain-mismatched behaviour is not required for the finance frontend. |
| components | [member-selector](https://www.spaceui.one/components/member-selector) | TinyFish detail read | Reviewed; existing member/role workflows retained; shared controls redesigned. |
| components | [slide-to-confirm](https://www.spaceui.one/components/slide-to-confirm) | TinyFish detail read | Reviewed; not imported. Showcase/decorative or domain-mismatched behaviour is not required for the finance frontend. |
| components | [squircle](https://www.spaceui.one/components/squircle) | TinyFish detail read | Continuous native corner-shape with border-radius fallback adopted; no runtime geometry dependency needed. |
| components | [interest-picker](https://www.spaceui.one/components/interest-picker) | TinyFish detail read | Reviewed; not imported. Showcase/decorative or domain-mismatched behaviour is not required for the finance frontend. |
| components | [voice-chat-widget](https://www.spaceui.one/components/voice-chat-widget) | TinyFish detail read | Reviewed; not imported. Showcase/decorative or domain-mismatched behaviour is not required for the finance frontend. |
| components | [badge-squircle](https://www.spaceui.one/components/badge-squircle) | TinyFish detail read | Source geometry adapted into the existing Badge export. |
| components | [morphing-command-bar](https://www.spaceui.one/components/morphing-command-bar) | TinyFish detail read | Reviewed; not imported. Showcase/decorative or domain-mismatched behaviour is not required for the finance frontend. |
| components | [morphing-area](https://www.spaceui.one/components/morphing-area) | TinyFish detail read | Reviewed; not imported. Showcase/decorative or domain-mismatched behaviour is not required for the finance frontend. |
| components | [morphing-search-pill](https://www.spaceui.one/components/morphing-search-pill) | TinyFish detail read | Reviewed; not imported. Showcase/decorative or domain-mismatched behaviour is not required for the finance frontend. |
| components | [user-presence-avatar](https://www.spaceui.one/components/user-presence-avatar) | TinyFish detail read | Reviewed; not imported. Showcase/decorative or domain-mismatched behaviour is not required for the finance frontend. |
| components | [event-calendar](https://www.spaceui.one/components/event-calendar) | TinyFish detail read | Reviewed; existing transaction calendar retained to preserve actual/projected finance totals. |
| components | [tournament-bracket](https://www.spaceui.one/components/tournament-bracket) | TinyFish detail read | Reviewed; not imported. Showcase/decorative or domain-mismatched behaviour is not required for the finance frontend. |
| components | [status-badge](https://www.spaceui.one/components/status-badge) | TinyFish detail read | Reviewed; not imported. Showcase/decorative or domain-mismatched behaviour is not required for the finance frontend. |
| components | [github-activity](https://www.spaceui.one/components/github-activity) | TinyFish detail read | Reviewed; not imported. Showcase/decorative or domain-mismatched behaviour is not required for the finance frontend. |
| components | [section-scrollspy](https://www.spaceui.one/components/section-scrollspy) | TinyFish detail read | Reviewed; not imported. Showcase/decorative or domain-mismatched behaviour is not required for the finance frontend. |
| components | [liquid-metal-border](https://www.spaceui.one/components/liquid-metal-border) | TinyFish detail read | Reviewed; not imported. Showcase/decorative or domain-mismatched behaviour is not required for the finance frontend. |
| components | [rainbow-glow-border](https://www.spaceui.one/components/rainbow-glow-border) | TinyFish detail read | Reviewed; not imported. Showcase/decorative or domain-mismatched behaviour is not required for the finance frontend. |
| components | [silk-border](https://www.spaceui.one/components/silk-border) | TinyFish detail read | Reviewed; not imported. Showcase/decorative or domain-mismatched behaviour is not required for the finance frontend. |
| components | [morph-icon](https://www.spaceui.one/components/morph-icon) | TinyFish detail read | Reviewed; not imported. Showcase/decorative or domain-mismatched behaviour is not required for the finance frontend. |
| components | [chroma-palette](https://www.spaceui.one/components/chroma-palette) | TinyFish detail read | Reviewed; not imported. Showcase/decorative or domain-mismatched behaviour is not required for the finance frontend. |
| components | [adaptive-density-grid](https://www.spaceui.one/components/adaptive-density-grid) | TinyFish detail read | Reviewed; not imported. Showcase/decorative or domain-mismatched behaviour is not required for the finance frontend. |
| components | [dirt-carousel](https://www.spaceui.one/components/dirt-carousel) | TinyFish detail read | Reviewed; not imported. Showcase/decorative or domain-mismatched behaviour is not required for the finance frontend. |
| components | [doodle-callout](https://www.spaceui.one/components/doodle-callout) | TinyFish detail read | Reviewed; not imported. Showcase/decorative or domain-mismatched behaviour is not required for the finance frontend. |
| components | [gooey-experiments](https://www.spaceui.one/components/gooey-experiments) | TinyFish detail read | Reviewed; not imported. Showcase/decorative or domain-mismatched behaviour is not required for the finance frontend. |
| components | [pin-list](https://www.spaceui.one/components/pin-list) | TinyFish detail read | Reviewed; not imported. Showcase/decorative or domain-mismatched behaviour is not required for the finance frontend. |
| components | [phone-input](https://www.spaceui.one/components/phone-input) | TinyFish detail read | Reviewed; not imported. Showcase/decorative or domain-mismatched behaviour is not required for the finance frontend. |
| components | [gradient-file-upload](https://www.spaceui.one/components/gradient-file-upload) | TinyFish detail read | Reviewed; not imported. Showcase/decorative or domain-mismatched behaviour is not required for the finance frontend. |
| components | [date-selector](https://www.spaceui.one/components/date-selector) | TinyFish detail read | Reviewed; not imported. Showcase/decorative or domain-mismatched behaviour is not required for the finance frontend. |
| components | [rating](https://www.spaceui.one/components/rating) | TinyFish detail read | Reviewed; not imported. Showcase/decorative or domain-mismatched behaviour is not required for the finance frontend. |
| components | [autoscale-input](https://www.spaceui.one/components/autoscale-input) | TinyFish detail read | Reviewed; not imported. Showcase/decorative or domain-mismatched behaviour is not required for the finance frontend. |
| components | [filters](https://www.spaceui.one/components/filters) | TinyFish detail read | Reviewed; existing advanced transaction filters retained with redesigned shared controls. |
| components | [resizable](https://www.spaceui.one/components/resizable) | TinyFish detail read | Reviewed; not imported. Showcase/decorative or domain-mismatched behaviour is not required for the finance frontend. |
| components | [scrollspy](https://www.spaceui.one/components/scrollspy) | TinyFish detail read | Reviewed; not imported. Showcase/decorative or domain-mismatched behaviour is not required for the finance frontend. |
| components | [data-grid](https://www.spaceui.one/components/data-grid) | TinyFish detail read | Reviewed 29 published variants; spacing/surface adapter applied to existing finance tables. Server pagination, selection, currency and existing column logic retained. |
| components | [sortable](https://www.spaceui.one/components/sortable) | TinyFish detail read | Reviewed; not imported. Showcase/decorative or domain-mismatched behaviour is not required for the finance frontend. |
| components | [kanban](https://www.spaceui.one/components/kanban) | TinyFish detail read | Reviewed; not imported. Showcase/decorative or domain-mismatched behaviour is not required for the finance frontend. |
| components | [timeline](https://www.spaceui.one/components/timeline) | TinyFish detail read | Reviewed; not imported. Showcase/decorative or domain-mismatched behaviour is not required for the finance frontend. |
| components | [notification-list](https://www.spaceui.one/components/notification-list) | TinyFish detail read | Reviewed; not imported. Showcase/decorative or domain-mismatched behaviour is not required for the finance frontend. |
| components | [icon-stack](https://www.spaceui.one/components/icon-stack) | TinyFish detail read | Reviewed; not imported. Showcase/decorative or domain-mismatched behaviour is not required for the finance frontend. |
| components | [image-dark](https://www.spaceui.one/components/image-dark) | TinyFish detail read | Reviewed; not imported. Showcase/decorative or domain-mismatched behaviour is not required for the finance frontend. |
| components | [button-squircle](https://www.spaceui.one/components/button-squircle) | TinyFish detail read | Source styling adapted into the existing Button export, retaining asChild compatibility. |
| components | [glass-button](https://www.spaceui.one/components/glass-button) | TinyFish detail read | Reviewed; not imported. Showcase/decorative or domain-mismatched behaviour is not required for the finance frontend. |
| components | [pixel-fill-button](https://www.spaceui.one/components/pixel-fill-button) | TinyFish detail read | Reviewed; not imported. Showcase/decorative or domain-mismatched behaviour is not required for the finance frontend. |
| components | [aurora-glow-button](https://www.spaceui.one/components/aurora-glow-button) | TinyFish detail read | Reviewed; not imported. Showcase/decorative or domain-mismatched behaviour is not required for the finance frontend. |
| components | [rainbow-glow-button](https://www.spaceui.one/components/rainbow-glow-button) | TinyFish detail read | Reviewed; not imported. Showcase/decorative or domain-mismatched behaviour is not required for the finance frontend. |
| components | [like-button](https://www.spaceui.one/components/like-button) | TinyFish detail read | Reviewed; not imported. Showcase/decorative or domain-mismatched behaviour is not required for the finance frontend. |
| components | [handle-reel](https://www.spaceui.one/components/handle-reel) | TinyFish detail read | Reviewed; not imported. Showcase/decorative or domain-mismatched behaviour is not required for the finance frontend. |
| components | [fluid-countdown](https://www.spaceui.one/components/fluid-countdown) | TinyFish detail read | Reviewed; not imported. Showcase/decorative or domain-mismatched behaviour is not required for the finance frontend. |
| components | [words-preloader](https://www.spaceui.one/components/words-preloader) | TinyFish detail read | Reviewed; not imported. Showcase/decorative or domain-mismatched behaviour is not required for the finance frontend. |
| components | [blur-reveal-text](https://www.spaceui.one/components/blur-reveal-text) | TinyFish detail read | Adapted title reveal in real auth brand panel; bounded cascade, semantic reading, reduced motion. |
| components | [morphing-text](https://www.spaceui.one/components/morphing-text) | TinyFish detail read | Reviewed; not imported. Showcase/decorative or domain-mismatched behaviour is not required for the finance frontend. |
| components | [flip-text](https://www.spaceui.one/components/flip-text) | TinyFish detail read | Reviewed; not imported. Showcase/decorative or domain-mismatched behaviour is not required for the finance frontend. |
| components | [gooey-text-reveal](https://www.spaceui.one/components/gooey-text-reveal) | TinyFish detail read | Reviewed; not imported. Showcase/decorative or domain-mismatched behaviour is not required for the finance frontend. |
| components | [scroll-text-reveal](https://www.spaceui.one/components/scroll-text-reveal) | TinyFish detail read | Reviewed; not imported. Showcase/decorative or domain-mismatched behaviour is not required for the finance frontend. |
| components | [scroll-manifesto](https://www.spaceui.one/components/scroll-manifesto) | TinyFish detail read | Reviewed; not imported. Showcase/decorative or domain-mismatched behaviour is not required for the finance frontend. |
| components | [textmoji](https://www.spaceui.one/components/textmoji) | TinyFish detail read | Reviewed; not imported. Showcase/decorative or domain-mismatched behaviour is not required for the finance frontend. |
| components | [animoji](https://www.spaceui.one/components/animoji) | TinyFish detail read | Reviewed; not imported. Showcase/decorative or domain-mismatched behaviour is not required for the finance frontend. |
| components | [scatter-text](https://www.spaceui.one/components/scatter-text) | TinyFish detail read | Reviewed; not imported. Showcase/decorative or domain-mismatched behaviour is not required for the finance frontend. |
| components | [pixel-reveal-text](https://www.spaceui.one/components/pixel-reveal-text) | TinyFish detail read | Reviewed; not imported. Showcase/decorative or domain-mismatched behaviour is not required for the finance frontend. |
| components | [thinking](https://www.spaceui.one/components/thinking) | TinyFish detail read | Reviewed; not imported. Showcase/decorative or domain-mismatched behaviour is not required for the finance frontend. |
| components | [loading](https://www.spaceui.one/components/loading) | TinyFish detail read | Reviewed; not imported. Showcase/decorative or domain-mismatched behaviour is not required for the finance frontend. |
| components | [smooth](https://www.spaceui.one/components/smooth) | TinyFish detail read | Reviewed; not imported. Showcase/decorative or domain-mismatched behaviour is not required for the finance frontend. |
| components | [bloop](https://www.spaceui.one/components/bloop) | TinyFish detail read | Reviewed; not imported. Showcase/decorative or domain-mismatched behaviour is not required for the finance frontend. |
| components | [bubble](https://www.spaceui.one/components/bubble) | TinyFish detail read | Reviewed; not imported. Showcase/decorative or domain-mismatched behaviour is not required for the finance frontend. |
| components | [gradient](https://www.spaceui.one/components/gradient) | TinyFish detail read | Reviewed; not imported. Showcase/decorative or domain-mismatched behaviour is not required for the finance frontend. |
| components | [cloud](https://www.spaceui.one/components/cloud) | TinyFish detail read | Reviewed; not imported. Showcase/decorative or domain-mismatched behaviour is not required for the finance frontend. |
| components | [heat-shade](https://www.spaceui.one/components/heat-shade) | TinyFish detail read | Reviewed; not imported. Showcase/decorative or domain-mismatched behaviour is not required for the finance frontend. |
| components | [silk-gradient](https://www.spaceui.one/components/silk-gradient) | TinyFish detail read | Reviewed; not imported. Showcase/decorative or domain-mismatched behaviour is not required for the finance frontend. |
| components | [silk-flare](https://www.spaceui.one/components/silk-flare) | TinyFish detail read | Reviewed; not imported. Showcase/decorative or domain-mismatched behaviour is not required for the finance frontend. |
| components | [paper-shader](https://www.spaceui.one/components/paper-shader) | TinyFish detail read | Reviewed; not imported. Showcase/decorative or domain-mismatched behaviour is not required for the finance frontend. |
| components | [pixel-reveal-image](https://www.spaceui.one/components/pixel-reveal-image) | TinyFish detail read | Reviewed; not imported. Showcase/decorative or domain-mismatched behaviour is not required for the finance frontend. |
| components | [fluid-distortion-image](https://www.spaceui.one/components/fluid-distortion-image) | TinyFish detail read | Reviewed; not imported. Showcase/decorative or domain-mismatched behaviour is not required for the finance frontend. |
| components | [fluid-crossfade](https://www.spaceui.one/components/fluid-crossfade) | TinyFish detail read | Reviewed; not imported. Showcase/decorative or domain-mismatched behaviour is not required for the finance frontend. |
| components | [fluid-dither-crossfade](https://www.spaceui.one/components/fluid-dither-crossfade) | TinyFish detail read | Reviewed; not imported. Showcase/decorative or domain-mismatched behaviour is not required for the finance frontend. |
| components | [liquid-mask-crossfade](https://www.spaceui.one/components/liquid-mask-crossfade) | TinyFish detail read | Reviewed; not imported. Showcase/decorative or domain-mismatched behaviour is not required for the finance frontend. |
| components | [mesh-gradient](https://www.spaceui.one/components/mesh-gradient) | TinyFish detail read | Reviewed; not imported. Showcase/decorative or domain-mismatched behaviour is not required for the finance frontend. |
| components | [liquid-mesh-blur](https://www.spaceui.one/components/liquid-mesh-blur) | TinyFish detail read | Reviewed; not imported. Showcase/decorative or domain-mismatched behaviour is not required for the finance frontend. |
| tools | [avatars](https://www.spaceui.one/tools/avatars) | TinyFish detail read | Official Squishmoji variant integrated locally; traditional avatar image/initial contracts retained. |
| tools | [avatars?type=squishmoji](https://www.spaceui.one/tools/avatars?type=squishmoji) | TinyFish detail read | Official Squishmoji variant integrated locally; traditional avatar image/initial contracts retained. |
| tools | [plush](https://www.spaceui.one/tools/plush) | Official source read; web timeout | Web fetch timed out three times; official source engine/playground reviewed. Fur/3D image editor not applicable to finance. |
| tools | [emoji](https://www.spaceui.one/tools/emoji) | TinyFish detail read | Two Fluent 3D assets resolved using Space UI tooling, self-hosted with original license; static and decorative. |
| tools | [reveal](https://www.spaceui.one/tools/reveal) | TinyFish detail read | Reviewed; image-brush WebGL authoring tool not applicable to finance records. |
| tools | [imagesplit](https://www.spaceui.one/tools/imagesplit) | TinyFish detail read | Reviewed; carousel-image slicing is authoring-only, outside this app. |
| tools | [flags](https://www.spaceui.one/tools/flags) | TinyFish detail read | Reviewed; existing country/locale data and labels retained. |
| tools | [motion](https://www.spaceui.one/tools/motion) | TinyFish detail read | All timing/reading rules adopted in docs, drawers, dialogs, title reveal and reduced-motion behaviour. |
| tools | [og-image](https://www.spaceui.one/tools/og-image) | TinyFish detail read | Reviewed; authoring tool, outside finance in-app workflows. |
| interactions | [agent-pipeline](https://www.spaceui.one/interactions/agent-pipeline) | TinyFish detail read | Reviewed; no production demo telemetry/workflow imported. Existing real agent/approval APIs retained. |
| interactions | [agent-genesis-forge](https://www.spaceui.one/interactions/agent-genesis-forge) | TinyFish detail read | Reviewed; no production demo telemetry/workflow imported. Existing real agent/approval APIs retained. |
| interactions | [agent-clearance-deck](https://www.spaceui.one/interactions/agent-clearance-deck) | TinyFish detail read | Reviewed; no production demo telemetry/workflow imported. Existing real agent/approval APIs retained. |
| interactions | [agent-activity-feed](https://www.spaceui.one/interactions/agent-activity-feed) | TinyFish detail read | Reviewed; no production demo telemetry/workflow imported. Existing real agent/approval APIs retained. |
| interactions | [cognitive-pulse-monitor](https://www.spaceui.one/interactions/cognitive-pulse-monitor) | TinyFish detail read | Reviewed; no production demo telemetry/workflow imported. Existing real agent/approval APIs retained. |
| interactions | [capability-matrix](https://www.spaceui.one/interactions/capability-matrix) | TinyFish detail read | Reviewed; no production demo telemetry/workflow imported. Existing real agent/approval APIs retained. |
| interactions | [agent-usage-card](https://www.spaceui.one/interactions/agent-usage-card) | TinyFish detail read | Adapted real-data usage interaction through official Frame/Meter/Squishmoji; no autoplay or demo costs. |
| interactions | [priority-sort-lane](https://www.spaceui.one/interactions/priority-sort-lane) | TinyFish detail read | Reviewed; no production demo telemetry/workflow imported. Existing real agent/approval APIs retained. |
| interactions | [deploy-pipeline](https://www.spaceui.one/interactions/deploy-pipeline) | TinyFish detail read | Reviewed; no production demo telemetry/workflow imported. Existing real agent/approval APIs retained. |
| interactions | [status-badge-glow](https://www.spaceui.one/interactions/status-badge-glow) | TinyFish detail read | Reviewed; no production demo telemetry/workflow imported. Existing real agent/approval APIs retained. |
| interactions | [realtime-voice](https://www.spaceui.one/interactions/realtime-voice) | TinyFish detail read | Reviewed; no production demo telemetry/workflow imported. Existing real agent/approval APIs retained. |
| interactions | [currency-converter](https://www.spaceui.one/interactions/currency-converter) | TinyFish detail read | Reviewed; no production demo telemetry/workflow imported. Existing real agent/approval APIs retained. |
| interactions | [hallucination-radar](https://www.spaceui.one/interactions/hallucination-radar) | TinyFish detail read | Reviewed; no production demo telemetry/workflow imported. Existing real agent/approval APIs retained. |
| blocks | [interactive-grid-hero](https://www.spaceui.one/blocks/interactive-grid-hero) | TinyFish detail read | Reviewed; not applicable to current finance workflows (marketing/media/community/gallery block). |
| blocks | [community-wall](https://www.spaceui.one/blocks/community-wall) | TinyFish detail read | Reviewed; not applicable to current finance workflows (marketing/media/community/gallery block). |
| blocks | [sign-in](https://www.spaceui.one/blocks/sign-in) | TinyFish detail read | Adapted composition using AuthShell, real login/register forms, existing MFA/passkeys/provider branches. |
| blocks | [card-info](https://www.spaceui.one/blocks/card-info) | TinyFish detail read | Two-tone card hierarchy used throughout shared surfaces. |
| blocks | [interactive-fun-facts](https://www.spaceui.one/blocks/interactive-fun-facts) | TinyFish detail read | Reviewed; not applicable to current finance workflows (marketing/media/community/gallery block). |
| blocks | [eleven-labs](https://www.spaceui.one/blocks/eleven-labs) | TinyFish detail read | Reviewed; not applicable to current finance workflows (marketing/media/community/gallery block). |
| blocks | [stats](https://www.spaceui.one/blocks/stats) | TinyFish detail read | Adapted visual metric hierarchy in dashboard and billing usage; never copied sample statistics. |
| blocks | [showcase-gallery](https://www.spaceui.one/blocks/showcase-gallery) | TinyFish detail read | Reviewed; not applicable to current finance workflows (marketing/media/community/gallery block). |
| blocks | [dither-carousel](https://www.spaceui.one/blocks/dither-carousel) | TinyFish detail read | Reviewed; not applicable to current finance workflows (marketing/media/community/gallery block). |
| blocks | [liquid-gooey-carousel](https://www.spaceui.one/blocks/liquid-gooey-carousel) | TinyFish detail read | Reviewed; not applicable to current finance workflows (marketing/media/community/gallery block). |
| blocks | [prism-carousel](https://www.spaceui.one/blocks/prism-carousel) | TinyFish detail read | Reviewed; not applicable to current finance workflows (marketing/media/community/gallery block). |
| blocks | [lens-carousel](https://www.spaceui.one/blocks/lens-carousel) | TinyFish detail read | Reviewed; not applicable to current finance workflows (marketing/media/community/gallery block). |
| blocks | [velocity-hover-preview](https://www.spaceui.one/blocks/velocity-hover-preview) | TinyFish detail read | Reviewed; not applicable to current finance workflows (marketing/media/community/gallery block). |
| hooks | [use-clipboard](https://www.spaceui.one/hooks/use-clipboard) | TinyFish detail read | Copied/adapted; invoice sharing now handles rejected clipboard writes and clears feedback timer on unmount. |
| hooks | [use-network](https://www.spaceui.one/hooks/use-network) | TinyFish detail read | Reviewed; existing PWA online/offline provider already owns this state. |
| hooks | [use-media-query](https://www.spaceui.one/hooks/use-media-query) | TinyFish detail read | Copied/adapted; used in finance mobile detection, shell, reduced-motion avatars and theme toggle. |
| hooks | [use-local-storage](https://www.spaceui.one/hooks/use-local-storage) | TinyFish detail read | Reviewed; retain existing auth/workspace storage isolation and invalidation contracts. |
| hooks | [use-session-storage](https://www.spaceui.one/hooks/use-session-storage) | TinyFish detail read | Reviewed; no additional runtime utility needed. Avoid duplicate lifecycle/state abstractions or changing finance contracts. |
| hooks | [use-cookie](https://www.spaceui.one/hooks/use-cookie) | TinyFish detail read | Reviewed; no additional runtime utility needed. Avoid duplicate lifecycle/state abstractions or changing finance contracts. |
| hooks | [use-cookie-listener](https://www.spaceui.one/hooks/use-cookie-listener) | TinyFish detail read | Reviewed; no additional runtime utility needed. Avoid duplicate lifecycle/state abstractions or changing finance contracts. |
| hooks | [use-device-os](https://www.spaceui.one/hooks/use-device-os) | TinyFish detail read | Reviewed; no additional runtime utility needed. Avoid duplicate lifecycle/state abstractions or changing finance contracts. |
| hooks | [use-is-mac](https://www.spaceui.one/hooks/use-is-mac) | TinyFish detail read | Reviewed; no additional runtime utility needed. Avoid duplicate lifecycle/state abstractions or changing finance contracts. |
| hooks | [use-fullscreen](https://www.spaceui.one/hooks/use-fullscreen) | TinyFish detail read | Reviewed; no additional runtime utility needed. Avoid duplicate lifecycle/state abstractions or changing finance contracts. |
| hooks | [use-battery-status](https://www.spaceui.one/hooks/use-battery-status) | TinyFish detail read | Reviewed; no additional runtime utility needed. Avoid duplicate lifecycle/state abstractions or changing finance contracts. |
| hooks | [use-orientation](https://www.spaceui.one/hooks/use-orientation) | TinyFish detail read | Reviewed; no additional runtime utility needed. Avoid duplicate lifecycle/state abstractions or changing finance contracts. |
| hooks | [use-prefers-theme](https://www.spaceui.one/hooks/use-prefers-theme) | TinyFish detail read | Reviewed; no additional runtime utility needed. Avoid duplicate lifecycle/state abstractions or changing finance contracts. |
| hooks | [use-script](https://www.spaceui.one/hooks/use-script) | TinyFish detail read | Reviewed; no additional runtime utility needed. Avoid duplicate lifecycle/state abstractions or changing finance contracts. |
| hooks | [use-share](https://www.spaceui.one/hooks/use-share) | TinyFish detail read | Reviewed; no additional runtime utility needed. Avoid duplicate lifecycle/state abstractions or changing finance contracts. |
| hooks | [use-tab-notification](https://www.spaceui.one/hooks/use-tab-notification) | TinyFish detail read | Reviewed; no additional runtime utility needed. Avoid duplicate lifecycle/state abstractions or changing finance contracts. |
| hooks | [use-title](https://www.spaceui.one/hooks/use-title) | TinyFish detail read | Reviewed; no additional runtime utility needed. Avoid duplicate lifecycle/state abstractions or changing finance contracts. |
| hooks | [use-click-outside](https://www.spaceui.one/hooks/use-click-outside) | TinyFish detail read | Reviewed; no additional runtime utility needed. Avoid duplicate lifecycle/state abstractions or changing finance contracts. |
| hooks | [use-event-listener](https://www.spaceui.one/hooks/use-event-listener) | TinyFish detail read | Reviewed; no additional runtime utility needed. Avoid duplicate lifecycle/state abstractions or changing finance contracts. |
| hooks | [use-hover](https://www.spaceui.one/hooks/use-hover) | TinyFish detail read | Reviewed; no additional runtime utility needed. Avoid duplicate lifecycle/state abstractions or changing finance contracts. |
| hooks | [use-intersection-observer](https://www.spaceui.one/hooks/use-intersection-observer) | TinyFish detail read | Reviewed; no additional runtime utility needed. Avoid duplicate lifecycle/state abstractions or changing finance contracts. |
| hooks | [use-key-press](https://www.spaceui.one/hooks/use-key-press) | TinyFish detail read | Reviewed; no additional runtime utility needed. Avoid duplicate lifecycle/state abstractions or changing finance contracts. |
| hooks | [use-lock-body-scroll](https://www.spaceui.one/hooks/use-lock-body-scroll) | TinyFish detail read | Reviewed; no additional runtime utility needed. Avoid duplicate lifecycle/state abstractions or changing finance contracts. |
| hooks | [use-mouse-position](https://www.spaceui.one/hooks/use-mouse-position) | TinyFish detail read | Reviewed; no additional runtime utility needed. Avoid duplicate lifecycle/state abstractions or changing finance contracts. |
| hooks | [use-scroll-device](https://www.spaceui.one/hooks/use-scroll-device) | TinyFish detail read | Reviewed; no additional runtime utility needed. Avoid duplicate lifecycle/state abstractions or changing finance contracts. |
| hooks | [use-scroll-position](https://www.spaceui.one/hooks/use-scroll-position) | TinyFish detail read | Reviewed; no additional runtime utility needed. Avoid duplicate lifecycle/state abstractions or changing finance contracts. |
| hooks | [use-scroll-to](https://www.spaceui.one/hooks/use-scroll-to) | TinyFish detail read | Reviewed; no additional runtime utility needed. Avoid duplicate lifecycle/state abstractions or changing finance contracts. |
| hooks | [use-size](https://www.spaceui.one/hooks/use-size) | TinyFish detail read | Reviewed; no additional runtime utility needed. Avoid duplicate lifecycle/state abstractions or changing finance contracts. |
| hooks | [use-window-size](https://www.spaceui.one/hooks/use-window-size) | TinyFish detail read | Reviewed; no additional runtime utility needed. Avoid duplicate lifecycle/state abstractions or changing finance contracts. |
| hooks | [use-confirm-exit](https://www.spaceui.one/hooks/use-confirm-exit) | TinyFish detail read | Reviewed; no additional runtime utility needed. Avoid duplicate lifecycle/state abstractions or changing finance contracts. |
| hooks | [use-debounce](https://www.spaceui.one/hooks/use-debounce) | TinyFish detail read | Reviewed; existing filtering/search timing retained. |
| hooks | [use-event-callback](https://www.spaceui.one/hooks/use-event-callback) | TinyFish detail read | Reviewed; no additional runtime utility needed. Avoid duplicate lifecycle/state abstractions or changing finance contracts. |
| hooks | [use-first-render](https://www.spaceui.one/hooks/use-first-render) | TinyFish detail read | Reviewed; no additional runtime utility needed. Avoid duplicate lifecycle/state abstractions or changing finance contracts. |
| hooks | [use-first-visit](https://www.spaceui.one/hooks/use-first-visit) | TinyFish detail read | Reviewed; no additional runtime utility needed. Avoid duplicate lifecycle/state abstractions or changing finance contracts. |
| hooks | [use-hold](https://www.spaceui.one/hooks/use-hold) | TinyFish detail read | Reviewed; no additional runtime utility needed. Avoid duplicate lifecycle/state abstractions or changing finance contracts. |
| hooks | [use-idle](https://www.spaceui.one/hooks/use-idle) | TinyFish detail read | Reviewed; no additional runtime utility needed. Avoid duplicate lifecycle/state abstractions or changing finance contracts. |
| hooks | [use-interval](https://www.spaceui.one/hooks/use-interval) | TinyFish detail read | Reviewed; no additional runtime utility needed. Avoid duplicate lifecycle/state abstractions or changing finance contracts. |
| hooks | [use-is-mounted](https://www.spaceui.one/hooks/use-is-mounted) | TinyFish detail read | Reviewed; no additional runtime utility needed. Avoid duplicate lifecycle/state abstractions or changing finance contracts. |
| hooks | [use-isomorphic-layout-effect](https://www.spaceui.one/hooks/use-isomorphic-layout-effect) | TinyFish detail read | Reviewed; no additional runtime utility needed. Avoid duplicate lifecycle/state abstractions or changing finance contracts. |
| hooks | [use-leave-detection](https://www.spaceui.one/hooks/use-leave-detection) | TinyFish detail read | Reviewed; no additional runtime utility needed. Avoid duplicate lifecycle/state abstractions or changing finance contracts. |
| hooks | [use-performance-mode](https://www.spaceui.one/hooks/use-performance-mode) | TinyFish detail read | Reviewed; no additional runtime utility needed. Avoid duplicate lifecycle/state abstractions or changing finance contracts. |
| hooks | [use-single-effect](https://www.spaceui.one/hooks/use-single-effect) | TinyFish detail read | Reviewed; no additional runtime utility needed. Avoid duplicate lifecycle/state abstractions or changing finance contracts. |
| hooks | [use-toggle](https://www.spaceui.one/hooks/use-toggle) | TinyFish detail read | Reviewed; no additional runtime utility needed. Avoid duplicate lifecycle/state abstractions or changing finance contracts. |
| hooks | [use-update-effect](https://www.spaceui.one/hooks/use-update-effect) | TinyFish detail read | Reviewed; no additional runtime utility needed. Avoid duplicate lifecycle/state abstractions or changing finance contracts. |
| hooks | [use-urgent-update](https://www.spaceui.one/hooks/use-urgent-update) | TinyFish detail read | Reviewed; no additional runtime utility needed. Avoid duplicate lifecycle/state abstractions or changing finance contracts. |
| hooks | [use-auto-height](https://www.spaceui.one/hooks/use-auto-height) | TinyFish detail read | Reviewed; no additional runtime utility needed. Avoid duplicate lifecycle/state abstractions or changing finance contracts. |
| hooks | [use-controlled-state](https://www.spaceui.one/hooks/use-controlled-state) | TinyFish detail read | Reviewed; no additional runtime utility needed. Avoid duplicate lifecycle/state abstractions or changing finance contracts. |
| hooks | [use-data-state](https://www.spaceui.one/hooks/use-data-state) | TinyFish detail read | Reviewed; no additional runtime utility needed. Avoid duplicate lifecycle/state abstractions or changing finance contracts. |
| hooks | [use-in-view](https://www.spaceui.one/hooks/use-in-view) | TinyFish detail read | Reviewed; no additional runtime utility needed. Avoid duplicate lifecycle/state abstractions or changing finance contracts. |
| hooks | [use-motion-value-state](https://www.spaceui.one/hooks/use-motion-value-state) | TinyFish detail read | Reviewed; no additional runtime utility needed. Avoid duplicate lifecycle/state abstractions or changing finance contracts. |
| hooks | [use-character-limit](https://www.spaceui.one/hooks/use-character-limit) | TinyFish detail read | Reviewed; no additional runtime utility needed. Avoid duplicate lifecycle/state abstractions or changing finance contracts. |
| hooks | [use-file-upload](https://www.spaceui.one/hooks/use-file-upload) | TinyFish detail read | Reviewed; retain existing file validation, preview/review and import contracts. |
| hooks | [use-input-value](https://www.spaceui.one/hooks/use-input-value) | TinyFish detail read | Reviewed; no additional runtime utility needed. Avoid duplicate lifecycle/state abstractions or changing finance contracts. |
| hooks | [use-load-more](https://www.spaceui.one/hooks/use-load-more) | TinyFish detail read | Reviewed; no additional runtime utility needed. Avoid duplicate lifecycle/state abstractions or changing finance contracts. |
| hooks | [use-map](https://www.spaceui.one/hooks/use-map) | TinyFish detail read | Reviewed; no additional runtime utility needed. Avoid duplicate lifecycle/state abstractions or changing finance contracts. |
| hooks | [use-mutation](https://www.spaceui.one/hooks/use-mutation) | TinyFish detail read | Reviewed; no additional runtime utility needed. Avoid duplicate lifecycle/state abstractions or changing finance contracts. |
| hooks | [use-pagination](https://www.spaceui.one/hooks/use-pagination) | TinyFish detail read | Reviewed; retain server pagination and financial totals. |
| hooks | [use-parse-markdown](https://www.spaceui.one/hooks/use-parse-markdown) | TinyFish detail read | Reviewed; no additional runtime utility needed. Avoid duplicate lifecycle/state abstractions or changing finance contracts. |
| hooks | [use-reading-time](https://www.spaceui.one/hooks/use-reading-time) | TinyFish detail read | Reviewed; no additional runtime utility needed. Avoid duplicate lifecycle/state abstractions or changing finance contracts. |
| hooks | [use-sanitize-content](https://www.spaceui.one/hooks/use-sanitize-content) | TinyFish detail read | Reviewed; no additional runtime utility needed. Avoid duplicate lifecycle/state abstractions or changing finance contracts. |
| hooks | [class](https://www.spaceui.one/hooks/class) | TinyFish detail read | Reviewed; no additional runtime utility needed. Avoid duplicate lifecycle/state abstractions or changing finance contracts. |
| hooks | [for](https://www.spaceui.one/hooks/for) | TinyFish detail read | Reviewed; no additional runtime utility needed. Avoid duplicate lifecycle/state abstractions or changing finance contracts. |
| hooks | [if](https://www.spaceui.one/hooks/if) | TinyFish detail read | Reviewed; no additional runtime utility needed. Avoid duplicate lifecycle/state abstractions or changing finance contracts. |
| hooks | [image](https://www.spaceui.one/hooks/image) | TinyFish detail read | Reviewed; no additional runtime utility needed. Avoid duplicate lifecycle/state abstractions or changing finance contracts. |
| hooks | [in-view](https://www.spaceui.one/hooks/in-view) | TinyFish detail read | Reviewed; no additional runtime utility needed. Avoid duplicate lifecycle/state abstractions or changing finance contracts. |
| hooks | [render-after](https://www.spaceui.one/hooks/render-after) | TinyFish detail read | Reviewed; no additional runtime utility needed. Avoid duplicate lifecycle/state abstractions or changing finance contracts. |
| hooks | [show](https://www.spaceui.one/hooks/show) | TinyFish detail read | Reviewed; no additional runtime utility needed. Avoid duplicate lifecycle/state abstractions or changing finance contracts. |
| hooks | [switch](https://www.spaceui.one/hooks/switch) | TinyFish detail read | Reviewed; no additional runtime utility needed. Avoid duplicate lifecycle/state abstractions or changing finance contracts. |
| hooks | [cache](https://www.spaceui.one/hooks/cache) | TinyFish detail read | Reviewed; no additional runtime utility needed. Avoid duplicate lifecycle/state abstractions or changing finance contracts. |
| hooks | [cookie](https://www.spaceui.one/hooks/cookie) | TinyFish detail read | Reviewed; no additional runtime utility needed. Avoid duplicate lifecycle/state abstractions or changing finance contracts. |
| hooks | [event](https://www.spaceui.one/hooks/event) | TinyFish detail read | Reviewed; no additional runtime utility needed. Avoid duplicate lifecycle/state abstractions or changing finance contracts. |
| hooks | [format-bytes](https://www.spaceui.one/hooks/format-bytes) | TinyFish detail read | Reviewed; no additional runtime utility needed. Avoid duplicate lifecycle/state abstractions or changing finance contracts. |
| hooks | [format-content](https://www.spaceui.one/hooks/format-content) | TinyFish detail read | Reviewed; no additional runtime utility needed. Avoid duplicate lifecycle/state abstractions or changing finance contracts. |
| hooks | [format-date](https://www.spaceui.one/hooks/format-date) | TinyFish detail read | Reviewed; existing locale/date-only finance formatting retained. |
| hooks | [format-text](https://www.spaceui.one/hooks/format-text) | TinyFish detail read | Reviewed; no additional runtime utility needed. Avoid duplicate lifecycle/state abstractions or changing finance contracts. |
| hooks | [is-negative](https://www.spaceui.one/hooks/is-negative) | TinyFish detail read | Reviewed; no additional runtime utility needed. Avoid duplicate lifecycle/state abstractions or changing finance contracts. |
| hooks | [logger](https://www.spaceui.one/hooks/logger) | TinyFish detail read | Reviewed; no additional runtime utility needed. Avoid duplicate lifecycle/state abstractions or changing finance contracts. |
| hooks | [range-map](https://www.spaceui.one/hooks/range-map) | TinyFish detail read | Reviewed; no additional runtime utility needed. Avoid duplicate lifecycle/state abstractions or changing finance contracts. |
| hooks | [sleep](https://www.spaceui.one/hooks/sleep) | TinyFish detail read | Reviewed; no additional runtime utility needed. Avoid duplicate lifecycle/state abstractions or changing finance contracts. |

## Verification contract

`npm run build`, `npm run lint`, and the existing Vitest suite validate source compatibility. New shell regression tests exercise actual menu opening, independent deletion links, mobile Escape dismissal and focus restoration.

`node scripts/verify-spaceui-browser.mjs` launches the actual production frontend build at four widths and both themes. It uses explicitly labelled API contract fixtures to check rendering, navigation, console errors and document overflow. It does not establish real authentication, storage, checkout, bank sync or AI execution. Final integration against a real backend/session remains a separate verification boundary; no mock or bypass is shipped in application code.

PWA fonts/emoji are explicit public-cache assets; API data/write replay remains excluded. The release digest changes with the frontend assets.

## Bundle observation

The baseline entry asset was 695.69kB raw / 206.33kB gzip. The redesigned build entry is 741.27kB raw / 225.30kB gzip. This is an asset-size observation, not measured Core Web Vitals or complete initial-route transfer. Heavy showcase shaders, carousels and demo telemetry were excluded. Local fonts replace Google-hosted font requests; only required glyph subsets/weights are requested by the browser.

## Final checks (12 October 2026)

| Check | Evidence |
|---|---|
| Build and typecheck | Passed, production Vite build |
| Lint | Passed |
| Vitest | 111 test files, 884 tests passed |
| Chromium frontend contract sweep | 360 visits: 45 paths × 4 widths × 2 themes; zero detected uncaught errors, app-error-boundary renders or document overflow |
| Mobile interaction regressions | Drawer opening, Escape dismissal, focus restoration and independent deletion destinations passed |
| PWA browser checks | Desktop + mobile Chromium: manifest icons, privacy, offline deep links, waiting-update isolation, accepted update and rejected proxy shell passed |
| Diff scope | All 113 changed files are under frontend/; backend code unchanged |

Visual inspection used local screenshots of the real built frontend with clearly labelled synthetic API fixtures. This validates frontend rendering; production auth, real banking, payments, AI execution and physical-device install flows still require their respective real services/devices. No fixtures are imported into shipped application code.
