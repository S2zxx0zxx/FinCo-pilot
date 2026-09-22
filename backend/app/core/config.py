from functools import lru_cache
from os import getenv
from pathlib import Path
from urllib.parse import urlsplit

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

CREDENTIALS_DIRECTORY: list[Path] = [
    Path(p) for p in getenv("CREDENTIALS_DIRECTORY", "/run/secrets").split(":") if p
]


class Settings(BaseSettings):
    # App
    app_name: str = "FinCo-Pilot"
    debug: bool = False
    deployment_environment: str = "development"  # development|test|staging|production

    # One-time bootstrap endpoint.
    setup_enabled: bool = True
    setup_token: SecretStr = SecretStr("")

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/fincopilot"
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_timeout_seconds: int = 30
    db_pool_recycle_seconds: int = 1800

    # Auth
    secret_key: SecretStr = SecretStr("change-me-in-production")
    local_auth_enabled: bool = True
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24

    # Transactional email / account recovery. Production public deployments
    # should set EMAIL_DELIVERY_REQUIRED=true so reset/verification cannot
    # silently degrade into an unusable endpoint.
    email_delivery_required: bool = False
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: SecretStr = SecretStr("")
    smtp_from_email: str = ""
    smtp_starttls: bool = True
    smtp_use_ssl: bool = False

    # Observability. Metrics are intentionally token-protected when enabled in
    # production because labels/counters are operational data, not a public API.
    metrics_enabled: bool = True
    metrics_token: SecretStr = SecretStr("")

    # Pluggy
    pluggy_client_id: str = ""
    pluggy_client_secret: SecretStr = SecretStr("")
    pluggy_oauth_redirect_uri: str = ""

    # Enable Banking
    enable_banking_app_id: str = ""
    enable_banking_private_key: SecretStr = SecretStr("")
    enable_banking_private_key_file: str = ""
    enable_banking_api_url: str = "https://api.enablebanking.com"
    enable_banking_oauth_redirect_uri: str = ""

    # SimpleFIN
    simplefin_enabled: bool = False
    simplefin_api_url: str = "https://beta-bridge.simplefin.org"

    # Frontend
    frontend_url: str = "http://localhost:5173"

    # WebAuthn / passkeys
    webauthn_rp_name: str = "FinCo-Pilot"
    webauthn_rp_id: str = ""
    webauthn_origin: str = ""
    webauthn_challenge_ttl_seconds: int = 300

    # Defaults
    default_currency: str = "INR"

    # FX Rates
    openexchangerates_app_id: str = ""
    supported_currencies: str = "USD,EUR,GBP,BRL,CAD,AUD,CHF,ARS,JPY,MXN,INR,SEK,DKK,NOK,PLN,CZK,HUF,RON,CRC,IDR,COP,CLP,DOP,RUB,GTQ,PHP,UAH,NZD,VND,SGD,AZN,TRY,PKR"
    fx_sync_mode: str = "on_demand"
    fx_allow_unsafe_1to1_fallback: bool = True
    require_fx_provider: bool = False

    # Storage
    storage_provider: str = "local"  # local|s3
    require_object_storage: bool = False
    storage_local_path: str = "./data/attachments"
    storage_max_file_size_mb: int = 10
    storage_allowed_extensions: str = "jpg,jpeg,png,webp,gif,heic,pdf"
    storage_max_attachments_per_transaction: int = 10
    storage_max_attachments_per_invoice: int = 20

    # S3-compatible Storage
    storage_s3_bucket: str = ""
    storage_s3_region: str = ""
    storage_s3_access_key: SecretStr = SecretStr("")
    storage_s3_secret_key: SecretStr = SecretStr("")
    storage_s3_endpoint_url: str = ""

    # Registration
    registration_enabled: bool = True

    # Billing. Until a real payment provider + webhook lifecycle is configured,
    # paid checkout stays disabled rather than presenting a dead purchase flow.
    billing_checkout_enabled: bool = False

    # Razorpay
    razorpay_key_id: str = ""
    razorpay_key_secret: SecretStr = SecretStr("")

    # OIDC
    oidc_enabled: bool = False
    oidc_provider_name: str = "OIDC"
    oidc_discovery_url: str = ""
    oidc_client_id: str = ""
    oidc_client_secret: SecretStr = SecretStr("")
    oidc_redirect_uri: str = ""
    oidc_scopes: str = "openid email profile"
    oidc_auto_register: bool = True
    oidc_existing_user_link_mode: str = "disabled"
    oidc_require_verified_email: bool = True
    oidc_sync_roles: bool = False
    oidc_roles_claim: str = "groups"
    oidc_admin_roles: str = ""
    oidc_workspace_role_map: str = ""

    # Celery / Redis
    redis_url: str = "redis://localhost:6379/0"
    bank_sync_lock_ttl_seconds: int = 300

    # Reverse proxy
    trusted_proxy_hops: int = 0

    logo_size: int = 128
    tesouro_direto_enabled: bool = True

    @property
    def is_production(self) -> bool:
        return self.deployment_environment.strip().lower() == "production"

    @property
    def oidc_login_available(self) -> bool:
        return bool(self.oidc_enabled and self.oidc_client_id and self.oidc_discovery_url)

    @property
    def email_delivery_available(self) -> bool:
        return bool(self.smtp_host.strip() and self.smtp_from_email.strip())

    @model_validator(mode="after")
    def validate_auth_settings(self) -> "Settings":
        environment = self.deployment_environment.strip().lower()
        if environment not in {"development", "test", "staging", "production"}:
            raise ValueError(
                "DEPLOYMENT_ENVIRONMENT must be one of development, test, staging, production"
            )

        if not self.local_auth_enabled and not self.oidc_login_available:
            missing = []
            if not self.oidc_enabled:
                missing.append("OIDC_ENABLED=true")
            if not self.oidc_client_id:
                missing.append("OIDC_CLIENT_ID")
            if not self.oidc_discovery_url:
                missing.append("OIDC_DISCOVERY_URL")
            raise ValueError(
                "LOCAL_AUTH_ENABLED=false requires a complete OIDC configuration; "
                f"missing: {', '.join(missing)}"
            )

        if self.smtp_use_ssl and self.smtp_starttls:
            raise ValueError("SMTP_USE_SSL and SMTP_STARTTLS cannot both be true")
        if not 1 <= self.smtp_port <= 65535:
            raise ValueError("SMTP_PORT must be between 1 and 65535")

        if self.storage_provider not in {"local", "s3"}:
            raise ValueError("STORAGE_PROVIDER must be local or s3")
        if self.storage_provider == "s3":
            missing_storage = []
            if not self.storage_s3_bucket.strip():
                missing_storage.append("STORAGE_S3_BUCKET")
            if not self.storage_s3_region.strip():
                missing_storage.append("STORAGE_S3_REGION")
            if not self.storage_s3_access_key.get_secret_value().strip():
                missing_storage.append("STORAGE_S3_ACCESS_KEY")
            if not self.storage_s3_secret_key.get_secret_value().strip():
                missing_storage.append("STORAGE_S3_SECRET_KEY")
            if missing_storage:
                raise ValueError(
                    "STORAGE_PROVIDER=s3 requires: " + ", ".join(missing_storage)
                )

        if environment == "production":
            secret = self.secret_key.get_secret_value().strip()
            if secret in {"", "change-me-in-production", "dev-secret-change-in-production"} or len(secret) < 32:
                raise ValueError(
                    "Production SECRET_KEY must be a unique high-entropy value of at least 32 characters"
                )

            parsed_frontend = urlsplit(self.frontend_url)
            if parsed_frontend.scheme != "https" or not parsed_frontend.hostname:
                raise ValueError("Production FRONTEND_URL must be an absolute https:// URL")
            if parsed_frontend.hostname in {"localhost", "127.0.0.1", "::1"}:
                raise ValueError("Production FRONTEND_URL cannot point at localhost")

            db_lower = self.database_url.lower()
            if "postgres:postgres@" in db_lower or "@localhost:" in db_lower:
                raise ValueError(
                    "Production DATABASE_URL cannot use the shipped default credentials/localhost"
                )

            if self.setup_enabled and not self.setup_token.get_secret_value().strip():
                raise ValueError(
                    "Production SETUP_ENABLED=true requires a high-entropy SETUP_TOKEN; "
                    "prefer SETUP_ENABLED=false after provisioning the first admin"
                )

            if self.fx_allow_unsafe_1to1_fallback:
                raise ValueError(
                    "Production must set FX_ALLOW_UNSAFE_1TO1_FALLBACK=false to avoid silently wrong conversions"
                )
            if self.require_fx_provider and not self.openexchangerates_app_id.strip():
                raise ValueError(
                    "Production REQUIRE_FX_PROVIDER=true requires OPENEXCHANGERATES_APP_ID"
                )

            if self.simplefin_enabled and "beta-bridge.simplefin.org" in self.simplefin_api_url.lower():
                raise ValueError(
                    "Production SimpleFIN cannot use the beta bridge; set SIMPLEFIN_API_URL=https://bridge.simplefin.org"
                )

            if self.trusted_proxy_hops < 1:
                raise ValueError(
                    "Production TRUSTED_PROXY_HOPS must match the trusted reverse-proxy chain (normally 1)"
                )

            if self.local_auth_enabled and self.email_delivery_required and not self.email_delivery_available:
                raise ValueError(
                    "Production local auth requires SMTP_HOST and SMTP_FROM_EMAIL when EMAIL_DELIVERY_REQUIRED=true"
                )

            if self.metrics_enabled and not self.metrics_token.get_secret_value().strip():
                raise ValueError(
                    "Production METRICS_ENABLED=true requires a high-entropy METRICS_TOKEN"
                )

            if self.require_object_storage and self.storage_provider != "s3":
                raise ValueError(
                    "Production REQUIRE_OBJECT_STORAGE=true requires STORAGE_PROVIDER=s3"
                )

        if self.db_pool_size < 1 or self.db_max_overflow < 0:
            raise ValueError("Database pool sizes must be non-negative and DB_POOL_SIZE must be >= 1")
        if self.db_pool_timeout_seconds < 1 or self.db_pool_recycle_seconds < 1:
            raise ValueError("Database pool timeout/recycle values must be positive")
        if self.bank_sync_lock_ttl_seconds < 60:
            raise ValueError("BANK_SYNC_LOCK_TTL_SECONDS must be at least 60 seconds")

        return self

    model_config = SettingsConfigDict(
        env_file=(".env", Path(__file__).resolve().parents[2] / ".env"),
        secrets_dir=CREDENTIALS_DIRECTORY,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
