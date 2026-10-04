"""Shared workspace deletion: user consent + fresh authentication, separately audited operators."""

import secrets
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import current_active_user, current_superuser
from app.core.database import get_async_session
from app.core.rate_limit import login_rate_limit
from app.models.workspace_deletion import WorkspaceDeletion, WorkspaceDeletionHold, utcnow
from app.models.user import User
from app.services import workspace_deletion_service as service
from app.core.workspace_deletion import WorkspaceDeletionState as State

from app.api.account_deletion import DeletionRoute, require_fresh


router = APIRouter(
    route_class=DeletionRoute,
    prefix="/api/workspace-deletion",
    tags=["workspace-deletion"],
    dependencies=[Depends(login_rate_limit)],
)


class Consent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    workspace_id: uuid.UUID
    confirmation: str = Field(pattern="^DELETE THIS WORKSPACE$")


class Evidence(BaseModel):
    model_config = ConfigDict(extra="forbid")
    evidence_sha256: str = Field(pattern="^[0-9a-f]{64}$")


class Receipt(Evidence):
    requirement: str = Field(min_length=1, max_length=150)


class BackupEvidence(Evidence):
    verified_after: datetime


class Hold(Evidence):
    workspace_id: uuid.UUID
    reason: str = Field(pattern="^(legal|tax|dispute|fraud|retention)$")


@router.get("/workspaces")
async def deletion_workspaces(
    user: User = Depends(current_active_user), session: AsyncSession = Depends(get_async_session)
):
    from app.models.workspace import Workspace, WorkspaceMember

    rows = await session.execute(
        select(Workspace, WorkspaceMember.role)
        .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
        .where(WorkspaceMember.user_id == user.id)
        .order_by(Workspace.created_at)
    )
    return [
        {
            "id": str(w.id),
            "name": w.name,
            "role": role,
            "is_archived": w.is_archived,
            "manager_id": str(w.managed_by_user_id) if w.managed_by_user_id else None,
            "billing_owner_id": str(w.billing_owner_user_id) if w.billing_owner_user_id else None,
        }
        for w, role in rows
    ]


