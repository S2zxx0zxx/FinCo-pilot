"""Synthetic PostgreSQL schema-gate proof, restricted to CI's disposable DB."""

import asyncio
import os

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import Base
from app.core.database_runtime import create_database_engine
from app.core.schema_safety import SchemaContractError, reject_unmanaged_schema, verify_runtime_schema
from app.models import *  # noqa: F403
from app.agents.models import *  # noqa: F403


async def run() -> None:
    settings = get_settings()
    if os.environ.get("FINCO_DISPOSABLE_DB_TEST") != "yes" or make_url(settings.database_url).database != "finco_ci":
        raise RuntimeError("Schema-gate mutation proof is restricted to the disposable finco_ci database")
    engine = create_database_engine(settings, short_lived=True)
    try:
        async with engine.connect() as connection:
            await connection.run_sync(lambda c: reject_unmanaged_schema(c, Base.metadata.tables.keys()))
            async with AsyncSession(bind=connection) as session:
                await verify_runtime_schema(session)
            await connection.rollback()
            for defect in ("missing_history", "wrong_head", "wrong_column"):
                transaction = await connection.begin()
                try:
                    if defect == "missing_history":
                        await connection.execute(text("ALTER TABLE alembic_version RENAME TO synthetic_hidden_version"))
                        try:
                            await connection.run_sync(lambda c: reject_unmanaged_schema(c, Base.metadata.tables.keys()))
                        except SchemaContractError:
                            pass
                        else:
                            raise AssertionError("Unmanaged native schema was accepted")
                    elif defect == "wrong_head":
                        await connection.execute(text("UPDATE alembic_version SET version_num='001'"))
                    else:
                        await connection.execute(text("ALTER TABLE users RENAME COLUMN auth_epoch TO synthetic_hidden_epoch"))
                    async with AsyncSession(bind=connection) as session:
                        try:
                            await verify_runtime_schema(session)
                        except SchemaContractError:
                            pass
                        else:
                            raise AssertionError(f"Runtime accepted synthetic {defect}")
                finally:
                    await transaction.rollback()
            async with AsyncSession(bind=connection) as session:
                await verify_runtime_schema(session)
        print("PASS: native PostgreSQL rejects missing history, wrong head and wrong core column; injected defects rolled back")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run())
