# Original-order audit — 12 October 2026

Repository: S2zxx0zxx/FinCo-pilot. PR: #75. This audit distinguishes research from shipped implementation.

| Original requirement | Evidence and actual result | Remaining boundary |
|---|---|---|
| Read docs, skills and typography first | Initial research and vendored source references; skills/typography fetched again on 12 October | The upstream example typography scale is adapted to finance UI, not copied pixel-for-pixel |
| Crawl every supplied category | 265 detail links indexed: 61 primitives, 90 components, 9 tools, 13 interactions, 13 blocks, 79 hooks | This is the discovered catalog at the pinned source, not a guarantee about all future site additions |
| Read every detail page | 264 TinyFish detail fetches succeeded; Plush official source metadata inspected | Plush web extraction timed out again during this audit; no successful live extraction claimed |
| Adopt skills | Space Motion and Space Interactions references vendored; interface timing/composition rules used | Previously documentation-only discovery. Added frontend/AGENTS.md to route future frontend work to these references; no standard .agents/skills installation claimed |
| Choose fitting variants and use Space UI | Shared control adapters, source Empty/Frame/Meter, shell/sheet, theme reveal, auth reveal, usage composition, local identities and emoji | Not all 265 entries imported. Unused items have ledger decisions; those decisions are engineering selections, not user approval or proof each was objectively best |
| Upgrade whole frontend | All 38 page implementations inherit typography/tokens/shared controls; ledger classifies 28 as direct surface/composition changes and 10 as inherited changes | Existing specialist layouts, charts, calendars and business logic remain. This is not 38 separate page rewrites |
| Use tools, avatars and emoji | Local Squishmoji identities and self-hosted coin/target assets | Fur editor, image splitter, film export and other authoring tools are reviewed, not embedded as app features |
| Use hooks | Source useMediaQuery and useClipboard adopted | Remaining utilities are reviewed and retained/excluded as recorded; no claim all 79 hooks/utilities are runtime dependencies |
| Keep frontend scope | All changed files within frontend; backend contracts retained | Real authenticated backend/payment/bank/AI flows are not validated by synthetic browser fixtures |
| Create PR | #75 exists on correct repository; previous head has successful GitHub CI and Vercel preview statuses | PR remains open; no merge or production promotion performed |

## Gaps addressed during this audit

- Added discoverable frontend instructions pointing future agents to the vendored Space UI references.
- Popover previously inherited timing/corners but retained its original border/shadow classes. Added a source-informed two-tone adapter, bounded viewport width, and retained Radix focus/position/form contracts.
- Tooltip still retained original shadow styling and lacked shared panel timing. Adapted the published popover-tone surface, matching arrow, continuous corners and open/close timing. Reduced-motion rules continue to cover both controls.

## Honest completion statement

The delivered frontend is a selective Space UI integration with shared system coverage and documented research, not a wholesale replacement with every library item. Review-only items are not unfinished implementations automatically. If the requirement is literally to install every catalog entry or rewrite every specialist page, that requirement has not been fulfilled and is not claimed here.

The existing production build, lint, 884-test suite, 360 synthetic browser route visits and PWA checks establish frontend compatibility at the initial PR head. Follow-up build/lint and browser checks validate the small adapter changes separately. CodeRabbit skipped its automated review because the file count exceeded its limit; a success status from that bot does not constitute a completed review.

Follow-up validation: production build/typecheck and ESLint passed; both actual-shell regression tests passed; the quick Chromium fixture sweep passed all five visits with zero reported failures. The missing browser executable was restored before this follow-up sweep. The full 360-visit matrix was not rerun for these styling/instruction changes.
