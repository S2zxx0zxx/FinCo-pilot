from functools import lru_cache
from os import getenv
from pathlib import Path
from urllib.parse import urlsplit

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Use the same environment variable that systemd uses: https://systemd.io/CREDENTIALS/
# If not defined, defaults to docker secrets defaults (https://docs.docker.com/compose/how-tos/use_secrets/)
CREDENTIALS_DIRECTORY: list[Path] = [
    Path(p) for p in getenv("CREDENTIALS_DIRECTORY", "/run/secrets").split(":") if p
]


class Settings(BaseSettings):
    # App
    app_name: str = "FinCo-Pilot"
    debug: bool = False
    deployment_environment: str = "development"  # development|test|staging|production

    # One-time bootstrap endpoint. Development keeps the historical no-token
    # convenience; production must either disable it or protect it with a
    # high-entropy token and remove/rotate that token immediately after use.
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
    access_token_expire_minutes: int = 60 * 24  # 24 hours

    # Pluggy
    pluggy_client_id: str = ""
    pluggy_client_secret: SecretStr = SecretStr("")
    # Empty means "derive from FRONTEND_URL" (see BankProvider.redirect_uri).
    # Set explicitly only when the URL registered in the provider dashboard
    # differs from where the app is served.
    pluggy_oauth_redirect_uri: str = ""

    # Enable Banking (European PSD2 banks)
    enable_banking_app_id: str = ""
    enable_banking_private_key: SecretStr = SecretStr("")  # raw PEM; supports \n-escaped envs
    enable_banking_private_key_file: str = ""  # path to PEM file; takes precedence
    enable_banking_api_url: str = "https://api.enablebanking.com"
    enable_banking_oauth_redirect_uri: str = ""  # empty derives from FRONTEND_URL

    # SimpleFIN Bridge (US/intl banks, paste-a-token flow). Off by default.
    # The bridge URL defaults to the beta/sandbox host so users can test with
    # the demo token; production validation refuses this endpoint.
    simplefin_enabled: bool = False
    simplefin_api_url: str = "https://beta-bridge.simplefin.org"

    # Frontend
    frontend_url: str = "http://localhost:5173"

    # WebAuthn / passkeys
    webauthn_rp_name: str = "FinCo-Pilot"
    # Empty means the RP ID follows the domain the browser is on, which is what
    # most deployments want. Set it to pin passkeys to one domain (e.g.
    # fincopilot.example.com); requests from other origins are then rejected.
    webauthn_rp_id: str = ""
    # Empty means the expected origin follows the browser. Only set this when the
    # app is reached at exactly one origin and you want it enforced.
    webauthn_origin: str = ""
    webauthn_challenge_ttl_seconds: int = 300

    # Defaults
    default_currency: str = "INR"  # fallback currency when user preference is unavailable

    # FX Rates
    openexchangerates_app_id: str = ""
    supported_currencies: str = "USD,EUR,GBP,BRL,CAD,AUD,CHF,ARS,JPY,MXN,INR,SEK,DKK,NOK,PLN,CZK,HUF,RON,CRC,IDR,COP,CLP,DOP,RUB,GTQ,PHP,UAH,NZD,VND,SGD,AZN,TRY,PKR"  # comma-separated list
    fx_sync_mode: str = "on_demand"  # "on_demand" or "scheduled"
    # Backward-compatible in development/tests only. Production deployments
    # must set this false; returning a fake 1:1 rate for unlike currencies can
    # silently corrupt displayed financial totals.
    fx_allow_unsafe_1to1_fallback: bool = True
    # When true, readiness and production validation require a configured FX
    # provider. Public multi-currency deployments should keep this enabled.
    require_fx_provider: bool = False

    # Storage
    storage_provider: str = "local"  # "local" currently; object storage support can be added behind this interface
    storage_local_path: str = "./data/attachments"
    storage_max_file_size_mb: int = 10
    storage_allowed_extensions: str = "jpg,jpeg,png,webp,gif,heic,pdf"
    storage_max_attachments_per_transaction: int = 10
    # An invoice gathers more paper than a transaction does: the bill, the
    # fiscal document, a receipt, the contract behind it, and a correction
    # of any of them.
    storage_max_attachments_per_invoice: int = 20

    # S3 Storage (reserved for the object-storage implementation)
    storage_s3_bucket: str = ""
    storage_s3_region: str = ""
    storage_s3_access_key: SecretStr = SecretStr("")
    storage_s3_secret_key: SecretStr = SecretStr("")
    storage_s3_endpoint_url: str = ""  # for S3-compatible services (MinIO, DigitalOcean Spaces)

    # Registration
    registration_enabled: bool = True

    # OIDC login (works with Authentik, Pocket ID, and other standard OIDC providers)
    oidc_enabled: bool = False
    oidc_provider_name: str = "OIDC"
    oidc_discovery_url: str = (
        ""  # e.g. https://auth.example.com/application/o/fincopilot/.well-known/openid-configuration
    )
    oidc_client_id: str = ""
    oidc_client_secret: SecretStr = SecretStr("")
    oidc_redirect_uri: str = ""  # defaults to {FRONTEND_URL}/api/auth/oidc/callback
    oidc_scopes: str = "openid email profile"
    oidc_auto_register: bool = True
    oidc_existing_user_link_mode: str = "disabled"  # disabled|verified_email|email
    oidc_require_verified_email: bool = True
    oidc_sync_roles: bool = False
    oidc_roles_claim: str = "groups"
    oidc_admin_roles: str = ""  # comma-separated provider roles/groups that grant FinCo-Pilot admin
    oidc_workspace_role_map: str = ""  # JSON: {"provider-role": "owner|editor|viewer"}

    # Celery / Redis
    redis_url: str = "redis://localhost:6379/0"
    bank_sync_lock_ttl_seconds: int = 300

    # Reverse-proxy trust for client-IP-based rate limiting. 0 (default) means
    # request.client.host is used as-is, which is only correct when nothing
    # sits between the client and this service. In the shipped docker-compose
    # topology the backend is reached through the bundled nginx frontend, so
    # request.client.host is always nginx's container address. Set this to the
    # number of trusted reverse proxies in front of the backend (usually 1) to
    # derive the client IP from X-Forwarded-For instead, trusting only that
    # many hops from the right; a chain shorter than expected is not trusted.
    trusted_proxy_hops: int = 0

    # Logo size for market-priced asset icons. The logo URL is built from
    # the company website we get from the market-price provider; no API
    # key or third-party account is required. Defaults to 128×128 which
    # is what Google's favicon service caps at before upscaling.
    logo_size: int = 128

    # Brazilian Treasury bond prices (official Tesouro Transparente CSV).
    # On by default since most users are Brazilian; the official CSV is only
    # fetched when someone actually searches a bond, and the UI pre-warm is
    # gated to Brazilian users, so non-Brazilian installs pay ~zero cost.
    # Set TESOURO_DIRETO_ENABLED=false to fully disable (e.g. to avoid the
    # external dependency on the Brazilian government endpoint).
    tesouro_direto_enabled: bool = True

    @property
    def is_production(self) -> bool:
        return self.deployment_environment.strip().lower() == "production"

    @property
    def oidc_login_available(self) -> bool:
        return bool(self.oidc_enabled and self.oidc_client_id and self.oidc_discovery_url)

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

        if self.db_pool_size < 1 or self.db_max_overflow < 0:
            raise ValueError("Database pool sizes must be non-negative and DB_POOL_SIZE must be >= 1")
        if self.db_pool_timeout_seconds < 1 or self.db_pool_recycle_seconds < 1:
            raise ValueError("Database pool timeout/recycle values must be positive")
        if self.bank_sync_lock_ttl_seconds < 60:
            raise ValueError("BANK_SYNC_LOCK_TTL_SECONDS must be at least 60 seconds")

        return self

    # The CWD-relative ".env" is kept for backward compatibility; the anchored
    # backend/.env guarantees the API and the Celery worker/beat resolve the
    # same file no matter which working directory each service is launched
    # from (a systemd unit without WorkingDirectory= used to leave the worker
    # with default settings, silently disabling every bank-sync provider).
    #
    # extra="ignore" because the same .env is shared with Docker Compose and with
    # the optional modules: it legitimately holds keys this model doesn't declare
    # (COMPOSE_PROFILES, FRONTEND_PORT, AGENTS_*, ...). Unknown keys coming from
    # the process environment are ignored by pydantic-settings anyway; without
    # this, the very same key written into the .env file aborted startup with
    # "Extra inputs are not permitted".
    model_config = SettingsConfigDict(
        env_file=(".env", Path(__file__).resolve().parents[2] / ".env"),
        secrets_dir=CREDENTIALS_DIRECTORY,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
