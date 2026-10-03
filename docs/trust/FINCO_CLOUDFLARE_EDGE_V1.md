# FinCo-Pilot Cloudflare Edge V1

Status: **account-side edge resources provisioned; durable-origin/live acceptance remains release-gated.**

This runbook defines the zero-cost Cloudflare edge path selected for FinCo-Pilot. It does not claim that a Cloudflare Tunnel replaces the production compute host, database, Redis, backups, SMTP, or other roadmap gates.

## 1. Selected architecture

```text
Browser
  -> Cloudflare DNS / TLS edge
  -> remotely managed Cloudflare Tunnel
  -> frontend Nginx :8080
  -> /api -> backend FastAPI :8000
```

Public launch hostname:

```text
https://fincopilot.satzzxzxx.me
```

Remote tunnel name:

```text
fincopilot-origin
```

The existing root `satzzxzxx.me` GitHub Pages records and existing mail records are intentionally left unchanged.

Cloudflare Pages and Workers are not used as a replacement application runtime: FinCo-Pilot has FastAPI, PostgreSQL, Redis/Celery, migrations and long-lived server processes. Cloudflare Containers also is not enabled by this contract; the connected account currently requires a paid Workers plan for Containers, and no paid plan is authorized by this setup.

## 2. DNS and tunnel contract

The dedicated FinCo-Pilot hostname is a proxied CNAME to the remotely managed Tunnel. The Tunnel's remote ingress is:

```text
fincopilot.satzzxzxx.me -> http://frontend:8080
catch-all                 -> http_status:404
```

Do not expose backend port 8000 publicly. Production Compose binds backend and frontend diagnostic host ports to loopback only. Public traffic reaches the frontend over the Tunnel and reaches the backend only through the frontend reverse proxy.

The tunnel connector token is a secret. Never put it in Git, documentation, screenshots, chat, Compose environment interpolation, or a public `.env`.

Production host file:

```text
${FINCOPILOT_SECRETS_DIR}/cloudflare_tunnel_token
```

The `cloudflared` service receives only that dedicated secret.

## 3. Required production non-secret configuration

For the selected hostname:

```env
FRONTEND_URL=https://fincopilot.satzzxzxx.me
TRUSTED_PROXY_HOPS=2
CLOUDFLARED_VERSION=2026.9.3
```

Two trusted hops are expected in this topology: Cloudflare/cloudflared and the frontend Nginx proxy before FastAPI. A different reverse-proxy chain must set `TRUSTED_PROXY_HOPS` to its verified topology rather than copying this value blindly.

The frontend Nginx config preserves an incoming trusted `X-Forwarded-Proto: https` value instead of overwriting it with the local HTTP hop from cloudflared to Nginx. Unknown values fall back to the local scheme.

## 4. Cloudflare R2 boundary

Production attachment storage remains a separate private Cloudflare R2 boundary.

Selected private bucket:

```text
fincopilot-prod
```

Observed provider configuration:

- Standard storage class;
- APAC location hint;
- default jurisdiction;
- public `r2.dev` access disabled;
- no public custom domain;
- no browser CORS policy;
- default abandoned multipart cleanup enabled.

A location hint is **not** an India data-residency guarantee.

Runtime shape:

```env
STORAGE_PROVIDER=s3
REQUIRE_OBJECT_STORAGE=true
STORAGE_S3_VENDOR=cloudflare_r2
STORAGE_S3_BUCKET=fincopilot-prod
STORAGE_S3_REGION=auto
STORAGE_S3_ENDPOINT_URL=https://<CLOUDFLARE_ACCOUNT_ID>.r2.cloudflarestorage.com
STORAGE_S3_PREFIX=fincopilot-prod
```

Create an R2 API credential with **Object Read & Write** limited to this bucket. Store its values only as:

```text
${FINCOPILOT_SECRETS_DIR}/storage_s3_access_key
${FINCOPILOT_SECRETS_DIR}/storage_s3_secret_key
```

Do not enable `r2.dev`, a public bucket domain, or broad account-wide bucket-management permissions for the application runtime.

## 5. Starting the edge connector

After all normal production secrets and non-secret configuration are present on the durable origin host:

```bash
docker compose -f docker-compose.prod.yml --profile cloudflare-edge up -d
```

The Compose profile uses a version-pinned cloudflared image and reads the connector token with `--token-file`. The tunnel can be rotated independently from FinCo-Pilot application signing/provider credentials.

A developer laptop may be used for a temporary staging smoke, but an intermittently connected laptop is not a production hosting acceptance.

## 6. R2 acceptance

After the bucket-scoped S3 credential files are installed:

```bash
cd backend
python -m scripts.verify_production_object_storage
```

Expected safe result:

```text
FinCo-Pilot object-storage acceptance: PASS
write_head_read_delete_roundtrip=pass
integrity_metadata=verified
```

Then upload a harmless attachment through the authenticated FinCo-Pilot UI, download it, delete it, and verify the object disappears.

## 7. Edge acceptance checklist

The Cloudflare edge is operationally accepted only when all applicable checks pass on the durable origin:

1. `cloudflared` establishes an active connector for `fincopilot-origin`.
2. `https://fincopilot.satzzxzxx.me` loads over HTTPS without exposing a direct origin port.
3. `GET /api/info` succeeds through the same public hostname.
4. Login/registration/recovery routes operate through the edge.
5. Passkey/WebAuthn origin behavior is verified against the exact HTTPS hostname when enabled.
6. Backend rate-limit client-IP resolution is verified with `TRUSTED_PROXY_HOPS=2`.
7. The original HTTPS scheme is preserved to the backend.
8. No Cache-Everything rule or other edge rule caches authenticated financial API responses.
9. Tunnel/provider failure produces an unavailable service, not a bypass to a public origin.
10. No tunnel token, R2 credential, application secret or provider secret appears in logs, Compose expansion, Git, browser bundles or screenshots.
11. R2 credential-safe acceptance probe passes.
12. A real authenticated R2 attachment upload/download/delete passes.

## 8. What this does not close

This edge setup does not by itself close:

- production compute hosting (#1);
- final domain/host acceptance (#2);
- managed PostgreSQL live acceptance (#14);
- Redis/worker live acceptance (#15);
- R2 credential/probe acceptance (#16);
- SMTP (#17);
- backup/restore and disaster recovery (#25/#26);
- final browser/device/load acceptance (#58).

Cloudflare edge and R2 can be ready while the complete production stack remains release-gated.
