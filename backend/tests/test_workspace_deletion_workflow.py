import uuid
from datetime import timedelta
from unittest.mock import AsyncMock, patch
import pytest
from fastapi import HTTPException
from sqlalchemy import select
from app.models.account_deletion import utcnow
from app.models.workspace_deletion import (
    WorkspaceDeletion,
    WorkspaceDeletionHold,
    WorkspaceDeletionEvent,
)
from app.models.workspace import Workspace, WorkspaceMember
from app.models.account import Account
from app.models.subscription import Subscription
from app.services import workspace_deletion_service as service


async def target(session, user):
    workspace = Workspace(
        id=uuid.uuid4(),
        name="Synthetic business",
        kind="business",
        is_archived=True,
        created_by_user_id=user.id,
        managed_by_user_id=user.id,
        billing_owner_user_id=user.id,
    )
    session.add(workspace)
    await session.flush()
    session.add(WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role="owner"))
    await session.commit()
    return workspace


async def approved(session, user, admin, workspace):
    result = await service.request_deletion(session, user, workspace.id)
    job = await session.get(WorkspaceDeletion, uuid.UUID(result["id"]))
    await service.review_deletion(session, job, admin, "a" * 64)
    for k in job.manifest["requirements"]:
        if not service.post_primary_requirement(k):
            await service.record_receipt(session, job, admin, k, "b" * 64)
    return job


@pytest.mark.asyncio
async def test_delete_only_selected_graph_keeps_account_subscription_and_other_workspaces(
    session, test_user, test_superuser, test_workspace, tmp_path
):
    workspace = await target(session, test_user)
    subscription = await session.scalar(
        select(Subscription).where(Subscription.user_id == test_user.id)
    )
    account = Account(
        id=uuid.uuid4(),
        workspace_id=workspace.id,
        user_id=test_superuser.id,
        name="Other author",
        type="checking",
        currency="INR",
        balance=10,
    )
    session.add(account)
    await session.commit()
    with patch(
        "app.services.account_deletion_service.get_storage_provider",
        return_value=AsyncMock(list_keys=AsyncMock(return_value=[])),
    ):
        job = await approved(session, test_user, test_superuser, workspace)
        assert not job.blockers
        assert not any(
            k.startswith(("billing_cancel:", "llm_revoke")) for k in job.manifest["requirements"]
        )
        await service.execute_deletion(session, job, str(test_superuser.id))
    assert (
        job.state == "external_retry" and job.error_code == "post_primary_reconciliation_required"
    )
    assert await session.get(Workspace, workspace.id, populate_existing=True) is None
    assert await session.get(Account, account.id, populate_existing=True) is None
    assert await session.get(Workspace, test_workspace.id) is not None
    await session.refresh(test_user)
    assert test_user.is_active and not test_user.hashed_password.startswith("!deleted:")
    assert await session.get(Subscription, subscription.id) is not None
    for k in job.manifest["requirements"]:
        if service.post_primary_requirement(k):
            await service.record_receipt(session, job, test_superuser, k, "c" * 64)
    await service.execute_deletion(session, job, str(test_superuser.id))
    assert job.state == "backup_expiry_pending" and job.manifest["objects"] == []
    with pytest.raises(HTTPException):
        await service.complete_backups(
            session, job, test_superuser, "d" * 64, job.primary_deleted_at - timedelta(seconds=1)
        )
    await service.complete_backups(session, job, test_superuser, "d" * 64, utcnow())
    assert job.state == "complete"
    events = list(
        (
            await session.scalars(
                select(WorkspaceDeletionEvent).where(WorkspaceDeletionEvent.deletion_id == job.id)
            )
        ).all()
    )
    assert "primary_purged" in [e.event_type for e in events]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "change,blocker",
    [
        ("archive", "workspace_not_archived"),
        ("manager", "other_external_manager_present"),
        ("billing_null", "billing_owner_unresolved"),
        ("billing_other", "billing_owner_mismatch"),
        ("member", "other_members_present"),
        ("owner", "other_owners_present"),
        ("hold", "verified_legal_hold"),
        ("last", "requester_last_accessible_workspace"),
    ],
)
async def test_real_database_preconditions(
    session, test_user, test_superuser, test_workspace, change, blocker
):
    workspace = await target(session, test_user)
    if change == "archive":
        workspace.is_archived = False
    if change == "manager":
        workspace.managed_by_user_id = test_superuser.id
    if change == "billing_null":
        workspace.billing_owner_user_id = None
    if change == "billing_other":
        workspace.billing_owner_user_id = test_superuser.id
    if change in {"member", "owner"}:
        session.add(
            WorkspaceMember(
                workspace_id=workspace.id,
                user_id=test_superuser.id,
                role="owner" if change == "owner" else "viewer",
            )
        )
    if change == "hold":
        session.add(
            WorkspaceDeletionHold(
                workspace_id=workspace.id,
                reason="legal",
                evidence_sha256="a" * 64,
                verified_by=str(test_superuser.id),
            )
        )
    if change == "last":
        test_workspace.is_archived = True
    await session.commit()
    _, blockers, _ = await service.inventory(session, test_user, workspace.id)
    assert blocker in blockers


