import uuid
from datetime import timedelta
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from app.models.account_deletion import AccountDeletion, AccountDeletionHold, utcnow
from app.models.workspace import Workspace, WorkspaceMember
from app.models.user import User
from app.models.account import Account
from app.models.transaction_attachment import TransactionAttachment
from app.services import account_deletion_service as service


async def operator(session):
    user = User(id=uuid.uuid4(), email='operator@example.com', hashed_password='unused', is_active=True, is_superuser=True, is_verified=True)
    session.add(user)
    await session.commit()
    return user


async def approved(session, user, admin):
    result = await service.request_deletion(session, user)
    job = await session.get(AccountDeletion, uuid.UUID(result['id']))
    await service.review_deletion(session, job, admin, 'a' * 64)
    for requirement in job.manifest['requirements']:
        await service.record_receipt(session, job, admin, requirement, 'b' * 64)
    return job, result


@pytest.mark.asyncio
async def test_private_cleanup_shared_preservation_backup_gate(session, test_user, test_workspace):
    admin = await operator(session)
    shared = Workspace(id=uuid.uuid4(), name='Shared', kind='business', created_by_user_id=test_user.id, managed_by_user_id=test_user.id, billing_owner_user_id=admin.id)
    session.add(shared)
    await session.flush()
    session.add_all([WorkspaceMember(workspace_id=shared.id, user_id=test_user.id, role='editor'), WorkspaceMember(workspace_id=shared.id, user_id=admin.id, role='owner')])
    financial = Account(id=uuid.uuid4(), user_id=test_user.id, workspace_id=shared.id, name='Keep', type='checking', currency='INR', balance=12)
    session.add(financial)
    await session.commit()
    job, _ = await approved(session, test_user, admin)
    assert not job.blockers
    await service.execute_deletion(session, job)
    assert job.state == 'backup_expiry_pending'
    assert await session.get(Workspace, test_workspace.id) is None
    await session.refresh(shared)
    assert shared.name == 'Shared' and shared.created_by_user_id is None and shared.managed_by_user_id is None
    assert await session.get(Account, financial.id)
    await session.refresh(test_user)
    assert not test_user.is_active and not test_user.is_superuser
    assert test_user.email.endswith('@invalid.example') and not test_user.preferences
    with pytest.raises(HTTPException):
        await service.complete_backups(session, job, admin, 'c' * 64, job.primary_deleted_at - timedelta(seconds=1))
    await service.complete_backups(session, job, admin, 'c' * 64, utcnow())
    assert job.state == 'complete'
    with pytest.raises(HTTPException):
        await service.execute_deletion(session, job)


@pytest.mark.asyncio
async def test_block_last_admin_shared_owner_payer_and_hold(session, test_user, test_workspace):
    test_user.is_superuser = True
    test_workspace.kind = 'business'
    test_workspace.billing_owner_user_id = test_user.id
    session.add(AccountDeletionHold(user_id=test_user.id, evidence_sha256='a'*64, reason='legal', verified_by=str(test_user.id)))
    await session.commit()
    result = await service.request_deletion(session, test_user)
    assert result['state'] == 'blocked'
    assert set(result['blockers']) == {'last_active_superuser', 'sole_owner_shared_workspace', 'shared_workspace_billing_owner', 'verified_legal_hold'}
    job = await session.get(AccountDeletion, uuid.UUID(result['id']))
    with pytest.raises(HTTPException):
        await service.execute_deletion(session, job)
    assert test_user.is_active and await session.get(Workspace, test_workspace.id)


@pytest.mark.asyncio
async def test_changed_inventory_and_missing_receipts_fail_before_purge(session, test_user, test_workspace):
    admin = await operator(session)
    result = await service.request_deletion(session, test_user)
    job = await session.get(AccountDeletion, uuid.UUID(result['id']))
    await service.review_deletion(session, job, admin, 'a' * 64)
    with pytest.raises(HTTPException, match='receipts'):
        await service.execute_deletion(session, job)
    await session.refresh(admin)
    await session.refresh(test_workspace)
    for requirement in job.manifest['requirements']:
        await service.record_receipt(session, job, admin, requirement, 'b' * 64)
    test_workspace.name = 'Changed after review'
    await session.commit()
    with pytest.raises(HTTPException, match='Inventory changed'):
        await service.execute_deletion(session, job)
    await session.refresh(test_user)
    assert test_user.is_active and not job.lease_token


