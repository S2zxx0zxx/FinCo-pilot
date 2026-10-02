# FinCo-Pilot Production Secret Management V1

Status: engineering contract for roadmap **#13 — Production secret management**.

Contract ID: `FINCO_PRODUCTION_SECRET_MANAGEMENT_V1`  
Machine-readable source: `backend/app/core/secret_management.py`

This document defines how production credentials are classified, delivered,
rotated and verified. It never contains real credentials.

## 1. Non-negotiable rules

1. Real secrets never enter Git, PR bodies/comments, issue text, screenshots,
   chat, frontend bundles, `VITE_*` variables, documentation examples or
   copied terminal output.
2. A credential that was exposed is **rotated/revoked**, not merely deleted
   from the latest file.
3. Production Compose receives secret values from read-only files under
   `/run/secrets`; secret values are not interpolated into
   `docker-compose.prod.yml` service environments.
4. Kubernetes production uses an operator-managed existing Secret. The chart
   refuses `deploymentEnvironment=production` without
   `global.existingSecret`.
5. Provider credentials use least privilege and a dedicated FinCo-Pilot
   credential where the provider supports it. Do not reuse personal/admin/root
   credentials as application runtime keys.
6. Application signing secrets, MCP signing secrets and provider API keys are
   separate. One compromise must not automatically compromise every boundary.
7. Rotation is an operational change: update the secret store, restart only the
   required consumers, smoke-test, then revoke the old provider credential.
8. Never reset OmniRoute persistence or regenerate unrelated OmniRoute secrets
   as part of a FinCo-Pilot key rotation.

## 2. Supported production delivery paths

### Docker Compose

Set the non-secret host path:

```env
FINCOPILOT_SECRETS_DIR=/srv/fincopilot/secrets
```

`docker-compose.prod.yml` mounts that directory read-only as
`/run/secrets`. Pydantic Settings reads files from
`CREDENTIALS_DIRECTORY=/run/secrets`.

Recommended host permissions:

```bash
sudo install -d -m 0700 /srv/fincopilot/secrets
sudo chmod 0600 /srv/fincopilot/secrets/*
```

The directory must be owned/readable only by the deployment principal required
to start the containers. Do not put the directory under the repository.

Provider values should be written from a password manager/secret manager
without placing the literal value in shell history. For operator-generated
high-entropy signing material, use a cryptographic generator and write the
result directly to the protected file.

The bundled PostgreSQL container receives only
`/run/secrets/postgres_password` through Docker's secret-file mechanism and
uses `POSTGRES_PASSWORD_FILE`. Application services receive the protected
secret directory because they have multiple independent runtime credentials.

### Kubernetes / Helm

Production values must contain:

```yaml
global:
  existingSecret: fincopilot-production-secrets
config:
  deploymentEnvironment: production
```

The externally-created Secret uses the **uppercase runtime names**, e.g.
`SECRET_KEY`, `DATABASE_URL`, `SMTP_PASSWORD`,
`AGENTS_MCP_JWT_SECRET` and `AGENTS_OPENAI_COMPAT_API_KEY`.

Do not commit a Kubernetes Secret manifest with real `data` or `stringData`.
Enable encryption at rest for Kubernetes Secret data, restrict
`get/list/watch` using least-privilege RBAC and prefer a supported external
secret store / CSI integration when the deployment platform provides one.

### Managed hosting

A platform secret manager that injects environment variables at runtime is
acceptable when it prevents values from entering source control, build logs and
frontend assets. Pydantic environment values intentionally take precedence over
secret files, so do not configure the same credential in two places.

## 3. Canonical secret inventory

