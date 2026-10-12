# Landing — Space UI component decision register

## Evidence

User entry links reviewed via TinyFish: https://www.spaceui.one/docs, /primitives, /components, /tools, /interactions, /blocks, /hooks, /tools/avatars?type=squishmoji, /tools/motion, /components/animoji, /docs/skills and /docs/fundamentals/typography. Official Next.js installation and accessibility pages were also read.

Existing repo catalog frontend/docs/spaceui-catalog.json already records 265 item entries with 264 detail-page reviews, corresponding source mappings, upstream commit 6489d244d1652470efdc810a79a289ebd966c177: 61 primitives, 90 components, 9 tools, 13 interactions, 13 blocks and 79 hooks. That record is historical; actual chosen registry manifests and upstream code were re-fetched in this implementation.

## Implemented Space UI selections

| Area | Official Space UI artifact | FinCo implementation |
|---|---|---|
| CTA / navigation | primitives-button, primitives-link | Keyboard-focusable links for existing product routes |
| Cards / status | primitives-card, primitives-badge | Two-tone feature hierarchy and context labels |
| FAQ | primitives-accordion | Expand/collapse answers with Base UI semantics |
| Hero | components-spaceui-blur-reveal-text | Restrained focus-in headline |
| Background | block-interactive-grid-hero-1 ProximityGrid | Low-contrast hero geometry; motion disabled for reduced-motion |
| Mascot | @usespaceui/squishmoji/react | Local procedural illustration, not proof or an actual user |
| Utilities | lib-utils, SpaceUI typography guidance | Class merge, optical type scale, tabular-nums and touch targets |
| Motion | Space Motion skill + MotionConfig | Purposeful 150–350 ms interactions, reduced-motion safeguard |
| Iconography | Tabler + Lucide convention | Only Space UI-compatible icon families |
| Emoji | components-spaceui-animoji copied | Available as a local component, not overused in finance content |

## Evaluated, deliberately not inserted

Complex WebGL carousel/gallery blocks, motion-heavy demos, currency conversion simulations, agent telemetry, default sound, identity-free testimonial avatars, unrelated forms, payments, login/signup controls and arbitrary primitives would increase weight or imply unavailable product features. No component is applied only to satisfy a count.

## Originality and reference research

Design cues: Linear for a single clear promise and product-first proof; Mercury for calm fintech trust; Stripe for progressive visual explanations. There is no evidence those companies built using Space UI, and no such claim is made. No competitor graphics/copy/brand assets used.

## Safety and release

App remains deployed separately. CTA destinations are real paths but production availability is independently blocked in the 2026-10-12 audit. No fabricated customer counts, security certificates, revenue, returns, live bank coverage or performance numbers. Do not mark landing visually production-ready until real-browser and device tests have passed.


## Independent review follow-up

The original historical notes above describe the first draft. IMPLEMENTATION_BLUEPRINT.md and RELEASE_ACCEPTANCE.md are the current source/behavior records. Added real Tabs/Avatar/media-query adoption, actual app sample screenshots, visible and reduced-motion headline safeguards, default-off optional Space UI sound, self-hosted Animoji, font subsetting and comprehensive browser state scans. A direct official Showcase review now establishes conceptual examples (Rival/Sunabase/Oleap); this does not establish real customer success metrics.