@pytest.mark.asyncio
async def test_object_failure_resumes_from_durable_manifest(session, test_user, test_workspace, test_account, test_transactions):
    admin = await operator(session)
    attachment = TransactionAttachment(transaction_id=test_transactions[0].id, workspace_id=test_workspace.id, user_id=test_user.id, filename='private.pdf', storage_key='private-key', content_type='application/pdf', size=4)
    session.add(attachment)
    await session.commit()
    job, _ = await approved(session, test_user, admin)
    provider = AsyncMock()
    provider.name = 'local'
    provider.delete.side_effect = RuntimeError('secret provider message')
    with patch.object(service, 'get_storage_provider', return_value=provider):
        await service.execute_deletion(session, job)
        assert job.state == 'external_retry' and job.manifest['objects'][0]['key'] == 'private-key'
        await session.refresh(test_user)
        assert not test_user.is_active
        assert 'secret' not in str(service.public_status(job))
        provider.delete.side_effect = None
        await service.execute_deletion(session, job)
    assert job.state == 'backup_expiry_pending' and job.manifest['objects'] == []
    assert provider.delete.await_count == 2


@pytest.mark.asyncio
async def test_active_request_unique_and_status_has_no_manifest(session, test_user, test_workspace):
    result = await service.request_deletion(session, test_user)
    with pytest.raises(HTTPException, match='active deletion'):
        await service.request_deletion(session, test_user)
    job = await session.get(AccountDeletion, uuid.UUID(result['id']))
    assert 'tracking_digest' not in service.public_status(job)
    assert 'manifest' not in service.public_status(job)


@pytest.mark.asyncio
async def test_executor_lease_blocks_duplicate(session, test_user, test_workspace):
    admin = await operator(session)
    job, _ = await approved(session, test_user, admin)
    job.lease_token, job.lease_until = 'f'*64, utcnow() + timedelta(minutes=10)
    await session.commit()
    with pytest.raises(HTTPException, match='owns the request'):
        await service.execute_deletion(session, job)
    assert test_user.is_active


@pytest.mark.asyncio
async def test_shared_key_conflict_retains_bytes_and_retries_without_false_success(session, test_user, test_workspace, test_transactions):
    admin = await operator(session)
    shared = Workspace(id=uuid.uuid4(), name='Shared bytes', kind='business', billing_owner_user_id=admin.id)
    session.add(shared)
    await session.flush()
    session.add(WorkspaceMember(workspace_id=shared.id, user_id=admin.id, role='owner'))
    for workspace in (test_workspace, shared):
        session.add(TransactionAttachment(transaction_id=test_transactions[0].id, workspace_id=workspace.id,
            user_id=test_user.id, filename='same.pdf', storage_key='same-key', content_type='application/pdf', size=1))
    await session.commit()
    result = await service.request_deletion(session, test_user)
    job = await session.get(AccountDeletion, uuid.UUID(result['id']))
    assert 'cross_workspace_reference' in job.blockers
    with pytest.raises(HTTPException):
        await service.execute_deletion(session, job)
    assert test_user.is_active


@pytest.mark.asyncio
async def test_last_active_owner_cannot_leave_with_only_inactive_coowner(session, test_user, test_workspace):
    admin = await operator(session)
    admin.is_active = False
    test_workspace.kind = 'business'
    session.add(WorkspaceMember(workspace_id=test_workspace.id, user_id=admin.id, role='owner'))
    await session.commit()
    result = await service.request_deletion(session, test_user)
    assert 'sole_owner_shared_workspace' in result['blockers']


@pytest.mark.asyncio
async def test_expired_review_and_new_hold_require_recheck(session, test_user, test_workspace):
    admin = await operator(session)
    job, _ = await approved(session, test_user, admin)
    job.review = {**job.review, 'at': (utcnow() - timedelta(days=2)).isoformat()}
    await session.commit()
    with pytest.raises(HTTPException, match='review expired'):
        await service.execute_deletion(session, job)
    await session.refresh(admin)
    await session.refresh(test_user)
    await service.review_deletion(session, job, admin, 'a'*64)
    for requirement in job.manifest['requirements']:
        await service.record_receipt(session, job, admin, requirement, 'b'*64)
    session.add(AccountDeletionHold(user_id=test_user.id, evidence_sha256='d'*64, reason='dispute', verified_by=str(admin.id)))
    await session.commit()
    with pytest.raises(HTTPException) as error:
        await service.execute_deletion(session, job)
    assert error.value.detail == {'blockers': ['verified_legal_hold']}


@pytest.mark.asyncio
async def test_user_cannot_be_reactivated_through_admin_service(session, test_user, test_workspace):
    from app.schemas.admin import AdminUserUpdate
    from app.services.admin_service import update_user
    from app.models.account_deletion import AccountDeletionEvent
    from sqlalchemy import select
    admin = await operator(session)
    job, _ = await approved(session, test_user, admin)
    await service.execute_deletion(session, job)
    with pytest.raises(ValueError, match='tombstones'):
        await update_user(session, test_user.id, AdminUserUpdate(is_active=True), admin.id)
    events = list((await session.scalars(select(AccountDeletionEvent).where(AccountDeletionEvent.deletion_id == job.id))).all())
    assert {'requested', 'reviewed', 'external_receipt', 'primary_purged', 'backup_expiry_pending'} <= {event.event_type for event in events}
    assert 'private-key' not in str([e.details for e in events])