@router.get("/preview/{workspace_id}")
async def preview(
    workspace_id: uuid.UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    manifest, blockers, _ = await service.inventory(session, user, workspace_id)
    return {
        "blockers": blockers,
        "private_workspace_count": len(manifest["private_workspaces"]),
        "preserved_workspace_count": 0,
        "required_operator_steps": len(manifest["requirements"]),
        "reauthentication_seconds": 300,
    }


@router.post("", status_code=202, dependencies=[Depends(require_fresh)])
async def request(
    body: Consent,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    return await service.request_deletion(session, user, body.workspace_id)


@router.get("/mine")
async def mine(
    workspace_id: uuid.UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    job = await session.scalar(
        select(WorkspaceDeletion).where(
            WorkspaceDeletion.workspace_id == workspace_id,
            WorkspaceDeletion.requester_id == user.id,
            WorkspaceDeletion.active_workspace_id.is_not(None),
        )
    )
    return service.public_status(job) if job else None


@router.get("/{identity}/status")
async def status(
    identity: uuid.UUID,
    tracking_token: str = Header(default="", alias="X-Deletion-Receipt"),
    session: AsyncSession = Depends(get_async_session),
):
    job = await session.get(WorkspaceDeletion, identity)
    if (
        not job
        or not 32 <= len(tracking_token) <= 128
        or not secrets.compare_digest(job.tracking_digest, service.digest(tracking_token))
    ):
        raise HTTPException(404, "Deletion receipt not found")
    return service.public_status(job)


@router.post("/{identity}/cancel", dependencies=[Depends(require_fresh)])
async def cancel(
    identity: uuid.UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    job = await service.locked_job(session, identity)
    if job.requester_id != user.id:
        raise HTTPException(404, "Deletion request not found")
    if job.lease_token or job.state not in {
        State.READY.value,
        State.REQUESTED.value,
        State.BLOCKED.value,
    }:
        raise HTTPException(409, "Execution has started; cancellation is no longer possible")
    service.audit(session, job, "cancelled", str(user.id))
    service.transition(job, State.CANCELLED)
    job.active_workspace_id = None
    job.manifest, job.review, job.receipts = {}, {}, {}
    await session.commit()
    return service.public_status(job)


@router.get("/operator/requests")
async def operator_requests(
    user: User = Depends(current_superuser), session: AsyncSession = Depends(get_async_session)
):
    jobs = await session.scalars(
        select(WorkspaceDeletion).order_by(WorkspaceDeletion.requested_at.desc()).limit(100)
    )
    return [service.public_status(job) for job in jobs]


@router.get("/operator/{identity}", dependencies=[Depends(require_fresh)])
async def operator_request(
    identity: uuid.UUID,
    user: User = Depends(current_superuser),
    session: AsyncSession = Depends(get_async_session),
):
    job = await service.locked_job(session, identity)
    return {
        **service.public_status(job),
        "requirements": job.manifest.get("requirements", []),
        "review_fingerprint": job.review.get("fingerprint"),
        "receipts": job.receipts,
        "user_id": str(job.requester_id),
        "private_workspaces": job.manifest.get("private_workspaces", []),
        "objects": job.manifest.get("objects", []),
    }


@router.post("/operator/holds", status_code=201, dependencies=[Depends(require_fresh)])
async def add_hold(
    body: Hold,
    user: User = Depends(current_superuser),
    session: AsyncSession = Depends(get_async_session),
):
    await service.lock_inventory(session)
    from app.models.workspace import Workspace

    target = await session.get(Workspace, body.workspace_id)
    if not target or await session.scalar(
        select(WorkspaceDeletion.id).where(
            WorkspaceDeletion.workspace_id == body.workspace_id,
            WorkspaceDeletion.state.not_in(["ready", "blocked", "requested", "cancelled"]),
        )
    ):
        raise HTTPException(409, "Hold cannot be added after destructive execution starts")
    hold = WorkspaceDeletionHold(
        workspace_id=body.workspace_id,
        reason=body.reason,
        evidence_sha256=body.evidence_sha256,
        verified_by=str(user.id),
    )
    session.add(hold)
    await session.commit()
    return {"id": str(hold.id)}


@router.post("/operator/holds/{identity}/release", dependencies=[Depends(require_fresh)])
async def release_hold(
    identity: uuid.UUID,
    body: Evidence,
    user: User = Depends(current_superuser),
    session: AsyncSession = Depends(get_async_session),
):
    hold = await session.scalar(
        select(WorkspaceDeletionHold).where(WorkspaceDeletionHold.id == identity).with_for_update()
    )
    if not hold:
        raise HTTPException(404, "Hold not found")
    if hold.released_at:
        raise HTTPException(409, "Hold already released")
    hold.released_at, hold.release_evidence_sha256, hold.released_by = (
        utcnow(),
        body.evidence_sha256,
        str(user.id),
    )
    await session.commit()
    return {"released": True}


@router.post("/operator/{identity}/review", dependencies=[Depends(require_fresh)])
async def review(
    identity: uuid.UUID,
    body: Evidence,
    user: User = Depends(current_superuser),
    session: AsyncSession = Depends(get_async_session),
):
    job = await service.locked_job(session, identity)
    await service.review_deletion(session, job, user, body.evidence_sha256)
    return service.public_status(job)


@router.post("/operator/{identity}/receipt", dependencies=[Depends(require_fresh)])
async def receipt(
    identity: uuid.UUID,
    body: Receipt,
    user: User = Depends(current_superuser),
    session: AsyncSession = Depends(get_async_session),
):
    job = await service.locked_job(session, identity)
    await service.record_receipt(session, job, user, body.requirement, body.evidence_sha256)
    return service.public_status(job)


@router.post("/operator/{identity}/execute", dependencies=[Depends(require_fresh)])
async def execute(
    identity: uuid.UUID,
    user: User = Depends(current_superuser),
    session: AsyncSession = Depends(get_async_session),
):
    job = await service.locked_job(session, identity)
    # A requester cannot self-attest to external/hold/backup checks.
    if job.requester_id == user.id:
        raise HTTPException(409, "A different active operator must execute deletion")
    await service.execute_deletion(session, job, str(user.id))
    return service.public_status(job)


@router.post("/operator/{identity}/backup-proof", dependencies=[Depends(require_fresh)])
async def backup_proof(
    identity: uuid.UUID,
    body: BackupEvidence,
    user: User = Depends(current_superuser),
    session: AsyncSession = Depends(get_async_session),
):
    job = await service.locked_job(session, identity)
    await service.complete_backups(session, job, user, body.evidence_sha256, body.verified_after)
    return service.public_status(job)


class WorkspaceConfirmation(Evidence):
    confirmation: uuid.UUID


async def governance_job(session, identity, confirmation):
    job = await service.locked_job(session, identity)
    if job.workspace_id != confirmation or job.lease_token or job.state not in {"ready", "blocked"}:
        raise HTTPException(
            409, "Exact workspace confirmation and an unstarted request are required"
        )
    await service.lock_inventory(session)
    return job


@router.post("/{identity}/detach-manager", dependencies=[Depends(require_fresh)])
async def detach_manager(
    identity: uuid.UUID,
    body: WorkspaceConfirmation,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    job = await governance_job(session, identity, body.confirmation)
    workspace = await service.actual_owner(session, job.workspace_id, user.id)
    if job.requester_id != user.id:
        raise HTTPException(404, "Request not found")
    workspace.managed_by_user_id = None
    service.audit(
        session, job, "manager_detached", str(user.id), evidence_sha256=body.evidence_sha256
    )
    await session.commit()
    return service.public_status(job)


@router.post("/{identity}/transfer-billing", dependencies=[Depends(require_fresh)])
async def transfer_billing(
    identity: uuid.UUID,
    body: WorkspaceConfirmation,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    job = await governance_job(session, identity, body.confirmation)
    workspace = await service.actual_owner(session, job.workspace_id, user.id)
    await service.actual_owner(session, job.workspace_id, job.requester_id)
    target = await session.get(User, job.requester_id, populate_existing=True)
    if workspace.billing_owner_user_id != user.id or not target or not target.is_active:
        raise HTTPException(
            403,
            "Only the current actual payer-owner can transfer billing to the active requesting owner",
        )
    workspace.billing_owner_user_id = job.requester_id
    service.audit(
        session, job, "billing_transferred", str(user.id), evidence_sha256=body.evidence_sha256
    )
    await session.commit()
    return service.public_status(job)


@router.post("/operator/{identity}/repair-billing", dependencies=[Depends(require_fresh)])
async def repair_billing(
    identity: uuid.UUID,
    body: WorkspaceConfirmation,
    user: User = Depends(current_superuser),
    session: AsyncSession = Depends(get_async_session),
):
    job = await governance_job(session, identity, body.confirmation)
    workspace = await service.actual_owner(session, job.workspace_id, job.requester_id)
    target = await session.get(User, job.requester_id, populate_existing=True)
    if (
        workspace.billing_owner_user_id is not None
        or not target
        or not target.is_active
        or user.id == job.requester_id
    ):
        raise HTTPException(
            409, "Independent evidence-based repair only applies to unresolved billing ownership"
        )
    workspace.billing_owner_user_id = job.requester_id
    service.audit(
        session, job, "billing_repaired", str(user.id), evidence_sha256=body.evidence_sha256
    )
    await session.commit()
    return service.public_status(job)
