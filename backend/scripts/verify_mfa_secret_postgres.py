"""Disposable CI proof that migration 098 preserves seeds and refuses destructive rollback."""
import asyncio
import importlib.util
import os
import uuid
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.database import engine
from app.core.mfa_secret import PREFIX, encrypt_seed
from app.models.user import User


def migration(connection, direction):
    path = Path(__file__).resolve().parents[1] / "alembic" / "versions" / "098_encrypted_mfa_seeds.py"
    spec = importlib.util.spec_from_file_location("mfa_migration", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with Operations.context(MigrationContext.configure(connection)):
        getattr(module, direction)()


async def main():
    if os.environ.get("CI") != "true" or os.environ.get("FINCO_DISPOSABLE_DB_TEST") != "yes":
        raise SystemExit("Refusing proof outside explicitly disposable CI")
    schema = "mfa_ci_" + uuid.uuid4().hex
    isolated = create_async_engine(engine.url, connect_args={"server_settings": {"search_path": schema}})
    user_id = uuid.uuid4()
    seed = "JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP"
    try:
        async with engine.begin() as connection:
            await connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        async with isolated.begin() as connection:
            await connection.execute(text("CREATE TABLE users (id uuid PRIMARY KEY, totp_secret varchar(32))"))
            await connection.execute(text("INSERT INTO users(id,totp_secret) VALUES (:id,:seed)"), {"id": user_id, "seed": seed})
            await connection.run_sync(lambda sync: migration(sync, "upgrade"))
            assert await connection.scalar(text("SELECT totp_secret FROM users")) == seed
            sealed = encrypt_seed(seed)
            assert sealed and sealed.startswith(PREFIX) and seed not in sealed
            await connection.execute(text("UPDATE users SET totp_secret=:seed"), {"seed": sealed})
        sessions = async_sessionmaker(isolated)
        async with sessions() as session:
            assert await session.scalar(select(User.totp_secret).where(User.id == user_id)) == seed
        try:
            async with isolated.begin() as connection:
                await connection.run_sync(lambda sync: migration(sync, "downgrade"))
        except RuntimeError as exc:
            assert "Refusing to narrow" in str(exc)
        else:
            raise AssertionError("Encrypted credentials must block destructive narrowing")
        async with isolated.connect() as connection:
            assert await connection.scalar(text("SELECT totp_secret FROM users")) == sealed
        print("PASS: PostgreSQL migration preserves legacy seed, ORM decrypts encrypted seed, destructive downgrade refused without data loss")
    finally:
        await isolated.dispose()
        async with engine.begin() as connection:
            await connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
