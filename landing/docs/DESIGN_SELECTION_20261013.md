# Landing refinement selections — 13 October 2026

Starting main: 75df7e80028eb3fa5b2bf7a49f7c6025da905a89. Prior landing PR #81 is merged. main has 34 commits after that merge; compare lists auth/Sentry/FX changes, no landing changes. This branch preserves those changes and modifies only landing files.

## Preview evidence and limits

Official source revision: 6489d244d1652470efdc810a79a289ebd966c177. The 265-entry catalog remains the requirement register. Current local MDX reading discovered 841 references / 831 unique demo IDs; every unique URL was attempted. HTTP 429 dominates the unavailable outcomes. Some successful HTTP responses still showed `Loading preview...`, and several screenshots timed out. Eleven contact sheets were inspected; a static snapshot does not establish all interactive states or an entire video. SPACEUI_PREVIEW_REVIEW_20261013.json preserves entry-level demo IDs and outcomes. It does not label all 831 outputs as reviewed successfully. Full live visual review is still incomplete.

TinyFish Motion playground: https://agent.tinyfish.ai/runs/d86374a3-eca0-41c9-98aa-e9b40db8f703. Exercised Showcase Stream, Sphere Wall and Grid Reveal plus restart/timing/ratio controls. These are media showcase compositions, not drop-in landing components. No exported template media/code was copied. Pro demos may be observed publicly; no gated Pro interaction source was imported.

## Concrete selections

| Location | Selected official source | Output observed / reason | Adaptation |
|---|---|---|---|
| H1 reveal | blur-reveal-text + hooks/animation/use-in-view | Prior heading remained blur(7px) after settling; source hook has callback ref and missing-observer fallback | Stable native heading across hydration, explicit per-word animation, cap stagger at 300ms, above-fold immediate trigger; server/reduced-motion text readable |
| Sample Budgets tab | primitives/meter | Meter-01 renders labelled finite bar; meter-03 shows bounded rating. Meaningful allocation is clearer than an unrelated trend chart | Three labelled sample plan shares 49/26/25, matched existing ₹12,200/₹6,400/₹6,200 illustrative rows; rounded percentages, not a financial recommendation or live progress |
| How it works | components/spaceui/timeline | Timeline-05 connected milestones; timeline-11 readable event feed | Three semantic ordered-list items; horizontal desktop and stacked mobile; no falsely completed onboarding state |
| Product boundary | primitives/separator | Minimal semantic divider source | Decorative proof-section rule; hidden from assistive technology |
| Benefit selector | existing official Tabs | Keyboard behavior already exists; default vertical flex-row squeezed description | Preserve ArrowDown semantics; override composition to stacked full-width panel |
| Surface finish | Space Motion skill, typography docs | Two-tone Frame/card examples and restrained type hierarchy | Remove decorative hero glow and excess shadows; continuous-corner enhancement with radius fallback; balanced headings and tabular figures |
| Avatar, emoji, sounds, tabs, FAQ, hero grid | Existing source-adopted implementations | Already part of page; no need to duplicate | Retain procedural identity, self-hosted compass, explicit sound opt-in, responsive product pictures and lightweight desktop decoration |

## Decisions by category

- Primitives: buttons/links/cards/badges/accordion/tabs/avatar already map to real landing controls; Meter and Separator add useful semantics. Inputs, authentication dialogs, calendars and data tables belong to the original app, not an invented marketing form.
- Components: Timeline adopted; animated typography retained with reliability fixes. Morphing text was seen in a snapshot, but swapping financial claims would interrupt reading. Heavy orbs, fluid-dither galleries and shaders have no product-explanation advantage here.
- Interactions: agent feed snapshot communicates agent execution; it would imply a live finance service if transplanted. Keep original optional-AI description; no fake pipeline, rating or activity feed.
- Blocks: earlier official Showcase references remain conceptual. Preserve actual product evidence rather than import unrelated banking/AI demo claims or gated block code.
- Hooks: add callback-ref useInView; retain useMediaQuery. Do not install clipboard/storage/form hooks without an actual visitor task.
- Tools: Squishmoji and Animoji are already used. Motion tool evaluated via interaction. Sounds remain optional; no ambient music/autoplay. Typography rules use self-hosted Open Runde, controlled measure and balanced/pretty wrapping.

## Skill application

Read official Space Motion SKILL.md, timing.md and resources.md; Space Interactions SKILL.md; typography.mdx. Film-export principles do not create a request for a marketing video. Interaction-specific reicon exclusivity applies to new flagship interaction cards; this change uses general primitives/components with the site's existing Space UI icon-family provenance. No new flagship interaction is claimed. React best-practices review: stable refs, no conditional hooks, source preserved, no finance fetches, explicit ARIA, no unnecessary new dependencies.

## Acceptance still requiring external evidence

Physical Android/iPhone and VoiceOver/TalkBack cannot be substituted by Playwright emulation. Full authenticated signup → SSO → dashboard requires an authorized usable account; read-only public checks cannot establish it. Domain cutover, database changes and app authentication changes remain outside this landing PR.

Scrollspy was also source-inspected and excluded: its cleanup creates a new scrollTo(item) function when removing the click listener instead of retaining the registered function. Adopting it for an active-nav effect would need a separate listener-lifecycle repair. Native anchor navigation is retained.
