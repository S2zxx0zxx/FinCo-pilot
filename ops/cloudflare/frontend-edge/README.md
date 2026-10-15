# Production frontend edge proxy

This module serves an immutable verified Vercel frontend artifact at the existing
app host. Worker **Routes**, not a Custom Domain, preserve the existing proxied
DNS/Tunnel destination for same-host `/api` requests. No backend or database
migration is performed. `/mcp` HTML fallbacks fail closed; a working MCP backend
must be supplied by the existing origin before advertising that capability.

Required plain-text bindings: APP_HOST=fincopilot.app,
FRONTEND_DEPLOYMENT_ORIGIN=https://<verified-immutable-deployment>.vercel.app,
FRONTEND_DEPLOYMENT_COMMIT=<exact-source-SHA>. Never use a moving branch alias.
The module has no secrets or storage bindings. Use an explicit compatibility
date; request logs, invocation logs, traces and Logpush remain disabled because
API URLs can contain recovery tokens or financial identifiers. Generic failures
are returned without replay, console logging or origin exception details.

Run `node --test ops/cloudflare/frontend-edge/worker.test.mjs` before upload.
Upload alone does not change traffic. Re-read existing routes before creating
only `fincopilot.app/*` for this module. Do not change DNS/Tunnel configuration.
Verify anonymous API status/body contracts, public config, configured Clerk UI,
production HTML, discovery MIME types, hashed assets, no-store errors/recovery,
PWA lifecycle and preserved artwork before retaining the route. Roll back by
deleting **only the route ID created by this rollout**; the old origin remains.
Do not remove unrelated routes or write private financial data during acceptance.

Source review: streamed responses, no request data in globals, all fetches awaited,
no passThroughOnException, no retries of API writes, no logs of headers/bodies.
Closed public-file routing is checked against every committed public asset.
Latest official references reviewed on 2026-10-14:
https://developers.cloudflare.com/workers/best-practices/workers-best-practices/
https://developers.cloudflare.com/workers/configuration/multipart-upload-metadata/
https://developers.cloudflare.com/workers/configuration/routing/routes/

Deployment is a separate acceptance step. Consult the deployment receipt;
absence of a receipt means source readiness, not a completed live rollout.

Vercel preview headers intentionally default to no-store, including missing
static files. Broad /static immutable headers also matched 404s in the actual
platform and were removed. Production nginx and this status-aware Worker keep
successful hashed files immutable while preventing stale cached errors.
