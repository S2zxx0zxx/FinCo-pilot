from pathlib import Path
from pydantic import SecretStr, ValidationError
import pytest

from app.core.config import Settings


def write(dir: Path, name: str, value: str) -> None:
    (dir / name).write_text(value)


@pytest.fixture
def secrets(tmp_path: Path):
    d = tmp_path / "secrets"
    d.mkdir()
    return d


def test_env_file_is_anchored_to_backend_dir():
    """The worker/beat must resolve the same .env as the API regardless of the
    working directory each service is launched from."""
    env_files = Settings.model_config["env_file"]
    backend_env = Path(__file__).resolve().parents[1] / ".env"
    assert isinstance(env_files, tuple)
    assert backend_env in tuple(Path(p) for p in env_files)


def test_env_file_with_unknown_keys_still_loads(tmp_path: Path, secrets: Path, monkeypatch):
    """The .env is shared with Docker Compose and the optional modules, so it
    holds keys Settings doesn't declare (COMPOSE_PROFILES, FRONTEND_PORT,
    AGENTS_*). Unknown keys must be ignored, not abort startup."""
    monkeypatch.delenv("SECRET_KEY")
    env_file = tmp_path / ".env"
    env_file.write_text(
        "SECRET_KEY=from-env-file\n"
        "AGENTS_ENABLED=true\n"
        "COMPOSE_PROFILES=agents\n"
        "FRONTEND_PORT=3132\n"
    )

    settings = Settings(_env_file=str(env_file), _secrets_dir=str(secrets))

    assert settings.secret_key.get_secret_value() == "from-env-file"


def test_agent_settings_env_file_is_anchored_to_backend_dir():
    """Agents settings must resolve the same .env as the main Settings, so a
    worker started outside backend/ doesn't silently fall back to defaults."""
    from app.agents.config import AgentSettings

    env_files = AgentSettings.model_config["env_file"]
    backend_env = Path(__file__).resolve().parents[1] / ".env"
    assert isinstance(env_files, tuple)
    assert backend_env in tuple(Path(p) for p in env_files)


def test_oidc_secret_reads_from_secrets_dir(secrets: Path):
    write(secrets, "oidc_client_secret", "file-secret")

    settings = Settings(_secrets_dir=str(secrets))
    assert settings.oidc_client_secret.get_secret_value() == "file-secret"


def test_oidc_secret_strips_whitespace(secrets: Path):
    write(secrets, "oidc_client_secret", "  stripped-value  \n\n")

    settings = Settings(_secrets_dir=str(secrets))
    assert settings.oidc_client_secret.get_secret_value() == "stripped-value"


def test_oidc_secret_inline_when_no_file(secrets: Path):
    settings = Settings(
        oidc_client_secret="inline-secret",
        _secrets_dir=str(secrets),
    )

    assert settings.oidc_client_secret.get_secret_value() == "inline-secret"


def test_oidc_secret_default_when_no_file(secrets: Path):
    settings = Settings(_secrets_dir=str(secrets))

    assert settings.oidc_client_secret.get_secret_value() == ""


def test_multiple_secrets_dirs_merge(tmp_path: Path):
    d1, d2 = tmp_path / "d1", tmp_path / "d2"
    d1.mkdir()
    d2.mkdir()

    secrets = {
        d1: {
            "oidc_client_secret": "from-d1",
            "oidc_provider_name": "Provider D1",
        },
        d2: {
            "oidc_client_secret": "from-d2",
            "oidc_client_id": "from-d2",
        },
    }
    for directory, values in secrets.items():
        for name, value in values.items():
            write(directory, name, value)

    expectedSecrets = {**secrets[d1], **secrets[d2]}
    settings = Settings(_secrets_dir=[str(d1), str(d2)])

    for key, expectedValue in expectedSecrets.items():
        value = getattr(settings, key)
        if isinstance(value, SecretStr):
            value = value.get_secret_value()

        assert value == expectedValue


def test_local_auth_enabled_defaults_true(secrets: Path):
    settings = Settings(_secrets_dir=str(secrets))

    assert settings.local_auth_enabled is True


def test_local_auth_can_be_disabled_when_oidc_is_enabled(secrets: Path):
    settings = Settings(
        oidc_enabled=True,
        oidc_client_id="fincopilot",
        oidc_discovery_url="https://id.example.com/.well-known/openid-configuration",
        local_auth_enabled=False,
        _secrets_dir=str(secrets),
    )

    assert settings.local_auth_enabled is False


def test_local_auth_disabled_requires_oidc(secrets: Path):
    with pytest.raises(ValidationError, match="LOCAL_AUTH_ENABLED=false requires a complete OIDC configuration"):
        Settings(local_auth_enabled=False, _secrets_dir=str(secrets))


@pytest.mark.parametrize(
    ("missing_field", "oidc_client_id", "oidc_discovery_url"),
    [
        (
            "OIDC_CLIENT_ID",
            "",
            "https://id.example.com/.well-known/openid-configuration",
        ),
        ("OIDC_DISCOVERY_URL", "fincopilot", ""),
    ],
)
def test_local_auth_disabled_requires_complete_oidc_configuration(
    secrets: Path,
    missing_field: str,
    oidc_client_id: str,
    oidc_discovery_url: str,
):
    with pytest.raises(ValidationError, match=missing_field):
        Settings(
            oidc_enabled=True,
            oidc_client_id=oidc_client_id,
            oidc_discovery_url=oidc_discovery_url,
            local_auth_enabled=False,
            _secrets_dir=str(secrets),
        )



@pytest.mark.parametrize("ttl", [0, 119, 1801, 9999])
def test_billing_offer_reservation_ttl_is_bounded(secrets: Path, ttl: int):
    with pytest.raises(ValidationError, match="BILLING_OFFER_RESERVATION_TTL_SECONDS"):
        Settings(
            billing_offer_reservation_ttl_seconds=ttl,
            _secrets_dir=str(secrets),
        )


def test_invalid_tax_display_mode_is_rejected(secrets: Path):
    with pytest.raises(ValidationError, match="BILLING_TAX_DISPLAY_MODE"):
        Settings(
            billing_tax_display_mode="guess",
            _secrets_dir=str(secrets),
        )


def _production_settings_kwargs() -> dict:
    return {
        "deployment_environment": "production",
        "secret_key": "synthetic-production-key-with-more-than-32-characters",
        "frontend_url": "https://app.example.test",
        "database_url": "postgresql+asyncpg://finco:synthetic@db.example.test:5432/finco",
        "setup_enabled": False,
        "fx_allow_unsafe_1to1_fallback": False,
        "trusted_proxy_hops": 1,
        "metrics_enabled": False,
        "billing_checkout_enabled": True,
    }


def test_production_paid_checkout_refuses_unconfigured_tax_treatment(secrets: Path):
    with pytest.raises(ValidationError, match="BILLING_TAX_DISPLAY_MODE"):
        Settings(
            **_production_settings_kwargs(),
            billing_tax_display_mode="unconfigured",
            _secrets_dir=str(secrets),
        )


def test_production_paid_checkout_accepts_explicit_tax_display_contract(secrets: Path):
    settings = Settings(
        **_production_settings_kwargs(),
        billing_tax_display_mode="inclusive",
        _secrets_dir=str(secrets),
    )
    assert settings.billing_tax_display_mode == "inclusive"
