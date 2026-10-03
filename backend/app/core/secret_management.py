"""Canonical production-secret inventory and rotation contract for FinCo-Pilot.

Roadmap #13 defines how secret material is classified, delivered and rotated.
It deliberately contains no secret values. Runtime values stay outside source
control and are injected by an operator-controlled secret store.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


INVENTORY_ID = "FINCO_PRODUCTION_SECRET_MANAGEMENT_V1"
INVENTORY_VERSION = "2026-10-02"


class SecretKind(str, Enum):
    APPLICATION_SIGNING_KEY = "application_signing_key"
    CONNECTION_STRING = "connection_string"
    BOOTSTRAP_TOKEN = "bootstrap_token"
    PROVIDER_CREDENTIAL = "provider_credential"
    PRIVATE_KEY = "private_key"
    INTERNAL_SIGNING_KEY = "internal_signing_key"


class RotationImpact(str, Enum):
    RESTART_CONSUMERS = "restart_consumers"
    INVALIDATE_APP_SESSIONS = "invalidate_app_sessions"
    INVALIDATE_MCP_TOKENS = "invalidate_mcp_tokens"
    COORDINATED_INFRA_CHANGE = "coordinated_infra_change"
    PROVIDER_REVOKE_AND_REPLACE = "provider_revoke_and_replace"
    DISABLE_AFTER_BOOTSTRAP = "disable_after_bootstrap"


@dataclass(frozen=True)
class ProductionSecret:
    env_name: str
    file_name: str
    kind: SecretKind
    consumers: tuple[str, ...]
    required_when: str
    rotation_impact: RotationImpact
    provider_managed: bool
    forbid_plaintext_prod_compose: bool = True
    notes: str = ""


PRODUCTION_SECRETS: dict[str, ProductionSecret] = {
    "CREDENTIAL_ENCRYPTION_KEY": ProductionSecret(
        "CREDENTIAL_ENCRYPTION_KEY", "credential_encryption_key", SecretKind.INTERNAL_SIGNING_KEY,
        ("backend", "celery-worker", "mcp-server"), "every production deployment",
        RotationImpact.COORDINATED_INFRA_CHANGE, False,
        notes="Independent encryption key. Retain old keys in LEGACY_DATA_KEYS until all stored credentials are re-encrypted.",
    ),
    "CORE_COPILOT_SIGNING_KEY": ProductionSecret(
        "CORE_COPILOT_SIGNING_KEY", "core_copilot_signing_key", SecretKind.INTERNAL_SIGNING_KEY,
        ("backend",), "every production deployment", RotationImpact.COORDINATED_INFRA_CHANGE, False,
        notes="Independent system-agent identity key. Retain previous keys until every protected agent is re-signed.",
    ),
    "LEGACY_DATA_KEYS": ProductionSecret(
        "LEGACY_DATA_KEYS", "legacy_data_keys", SecretKind.INTERNAL_SIGNING_KEY,
        ("backend", "celery-worker", "mcp-server"), "migrating existing encrypted credentials or system agents",
        RotationImpact.COORDINATED_INFRA_CHANGE, False,
        notes="JSON with separate credentials/copilot key arrays; read-only compatibility, never accepted for JWT authentication.",
    ),
    "SECRET_KEY": ProductionSecret(
        "SECRET_KEY", "secret_key", SecretKind.APPLICATION_SIGNING_KEY,
        ("backend", "celery-worker", "celery-beat", "migration"),
        "every production deployment", RotationImpact.INVALIDATE_APP_SESSIONS, False,
        notes="Generate independently with high entropy; rotation invalidates application JWT sessions.",
    ),
    "DATABASE_URL": ProductionSecret(
        "DATABASE_URL", "database_url", SecretKind.CONNECTION_STRING,
        ("backend", "celery-worker", "celery-beat", "migration", "mcp-server"),
        "every production deployment", RotationImpact.COORDINATED_INFRA_CHANGE, False,
        notes="Treat the whole URL as secret because it normally embeds database credentials.",
    ),
    "POSTGRES_PASSWORD": ProductionSecret(
        "POSTGRES_PASSWORD", "postgres_password", SecretKind.PROVIDER_CREDENTIAL,
        ("postgresql",), "the bundled PostgreSQL service is used",
        RotationImpact.COORDINATED_INFRA_CHANGE, False,
        notes="Database-container credential; not an application Settings field.",
    ),
    "SETUP_TOKEN": ProductionSecret(
        "SETUP_TOKEN", "setup_token", SecretKind.BOOTSTRAP_TOKEN, ("backend",),
        "SETUP_ENABLED=true", RotationImpact.DISABLE_AFTER_BOOTSTRAP, False,
        notes="Use only for first-admin bootstrap and disable setup immediately afterwards.",
    ),
    "SMTP_PASSWORD": ProductionSecret(
        "SMTP_PASSWORD", "smtp_password", SecretKind.PROVIDER_CREDENTIAL,
        ("backend", "celery-worker"), "authenticated transactional SMTP is enabled",
        RotationImpact.PROVIDER_REVOKE_AND_REPLACE, True,
    ),
    "METRICS_TOKEN": ProductionSecret(
        "METRICS_TOKEN", "metrics_token", SecretKind.PROVIDER_CREDENTIAL, ("backend",),
        "METRICS_ENABLED=true in production", RotationImpact.RESTART_CONSUMERS, False,
    ),
    "RAZORPAY_KEY_SECRET": ProductionSecret(
        "RAZORPAY_KEY_SECRET", "razorpay_key_secret", SecretKind.PROVIDER_CREDENTIAL,
        ("backend", "celery-worker"), "Razorpay checkout/webhook operations are enabled",
        RotationImpact.PROVIDER_REVOKE_AND_REPLACE, True,
    ),
    "ZOHO_DESK_CLIENT_SECRET": ProductionSecret(
        "ZOHO_DESK_CLIENT_SECRET", "zoho_desk_client_secret", SecretKind.PROVIDER_CREDENTIAL,
        ("backend",), "Zoho direct ticket submission is enabled",
        RotationImpact.PROVIDER_REVOKE_AND_REPLACE, True,
    ),
    "ZOHO_DESK_REFRESH_TOKEN": ProductionSecret(
        "ZOHO_DESK_REFRESH_TOKEN", "zoho_desk_refresh_token", SecretKind.PROVIDER_CREDENTIAL,
        ("backend",), "Zoho direct ticket submission is enabled",
        RotationImpact.PROVIDER_REVOKE_AND_REPLACE, True,
    ),
    "PLUGGY_CLIENT_SECRET": ProductionSecret(
        "PLUGGY_CLIENT_SECRET", "pluggy_client_secret", SecretKind.PROVIDER_CREDENTIAL,
        ("backend", "celery-worker"), "the Pluggy connector is enabled",
        RotationImpact.PROVIDER_REVOKE_AND_REPLACE, True,
    ),
    "ENABLE_BANKING_PRIVATE_KEY": ProductionSecret(
        "ENABLE_BANKING_PRIVATE_KEY", "enable_banking_private.pem", SecretKind.PRIVATE_KEY,
        ("backend", "celery-worker"), "the Enable Banking connector is enabled",
        RotationImpact.PROVIDER_REVOKE_AND_REPLACE, True,
        notes="Prefer the dedicated PEM file path instead of an inline environment value.",
    ),
    "OIDC_CLIENT_SECRET": ProductionSecret(
        "OIDC_CLIENT_SECRET", "oidc_client_secret", SecretKind.PROVIDER_CREDENTIAL,
        ("backend",), "OIDC login is enabled with a confidential client",
        RotationImpact.PROVIDER_REVOKE_AND_REPLACE, True,
    ),
    "OPENEXCHANGERATES_APP_ID": ProductionSecret(
        "OPENEXCHANGERATES_APP_ID", "openexchangerates_app_id", SecretKind.PROVIDER_CREDENTIAL,
        ("backend", "celery-worker", "celery-beat"), "REQUIRE_FX_PROVIDER=true",
        RotationImpact.PROVIDER_REVOKE_AND_REPLACE, True,
        notes="Despite the provider name 'app id', this authorizes API usage and is handled as a credential.",
    ),
    "STORAGE_S3_ACCESS_KEY": ProductionSecret(
        "STORAGE_S3_ACCESS_KEY", "storage_s3_access_key", SecretKind.PROVIDER_CREDENTIAL,
        ("backend", "celery-worker"), "STORAGE_PROVIDER=s3",
        RotationImpact.PROVIDER_REVOKE_AND_REPLACE, True,
    ),
    "STORAGE_S3_SECRET_KEY": ProductionSecret(
        "STORAGE_S3_SECRET_KEY", "storage_s3_secret_key", SecretKind.PROVIDER_CREDENTIAL,
        ("backend", "celery-worker"), "STORAGE_PROVIDER=s3",
        RotationImpact.PROVIDER_REVOKE_AND_REPLACE, True,
    ),
    "AGENTS_MCP_JWT_SECRET": ProductionSecret(
        "AGENTS_MCP_JWT_SECRET", "agents_mcp_jwt_secret", SecretKind.INTERNAL_SIGNING_KEY,
        ("backend", "mcp-server"), "AGENTS_ENABLED=true",
        RotationImpact.INVALIDATE_MCP_TOKENS, False,
        notes="Keep distinct from SECRET_KEY; rotation invalidates external and internal MCP JWTs.",
    ),
    "AGENTS_OPENAI_API_KEY": ProductionSecret(
        "AGENTS_OPENAI_API_KEY", "agents_openai_api_key", SecretKind.PROVIDER_CREDENTIAL,
        ("backend", "celery-worker"), "the operator default provider is OpenAI",
        RotationImpact.PROVIDER_REVOKE_AND_REPLACE, True,
    ),
    "AGENTS_ANTHROPIC_API_KEY": ProductionSecret(
        "AGENTS_ANTHROPIC_API_KEY", "agents_anthropic_api_key", SecretKind.PROVIDER_CREDENTIAL,
        ("backend", "celery-worker"), "the operator default provider is Anthropic",
        RotationImpact.PROVIDER_REVOKE_AND_REPLACE, True,
    ),
    "AGENTS_OPENAI_COMPAT_API_KEY": ProductionSecret(
        "AGENTS_OPENAI_COMPAT_API_KEY", "agents_openai_compat_api_key", SecretKind.PROVIDER_CREDENTIAL,
        ("backend", "celery-worker"), "an authenticated OpenAI-compatible/OmniRoute route is enabled",
        RotationImpact.PROVIDER_REVOKE_AND_REPLACE, True,
        notes="For Core Copilot use a dedicated FinCopilot inference credential, not a broad provider admin key.",
    ),
    "AGENTS_EMBEDDING_OPENAI_API_KEY": ProductionSecret(
        "AGENTS_EMBEDDING_OPENAI_API_KEY", "agents_embedding_openai_api_key", SecretKind.PROVIDER_CREDENTIAL,
        ("backend", "celery-worker"), "remote OpenAI/OpenAI-compatible embeddings are enabled",
        RotationImpact.PROVIDER_REVOKE_AND_REPLACE, True,
    ),
    "REDIS_URL": ProductionSecret(
        "REDIS_URL", "redis_url", SecretKind.CONNECTION_STRING,
        ("backend", "celery-worker", "celery-beat", "mcp-server"),
        "every production deployment",
        RotationImpact.COORDINATED_INFRA_CHANGE, False,
        notes=(
            "Roadmap #15 treats the full Redis URL as secret because production "
            "requires an authenticated external target; rotate endpoint credentials "
            "and restart all Redis/Celery consumers together."
        ),
    ),
}


def get_production_secret(env_name: str) -> ProductionSecret:
    try:
        return PRODUCTION_SECRETS[env_name]
    except KeyError as exc:
        raise KeyError(f"Unknown production secret: {env_name}") from exc


def plaintext_forbidden_prod_compose_names() -> frozenset[str]:
    return frozenset(
        item.env_name
        for item in PRODUCTION_SECRETS.values()
        if item.forbid_plaintext_prod_compose
    )
