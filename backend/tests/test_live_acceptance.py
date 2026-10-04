import json
from datetime import date, timedelta
from decimal import Decimal

import pytest
from pydantic import SecretStr, ValidationError

from app.core.config import Settings, get_settings
from app.models.app_settings import AppSetting
from app.models.fx_rate import FxRate
from app.services.admin_bootstrap_service import BOOTSTRAP_RECORD_KEY
from scripts.verify_live_acceptance import runtime_gates


@pytest.mark.asyncio
async def test_audit_never_calls_incomplete_setup_complete(session, clean_db):
    gates = await runtime_gates(session, get_settings(), date(2026, 10, 4))
    assert not gates["production_environment"]
    assert not gates["setup_disabled_and_token_removed"]
    assert not gates["first_admin_active"]
    assert not gates["first_admin_email_verified"]
    assert not gates["first_admin_mfa_enrolled"]
    assert not gates["fx_common_date_provider_cache"]
    assert not session.new and not session.dirty and not session.deleted


@pytest.mark.asyncio
async def test_audit_identifies_recorded_admin_and_common_provider_date(session, test_superuser):
    today = date(2026, 10, 4)
    test_superuser.is_verified = True
    test_superuser.is_2fa_enabled = True
    test_superuser.totp_secret = "SYNTHETIC-SEED"
    session.add(AppSetting(key=BOOTSTRAP_RECORD_KEY, value=json.dumps({"event": "first_admin_bootstrapped", "version": 1, "user_id": str(test_superuser.id)})))
    for code in ("INR", "EUR"):
        session.add(FxRate(base_currency="USD", quote_currency=code, date=today, rate=Decimal("2"), source="openexchangerates"))
    await session.commit()
    settings = get_settings().model_copy(update={"deployment_environment": "production", "setup_enabled": False, "setup_token": SecretStr(""), "supported_currencies": "USD,INR,EUR", "require_fx_provider": True, "fx_sync_mode": "scheduled", "fx_allow_unsafe_1to1_fallback": False})
    gates = await runtime_gates(session, settings, today)
    assert gates["first_admin_active"] and gates["first_admin_email_verified"] and gates["first_admin_mfa_enrolled"]
    assert gates["fx_common_date_provider_cache"]
    assert gates["setup_disabled_and_token_removed"]
    assert not session.new and not session.dirty and not session.deleted


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["different_dates", "future", "stale", "synthetic_source"])
async def test_audit_rejects_untruthful_fx_cache(session, clean_db, kind):
    today = date(2026, 10, 4)
    for index, code in enumerate(("INR", "EUR")):
        observed = today
        if kind == "different_dates":
            observed -= timedelta(days=index)
        elif kind == "future":
            observed += timedelta(days=1)
        elif kind == "stale":
            observed -= timedelta(days=8)
        session.add(FxRate(base_currency="USD", quote_currency=code, date=observed, rate=Decimal("2"), source="fixture" if kind == "synthetic_source" else "openexchangerates"))
    await session.commit()
    settings = get_settings().model_copy(update={"supported_currencies": "USD,INR,EUR"})
    assert not (await runtime_gates(session, settings, today))["fx_common_date_provider_cache"]


def test_configuration_failure_text_does_not_echo_secrets():
    marker = "synthetic-do-not-log-this-secret"
    with pytest.raises(ValidationError) as error:
        Settings(deployment_environment="invalid", database_url=marker, smtp_password=marker)
    assert marker not in str(error.value)
    assert "input_value" not in str(error.value)
