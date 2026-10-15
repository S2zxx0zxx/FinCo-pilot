"""Disposable native proof of stale-role rejection and mutation serialization.

No provider calls or live records: creates/drops only a random synthetic schema.
"""
import asyncio
import os
import uuid

from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.database import Base, engine
from app.core.workspace_context import current_workspace, current_writable_workspace
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember
from app.services.workspace_service import update_member_role


async def wait_for_lock(observer, pid, task):
    for _ in range(250):
        if task.done():
            raise AssertionError("Contending operation completed without waiting for workspace lock")
        if await observer.scalar(text("SELECT cardinality(pg_blocking_pids(:pid)) > 0"), {"pid": pid}):
            return
        await asyncio.sleep(0.02)
    raise AssertionError("Expected native PostgreSQL lock wait was not observed")


async def main():
    if os.environ.get("CI") != "true" or os.environ.get("FINCO_DISPOSABLE_DB_TEST") != "yes":
        raise SystemExit("Refusing role race proof outside explicitly disposable CI")
    schema = "role_race_ci_" + uuid.uuid4().hex
    isolated = create_async_engine(engine.url, connect_args={"server_settings": {
        "search_path": schema + ",public", "statement_timeout": "10000",
    }})
    sessions = async_sessionmaker(isolated, expire_on_commit=False)
    uid, wid = uuid.uuid4(), uuid.uuid4()
    try:
        async with engine.begin() as connection:
            await connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        async with isolated.begin() as connection:
            await connection.run_sync(lambda conn: Base.metadata.create_all(
                conn, tables=[Base.metadata.tables[name] for name in (
                    "users", "workspaces", "workspace_members", "workspace_deletions",
                )],
                checkfirst=False,
            ))
        async with sessions() as session:
            session.add(User(id=uid, email="role-race@example.invalid", hashed_password="synthetic-unusable",
                             is_active=True, is_verified=True, is_superuser=False))
            await session.flush()
            session.add(Workspace(id=wid, name="Synthetic role proof", kind="business",
                                  created_by_user_id=uid, billing_owner_user_id=uid))
            await session.flush()
            session.add(WorkspaceMember(workspace_id=wid, user_id=uid, role="editor"))
            await session.commit()

        async with sessions() as writer, sessions() as owner:
            user = await writer.get(User, uid)
            assert user is not None
            ctx = await current_workspace(str(wid), user, writer)
            assert ctx.role == "editor"
            pid = await writer.scalar(text("SELECT pg_backend_pid()"))
            await update_member_role(owner, wid, uid, "viewer")
            task = asyncio.create_task(current_writable_workspace(ctx, writer))
            try:
                await wait_for_lock(owner, pid, task)
                await owner.commit()
                try:
                    await asyncio.wait_for(task, 5)
                except HTTPException as exc:
                    assert exc.status_code == 403
                else:
                    raise AssertionError("Stale editor retained write access after committed downgrade")
            finally:
                await owner.rollback()
                if not task.done():
                    task.cancel()
                await asyncio.gather(task, return_exceptions=True)
                await writer.rollback()

        async with sessions() as session:
            await update_member_role(session, wid, uid, "editor")
            await session.commit()
        async with sessions() as writer, sessions() as owner:
            user = await writer.get(User, uid)
            assert user is not None
            ctx = await current_workspace(str(wid), user, writer)
            assert (await current_writable_workspace(ctx, writer)).can_write
            pid = await owner.scalar(text("SELECT pg_backend_pid()"))
            task = asyncio.create_task(update_member_role(owner, wid, uid, "viewer"))
            try:
                await wait_for_lock(writer, pid, task)
                await writer.commit()
                await asyncio.wait_for(task, 5)
                await owner.commit()
            finally:
                await writer.rollback()
                if not task.done():
                    task.cancel()
                await asyncio.gather(task, return_exceptions=True)
                await owner.rollback()
        async with sessions() as session:
            role = await session.scalar(select(WorkspaceMember.role).where(
                WorkspaceMember.workspace_id == wid, WorkspaceMember.user_id == uid,
            ))
            assert role == "viewer"
        print("PASS: native workspace lock waits observed; stale editor denied after downgrade; in-flight writer finishes before downgrade")
    finally:
        await isolated.dispose()
        async with engine.begin() as connection:
            await connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
