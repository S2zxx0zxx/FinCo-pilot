"""Read-only runtime gates; never substitutes for real inbox/login/provider evidence."""
from __future__ import annotations

import asyncio
import json
import sys
import uuid
from datetime import date, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import Text, cast, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from app.core.config import Settings


async def runtime_gates(session: AsyncSession, settings: Settings, today: date) -> dict[str, bool]:
    from app.models.app_settings import AppSetting
    from app.models.fx_rate import FxRate
    from app.models.user import User
    from app.services.admin_bootstrap_service import BOOTSTRAP_RECORD_KEY

    from app.core.mfa_secret import PREFIX

    gates = {
        "production_environment": settings.is_production,
        "setup_disabled_and_token_removed": not settings.setup_enabled and not settings.setup_token.get_secret_value().strip(),
        "smtp_configuration": settings.email_delivery_required and settings.email_delivery_available,
        "fx_release_configuration": settings.require_fx_provider and settings.fx_sync_mode == "scheduled" and not settings.fx_allow_unsafe_1to1_fallback,
        "mfa_seeds_encrypted": not bool(await session.scalar(select(func.count(User.id)).where(User.totp_secret.is_not(None), cast(User.totp_secret, Text).not_like(PREFIX + "%")))),
        "first_admin_active": False,
        "first_admin_email_verified": False,
        "first_admin_mfa_enrolled": False,
        "fx_common_date_provider_cache": False,
    }
    record = await session.get(AppSetting, BOOTSTRAP_RECORD_KEY)
    user = None
    if record:
        try:
            payload = json.loads(record.value)
            if isinstance(payload, dict) and payload.get("event") == "first_admin_bootstrapped" and payload.get("version") == 1:
                user = await session.get(User, uuid.UUID(payload["user_id"]))
        except (TypeError, ValueError, KeyError):
            pass
    if user and user.is_active and user.is_superuser:
        gates["first_admin_active"] = True
        gates["first_admin_email_verified"] = bool(user.is_verified)
        gates["first_admin_mfa_enrolled"] = bool(user.is_2fa_enabled and user.totp_secret)
    supported = {code.strip().upper() for code in settings.supported_currencies.split(",") if code.strip()} - {"USD"}
    observations = (await session.scalars(select(FxRate).where(
        FxRate.base_currency == "USD", FxRate.quote_currency.in_(supported),
        FxRate.date <= today, FxRate.date >= today - timedelta(days=7),
        FxRate.source == "openexchangerates",
    ))).all()
    dates: dict[date, set[str]] = {}
    for row in observations:
        if row.rate.is_finite() and row.rate > 0:
            dates.setdefault(row.date, set()).add(row.quote_currency)
    gates["fx_common_date_provider_cache"] = not supported or any(supported <= codes for codes in dates.values())
    return gates


async def verify() -> dict[str, object]:
    from datetime import datetime, timezone
    from app.core.config import get_settings
    from scripts.verify_production_postgres import _expected_heads

    settings = get_settings()
    if not settings.is_production:
        raise ValueError("Production required")
    from app.core.database import async_session_maker, engine

    try:
        async with async_session_maker() as session:
            gates = await runtime_gates(session, settings, datetime.now(timezone.utc).date())
            revisions = set((await session.execute(text("SELECT version_num FROM alembic_version"))).scalars())
            gates["migrations_current"] = revisions == _expected_heads()
            await session.rollback()  # Inspection never persists application changes.
    finally:
        await engine.dispose()
    return {
        "scope": "runtime_configuration_and_database_only",
        "automated_gates_passed": all(gates.values()),
        "gates": gates,
        "live_acceptance_complete": False,
        "remaining_evidence": ["real_admin_login_and_rbac", "operator_mfa_and_recovery_custody", "smtp_tls_auth_and_independent_inboxes", "dns_dkim_dmarc_alignment", "fx_latest_historical_provider_and_sync", "controlled_outage_and_recovery"],
        "database_written": False,
        "email_sent": False,
        "provider_requested": False,
    }


def main() -> int:
    try:
        report = asyncio.run(verify())
        print(json.dumps(report, sort_keys=True))
        return 0 if report["automated_gates_passed"] else 1
    except Exception:
        # Settings/SQL exceptions may contain secret values or connection URLs.
        print(json.dumps({"automated_gates_passed": False, "live_acceptance_complete": False, "reason": "configuration_or_database_unavailable"}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