@pytest.mark.asyncio
async def test_virtual_manager_and_editor_have_no_deletion_authority(
    session, test_user, test_superuser
):
    workspace = await target(session, test_user)
    workspace.managed_by_user_id = test_superuser.id
    await session.commit()
    with pytest.raises(HTTPException) as e:
        await service.request_deletion(session, test_superuser, workspace.id)
    assert e.value.status_code == 404
    session.add(
        WorkspaceMember(workspace_id=workspace.id, user_id=test_superuser.id, role="editor")
    )
    await session.commit()
    with pytest.raises(HTTPException) as e:
        await service.request_deletion(session, test_superuser, workspace.id)
    assert e.value.status_code == 403


@pytest.mark.asyncio
async def test_new_collaborator_invalidates_review_no_data_loss(session, test_user, test_superuser):
    workspace = await target(session, test_user)
    job = await approved(session, test_user, test_superuser, workspace)
    session.add(
        WorkspaceMember(workspace_id=workspace.id, user_id=test_superuser.id, role="viewer")
    )
    await session.commit()
    workspace_id = workspace.id
    with pytest.raises(HTTPException):
        await service.execute_deletion(session, job, str(test_superuser.id))
    assert await session.get(Workspace, workspace_id) is not None
    assert job.lease_token is None


@pytest.mark.asyncio
async def test_mutual_account_deletion_gate_and_no_post_evidence_shortcut(
    session, test_user, test_superuser
):
    from app.services import account_deletion_service as personal

    workspace = await target(session, test_user)
    job = await approved(session, test_user, test_superuser, workspace)
    _, blockers, _ = await personal.inventory(session, test_user)
    assert "workspace_deletion_pending" in blockers
    with pytest.raises(HTTPException):
        await service.record_receipt(
            session, job, test_superuser, "processor_cleanup_after_primary", "c" * 64
        )
    with pytest.raises(HTTPException):
        await service.execute_deletion(session, job, str(test_user.id))


@pytest.mark.asyncio
async def test_actual_private_namespace_bytes_retry_and_shared_bytes_preserved(
    session, test_user, test_superuser, test_workspace, tmp_path
):
    from app.core.config import get_settings

    actor_id = str(test_superuser.id)
    settings = get_settings()
    workspace = await target(session, test_user)
    wid = workspace.id
    private = tmp_path / str(wid) / "orphan.bin"
    shared = tmp_path / str(test_workspace.id) / "keep.bin"
    private.parent.mkdir()
    shared.parent.mkdir()
    private.write_bytes(b"synthetic private")
    shared.write_bytes(b"synthetic shared")
    with (
        patch.object(settings, "storage_provider", "local"),
        patch.object(settings, "storage_local_path", str(tmp_path)),
    ):
        job = await approved(session, test_user, test_superuser, workspace)
        with patch(
            "app.services.workspace_deletion_service.delete_managed_file",
            side_effect=OSError("synthetic storage outage"),
        ):
            await service.execute_deletion(session, job, actor_id)
        assert job.state == "external_retry" and job.error_code == "object_cleanup_requires_retry"
        assert private.exists() and shared.exists()
        assert await session.get(Workspace, wid, populate_existing=True) is None
        await service.execute_deletion(session, job, actor_id)
        assert not private.exists() and shared.read_bytes() == b"synthetic shared"
        assert job.error_code == "post_primary_reconciliation_required"


@pytest.mark.asyncio
async def test_workspace_hold_cannot_be_bypassed_by_personal_deletion(
    session, test_user, test_superuser, test_workspace
):
    from app.services import account_deletion_service as personal

    session.add(
        WorkspaceDeletionHold(
            workspace_id=test_workspace.id,
            reason="legal",
            evidence_sha256="a" * 64,
            verified_by=str(test_superuser.id),
        )
    )
    await session.commit()
    _, blockers, _ = await personal.inventory(session, test_user)
    assert "verified_workspace_hold" in blockers


@pytest.mark.asyncio
async def test_hold_on_historical_author_blocks_workspace_deletion(
    session, test_user, test_superuser
):
    from app.models.account_deletion import AccountDeletionHold

    workspace = await target(session, test_user)
    session.add(
        Account(
            user_id=test_superuser.id,
            workspace_id=workspace.id,
            name="Historical author",
            type="checking",
            currency="INR",
            balance=1,
        )
    )
    session.add(
        AccountDeletionHold(
            user_id=test_superuser.id,
            reason="legal",
            evidence_sha256="a" * 64,
            verified_by=str(test_user.id),
        )
    )
    await session.commit()
    _, blockers, _ = await service.inventory(session, test_user, workspace.id)
    assert "verified_legal_hold" in blockers


@pytest.mark.asyncio
async def test_inactive_owner_does_not_replace_last_active_owner_but_can_be_resolved(
    session, test_user, test_superuser
):
    from app.services import workspace_service

    workspace = await target(session, test_user)
    test_superuser.is_active = False
    session.add(WorkspaceMember(workspace_id=workspace.id, user_id=test_superuser.id, role="owner"))
    await session.commit()
    with pytest.raises(HTTPException):
        await workspace_service.remove_member(session, workspace.id, test_user.id)
    await workspace_service.remove_member(session, workspace.id, test_superuser.id)
    await session.commit()
    members = list(
        (
            await session.scalars(
                select(WorkspaceMember).where(WorkspaceMember.workspace_id == workspace.id)
            )
        ).all()
    )
    assert len(members) == 1 and members[0].user_id == test_user.id and members[0].role == "owner"