| Runtime name | Compose file | Required when | Rotation effect |
| --- | --- | --- | --- |
| `SECRET_KEY` | `secret_key` | every production deployment | all application JWT sessions become invalid |
| `DATABASE_URL` | `database_url` | every production deployment | coordinate DB credential + app restart |
| `POSTGRES_PASSWORD` | `postgres_password` | bundled PostgreSQL | coordinate DB credential + `DATABASE_URL` |
| `SETUP_TOKEN` | `setup_token` | temporary bootstrap enabled | disable bootstrap after first admin |
| `SMTP_PASSWORD` | `smtp_password` | authenticated SMTP | provider revoke/replace |
| `METRICS_TOKEN` | `metrics_token` | production metrics enabled | restart metrics consumer |
| `RAZORPAY_KEY_SECRET` | `razorpay_key_secret` | Razorpay runtime enabled | provider revoke/replace |
| `ZOHO_DESK_CLIENT_SECRET` | `zoho_desk_client_secret` | direct Zoho tickets | provider revoke/replace |
| `ZOHO_DESK_REFRESH_TOKEN` | `zoho_desk_refresh_token` | direct Zoho tickets | provider revoke/replace |
| `PLUGGY_CLIENT_SECRET` | `pluggy_client_secret` | Pluggy enabled | provider revoke/replace |
| Enable Banking private key | `enable_banking_private.pem` | Enable Banking enabled | provider key replacement |
| `OIDC_CLIENT_SECRET` | `oidc_client_secret` | confidential OIDC client | provider revoke/replace |
| `OPENEXCHANGERATES_APP_ID` | `openexchangerates_app_id` | production FX provider required | provider revoke/replace |
| `STORAGE_S3_ACCESS_KEY` | `storage_s3_access_key` | S3 storage | provider revoke/replace |
| `STORAGE_S3_SECRET_KEY` | `storage_s3_secret_key` | S3 storage | provider revoke/replace |
| `AGENTS_MCP_JWT_SECRET` | `agents_mcp_jwt_secret` | agents enabled | all MCP JWTs become invalid |
| `AGENTS_OPENAI_API_KEY` | `agents_openai_api_key` | operator OpenAI route | provider revoke/replace |
| `AGENTS_ANTHROPIC_API_KEY` | `agents_anthropic_api_key` | operator Anthropic route | provider revoke/replace |
| `AGENTS_OPENAI_COMPAT_API_KEY` | `agents_openai_compat_api_key` | authenticated OmniRoute/OpenAI-compatible route | provider revoke/replace |
| `AGENTS_EMBEDDING_OPENAI_API_KEY` | `agents_embedding_openai_api_key` | remote embeddings | provider revoke/replace |

`REDIS_URL` is a canonical production secret under roadmap #15. Production
requires an authenticated external Redis target over TLS, so the full URL is
always secret material. Compose reads it from `/run/secrets/redis_url`; Helm
reads `REDIS_URL` from the operator-managed existing Secret. See
[`FINCO_PRODUCTION_REDIS_WORKERS_V1.md`](./FINCO_PRODUCTION_REDIS_WORKERS_V1.md).

Cloudflare R2 is the selected roadmap #16 object-storage provider. Its S3
Access Key ID and Secret Access Key remain provider credentials even though the
first value is named "access key". Production Compose reads them from
`/run/secrets/storage_s3_access_key` and
`/run/secrets/storage_s3_secret_key`; Kubernetes reads the uppercase names
from the operator-managed existing Secret. Rotate both as one provider
credential set and run
`python -m scripts.verify_production_object_storage` before revoking the old
set. See
[`FINCO_PRODUCTION_OBJECT_STORAGE_V1.md`](./FINCO_PRODUCTION_OBJECT_STORAGE_V1.md).

The machine-readable inventory is authoritative if this table ever drifts.

## 4. Source precedence and why production Compose changed

Pydantic Settings resolves higher-priority environment/.env values before file
secrets. Therefore merely mounting `/run/secrets` was insufficient while
`docker-compose.prod.yml` still interpolated the same credential into the
service environment.

V1 removes the sensitive application mappings from production Compose. This
prevents commands such as expanded Compose configuration inspection and process
environment inspection from becoming the normal storage path for those values.

Local `docker-compose.yml` retains environment compatibility for development.
That is not the production secret-delivery contract.

## 5. Rotation playbooks

### Provider-issued API/OAuth credential

Use when rotating Razorpay, Zoho, SMTP, Pluggy, OIDC, storage, FX or AI
provider credentials:

1. Create/authorize a new least-privilege credential at the provider.
2. Put only the new value into the production secret store.
3. Restart the minimum consumer set from the machine-readable registry.
4. Run the provider-specific smoke test.
5. Confirm no auth errors or fallback to an unintended provider.
6. Revoke the old credential at the provider.
7. Run the smoke test again after revocation.
8. Record only the credential identifier/version and rotation timestamp in the
   operator log — never the value.

When a provider cannot overlap old/new credentials, use a controlled
maintenance window and fail closed rather than silently falling back.

### `SECRET_KEY`

`SECRET_KEY` signs application credentials. Rotation intentionally invalidates
existing application JWT sessions.

1. Announce/choose a maintenance boundary.
2. Generate a new independent high-entropy value.
3. Replace `secret_key`.
4. Restart API/workers that load Settings.
5. Require users to sign in again.
6. Verify login, logout, password reset/verification and protected APIs.
7. Destroy the old value.

