# HeroUI v3 landing replacement — 17 October 2026

The owner rejected the Ant Design version of PR #99 and requested a complete HeroUI v3 replacement. Main was fetched again at `887eaee578c8766b5757c057473ed20c7ab6c52e`; PR #99 was open and unmerged at `43385a9e6fd9eccda292b17dee33bf85857d046b`. Recent PRs #95–99 were checked for overlapping public routing, discovery, identity and branding work. This change updates the existing isolated review branch, avoiding competing landing redesign PRs. It does not merge other open work.

## Verified library integration

Registry reads and installed package metadata confirm `@heroui/react@3.2.6` and `@heroui/styles@3.2.6`. Official quick-start requirements are React 19+ and Tailwind 4, already used by this package. The documented CSS order is Tailwind first, then HeroUI styles. The v3 compound APIs were read before implementation and checked against installed TypeScript declarations. No v2 HeroUIProvider, tailwind plugin or v2 component API is assumed.

Official pages read through TinyFish on this date:

- https://heroui.com/en/docs/react/getting-started/quick-start
- https://heroui.com/en/docs/react/components/card
- https://heroui.com/en/docs/react/components/button
- https://heroui.com/en/docs/react/components/link
- https://heroui.com/en/docs/react/components/drawer
- https://heroui.com/en/docs/react/components/accordion
- https://heroui.com/en/docs/react/components/tabs
- https://heroui.com/en/docs/react/components/number-field
- https://heroui.com/en/docs/react/components/alert
- https://heroui.com/en/docs/react/components/progress-bar

The supplied raw MDX URL and guessed installation URLs returned 404. Current canonical quick-start and component pages supplied the actual APIs; no API was inferred from the user's category-only index.

## Complete replacement map

| Interface | HeroUI v3 implementation |
| --- | --- |
| Navigation and actions | Link, Button, Drawer with native overlay state |
| Monthly illustration | Card compound parts, Chip, Separator, ProgressBar |
| Six feature explanations | Card, Chip, Link |
| Real product captures | Tabs.ListContainer, Tabs.List, Tabs.Tab, Tabs.Indicator, Tabs.Panel |
| Local reserve example | NumberField, Label, Alert and Card |
| Three onboarding steps | Semantic ordered list of HeroUI Cards and Chips |
| Import guide and sample | Card, Chip, Link |
| Privacy and boundaries | Cards and Links |
| Ten FAQs | Accordion compound parts |
| Closing action and footer | Card, Chip, Links and Separator |

All loaded homepage primitives now use HeroUI. Page composition and responsive spacing use CSS, with white, sage and forest tokens, larger rounded surfaces, pill controls, a new monthly-summary composition and rewritten introductory copy. Supporting documentation inherits the new typography and palette. The self-hosted font, actual application captures and their synthetic-data provenance remain in place. The wordmark stays text-only. The social card follows the new palette.

Removed all Ant packages and their transitive dependencies from this package, AntdRegistry, ConfigProvider wrapper, fixed Ant theme, static extractor and generated stylesheet hook/ignore entry. HeroUI styles compile as ordinary CSS under the existing frontend `ignore-scripts` policy. Historical Ant evidence and unused Space UI files/licenses remain as history; they are not loaded by the new page.

## Preserved product boundaries

- Existing registration, login, pricing, support and policy destinations, same-origin `/welcome/` export, installed-app handoff, canonical/discovery policy and noindex preview controls.
- Six source-backed feature descriptions, onboarding/import guide and CSV, ten answers explaining current configuration and format limits. No invented customers, certifications, pricing or bank coverage.
- Every example amount is synthetic. The demo is local arithmetic, not a finance API or affordability recommendation. Product images are actual captures of synthetic records.
- No backend, authentication, payments, financial records, database, DNS or production environment mutation. Owner reviews and merges separately.

## Verification and fixes

TypeScript, 19 source/publication contracts and a normal optimized Next build passed. Initial production-browser acceptance passed all nine widths (320, 375, 390, 620, 768, 920, 921, 1024, 1440), seven WCAG AA states with zero violations, keyboard tabs, drawer Escape/focus return, FAQ, demo positive/zero/negative/empty states, responsive images, sample CSV, no-JS styles, reduced motion, skip link and zero third-party requests. Documentation passed 12 page/viewport checks and three no-JS pages.

HeroUI NumberField intentionally exposes an accessible textbox with `aria-roledescription="Number field"`, not the old Ant spinbutton role. The test uses its actual accessible role and label. Screenshot review then caught a fourth child in NumberField.Group wrapping its grid controls. Currency formatting now comes from the native NumberField API; the extra prefix node was removed. A geometric regression requires the input and both steppers to fit within the group at every width; ArrowUp/ArrowDown also verify reserve calculations. A missing space at a responsive line break was corrected. Assertions, contrast thresholds and focus checks were retained.

Final build/browser/CI/deployment receipts are recorded in the PR description at its current exact commit. Earlier Ant metrics and earlier head checks are historical, not evidence for this replacement. Local Lighthouse is simulated mobile on loopback, not physical-device or field Core Web Vitals; do not infer a controlled speed improvement from separate samples.

React quality review: state is local to the drawer and calculator; no financial API/data fetching or effect chains were added. Derived remainder is computed directly. Lists use stable content keys. Overlay/tab/field/accordion semantics come from HeroUI/React Aria; interactive navigation remains link-based. Global reduced-motion handling, visible focus and server-rendered heading/style checks are preserved.

First hosted CI at `42af20b` caught a Firefox test race reading the previous tab's image before selection committed, and a WebKit collapsed-FAQ visibility failure. The tab check now waits for the named Accounts panel before inspecting its image. React Aria sizes panels with asynchronous animation promises and sets `hidden="until-found"`; explicit CSS keyed to its existing `aria-hidden=true` keeps collapsed panels at zero height and invisible across engines, including late size completion. The FAQ test now also requires its answer to become hidden. No timeouts, keyboard checks, contrast rules or visibility assertions were removed. Fresh exact-head three-engine runs are required after this correction.

At `ca544ad6`, all three strict-Nginx engines passed and standalone Chromium/WebKit passed, but Firefox still did not select Accounts at the first 320px touch viewport; waiting alone did not resolve it, so the first diagnosis of a read race was insufficient. The acceptance harness had declared `hasTouch=true` but dispatched mouse clicks. Mobile controls now receive actual touchscreen taps; desktop widths retain mouse clicks, and keyboard selection remains independently checked. No fallback activation or retry masks a failed selection. Fresh Firefox results determine acceptance. The local Firefox automation runtime also stalls before loading a page, so GitHub's native Firefox runner is used for that engine's evidence.

The touch run at `4fa62a2` caught a Chromium axe scan during HeroUI's native drawer fade: computed text colors were temporarily blended by backdrop opacity. The old hard-coded `aria-busy=false` marker was removed. The harness now waits for React Aria entering attributes to clear and actual subtree animations to finish before scanning; the original 5-second readiness bound and every contrast assertion remain. FAQ/keyboard checks also wait for their public expanded/selected state before asserting it, preserving the expected behavior rather than assuming a render has committed immediately after input.
