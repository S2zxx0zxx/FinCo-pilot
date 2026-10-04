"""Inspect by default; explicitly encrypt a bounded batch of existing authenticator seeds."""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def seal_batch(session: AsyncSession, execute: bool, limit: int) -> dict[str, int | bool]:
    from sqlalchemy import Text, cast, func, select
    from sqlalchemy.orm.attributes import flag_modified
    from app.core.mfa_secret import PREFIX
    from app.models.user import User
    if not 1 <= limit <= 500:
        raise ValueError("Batch size must be 1 to 500")
    legacy = (User.totp_secret.is_not(None), cast(User.totp_secret, Text).not_like(PREFIX + "%"))
    count = int(await session.scalar(select(func.count(User.id)).where(*legacy)) or 0)
    converted = 0
    if execute:
        users = (await session.scalars(select(User).where(*legacy).order_by(User.id).limit(limit).with_for_update(skip_locked=True).execution_options(populate_existing=True))).all()
        for user in users:
            if not user.totp_secret:
                raise ValueError("Legacy authenticator data invalid; no changes committed")
            # Rebinding through the encrypted column seals plaintext without
            # replacing the seed, enabled state, recovery codes or auth epoch.
            flag_modified(user, "totp_secret")
        converted = len(users)
        await session.flush()
        remaining = int(await session.scalar(select(func.count(User.id)).where(*legacy)) or 0)
        await session.commit()
    else:
        remaining = count
        await session.rollback()
    return {"execute": execute, "legacy_rows_before": count, "rows_encrypted": converted, "legacy_rows_remaining": remaining}


async def operation(execute: bool, limit: int):
    from app.core.config import get_settings
    if not get_settings().is_production:
        raise ValueError("Production configuration required")
    from app.core.database import async_session_maker, engine
    try:
        async with async_session_maker() as session:
            try:
                return await seal_batch(session, execute, limit)
            except Exception:
                await session.rollback()
                raise
    finally:
        await engine.dispose()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="Encrypt one batch; requires migration 098 and retained encryption keys")
    parser.add_argument("--batch-size", type=int, default=100)
    args = parser.parse_args()
    try:
        print(json.dumps(asyncio.run(operation(args.execute, args.batch_size))))
        return 0
    except Exception:
        print('Legacy MFA sealing: FAIL (configuration/database/key); no secret printed', file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
