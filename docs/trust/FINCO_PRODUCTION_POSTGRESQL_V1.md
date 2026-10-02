# FinCo-Pilot Production PostgreSQL V1

Status: engineering contract for roadmap **#14 — Production PostgreSQL**.

Contract ID: `FINCO_PRODUCTION_POSTGRESQL_V1`

## 1. Production topology

FinCo-Pilot production defaults to an **external managed PostgreSQL 15+**
service with pgvector available. Neon is compatible with this contract and is
the preferred zero-cost bootstrap provider, but the runtime remains
provider-neutral.

Development may keep the bundled `pgvector/pgvector:pg16` container. The
production Compose database container is behind the explicit
`bundled-db` profile; Helm production rendering refuses an enabled bundled
PostgreSQL chart. A production release must therefore supply `DATABASE_URL`
through the secret-management contract from roadmap #13.

## 2. Connection security

Production external PostgreSQL must use encrypted transport. Recommended:

```env
DATABASE_EXTERNAL_REQUIRED=true
DB_SSL_MODE=verify-full
DB_SSL_CA_FILE=
```

`verify-full` uses the operating system CA bundle unless
`DB_SSL_CA_FILE` names an operator-managed CA file. `require` is supported
for providers that explicitly document that mode, but it encrypts without
certificate/hostname verification and is weaker than `verify-full`.

Managed-provider URLs often include libpq parameters such as
`sslmode=require` and `channel_binding=require`. FinCo-Pilot removes
libpq-only TLS query parameters before handing the URL to SQLAlchemy/asyncpg
and applies the configured TLS policy through asyncpg connection arguments.
The password-bearing URL remains a secret and is never logged by the
acceptance probe.

## 3. Pooling and timeouts

The API uses one bounded SQLAlchemy pool:

```env
DB_POOL_MODE=queue
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=5
DB_POOL_TIMEOUT_SECONDS=15
DB_POOL_RECYCLE_SECONDS=900
DB_CONNECT_TIMEOUT_SECONDS=10
DB_COMMAND_TIMEOUT_SECONDS=30
DB_STATEMENT_TIMEOUT_MS=30000
DB_IDLE_TRANSACTION_TIMEOUT_MS=30000
DB_PREPARED_STATEMENT_CACHE_SIZE=100
DB_APPLICATION_NAME=fincopilot
```

Celery jobs and Alembic migrations use `NullPool` because their engines are
short-lived. This prevents every worker task from creating another persistent
pool against a managed service.

If an operator deliberately uses a transaction-pooling endpoint (for example a
PgBouncer-style provider URL), set:

```env
DB_POOL_MODE=null
DB_PREPARED_STATEMENT_CACHE_SIZE=0
```

and validate that provider mode in staging before production traffic.

## 4. Schema and migrations

- Alembic remains the only schema authority.
- Migration 046 verifies pgvector is available and installs the `vector`
  extension.
- Online Alembic runs take a PostgreSQL session advisory lock before applying
  migrations, preventing two deploy processes from mutating the schema at the
  same time.
- Production deploys run upgrade-only migrations. Never use
  `alembic downgrade` against production data.
- The release acceptance probe requires the database's `alembic_version` to
  match the application's current Alembic head exactly.

## 5. Safe production acceptance

After the secret manager contains the real `DATABASE_URL`, run:

```bash
cd backend
python -m scripts.verify_production_postgres
```

The probe verifies without printing credentials:

1. PostgreSQL 15+;
2. the connection is not a recovery/read-only standby;
3. TLS is active when configured as required;
4. pgvector is available and installed;
5. Alembic DB head equals the application release head;
6. a transaction-local temporary-table write/read succeeds;
7. the temporary write is rolled back.

The output contains only a sanitized host/database target and acceptance
metadata. It never prints `DATABASE_URL`, passwords, roles, user rows, or
financial data.

## 6. Neon bootstrap profile

For a zero-cost early production database, create a dedicated Neon project in
an appropriate region, use its **direct** PostgreSQL endpoint initially, and
keep pgvector enabled through the existing Alembic migration.

Store the provider URL as the `database_url` secret file for production
Compose or as `DATABASE_URL` in the operator-managed Kubernetes Secret.
Do not commit it to `.env`, Helm values, workflow YAML, issues, chat, or
screenshots.

If the provider gives a URL beginning with `postgresql://`, FinCo-Pilot
normalizes it to the asyncpg dialect at runtime. Provider-supplied
`sslmode/channel_binding` query parameters do not replace
`DB_SSL_MODE=verify-full`.

## 7. Backup boundary

Roadmap #14 selects and hardens the production database runtime. It does not
claim disaster recovery merely because a managed provider has history/PITR.

Roadmap **#25 — Backup + actual restore** must still create a real backup or
provider snapshot, restore it into an isolated target, run migrations and
application integrity checks there, and record evidence before DR is marked
accepted.

## 8. Acceptance checklist

Roadmap #14 is engineering-complete when:

- production requires an externally supplied PostgreSQL secret;
- external DB/TLS fail-closed validation is merged;
- all API/worker/migration engines share the canonical runtime policy;
- worker engines do not create persistent per-task pools;
- migration concurrency is serialized with an advisory lock;
- Compose and Helm production paths default away from bundled PostgreSQL;
- CI runs migrations plus the disposable PostgreSQL acceptance probe;
- backend, frontend, migration-chain and Helm checks are green.

Operational acceptance additionally requires the real managed project,
provider-issued `DATABASE_URL`, migrations, and the production acceptance
probe to pass against that project. Secrets never enter Git or chat.
