"""Non-destructive, atomic credential and Core Copilot key migration.

Dry-run by default. Keep prior keys in LEGACY_DATA_KEYS until a successful
--apply followed by a dry-run with the legacy ring removed. No secret values,
user IDs, provider URLs or row contents are printed.
"""
from __future__ import annotations

import argparse
import asyncio
import sys

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

import app.models  # noqa: F401 - register SQLAlchemy relationships
import app.agents.models  # noqa: F401
from app.agents.models.agent import Agent
from app.agents.models.connection import LlmConnection
from app.agents.services.agent_service import (
    _core_signature, has_protected_copilot_marker, is_core_copilot,
)
from app.agents.services.crypto import decrypt, encrypt
from app.core.config import get_settings
from app.core.database import async_session_maker
from app.models.bank_connection import BankConnection
from app.models.user import User


async def rotate_data(session: AsyncSession, *, apply: bool = False) -> dict[str, int]:
    changes: list[tuple[object, str, object]] = []
    counts = {"llm_credentials": 0, "bank_credentials": 0, "copilot_identities": 0, "mfa_seeds": 0}
    connections = (await session.execute(select(LlmConnection).with_for_update())).scalars().all()
    for row in connections:
        if row.api_key_encrypted:
            plaintext = decrypt(row.api_key_encrypted)
            if plaintext is None:
                raise ValueError("Unreadable LLM credential; restore all previous data keys")
            changes.append((row, "api_key_encrypted", encrypt(plaintext)))
            counts["llm_credentials"] += 1
    banks = (await session.execute(select(BankConnection).with_for_update())).scalars().all()
    for row in banks:
        credentials = dict(row.credentials or {})
        changed = False
        for field in ("access_url_enc", "session_id_enc"):
            if credentials.get(field):
                plaintext = decrypt(credentials[field])
                if plaintext is None:
                    raise ValueError("Unreadable bank credential; restore all previous data keys")
                credentials[field] = encrypt(plaintext)
                changed = True
                counts["bank_credentials"] += 1
        if changed:
            changes.append((row, "credentials", credentials))
    agents = (await session.execute(select(Agent).with_for_update())).scalars().all()
    for row in agents:
        if not has_protected_copilot_marker(row):
            continue
        if not is_core_copilot(row):
            raise ValueError("Unverified Copilot identity; restore all previous data keys")
        extra = dict(row.extra)
        extra["server_signature"] = _core_signature(
            agent_id=row.id, workspace_id=row.workspace_id,
            user_id=row.user_id, version=int(extra["version"]),
        )
        changes.append((row, "extra", extra))
        counts["copilot_identities"] += 1
    users = (await session.scalars(select(User).where(User.totp_secret.is_not(None)).with_for_update().execution_options(populate_existing=True))).all()
    for user in users:
        if not user.totp_secret:
            raise ValueError("Unreadable authenticator; restore all previous data keys")
        changes.append((user, "totp_secret", user.totp_secret))
        counts["mfa_seeds"] += 1
    # Validate every stored value before changing any row.
    if apply:
        for row, field, value in changes:
            setattr(row, field, value)
            if field == "totp_secret":
                flag_modified(row, field)
        await session.flush()
    return counts


async def _run(apply: bool) -> None:
    settings = get_settings()
    if not (settings.credential_encryption_key.get_secret_value().strip()
            and settings.core_copilot_signing_key.get_secret_value().strip()):
        raise ValueError("Configure independent target data keys before migration")
    async with async_session_maker() as session:
        async with session.begin():
            counts = await rotate_data(session, apply=apply)
        print(f"Data-key migration {'APPLIED' if apply else 'DRY RUN'}: {counts}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    try:
        asyncio.run(_run(args.apply))
    except Exception as exc:
        print(f"Data-key migration failed; transaction rolled back ({type(exc).__name__})", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
