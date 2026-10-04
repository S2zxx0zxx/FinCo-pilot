"""Single-use reset race proof, exclusively in a private disposable CI schema."""
import asyncio
import os
import uuid
from unittest.mock import AsyncMock, patch

from fastapi_users import exceptions
from fastapi_users.db import SQLAlchemyUserDatabase
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.main import app  # noqa: F401  register all models
from app.core.auth import UserManager
from app.core.database import Base, engine
from app.models.user import User
from app.schemas.user import UserCreate


async def main():
    if os.environ.get('FINCO_DISPOSABLE_DB_TEST') != 'yes' or os.environ.get('CI') != 'true':
        raise SystemExit('Refusing proof outside explicitly disposable CI')
    schema = 'reset_ci_' + uuid.uuid4().hex
    isolated = create_async_engine(engine.url, connect_args={'server_settings': {'search_path': schema + ',public'}})
    sessions = async_sessionmaker(isolated, expire_on_commit=False)
    try:
        async with engine.begin() as connection:
            await connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        async with isolated.begin() as connection:
            await connection.run_sync(lambda sync: Base.metadata.create_all(sync, checkfirst=False))
            resolved = await connection.scalar(text("SELECT n.nspname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE c.oid='users'::regclass"))
            assert resolved == schema
        captured = AsyncMock()
        async with sessions() as session:
            manager = UserManager(SQLAlchemyUserDatabase(session, User))
            user = await manager.create(UserCreate(email='reset-proof@example.com', password='Synthetic-initial-password'))
            with patch.object(manager, 'on_after_forgot_password', captured):
                await manager.forgot_password(user)
            assert captured.await_args is not None
            token = captured.await_args.args[1]
        start = asyncio.Event()
        async def attempt(number):
            async with sessions() as session:
                manager = UserManager(SQLAlchemyUserDatabase(session, User))
                await start.wait()
                try:
                    await manager.reset_password(token, f'Synthetic-replacement-{number}')
                    return 'changed'
                except exceptions.InvalidResetPasswordToken:
                    await session.rollback()
                    return 'used'
        with patch('app.core.auth.send_password_changed_email', AsyncMock(return_value=True)):
            tasks = [asyncio.create_task(attempt(n)) for n in range(2)]
            start.set()
            results = await asyncio.wait_for(asyncio.gather(*tasks), 45)
        assert sorted(results) == ['changed', 'used'], results
        print('PASS: two concurrent PostgreSQL resets consumed one credential exactly once')
    finally:
        await isolated.dispose()
        async with engine.begin() as connection:
            await connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        await engine.dispose()


if __name__ == '__main__':
    asyncio.run(main())
