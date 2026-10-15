# Architecture decision - PROPOSED, awaiting owner decision

No architecture or production-routing change is authorized by this record. Both public hosts currently serve the financial Vite app; root `/` is a protected dashboard in App.tsx. Replacing it with marketing can break established journeys and is not a metadata-only change.

| Option | Concrete proposal | Benefit | Dependency/risk |
|---|---|---|---|
| A | Keep current apex and add explicitly owned public marketing routes, with rendered HTML | One public brand host; preserve root/dashboard | Need reviewed routing/build delivery for Next/static output alongside Vite and API; prevent PWA/SPA interception |
| B | Next marketing takes apex; finance app moves to a separate origin/path | Clear marketing/app separation long term | Highest migration risk: cookies, Clerk/OAuth, recovery, billing, API, PWA and existing links; separate approved project |
| C | Stage existing Next landing on proposed `discover.fincopilot.app`; retain current app hosts | Isolated reversible public marketing release; no login migration | Owner approves hostname/DNS; override existing wildcard explicitly; canonical/OG/sitemap must use new host; links continue to app; brand search spans hosts |

Working recommendation for review: C for an initial independent release if owner accepts the additional host; A remains viable after origin ownership is proved. This is not a completed choice. Do not edit `NEXT_PUBLIC_MARKETING_INDEXABLE` or publish new canonical URLs before approval and live acceptance.

## Public/private inventory

- Financial app root `/`, accounts, transactions, budgets, reports, goals, invoices, groups, agents and settings remain private as implemented by route/entitlement/workspace guards.
- `/login`, `/sign-in`, `/register`, `/sign-up/*`, `/sso-callback`, recovery/verification and OAuth callbacks are utility/auth routes. Audit server-visible noindex without weakening auth.
- `/i/:token` is a capability link with a credential; exclude from crawl/sitemap, analytics and probe inputs.
- `/pricing`, `/privacy`, `/terms`, `/support` are conditional public surfaces; eligibility requires current backend content, truthful claims and owner acceptance.
- `/api/*`, `/mcp`, files/downloads and private app URLs never belong in the marketing sitemap.

## Approval package and rollback

Before asking for cutover, prepare exact proposed host/records, current vs proposed routing, immutable tested deployment, link/callback/cookie inventory, CSP/cache/PWA checks and cost estimate. Keep the app/Tunnel/DNS untouched while preparing it. For C, rollback removes only the newly approved marketing binding/record and disables its indexing; for A/B, record exact old routing and an independently tested restore procedure first. Rollback is currently a specification, not a tested production action.

No public marketing generation should query finance APIs or the database. Prefer static output where feasible. Monitor at most the bounded URL budget in OPERATIONS.md. No new paid service proposed.
