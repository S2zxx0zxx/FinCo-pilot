"""Real PostgreSQL bootstrap race proof in a private disposable CI schema."""
import asyncio
import os
import uuid

from fastapi import HTTPException
from fastapi_users.db import SQLAlchemyUserDatabase
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.main import app  # noqa: F401  # register all application models
from app.core.auth import UserManager
from app.core.database import Base, engine
from app.models.app_settings import AppSetting
from app.models.user import User
from app.services.admin_bootstrap_service import BOOTSTRAP_RECORD_KEY, CreateAdminRequest, provision_first_admin


async def main():
    if os.environ.get("FINCO_DISPOSABLE_DB_TEST") != "yes" or os.environ.get("CI") != "true":
        raise SystemExit("Refusing proof outside explicitly disposable CI")
    schema = "bootstrap_ci_" + uuid.uuid4().hex
    isolated = create_async_engine(engine.url, connect_args={"server_settings": {"search_path": schema + ",public"}})
    sessions = async_sessionmaker(isolated, expire_on_commit=False)
    try:
        async with engine.begin() as connection:
            await connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        async with isolated.begin() as connection:
            await connection.run_sync(lambda sync: Base.metadata.create_all(sync, checkfirst=False))
            resolved_schema = await connection.scalar(text(
                "SELECT n.nspname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
                "WHERE c.oid=\'users\'::regclass"
            ))
            assert resolved_schema == schema, "Proof must resolve its own isolated user table"
        start = asyncio.Event()

        async def attempt(number):
            async with sessions() as session:
                await start.wait()
                try:
                    await provision_first_admin(session, UserManager(SQLAlchemyUserDatabase(session, User)),
                        CreateAdminRequest(email=f"operator{number}@example.com", password="Synthetic-CI-only-password", language="en"))
                    await session.commit()
                    return "created"
                except HTTPException as exc:
                    await session.rollback()
                    assert exc.status_code == 403
                    return "closed"
        tasks = [asyncio.create_task(attempt(n)) for n in range(2)]
        start.set()
        results = await asyncio.wait_for(asyncio.gather(*tasks), timeout=60)
        assert sorted(results) == ["closed", "created"], results
        async with sessions() as session:
            assert await session.scalar(select(func.count(User.id))) == 1
            assert await session.get(AppSetting, BOOTSTRAP_RECORD_KEY) is not None
        print("PASS: concurrent different-email bootstrap produced exactly one admin and completion record")
    finally:
        await isolated.dispose()
        async with engine.begin() as connection:
            await connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
