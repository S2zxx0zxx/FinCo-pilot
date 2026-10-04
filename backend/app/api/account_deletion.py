"""Personal deletion: user consent + fresh authentication, separately audited operators."""
import secrets
import time
import uuid
from datetime import datetime

import jwt
from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.routing import APIRoute
from sqlalchemy.exc import SQLAlchemyError
from pydantic import BaseModel, ConfigDict, Field, SecretStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import bearer_transport, current_active_user, current_superuser, get_jwt_strategy
from app.core.database import get_async_session
from app.core.rate_limit import login_rate_limit
from app.models.account_deletion import AccountDeletion, AccountDeletionHold, utcnow
from app.models.user import User
from app.services import account_deletion_service as service
from app.core.account_deletion import AccountDeletionState as State

class DeletionRoute(APIRoute):
    def get_route_handler(self):
        original = super().get_route_handler()
        async def safe_handler(request):
            try:
                return await original(request)
            except SQLAlchemyError:
                # Never leak SQL binds containing manifests, credentials or paths
                # through exception logging at the global request boundary.
                raise HTTPException(409, "Deletion database operation could not finish; retry or review current state") from None
        return safe_handler


router = APIRouter(route_class=DeletionRoute, prefix="/api/account-deletion", tags=["account-deletion"], dependencies=[Depends(login_rate_limit)])


class Consent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    confirmation: str = Field(pattern="^DELETE MY ACCOUNT$")


class Evidence(BaseModel):
    model_config = ConfigDict(extra="forbid")
    evidence_sha256: str = Field(pattern="^[0-9a-f]{64}$")


class Receipt(Evidence):
    requirement: str = Field(min_length=1, max_length=150)


class BackupEvidence(Evidence):
    verified_after: datetime


class Hold(Evidence):
    user_id: uuid.UUID
    reason: str = Field(pattern="^(legal|tax|dispute|fraud|retention)$")


def require_fresh(token: str = Depends(bearer_transport.scheme)):
    strategy = get_jwt_strategy()
    try:
        payload = jwt.decode(token, strategy.decode_key.get_secret_value() if isinstance(strategy.decode_key, SecretStr) else strategy.decode_key, algorithms=[strategy.algorithm], audience=strategy.token_audience)
        auth_time = payload.get("auth_time")
        if type(auth_time) is not int or not 0 <= time.time() - auth_time <= 300:
            raise ValueError("Fresh full authentication required")
    except (jwt.PyJWTError, ValueError, TypeError):
        raise HTTPException(403, "Sign in again with your full authentication method, then retry within five minutes") from None


@router.get("/preview")
async def preview(user: User = Depends(current_active_user), session: AsyncSession = Depends(get_async_session)):
    manifest, blockers, _ = await service.inventory(session, user)
    return {"blockers": blockers, "private_workspace_count": len(manifest["private_workspaces"]),
        "preserved_workspace_count": len(manifest["preserved_workspaces"]),
        "required_operator_steps": len(manifest["requirements"]), "reauthentication_seconds": 300}


@router.post("", status_code=202, dependencies=[Depends(require_fresh)])
async def request(body: Consent, user: User = Depends(current_active_user), session: AsyncSession = Depends(get_async_session)):
    return await service.request_deletion(session, user)


@router.get("/mine")
async def mine(user: User = Depends(current_active_user), session: AsyncSession = Depends(get_async_session)):
    job = await session.scalar(select(AccountDeletion).where(AccountDeletion.active_user_id == user.id))
    return service.public_status(job) if job else None


@router.get("/{identity}/status")
async def status(identity: uuid.UUID, tracking_token: str = Header(default="", alias="X-Deletion-Receipt"), session: AsyncSession = Depends(get_async_session)):
    job = await session.get(AccountDeletion, identity)
    if not job or not 32 <= len(tracking_token) <= 128 or not secrets.compare_digest(job.tracking_digest, service.digest(tracking_token)):
        raise HTTPException(404, "Deletion receipt not found")
    return service.public_status(job)