Do not rotate `SECRET_KEY` merely because another provider key changed.

### `AGENTS_MCP_JWT_SECRET`

This key is shared only by FinCo-Pilot backend and its MCP server.

1. Replace `agents_mcp_jwt_secret`.
2. Restart backend and MCP server in the same change window.
3. Treat all previously minted external MCP tokens as revoked.
4. Reissue only the external MCP credentials users still need.
5. Verify a new token succeeds and an old token fails.

Do not reuse `SECRET_KEY` here.

### Database credential

For bundled PostgreSQL, `postgres_password` and the password embedded in
`database_url` must describe the same effective database credential.

Change the database role password and application connection secret as one
coordinated operation. Restart API, workers, beat, migration/MCP consumers and
verify migrations/read/write health before deleting the old credential path.

Roadmap #14 owns the final production PostgreSQL host/backup acceptance.

### Redis credential / endpoint

Treat a Redis credential or managed endpoint rotation as a coordinated runtime
change because API rate limits/state, distributed locks, Celery broker and
Celery result metadata share the target.

1. Provision the replacement authenticated TLS endpoint/credential.
2. Write the new `redis_url` secret without printing it.
3. Restart API, workers, Beat and MCP consumers in a controlled window.
4. Run the Redis-only probe, then the live worker round-trip probe.
5. Confirm exactly one Beat scheduler is healthy.
6. Revoke the old Redis credential/endpoint after the replacement passes.
7. Do not copy queued/result keys between providers as if Redis were durable
   financial storage; PostgreSQL remains the financial source of truth.

### OmniRoute / Core Copilot credential

`AGENTS_OPENAI_COMPAT_API_KEY` should be a dedicated inference credential for
the approved FinCo-Pilot OmniRoute route.

Rotate that inference credential without deleting OmniRoute volumes, resetting
its database, regenerating unrelated provider credentials or changing the
approved `fincopilot-free-smart` routing contract. After rotation, verify
authenticated `/v1/models` and one real model smoke test. Roadmap #6/#49/#50
remain the provider/model and live-AI acceptance gates.

## 6. Compromise response

If a secret appears in chat, a screenshot, terminal recording, issue, PR,
committed file, log or other uncontrolled location:

1. Assume the value is exposed.
2. Revoke/rotate it at the authority that issued it.
3. Replace the production secret-store value.
4. Restart affected consumers.
5. Invalidate dependent sessions/tokens when the inventory says rotation has
   that effect.
6. Verify the old credential fails and the replacement succeeds.
7. Search current logs/build artifacts for accidental copies without printing
   the replacement.
8. If it entered Git history, rotation is mandatory even after a history
   rewrite. Coordinate any history cleanup separately.

A previously exposed Zoho OAuth client/refresh credential must therefore be
replaced before roadmap #7 is considered fully operationally accepted.

## 7. CI and repository guardrails

`python3 backend/scripts/check_secret_hygiene.py` fails when the current tree
contains:

- tracked deployable `.env` files;
- recognized high-confidence token/private-key patterns;
- direct application `os.getenv` / `os.environ` reads of canonical secrets;
- canonical secret values mapped directly into production Compose;
- missing production secret-delivery markers.

The Helm CI additionally proves:

- production rendering fails when `global.existingSecret` is absent;
- the same production chart lints/renders when an external Secret name is
  supplied.

These checks do not prove that a credential was never exposed historically.
Provider revocation and repository/platform secret scanning remain part of
incident response.

## 8. Safe verification

Safe commands do not print resolved secret values:

```bash
python3 backend/scripts/check_secret_hygiene.py
docker compose -f docker-compose.prod.yml config --quiet
helm lint charts/fincopilot
```

Avoid `docker compose config` without `--quiet` on an environment that may
still contain legacy secret variables. Do not use `env`, `printenv`, shell
tracing (`set -x`) or debug dumps as a credential test.

## 9. Acceptance boundary for roadmap #13

Engineering #13 is complete when:

1. the canonical inventory and rotation semantics are merged;
2. agent/operator secrets use typed settings instead of direct OS lookups;
3. production Compose uses mounted files and PostgreSQL's password-file path;
4. production Helm requires an existing Secret;
5. CI secret-hygiene + full backend/frontend/migration/Helm checks are green;
6. no real credential is added to Git.

Actual secret-manager provisioning on a public production host is necessarily
verified with the hosting/deployment work in roadmap #1/#2/#13 and provider
acceptance items. Code/CI green status must never be described as proof that
unprovisioned external secrets exist.
