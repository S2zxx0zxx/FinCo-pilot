"""Synthetic, isolated PostgreSQL proof: actual FKs, fencing, retries and evidence gates."""
import asyncio
import importlib.util
import os
import tempfile
import uuid
from datetime import timedelta
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from fastapi import HTTPException
from sqlalchemy import insert, select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.models  # noqa: F401
import app.agents.models  # noqa: F401
from app.core.config import get_settings
from app.core.database import Base, engine, async_session_maker
from app.models.account_deletion import AccountDeletion, utcnow
from app.models.account import Account
from app.models.transaction import Transaction
from app.models.transaction_attachment import TransactionAttachment
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember
from app.services import account_deletion_service as service


def migration(connection, direction, revision='099_account_deletion.py'):
    path = Path(__file__).resolve().parents[1] / 'alembic/versions' / revision
    spec = importlib.util.spec_from_file_location('deletion_migration', path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with Operations.context(MigrationContext.configure(connection)):
        getattr(module, direction)()


async def main():
    if os.environ.get('CI') != 'true' or os.environ.get('FINCO_DISPOSABLE_DB_TEST') != 'yes':
        raise SystemExit('Refusing account deletion proof outside explicitly disposable CI')
    # Prove the actual full Alembic chain is accepted, not only an ORM-created schema.
    async with async_session_maker() as migrated:
        await service.lock_inventory(migrated)
        await migrated.rollback()
    schema = 'deletion_ci_' + uuid.uuid4().hex
    isolated = create_async_engine(engine.url, connect_args={'server_settings': {'search_path': schema + ',public'}})
    sessions = async_sessionmaker(isolated, expire_on_commit=False)
    uid, aid, private_id, shared_id = (uuid.uuid4() for _ in range(4))
    try:
        async with engine.begin() as connection:
            await connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        async with isolated.begin() as connection:
            tables = [t for t in Base.metadata.sorted_tables if t.name not in {'account_deletions', 'account_deletion_holds', 'account_deletion_events', 'workspace_deletions', 'workspace_deletion_holds', 'workspace_deletion_events'}]
            await connection.run_sync(lambda conn: Base.metadata.create_all(conn, tables=tables, checkfirst=False))
            await connection.run_sync(lambda conn: migration(conn, 'upgrade'))
            await connection.run_sync(lambda conn: migration(conn, 'upgrade', '100_workspace_deletion.py'))
        with tempfile.TemporaryDirectory(prefix='finco-deletion-ci-') as directory:
            get_settings().storage_provider = 'local'
            get_settings().storage_local_path = directory
            private_bytes = Path(directory)/'private.pdf'
            private_bytes.write_bytes(b'synthetic private bytes')
            shared_bytes = Path(directory)/'shared.pdf'
            shared_bytes.write_bytes(b'synthetic shared bytes')
            orphan = Path(directory)/str(private_id)/'invoices/logo'/f'{uuid.uuid4()}.png'
            orphan.parent.mkdir(parents=True)
            orphan.write_bytes(b'synthetic replaced orphan logo')
            kept_orphan = Path(directory)/str(shared_id)/'invoices/logo'/f'{uuid.uuid4()}.png'
            kept_orphan.parent.mkdir(parents=True)
            kept_orphan.write_bytes(b'synthetic shared historical logo')
            async with sessions() as session:
                user = User(id=uid, email='synthetic-deletion@example.invalid', hashed_password='synthetic-unusable-hash', is_active=True, is_verified=True, is_superuser=False)
                admin = User(id=aid, email='synthetic-operator@example.invalid', hashed_password='synthetic-unusable-hash', is_active=True, is_verified=True, is_superuser=True)
                session.add_all([user, admin])
                await session.flush()
                session.add_all([Workspace(id=private_id, name='Synthetic private', kind='personal', created_by_user_id=uid), Workspace(id=shared_id, name='Synthetic shared', kind='business', created_by_user_id=uid, billing_owner_user_id=aid)])
                await session.flush()
                session.add_all([WorkspaceMember(workspace_id=private_id, user_id=uid, role='owner'), WorkspaceMember(workspace_id=shared_id, user_id=uid, role='editor'), WorkspaceMember(workspace_id=shared_id, user_id=aid, role='owner')])
                accounts = [Account(id=uuid.uuid4(), user_id=uid, workspace_id=wid, name='Synthetic', type='checking', currency='INR', balance=0) for wid in (private_id, shared_id)]
                session.add_all(accounts)
                await session.flush()
                from datetime import date
                transactions = [Transaction(id=uuid.uuid4(), user_id=uid, workspace_id=account.workspace_id, account_id=account.id, date=date.today(), amount=1, currency='INR', description='Synthetic', type='expense', source='manual') for account in accounts]
                session.add_all(transactions)
                await session.flush()
                session.add_all([TransactionAttachment(transaction_id=tx.id, user_id=uid, workspace_id=tx.workspace_id, filename=key, storage_key=key, content_type='application/pdf', size=4) for tx, key in zip(transactions, ['private.pdf', 'shared.pdf'], strict=True)])
                await session.commit()
                result = await service.request_deletion(session, user)
                jid = uuid.UUID(result['id'])
                job = await session.get(AccountDeletion, jid)
                assert job
                await service.review_deletion(session, job, admin, 'a'*64)
                for requirement in [key for key in job.manifest['requirements'] if not service.post_primary_requirement(key)]:
                    await service.record_receipt(session, job, admin, requirement, 'b'*64)
            # A competing writer really waits on the workflow's table lock.
            async with sessions() as fenced, sessions() as writer:
                await service.lock_inventory(fenced)
                async def write():
                    await writer.execute(update(Workspace).where(Workspace.id == shared_id).values(name='Synthetic shared'))
                    await writer.commit()
                task = asyncio.create_task(write())
                await asyncio.sleep(0.1)
                assert not task.done(), 'Competing writer bypassed table fence'
                await fenced.rollback()
                await task
            # The upload dependency's KEY SHARE lock must also hold the fence.
            async with sessions() as reader, sessions() as fenced:
                await reader.execute(select(Workspace).where(Workspace.id == private_id).with_for_update(read=True, key_share=True))
                task = asyncio.create_task(service.lock_inventory(fenced))
                await asyncio.sleep(0.1)
                assert not task.done(), 'Deletion bypassed an in-flight upload reader'
                await reader.rollback()
                await task
                await fenced.rollback()
            async with sessions() as session:
                job = await service.locked_job(session, jid)
                await service.execute_deletion(session, job, str(aid))
                assert job.state == 'external_retry' and job.error_code == 'post_primary_reconciliation_required'
                admin = await session.get(User, aid)
                assert admin
                for key in job.manifest['requirements']:
                    if service.post_primary_requirement(key):
                        await service.record_receipt(session, job, admin, key, 'd'*64)
                await service.execute_deletion(session, job, str(aid))
                assert job.state == 'backup_expiry_pending'
                assert not private_bytes.exists() and shared_bytes.exists()
                assert not orphan.exists() and kept_orphan.exists()
                assert await session.get(Workspace, private_id) is None
                assert await session.get(Account, accounts[0].id) is None
                assert await session.get(Account, accounts[1].id)
                assert await session.get(Transaction, transactions[1].id)
                deleted = await session.get(User, uid)
                assert deleted and not deleted.is_active and deleted.hashed_password.startswith('!deleted:')
            # Existing shared rows remain editable; new rows for the erased
            # actor and tombstone reactivation are blocked by DATABASE triggers.
            async with sessions() as session:
                await session.execute(update(Account).where(Account.id == accounts[1].id).values(name='Shared data still editable'))
                await session.commit()
            for statement in [update(User).where(User.id == uid).values(is_active=True), insert(WorkspaceMember).values(id=uuid.uuid4(), workspace_id=shared_id, user_id=uid, role='viewer')]:
                async with sessions() as session:
                    try:
                        await session.execute(statement)
                        await session.commit()
                    except IntegrityError:
                        await session.rollback()
                    else:
                        raise AssertionError('Deleted identity write/reactivation was accepted')
            async with sessions() as session:
                job = await service.locked_job(session, jid)
                admin = await session.get(User, aid)
                assert admin
                try:
                    await service.complete_backups(session, job, admin, 'c'*64, job.primary_deleted_at - timedelta(seconds=1))
                except HTTPException:
                    pass
                else:
                    raise AssertionError('Unexpired backup reported complete')
                await service.complete_backups(session, job, admin, 'c'*64, utcnow())
                assert job.state == 'complete'
            try:
                async with isolated.begin() as connection:
                    await connection.run_sync(lambda conn: migration(conn, 'downgrade'))
            except RuntimeError as exc:
                assert 'Refusing to destroy' in str(exc)
            else:
                raise AssertionError('Nonempty deletion ledger was destroyed')
            print('PASS: PostgreSQL deletion purges private graph/bytes, preserves editable shared graph, fences competing writes and stale actors, rejects tombstone reactivation/backup shortcuts/destructive downgrade')
    finally:
        await isolated.dispose()
        async with engine.begin() as connection:
            await connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        await engine.dispose()


if __name__ == '__main__':
    asyncio.run(main())
