from pydantic import SecretStr

from app.agents.config import AgentSettings
from app.core.config import Settings
from app.core.secret_management import (
    INVENTORY_ID,
    PRODUCTION_SECRETS,
    RotationImpact,
    SecretKind,
    get_production_secret,
    plaintext_forbidden_prod_compose_names,
)


def test_secret_inventory_is_self_keyed_and_has_no_duplicate_file_names():
    assert INVENTORY_ID == "FINCO_PRODUCTION_SECRET_MANAGEMENT_V1"
    assert len(PRODUCTION_SECRETS) >= 20
    file_names: set[str] = set()
    for key, item in PRODUCTION_SECRETS.items():
        assert item.env_name == key
        assert item.file_name.strip()
        assert item.required_when.strip()
        assert item.consumers
        assert item.file_name not in file_names
        file_names.add(item.file_name)


def test_critical_signing_and_provider_secrets_are_registered():
    expected = {
        "SECRET_KEY", "DATABASE_URL", "POSTGRES_PASSWORD", "SETUP_TOKEN",
        "RAZORPAY_KEY_SECRET", "ZOHO_DESK_CLIENT_SECRET", "ZOHO_DESK_REFRESH_TOKEN",
        "AGENTS_MCP_JWT_SECRET", "AGENTS_OPENAI_COMPAT_API_KEY", "STORAGE_S3_SECRET_KEY",
    }
    assert expected <= set(PRODUCTION_SECRETS)


def test_signing_key_rotations_have_explicit_invalidation_semantics():
    assert get_production_secret("SECRET_KEY").rotation_impact is RotationImpact.INVALIDATE_APP_SESSIONS
    assert get_production_secret("AGENTS_MCP_JWT_SECRET").rotation_impact is RotationImpact.INVALIDATE_MCP_TOKENS
    assert get_production_secret("SECRET_KEY").kind is SecretKind.APPLICATION_SIGNING_KEY


def test_provider_credentials_require_revoke_and_replace_rotation():
    for name in (
        "RAZORPAY_KEY_SECRET", "ZOHO_DESK_CLIENT_SECRET", "ZOHO_DESK_REFRESH_TOKEN",
        "PLUGGY_CLIENT_SECRET", "OIDC_CLIENT_SECRET", "AGENTS_OPENAI_COMPAT_API_KEY",
    ):
        item = get_production_secret(name)
        assert item.provider_managed is True
        assert item.rotation_impact is RotationImpact.PROVIDER_REVOKE_AND_REPLACE


def test_plaintext_prod_compose_guard_covers_unconditional_secrets():
    forbidden = plaintext_forbidden_prod_compose_names()
    assert "SECRET_KEY" in forbidden
    assert "DATABASE_URL" in forbidden
    assert "ZOHO_DESK_REFRESH_TOKEN" in forbidden
    assert "AGENTS_OPENAI_COMPAT_API_KEY" in forbidden
    assert "REDIS_URL" not in forbidden


def test_unknown_secret_fails_closed():
    try:
        get_production_secret("NEW_UNREVIEWED_SECRET")
    except KeyError as exc:
        assert "Unknown production secret" in str(exc)
    else:
        raise AssertionError("Unknown secret names must not silently inherit a policy")



def test_every_typed_runtime_secret_is_in_the_canonical_inventory():
    for field_name, field in Settings.model_fields.items():
        if field.annotation is SecretStr:
            assert field_name.upper() in PRODUCTION_SECRETS, field_name

    for field_name, field in AgentSettings.model_fields.items():
        if field.annotation is SecretStr:
            assert f"AGENTS_{field_name.upper()}" in PRODUCTION_SECRETS, field_name
