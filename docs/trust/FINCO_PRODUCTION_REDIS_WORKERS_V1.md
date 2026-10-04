# FinCo-Pilot Production Redis & Workers V1

Status: engineering contract for roadmap **#15 — Production Redis / workers**.

Contract ID: `FINCO_PRODUCTION_REDIS_WORKERS_V1`

This contract makes Redis and Celery an explicit production dependency instead
of silently relying on the development-only bundled Redis service.

## 1. Runtime responsibilities

Redis is used for:

- API/auth/support rate-limit counters;
- OAuth and short-lived authentication state;
- renewable distributed bank-sync locks;
- Celery broker queues;
- bounded Celery result metadata.

Redis is **not** the source of truth for balances, transactions, subscriptions,
users, workspaces, invoices or other durable financial records. Durable product
state remains PostgreSQL/object storage.

## 2. Production target contract

Production defaults require:

```env
REDIS_EXTERNAL_REQUIRED=true
REDIS_TLS_REQUIRED=true
REDIS_AUTH_REQUIRED=true
REDIS_MAX_CONNECTIONS=50
REDIS_SOCKET_CONNECT_TIMEOUT_SECONDS=5
REDIS_SOCKET_TIMEOUT_SECONDS=5
REDIS_HEALTH_CHECK_INTERVAL_SECONDS=30
CELERY_RESULT_EXPIRES_SECONDS=86400
CELERY_VISIBILITY_TIMEOUT_SECONDS=3600
CELERY_WORKER_PREFETCH_MULTIPLIER=1
```

`REDIS_URL` itself is secret material and must be delivered through the
roadmap #13 secret store as `redis_url` for Compose or `REDIS_URL` in the
operator-managed Kubernetes Secret. Production should use an authenticated
`rediss://` endpoint.

The runtime rejects obvious local/bundled Redis hosts when
`REDIS_EXTERNAL_REQUIRED=true`, rejects plaintext transport when
`REDIS_TLS_REQUIRED=true`, and rejects a credential-free URL when
`REDIS_AUTH_REQUIRED=true`.

## 3. Client safety

The FastAPI Redis client and bank-sync lock client share one canonical builder:

- bounded connection pool;
- finite connect/read timeouts;
- periodic connection health checks;
- optional private CA path;
- no connection URL or credential logging.

The bank-sync renewable lock remains compare-and-expire / compare-and-delete,
so a worker cannot extend or release another worker's lock.

## 4. Celery reliability posture

Celery uses the same secret-managed Redis target for broker and result backend.

V1 configures:

- broker retry on worker startup;
- bounded broker pool;
- worker prefetch multiplier of 1 by default;
- task-start tracking;
- bounded result expiry;
- bounded Redis visibility timeout;
- TLS certificate verification for `rediss://`;
- a side-effect-free `app.worker.health_probe` task for acceptance testing.

Global late acknowledgements are deliberately **not** enabled. Existing jobs
have different idempotency boundaries; forcing late ack globally could replay a
side-effecting task after worker loss. Per-task replay/idempotency can be
strengthened later without weakening #15.

## 5. Worker and scheduler topology

Production requires:

- one or more Celery workers;
- exactly one Celery Beat scheduler;
- no API-replica startup fan-out for scheduled jobs.

Compose and Helm add worker probes, graceful termination and
`max-tasks-per-child` recycling. Kubernetes Beat uses `Recreate` with one
replica and a PID health probe to prevent overlapping schedulers during rollout.

Beat does not mount attachment/knowledge volumes because it only schedules
tasks. Workers keep only the volumes needed by tasks they execute.

## 6. Bundled Redis boundary

Bundled Redis remains a development/local fallback.

- Production Compose places it behind the `bundled-redis` profile.
- Production Helm refuses to render while `redis.enabled=true`.
- Production Helm also requires the external/TLS/auth Redis gates.

Running the bundled profile does not satisfy the production acceptance gate.

## 7. Safe acceptance probe

Redis-only startup check:

```bash
python -m scripts.verify_production_redis --redis-only
```

Full live acceptance with a running worker:

```bash
python -m scripts.verify_production_redis --require-worker
```

The probe:

1. pings Redis;
2. writes a random namespaced value with a 30-second TTL;
3. reads and validates it;
4. validates the TTL;
5. deletes it;
6. validates the static Beat schedule;
7. optionally sends a side-effect-free task through broker → worker → result backend.

It never prints `REDIS_URL`, credentials, secret-file values or provider
response bodies.

## 8. CI evidence required

Roadmap #15 engineering closure requires green CI for:

- backend tests, Ruff and ty;
- secret hygiene;
- disposable Redis 8 ping/write/read/delete smoke;
- a real Celery worker broker/result round-trip;
- a real Celery Beat startup smoke;
- production Compose validation;
- Helm negative gates for bundled/non-TLS/unauthenticated Redis;
- Helm production lint/render with external Redis contract;
- existing PostgreSQL, migration and frontend checks.

## 9. Operational acceptance boundary

Code/CI does **not** prove a real production Redis account exists.

Operational #15 is accepted only after an operator-owned production Redis target
is provisioned, its authenticated `rediss://` URL is placed in secret storage,
the deployed API passes the Redis-only startup probe, a deployed worker passes
the full broker/result probe, and exactly one deployed Beat instance is healthy.

Record only the provider/project identifier and acceptance timestamp. Never
record the Redis URL or credential value in Git, issues, screenshots or chat.
