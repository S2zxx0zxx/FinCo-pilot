# Landing release acceptance — PR #81

This is the completion register for the user's thirteen-step sequence. Engineering work is on the existing landing branch. A row saying blocked is not a claim of completion.

| Step | Deliverable / evidence | State |
|---|---|---|
| 1 Latest state | main 8779483 refreshed and merged; branch baseline 70ec9bf; capture source tree check; refreshed open Draft PR #81 | Complete for recorded snapshot |
| 2 Requirements | This register + IMPLEMENTATION_BLUEPRINT.md + prior independent audit findings | Complete |
| 3 Research gaps | Official registry source, 265-entry CATALOG_DECISIONS.json, verified official Showcase / Rival / Sunabase / Oleap; source hashes and historical read limits | Complete assessment; no fabricated successful customer claims |
| 4 Blueprint | Visitor journey, section source mapping, alternatives, motion/responsive strategy and original brand exceptions | Complete |
| 5 Foundation fixes | Genuine Space UI Tabs/Avatar, keyboard semantics, menu Escape/focus, visible no-JS headline, reactive reduced motion, contrast | Implemented; actual browser evidence below |
| 6 Product presentation | Actual original Dashboard/Accounts screenshots, separate desktop/mobile, synthetic loopback fixtures, source/hash provenance | Complete; not a production E2E claim |
| 7 Space UI adoption | Primitives + official media-query hook + Squishmoji + self-hosted Animoji compass + lazy opt-in sounds; explicit source exceptions | Complete selected adoption |
| 8 Responsive polish | Nine widths, 44px preview targets, readable mobile specimen, matching mobile captures, no document overflow | Automated desktop/mobile viewports complete; physical devices pending |
| 9 Performance | Repeatable Lighthouse/resource scripts, PERFORMANCE_BASELINE.json; deferred emoji resolver/animation and desktop grid, subset fonts, compressed screenshots | Lab measurement complete; field/physical-phone INP pending |
| 10 Dedicated preview | Vercel project fincopilot-landing, root landing/, preserved default protection; final-head deployment metadata recorded in PR | Provisioned; final deployment is accepted only when READY and content verified |
| 11 Complete verification | Chromium local suite; pinned Chromium/Firefox/WebKit CI matrix; every sample-state axe scan; sound opt-in and preference change tests | Chromium local complete; exact-head CI results recorded in PR; physical VoiceOver/TalkBack pending |
| 12 Original app destinations | Real App.tsx path checks and separate TinyFish public conversion check; dedicated API readiness response | Blocked: API /ready returns 503 InvalidConfiguration; do not assert signup/login service works |
| 13 Final review/handoff | Refreshed main/head comparison, confined diff, reproducible lockfile, updated PR body and evidence | PR handoff complete when final CI/deploy checks are recorded; no finance-domain cutover or merge |

## Gates that must stay visible

- Public app health is an existing deployment/configuration problem. Earlier source audit also found legacy production DB schema incompatibility. Do not invent production settings, overwrite data, reset/stamp the database or bypass auth to make marketing links look successful.
- Marketing is its own Vercel project. The first isolated project deployment can receive a production-labelled platform target even though no finance custom domain is assigned. This is not a promotion of the finance application. Final review uses the branch deployment and retained protection; no apex/www/API DNS change.
- noindex is deliberate by default. SEO scores penalised for noindex are expected on previews. Set NEXT_PUBLIC_MARKETING_INDEXABLE=true only on accepted production environment/hostname. Canonical and share URL are currently the planned fincopilot.app origin and must be rechecked if the final marketing hostname differs.
- Safari-engine CI is WebKit automation, not testing a physical iPhone or VoiceOver. Physical device and field performance acceptance cannot be fabricated by a cloud agent.

## Browser acceptance

The committed suite scans all three illustrative states on 390 and 1440 widths, rather than only a scrolled-away state. It verifies ArrowRight/Home/End, ArrowDown vertical tabs, roving focus, panel associations, Escape focus restoration, actual screenshot source selection, no external asset requests, visible no-JS H1, live reduced-motion preference update, default-muted/opt-in/mute sound, FAQ and destination hrefs. Widths: 320,375,390,620,768,920,921,1024,1440.

## Performance interpretation

PERFORMANCE_BASELINE.json is a simulated-mobile Lighthouse run on a loopback production build. It is not field INP, authenticated app performance, 10k-user capacity or a guarantee on Android/iOS hardware. Intermediate profiling cut the initial resource snapshot from approximately 990kB to 440kB and total blocking time from approximately 320ms to under 100ms. Final measurements replace the intermediate values in the baseline file. noindex explains the preview SEO penalty.

## Reproduction

From landing/: npm ci; npm run verify. Start production server on port 3100, then npm run test:browser. LANDING_BROWSER=firefox or webkit selects another installed engine. npm run test:performance writes lab artifacts. To regenerate actual product specimens, build the unmodified frontend, serve its production output on loopback port 4173, then npm run capture:product. The capture script refuses a non-loopback origin, blocks external requests and injects only synthetic API fixtures. This is visual product evidence, not backend acceptance.

## Production route checklist (not executed here)

Before any apex landing replacement, confirm separate authenticated app origin, original /login /register /pricing /privacy /terms /support destinations, all original protected routes, /api and /mcp handling, OAuth and Clerk redirect allowlists, recovery/verification email links, payment callbacks, asset/PWA paths, no finance response public caching, and rollback origin/DNS values. Current task changes none of those production settings.

## 13 October follow-up status

Prior PR #81 was merged at c6c233ba. Current follow-up starts from 75df7e8; preserves all 34 subsequent commits and changes only landing/. Heading ref/hydration handling and full-width benefit tabs are repaired. Added official callback-ref useInView, finite labelled budget Meter, semantic process Timeline and decorative Separator; simplified surfaces and refined typography. Production test suite now checks settled unblurred H1, benefit panel width, 49/26/25 sample meter semantics, ordered process list and prior keyboard/reduced-motion/no-JS/asset/FAQ/CTA acceptance. Local clean build, TypeScript, four source contracts and Chromium nine-width/all-sample-state axe checks pass. PERFORMANCE_BASELINE.json records the new lab run (Performance 89 / Accessibility 100 / Best Practices 100; TBT 120ms / CLS 0). Exact-head CI and deployment are recorded in the follow-up PR after publication.

Research gate: full live inspection of every output/video is incomplete. Public endpoint rate-limited 606 demo requests; 26 snapshots were still loading; 10 captures failed. Do not claim 265 entries or 831 demos were all watched interactively. Selection sources, outcomes and exclusions remain explicit. Physical devices and real authenticated conversion remain external acceptance gates.

Current public check: login/register UI observed by TinyFish (run 546fd3e3-d323-4b90-b364-705ef8829eb2). Independent Support page returned HTTP 200 with “Customer support is not configured on this deployment yet.” Pricing/Terms/Privacy navigations timed out and remain inconclusive. Dedicated readiness is still HTTP 503 InvalidConfiguration. Prior Cloudflare 1033 on auth pages is historical, not today's observation. PUBLIC_JOURNEY_CHECK_20261013.json stores exact distinctions. No successful OAuth/signup/dashboard claim.