@router.post("/{identity}/cancel", dependencies=[Depends(require_fresh)])
async def cancel(identity: uuid.UUID, user: User = Depends(current_active_user), session: AsyncSession = Depends(get_async_session)):
    job = await service.locked_job(session, identity)
    if job.user_id != user.id:
        raise HTTPException(404, "Deletion request not found")
    if job.lease_token or job.state not in {State.READY.value, State.REQUESTED.value, State.BLOCKED.value}:
        raise HTTPException(409, "Execution has started; cancellation is no longer possible")
    service.audit(session, job, "cancelled", str(user.id))
    service.transition(job, State.CANCELLED)
    job.active_user_id = None
    job.manifest, job.review, job.receipts = {}, {}, {}
    await session.commit()
    return service.public_status(job)


@router.get("/operator/requests")
async def operator_requests(user: User = Depends(current_superuser), session: AsyncSession = Depends(get_async_session)):
    jobs = await session.scalars(select(AccountDeletion).order_by(AccountDeletion.requested_at.desc()).limit(100))
    return [service.public_status(job) for job in jobs]


@router.get("/operator/{identity}")
async def operator_request(identity: uuid.UUID, user: User = Depends(current_superuser), session: AsyncSession = Depends(get_async_session)):
    job = await service.locked_job(session, identity)
    return {**service.public_status(job), "requirements": job.manifest.get("requirements", []),
        "review_fingerprint": job.review.get("fingerprint"), "receipts": job.receipts,
        "user_id": str(job.user_id)}


@router.post("/operator/holds", status_code=201, dependencies=[Depends(require_fresh)])
async def add_hold(body: Hold, user: User = Depends(current_superuser), session: AsyncSession = Depends(get_async_session)):
    await service.lock_inventory(session)
    target = await session.get(User, body.user_id)
    if not target or await session.scalar(select(AccountDeletion.id).where(AccountDeletion.user_id == body.user_id, AccountDeletion.state.not_in(["ready", "blocked", "requested", "cancelled"]))):
        raise HTTPException(409, "Hold cannot be added after destructive execution starts")
    hold = AccountDeletionHold(user_id=body.user_id, reason=body.reason, evidence_sha256=body.evidence_sha256, verified_by=str(user.id))
    session.add(hold)
    await session.commit()
    return {"id": str(hold.id)}


@router.post("/operator/holds/{identity}/release", dependencies=[Depends(require_fresh)])
async def release_hold(identity: uuid.UUID, body: Evidence, user: User = Depends(current_superuser), session: AsyncSession = Depends(get_async_session)):
    hold = await session.scalar(select(AccountDeletionHold).where(AccountDeletionHold.id == identity).with_for_update())
    if not hold:
        raise HTTPException(404, "Hold not found")
    if hold.released_at:
        raise HTTPException(409, "Hold already released")
    hold.released_at, hold.release_evidence_sha256, hold.released_by = utcnow(), body.evidence_sha256, str(user.id)
    await session.commit()
    return {"released": True}


@router.post("/operator/{identity}/review", dependencies=[Depends(require_fresh)])
async def review(identity: uuid.UUID, body: Evidence, user: User = Depends(current_superuser), session: AsyncSession = Depends(get_async_session)):
    job = await service.locked_job(session, identity)
    await service.review_deletion(session, job, user, body.evidence_sha256)
    return service.public_status(job)


@router.post("/operator/{identity}/receipt", dependencies=[Depends(require_fresh)])
async def receipt(identity: uuid.UUID, body: Receipt, user: User = Depends(current_superuser), session: AsyncSession = Depends(get_async_session)):
    job = await service.locked_job(session, identity)
    await service.record_receipt(session, job, user, body.requirement, body.evidence_sha256)
    return service.public_status(job)


@router.post("/operator/{identity}/execute", dependencies=[Depends(require_fresh)])
async def execute(identity: uuid.UUID, user: User = Depends(current_superuser), session: AsyncSession = Depends(get_async_session)):
    job = await service.locked_job(session, identity)
    # A requester cannot self-attest to external/hold/backup checks.
    if job.user_id == user.id:
        raise HTTPException(409, "A different active operator must execute deletion")
    await service.execute_deletion(session, job, str(user.id))
    return service.public_status(job)


@router.post("/operator/{identity}/backup-proof", dependencies=[Depends(require_fresh)])
async def backup_proof(identity: uuid.UUID, body: BackupEvidence, user: User = Depends(current_superuser), session: AsyncSession = Depends(get_async_session)):
    job = await service.locked_job(session, identity)
    await service.complete_backups(session, job, user, body.evidence_sha256, body.verified_after)
    return service.public_status(job)
