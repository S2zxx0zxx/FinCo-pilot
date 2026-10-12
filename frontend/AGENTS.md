# Frontend Space UI guidance

Before changing frontend UI, read `docs/SPACEUI-REDESIGN.md` and the relevant entries in `docs/spaceui-catalog.json`.

For motion, read `docs/spaceui-reference/space-motion/SKILL.md` and its linked timing guidance. For interactive composition, read `docs/spaceui-reference/space-interactions/SKILL.md` and its linked rules. These are vendored upstream references, not CLI-installed skills. Apply interface guidance to this app; film/export instructions apply only when the requested task is a film.

Use two-tone surfaces, local Open Runde headings and Inter body text, continuous corners with fallback, bounded motion, faster closure and reduced-motion support. Preserve existing Radix/native form APIs, authentication, query scoping, financial precision, roles, billing entitlements and API payloads. Do not import showcase telemetry or synthetic QA fixtures into app code.

Record concrete source-to-app decisions. Distinguish copied source, adapted patterns, inherited styles, reviewed-but-unused items and unverified acquisition. Never describe a source review as a runtime integration or a shared theme change as a custom page rewrite.

Validate changed behavior with the appropriate build/lint/test checks. Browser contract fixtures do not establish real service integration. Keep backend work outside a frontend-only task.
