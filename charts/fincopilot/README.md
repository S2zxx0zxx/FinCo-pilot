# FinCo-Pilot Helm Chart

[FinCo-Pilot](https://github.com/S2zxx0zxx/FinCo-pilot) is an advanced, self-hosted personal finance manager with built-in AI agents. This Helm chart provides a complete, production-ready deployment of FinCo-Pilot to any Kubernetes cluster.

## Features

- **Complete Application Stack**: Deploys the Next.js React frontend and FastAPI backend, fully supporting all features including Open Banking integrations, OIDC authentication, and AI financial agents.
- **Asynchronous Task Scheduler**: Runs Celery workers and a Celery beat singleton for automated background processing (such as bank syncs, recurring transactions, and exchange rate updates).
- **Databases**: Easily configure connections to your external PostgreSQL and Redis instances.
- **Gateway API & Ingress**: Native support for standard Kubernetes Ingress or the modern Kubernetes Gateway API (`HTTPRoute`).

## Prerequisites

- Kubernetes 1.25+
- Helm 3.2.0+
- PostgreSQL 15+ (with the `pgvector` extension installed)
- Redis 7+
- Persistent Volume (PV) provisioner support in the underlying infrastructure

### Persistent Storage Requirements
Since the Backend, Celery Worker, and MCP Server all share the same files (like uploaded attachments and AI knowledge bases), they all mount the same Persistent Volume Claims concurrently.
**If your cluster spans multiple nodes, you MUST use a StorageClass that supports `ReadWriteMany` (RWX) access mode (e.g., NFS, CephFS, or Longhorn RWX).**
If your storage only supports `ReadWriteOnce` (RWO), you must restrict all FinCo-Pilot pods to run on a single node (using `nodeSelector` or `podAffinity`) but that is an antipattern in Kubernetes.

## Quickstart

If you want to install the latest official release from the GitHub Container Registry (GHCR):

```bash
helm install fincopilot oci://ghcr.io/S2zxx0zxx/charts/fincopilot --version <VERSION>
```

If you are developing locally and want to install from the source repository:

```bash
helm install fincopilot ./charts/fincopilot
```

## Configuration

All application-level features (such as AI Services, OIDC authentication, and Open Banking integrations) can be configured directly through Helm.
The keys in the `config:` and `secret:` blocks of the `values.yaml` map directly to the `UPPER_SNAKE_CASE` environment variables used in the standard Docker setup (converted to `camelCase`).

For a full list of available environment variables and API keys, please refer to the **[FinCo-Pilot Application Configuration Guide](https://github.com/S2zxx0zxx/FinCo-pilot)**.

### Secrets Management (Production)

Production is fail-closed: set `config.deploymentEnvironment=production` **and**
reference an operator-managed Kubernetes Secret. The chart will refuse to render
production while `global.existingSecret` is empty.

```yaml
global:
  existingSecret: "fincopilot-production-secrets"
config:
  deploymentEnvironment: "production"
```

Because workloads consume the Secret with `envFrom`, an externally-created
Secret uses the actual uppercase application environment names, for example
`SECRET_KEY`, `CREDENTIAL_ENCRYPTION_KEY`, `CORE_COPILOT_SIGNING_KEY`,
`LEGACY_DATA_KEYS` (during migration), `DATABASE_URL`, `SMTP_PASSWORD`,
`AGENTS_MCP_JWT_SECRET`, and `AGENTS_OPENAI_COMPAT_API_KEY`. Do **not** use
the camelCase `values.yaml` field names in an external Secret.

Do not commit a Secret manifest containing real values, a decrypted secrets
file, or a `--set secret.*=<value>` command. Provision the Secret out-of-band
from your deployment secret manager. On the cluster, enable Kubernetes Secret
encryption at rest, restrict `get/list/watch` with least-privilege RBAC, and
prefer a supported external secret store/CSI integration when available.

The full inventory, file/key names, rotation effects and compromise procedure
are in `docs/trust/FINCO_PRODUCTION_SECRET_MANAGEMENT_V1.md`.

### Production PostgreSQL

Production deliberately does not use the chart's bundled PostgreSQL. Configure:

```yaml
global:
  existingSecret: fincopilot-production-secrets
config:
  deploymentEnvironment: production
  databaseExternalRequired: "true"
  dbSslMode: "verify-full"
postgresql:
  enabled: false
```

The existing Secret must contain `DATABASE_URL`. Use PostgreSQL 15+ with
pgvector available. The complete pooling, TLS, migration and safe acceptance
contract is documented in
`docs/trust/FINCO_PRODUCTION_POSTGRESQL_V1.md`.

## Uninstalling the Chart

To uninstall/delete the `fincopilot` deployment:

```bash
helm uninstall fincopilot
```

This command removes all the Kubernetes components associated with the chart and deletes the release. Note that Persistent Volume Claims (PVCs) created by the chart might not be deleted automatically to prevent accidental data loss.


### Production Redis

The bundled Redis StatefulSet is development-only. Production rendering requires
`redis.enabled=false`, `config.redisExternalRequired=true`,
`config.redisTlsRequired=true` and `config.redisAuthRequired=true`.
Place the authenticated `rediss://` value in the operator-managed Secret under
the key `REDIS_URL`; do not put it in `values.yaml`.

Celery worker readiness/liveness probes use the real broker. Beat is a
single-replica `Recreate` deployment with a PID probe so rollouts do not run
two schedulers at once.

### Revision startup gate

Backend, worker, Beat and MCP pods run `scripts/prepare_release.py` in an init
container before starting. Production requires schema and provider acceptance,
plus a data-key migration dry run. API readiness uses `/api/health/ready`.
The migration hook remains an idempotent post-install/upgrade confirmation;
`helm --wait` no longer allows traffic before migrations. Existing installations
must follow [the data-key rollout runbook](../../docs/trust/FINCO_REVISION_1_16_V1.md)
and include their previous data keys in the externally managed Secret.


### Production SMTP (#17)

Local-auth production requires `config.emailDeliveryRequired=true`, verified TLS via
`config.smtpUseSsl=true` (with `smtpStarttls=false`) or mandatory STARTTLS, actual
`config.smtpHost`, `smtpPort`, `smtpUsername`, and a verified `smtpFromEmail`.
Put `SMTP_PASSWORD` in `global.existingSecret`; never commit production Secret values.
`config.smtpTimeoutSeconds` defaults to 10; `smtpMaxConcurrentSends` defaults to 4 per process.
An optional `smtpSslCaFile` needs an operator-provided read-only mount. Follow
`docs/trust/FINCO_PRODUCTION_SMTP_V1.md` for the no-send probe and inbox acceptance.
