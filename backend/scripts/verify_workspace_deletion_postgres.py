"""Disposable native PostgreSQL proof for original #30, never real user data."""

import asyncio
import os
import tempfile
import uuid
from pathlib import Path
from fastapi import HTTPException
from sqlalchemy import insert, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
import app.models  # noqa: F401
import app.agents.models  # noqa: F401
from app.core.database import Base, engine, async_session_maker
from app.core.config import get_settings
from app.models.user import User
from app.models.account import Account
from app.models.transaction import Transaction
from datetime import date
from app.models.workspace import Workspace, WorkspaceMember
from app.models.subscription import Subscription
from app.models.workspace_deletion import WorkspaceDeletion, utcnow
from app.services import workspace_deletion_service as service
from app.services import workspace_service
from scripts.verify_account_deletion_postgres import migration


async def main():
    if os.environ.get("CI") != "true" or os.environ.get("FINCO_DISPOSABLE_DB_TEST") != "yes":
        raise SystemExit("Refusing workspace deletion proof outside explicitly disposable CI")
    async with async_session_maker() as migrated:
        await service.lock_inventory(migrated)
        await migrated.rollback()
    schema = "workspace_deletion_ci_" + uuid.uuid4().hex
    isolated = create_async_engine(
        engine.url, connect_args={"server_settings": {"search_path": schema + ",public"}}
    )
    sessions = async_sessionmaker(isolated, expire_on_commit=False)
    uid, aid, wid, kept = (uuid.uuid4() for _ in range(4))
    try:
        async with engine.begin() as connection:
            await connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        async with isolated.begin() as connection:
            tables = [
                t
                for t in Base.metadata.sorted_tables
                if t.name
                not in {
                    "account_deletions",
                    "account_deletion_holds",
                    "account_deletion_events",
                    "workspace_deletions",
                    "workspace_deletion_holds",
                    "workspace_deletion_events",
                }
            ]
            await connection.run_sync(
                lambda conn: Base.metadata.create_all(conn, tables=tables, checkfirst=False)
            )
            await connection.run_sync(lambda conn: migration(conn, "upgrade"))
            await connection.run_sync(
                lambda conn: migration(conn, "upgrade", "100_workspace_deletion.py")
            )
        with tempfile.TemporaryDirectory(prefix="finco-workspace-ci-") as directory:
            get_settings().storage_provider = "local"
            get_settings().storage_local_path = directory
            private = Path(directory) / str(wid) / "private.bin"
            private.parent.mkdir()
            private.write_bytes(b"synthetic private")
            shared = Path(directory) / str(kept) / "keep.bin"
            shared.parent.mkdir()
            shared.write_bytes(b"synthetic keep")
            async with sessions() as session:
                user = User(
                    id=uid,
                    email="workspace-synthetic@example.invalid",
                    hashed_password="synthetic-unused",
                    is_active=True,
                    is_verified=True,
                    is_superuser=False,
                )
                admin = User(
                    id=aid,
                    email="workspace-operator@example.invalid",
                    hashed_password="synthetic-unused",
                    is_active=True,
                    is_verified=True,
                    is_superuser=True,
                )
                session.add_all([user, admin])
                await session.flush()
                session.add_all(
                    [
                        Workspace(
                            id=wid,
                            name="Synthetic business",
                            kind="business",
                            created_by_user_id=uid,
                            billing_owner_user_id=uid,
                            is_archived=True,
                        ),
                        Workspace(
                            id=kept,
                            name="Keep",
                            kind="personal",
                            created_by_user_id=uid,
                            billing_owner_user_id=uid,
                        ),
                    ]
                )
                await session.flush()
                session.add_all(
                    [
                        WorkspaceMember(workspace_id=wid, user_id=uid, role="owner"),
                        WorkspaceMember(workspace_id=kept, user_id=uid, role="owner"),
                        WorkspaceMember(workspace_id=kept, user_id=aid, role="owner"),
                    ]
                )
                accounts = [
                    Account(
                        id=uuid.uuid4(),
                        user_id=aid,
                        workspace_id=identity,
                        name="Synthetic other author",
                        type="checking",
                        currency="INR",
                        balance=1,
                    )
                    for identity in (wid, kept)
                ]
                session.add_all(accounts)
                await session.flush()
                session.add_all(
                    [
                        Transaction(
                            user_id=aid,
                            workspace_id=account.workspace_id,
                            account_id=account.id,
                            date=date.today(),
                            amount=1,
                            currency="INR",
                            description="Synthetic",
                            type="expense",
                            source="manual",
                        )
                        for account in accounts
                    ]
                )
                subscription = Subscription(user_id=uid, plan="free", status="free")
                session.add(subscription)
                await session.commit()
                result = await service.request_deletion(session, user, wid)
                job = await session.get(WorkspaceDeletion, uuid.UUID(result["id"]))
                assert job is not None and admin is not None
                await service.review_deletion(session, job, admin, "a" * 64)
                for key in job.manifest["requirements"]:
                    if not service.post_primary_requirement(key):
                        await service.record_receipt(session, job, admin, key, "b" * 64)
                jid = job.id

            # Two owners leaving concurrently serialize; one must be refused.
            async def leave(user_id):
                async with sessions() as s:
                    try:
                        await workspace_service.remove_member(s, kept, user_id)
                        await s.commit()
                        return True
                    except HTTPException as e:
                        await s.rollback()
                        assert e.status_code == 400
                        return False

            results = await asyncio.gather(leave(uid), leave(aid))
            assert sorted(results) == [False, True]
            # Keep requester access for this independent deletion acceptance.
            async with sessions() as session:
                if not await workspace_service.get_membership(session, kept, uid):
                    await workspace_service.add_member(session, kept, uid, "owner")
                    await session.commit()
                job = await service.locked_job(session, jid)
                user = await session.get(User, uid)
                admin = await session.get(User, aid)
                assert job is not None and admin is not None
                await service.review_deletion(session, job, admin, "a" * 64)
                for key in job.manifest["requirements"]:
                    if not service.post_primary_requirement(key):
                        await service.record_receipt(session, job, admin, key, "b" * 64)
                await service.execute_deletion(session, job, str(aid))
                assert (
                    job.state == "external_retry"
                    and not private.exists()
                    and shared.read_bytes() == b"synthetic keep"
                )
                assert await session.get(Workspace, wid) is None
                assert (
                    await session.scalar(select(Account.id).where(Account.workspace_id == wid))
                    is None
                )
                assert (
                    await session.scalar(
                        select(Transaction.id).where(Transaction.workspace_id == wid)
                    )
                    is None
                )
                assert (
                    await session.scalar(select(Account.id).where(Account.workspace_id == kept))
                    is not None
                )
                assert (
                    await session.scalar(
                        select(Transaction.id).where(Transaction.workspace_id == kept)
                    )
                    is not None
                )
                surviving_user = await session.get(User, uid)
                assert surviving_user is not None and surviving_user.is_active
                assert await session.scalar(
                    select(Subscription.id).where(Subscription.user_id == uid)
                )
                for key in job.manifest["requirements"]:
                    if service.post_primary_requirement(key):
                        await service.record_receipt(session, job, admin, key, "c" * 64)
                await service.execute_deletion(session, job, str(aid))
                assert job.state == "backup_expiry_pending"
                await service.complete_backups(session, job, admin, "d" * 64, utcnow())
            # Persisted tombstone prevents the same UUID being restored live.
            async with sessions() as s:
                try:
                    await s.execute(
                        insert(Workspace).values(id=wid, name="Must not return", kind="business")
                    )
                    await s.commit()
                    raise AssertionError("Deleted workspace resurrected")
                except IntegrityError:
                    await s.rollback()
            async with isolated.begin() as c:
                try:
                    await c.run_sync(
                        lambda conn: migration(conn, "downgrade", "100_workspace_deletion.py")
                    )
                except RuntimeError:
                    pass
                else:
                    raise AssertionError("Nonempty deletion ledger destroyed")
        print(
            "PASS: workspace purge preserves account/global subscription/other bytes; concurrent owner exits retain one owner; native tombstone refuses resurrection; actual evidence and downgrade gates enforced"
        )
    finally:
        await isolated.dispose()
        async with engine.begin() as c:
            await c.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))


if __name__ == "__main__":
    asyncio.run(main())
