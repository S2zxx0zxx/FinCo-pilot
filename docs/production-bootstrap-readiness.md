# Production configuration rejection on Vercel

Vercel previously imported `app.main` before any route was usable. Invalid
production Settings therefore produced platform HTTP 500 rather than the
application's dependency-aware readiness response. The current observed API
configuration is incomplete; this change does not supply missing credentials.

`backend/pyproject.toml` explicitly selects `app.vercel_entry:app`, following
[Vercel's FastAPI entrypoint documentation](https://vercel.com/kb/guide/ship-a-fastapi-app-on-vercel).
The bootstrap validates the original Settings before importing DB, auth or domain
modules. Valid configuration returns the exact original `app.main.app` instance,
including existing routes, guards, middleware and lifespan behavior.

Only a Settings `ValidationError` selects a restricted diagnostic application:

| Request | Result |
| --- | --- |
| GET/HEAD `/api/health`, `/api/health/live` | 200, process alive, `application_ready: false` |
| GET/HEAD `/api/health/ready` | 503, sanitized `InvalidConfiguration` |
| All other HTTP paths/methods | 503, no domain/auth/setup/docs/provider/metrics routes |
| Any WebSocket | Rejected before accept |

Responses use no-store, nosniff and server-generated request references; 503
responses include Retry-After. Validation details, credentials, environment
values, incoming tokens and financial bodies are not returned or logged by the
bootstrap. An unrelated import/runtime exception still fails normally rather
than being mislabeled as missing configuration. Container, worker, migration
and MCP entrypoints retain strict startup validation.

## Release and acceptance

Focused tests cover restricted endpoint behavior, secret-bearing validation
errors, a fresh production subprocess without DB/auth imports, WebSocket denial
and identity with the original app when Settings is valid. Required full CI
still gates the final commit. After deployment, confirm direct liveness 200 and
readiness 503, including no-store and an unavailable domain route. Do not treat
liveness as launch readiness. After actual provider configuration is complete,
redeploy and require the original application's schema/DB/Redis readiness plus
real user/provider journeys. A running instance does not hot-reload settings.

No production credentials, schema or data are mutated by this milestone. Legacy
conversion, infrastructure provisioning and provider acceptance remain separate
dependencies in the production master plan.
