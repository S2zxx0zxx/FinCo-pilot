"""Original #30: sole-owner authorization, reviewed scope and durable workspace purge."""

import secrets
import uuid
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import Base
from app.core.workspace_deletion import (
    WorkspaceDeletionState as State,
    SharedWorkspaceDeletionFacts,
    build_shared_workspace_deletion_plan,
    can_transition_workspace_deletion,
)
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember
from app.models.workspace_deletion import (
    WorkspaceDeletion,
    WorkspaceDeletionHold,
    WorkspaceDeletionEvent,
    utcnow,
)
from app.models.account_deletion import AccountDeletion, AccountDeletionHold
from app.services import account_deletion_service as common
from app.services.account_deletion_service import (
    digest,
    fingerprint,
    lock_inventory,
    post_primary_requirement,
    storage_namespace,
)
from app.core.config import get_settings
from app.core.deletion_files import delete_managed_file
from app.providers import get_storage_provider
from pathlib import Path


def transition(job, state):
    if not can_transition_workspace_deletion(State(job.state), state):
        raise HTTPException(409, "Invalid workspace deletion transition")
    job.state = state.value


def audit(session, job, action, actor=None, **details):
    session.add(
        WorkspaceDeletionEvent(
            deletion_id=job.id, event_type=action, actor_id=actor, details=details
        )
    )


def public_status(job):
    return {
        "id": str(job.id),
        "workspace_id": str(job.workspace_id),
        "requester_id": str(job.requester_id),
        "state": job.state,
        "blockers": job.blockers,
        "error_code": job.error_code,
        "requested_at": job.requested_at,
        "primary_deleted_at": job.primary_deleted_at,
        "completed_at": job.completed_at,
        "pending_external_count": sum(
            k not in job.receipts for k in job.manifest.get("requirements", [])
        ),
        "pending_object_count": sum(
            not item.get("done") for item in job.manifest.get("objects", [])
        ),
        "retained_data": [
            "user_account_and_global_subscription",
            "minimal_security_and_payment_evidence",
            "backups_until_verified_expiry",
        ],
    }


async def locked_job(session, identity):
    job = await session.scalar(
        select(WorkspaceDeletion)
        .where(WorkspaceDeletion.id == identity)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if not job:
        raise HTTPException(404, "Workspace deletion request not found")
    return job


async def actual_owner(session, identity, actor_id):
    workspace = await session.get(Workspace, identity, populate_existing=True)
    member = await session.scalar(
        select(WorkspaceMember)
        .where(WorkspaceMember.workspace_id == identity, WorkspaceMember.user_id == actor_id)
        .execution_options(populate_existing=True)
    )
    if not workspace or not member:
        raise HTTPException(404, "Workspace not found")
    if member.role != "owner":
        raise HTTPException(403, "An actual owner membership is required")
    return workspace


async def inventory(session, user, identity):
    workspace = await actual_owner(session, identity, user.id)
    members = list(
        (
            await session.scalars(
                select(WorkspaceMember).where(WorkspaceMember.workspace_id == identity)
            )
        ).all()
    )
    accessible = await session.scalar(
        select(Workspace.id)
        .where(
            Workspace.id != identity,
            Workspace.is_archived.is_(False),
            or_(
                Workspace.managed_by_user_id == user.id,
                Workspace.id.in_(
                    select(WorkspaceMember.workspace_id).where(WorkspaceMember.user_id == user.id)
                ),
            ),
        )
        .limit(1)
    )
    holds = list(
        (
            await session.execute(
                select(WorkspaceDeletionHold.__table__).where(
                    WorkspaceDeletionHold.workspace_id == identity
                )
            )
        ).mappings()
    )
    actor_holds = list(
        (
            await session.execute(
                select(AccountDeletionHold.__table__).where(
                    AccountDeletionHold.user_id.in_({m.user_id for m in members} | {user.id})
                )
            )
        ).mappings()
    )
    facts = SharedWorkspaceDeletionFacts(
        str(identity),
        workspace.kind,
        "owner",
        len(members),
        sum(m.role == "owner" for m in members),
        workspace.is_archived,
        workspace.billing_owner_user_id is not None,
        workspace.billing_owner_user_id == user.id,
        workspace.managed_by_user_id is not None,
        workspace.managed_by_user_id == user.id,
        accessible is None,
        any(h["released_at"] is None for h in [*holds, *actor_holds]),
    )
    plan = build_shared_workspace_deletion_plan(facts)
    manifest, blockers, conditions = await common.inventory(
        session, user, workspace_scope=[identity]
    )
    # Historical row authors can hold scoped records even after leaving membership.
    actor_ids = {user.id}
    for name, predicate in conditions.items():
        table = Base.metadata.tables[name]
        for column in table.columns:
            if any(fk.column.table.name == "users" for fk in column.foreign_keys):
                actor_ids.update(
                    value
                    for value in (
                        await session.scalars(select(column).where(predicate).distinct())
                    ).all()
                    if value is not None
                )
    actor_holds = list(
        (
            await session.execute(
                select(AccountDeletionHold.__table__).where(
                    AccountDeletionHold.user_id.in_(actor_ids)
                )
            )
        ).mappings()
    )
    if any(h["released_at"] is None for h in actor_holds):
        blockers.append("verified_legal_hold")
    manifest["preserved_workspaces"] = []
    manifest["workspace_governance"] = fingerprint(
        [
            dict(
                (await session.execute(select(Workspace.__table__).where(Workspace.id == identity)))
                .mappings()
                .one()
            ),
            facts,
        ]
    )
    manifest["hold_hash"] = fingerprint([holds, actor_holds])
    pending = await session.scalar(
        select(AccountDeletion.id)
        .where(
            AccountDeletion.active_user_id == user.id,
            AccountDeletion.state.not_in(["cancelled", "complete"]),
        )
        .limit(1)
    )
    if pending:
        blockers.append("account_deletion_pending")
    if not user.is_active:
        blockers.append("requester_inactive")
    return manifest, sorted(set([*blockers, *(b.value for b in plan.blockers)])), conditions


async def request_deletion(session, user, identity):
    # Lock the same workspace used by membership/governance mutations.
    await session.scalar(select(Workspace).where(Workspace.id == identity).with_for_update())
    await actual_owner(session, identity, user.id)
    if await session.scalar(
        select(WorkspaceDeletion.id).where(WorkspaceDeletion.active_workspace_id == identity)
    ):
        raise HTTPException(409, "An active request already exists; use its saved receipt")
    manifest, blockers, _ = await inventory(session, user, identity)
    token = secrets.token_urlsafe(32)
    job = WorkspaceDeletion(
        workspace_id=identity,
        requester_id=user.id,
        active_workspace_id=identity,
        tracking_digest=digest(token),
        state=State.REQUESTED.value,
        manifest=manifest,
        blockers=blockers,
        review={},
        receipts={},
    )
    session.add(job)
    await session.flush()
    transition(job, State.BLOCKED if blockers else State.READY)
    audit(
        session,
        job,
        "requested",
        str(user.id),
        blockers=blockers,
        manifest_sha256=fingerprint(manifest),
    )
    await session.commit()
    return {**public_status(job), "tracking_token": token}


async def review_deletion(session, job, actor, evidence):
    if job.lease_token or job.state not in {"ready", "blocked"}:
        raise HTTPException(409, "Review is only possible before execution")
    await lock_inventory(session)
    user = await session.get(User, job.requester_id, populate_existing=True)
    if not user:
        raise HTTPException(409, "Requester no longer exists")
    manifest, blockers, _ = await inventory(session, user, job.workspace_id)
    job.manifest, job.blockers, job.receipts = manifest, blockers, {}
    job.review = {
        "fingerprint": fingerprint(manifest),
        "evidence_sha256": evidence,
        "actor_id": str(actor.id),
        "at": utcnow().isoformat(),
    }
    if not blockers and job.state == "blocked":
        transition(job, State.READY)
    audit(
        session,
        job,
        "reviewed",
        str(actor.id),
        manifest_sha256=fingerprint(manifest),
        evidence_sha256=evidence,
        blockers=blockers,
    )
    await session.commit()


async def record_receipt(session, job, actor, requirement, evidence):
    post = post_primary_requirement(requirement)
    allowed = (job.state == "ready" and not post) or (
        job.state == "external_retry"
        and post
        and job.error_code == "post_primary_reconciliation_required"
        and job.manifest.get("primary_database_purged") is True
    )
    if (
        job.lease_token
        or not allowed
        or not job.review
        or requirement not in job.manifest.get("requirements", [])
    ):
        raise HTTPException(409, "Reviewed request and exact required receipt are necessary")
    job.receipts = {
        **job.receipts,
        requirement: {
            "evidence_sha256": evidence,
            "actor_id": str(actor.id),
            "fingerprint": job.review["fingerprint"],
            "at": utcnow().isoformat(),
        },
    }
    audit(
        session,
        job,
        "external_receipt",
        str(actor.id),
        requirement=requirement,
        evidence_sha256=evidence,
    )
    await session.commit()


async def purge_primary(session, job, actor_id):
    await lock_inventory(session)
    operator = await session.get(User, uuid.UUID(actor_id), populate_existing=True)
    if (
        not operator
        or not operator.is_active
        or not operator.is_superuser
        or operator.id == job.requester_id
    ):
        raise HTTPException(403, "A different current active operator is required")
    user = await session.get(User, job.requester_id, populate_existing=True)
    if not user:
        raise HTTPException(409, "Requester no longer exists")
    manifest, blockers, conditions = await inventory(session, user, job.workspace_id)
    if blockers:
        raise HTTPException(409, {"blockers": blockers})
    current = fingerprint(manifest)
    if (
        not job.review
        or job.review.get("fingerprint") != current
        or (utcnow() - datetime.fromisoformat(job.review["at"])).total_seconds() > 86400
    ):
        raise HTTPException(409, "Inventory changed or review expired; review again")
    if any(
        job.receipts.get(k, {}).get("fingerprint") != current
        for k in manifest["requirements"]
        if not post_primary_requirement(k)
    ):
        raise HTTPException(409, "Actual retention/provider cleanup evidence is still required")
    transition(job, State.EXECUTING)
    # Preserve bounded minimal security evidence before removing live MCP grants.
    approvals = Base.metadata.tables["mcp_approvals"]
    rows = list(
        (
            await session.execute(
                select(approvals).where(approvals.c.workspace_id == job.workspace_id)
            )
        ).mappings()
    )
    audit(
        session,
        job,
        "security_evidence_minimised",
        actor_id,
        count=len(rows),
        records_sha256=fingerprint(rows),
    )
    job.manifest = {**manifest, "primary_database_purged": True}
    # Durable manifest and purge commit together; failures leave retry metadata.
    await session.flush()
    for table in reversed(Base.metadata.sorted_tables):
        if table.name in conditions:
            await session.execute(delete(table).where(conditions[table.name]))
    audit(session, job, "primary_purged", actor_id, manifest_sha256=current)
    await session.commit()


async def cleanup_objects(session: AsyncSession, job: WorkspaceDeletion, lease: str):
    identity = job.id
    for index, item in enumerate(job.manifest.get("objects", [])):
        if item.get("done"):
            continue
        await lock_inventory(session)
        if item.get("namespace") != storage_namespace(item["kind"]):
            raise HTTPException(409, "Storage namespace changed; reconciliation required")
        if job.lease_token != lease:
            raise HTTPException(409, "Execution lease changed")
        if item["kind"] == "attachment":
            # An accidentally reused key must never delete a surviving workspace's bytes.
            for name in ("transaction_attachments", "invoice_attachments"):
                table = Base.metadata.tables[name]
                if await session.scalar(
                    select(table.c.id).where(table.c.storage_key == item["key"]).limit(1)
                ):
                    raise HTTPException(409, "Object is referenced by surviving data")
            provider = get_storage_provider()
            if provider.name != item["provider"]:
                raise HTTPException(409, "Storage provider changed; reconciliation required")
            if item["provider"] == "local":
                # The production local adapter uses descriptor-based deletion.
                # Other adapters keep their public async deletion interface.
                from app.providers.local_storage import LocalStorageProvider

                if isinstance(provider, LocalStorageProvider):
                    delete_managed_file(Path(get_settings().storage_local_path), item["key"])
                else:
                    await provider.delete(item["key"])
            else:
                await provider.delete(item["key"])
        else:
            from app.agents.config import get_agent_settings

            base = Path(get_agent_settings().knowledge_storage_path).absolute()
            candidate = Path(item["key"]).absolute()
            try:
                candidate.relative_to(base)
                candidate.resolve().relative_to(base.resolve())
            except ValueError:
                raise HTTPException(409, "Knowledge path is outside managed storage") from None
            if candidate == base or candidate.is_symlink():
                raise HTTPException(409, "Unsafe knowledge path")
            table = Base.metadata.tables["agent_knowledge_docs"]
            if await session.scalar(
                select(table.c.id).where(table.c.storage_path == item["key"]).limit(1)
            ):
                raise HTTPException(409, "Knowledge bytes are still referenced")
            delete_managed_file(base, str(candidate.relative_to(base)))
        manifest = {**job.manifest, "objects": [dict(obj) for obj in job.manifest["objects"]]}
        manifest["objects"][index]["done"] = True
        job.manifest = manifest
        audit(session, job, "object_deleted", object_sha256=digest(str(item["key"])))
        job.lease_until = utcnow() + timedelta(minutes=10)
        await session.commit()
        job = await locked_job(session, identity)


async def execute_deletion(session: AsyncSession, job: WorkspaceDeletion, actor_id: str):
    identity = job.id
    if job.state not in {State.READY.value, State.EXECUTING.value, State.EXTERNAL_RETRY.value}:
        raise HTTPException(409, "Deletion is not ready to execute or resume")
    deadline = job.lease_until
    if deadline and deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)
    if deadline and deadline > utcnow():
        raise HTTPException(409, "Another deletion executor owns the request")
    lease = secrets.token_hex(32)
    job.lease_token, job.lease_until = lease, utcnow() + timedelta(minutes=10)
    await session.commit()
    job = await locked_job(session, identity)
    if job.state == State.READY.value:
        try:
            await purge_primary(session, job, actor_id)
        except Exception:
            await session.rollback()
            job = await locked_job(session, identity)
            if job.lease_token == lease:
                job.lease_token, job.lease_until = None, None
                await session.commit()
            raise
        job = await locked_job(session, identity)
    elif job.state == State.EXTERNAL_RETRY.value:
        transition(job, State.EXECUTING)
        await session.commit()
        job = await locked_job(session, identity)
    elif job.state != State.EXECUTING.value:
        raise HTTPException(409, "Deletion is not ready to execute or resume")
    try:
        await cleanup_objects(session, job, lease)
    except Exception:
        await session.rollback()
        job = await locked_job(session, identity)
        if job.lease_token != lease:
            raise HTTPException(409, "Execution lease changed")
        transition(job, State.EXTERNAL_RETRY)
        job.lease_token, job.lease_until = None, None
        job.error_code = "object_cleanup_requires_retry"
        audit(session, job, "external_retry", actor_id, code=job.error_code)
        await session.commit()
        return
    if job.lease_token != lease:
        raise HTTPException(409, "Execution lease changed")
    job.lease_token, job.lease_until = None, None
    if any(
        job.receipts.get(key, {}).get("fingerprint") != job.review.get("fingerprint")
        for key in job.manifest.get("requirements", [])
        if post_primary_requirement(key)
    ):
        transition(job, State.EXTERNAL_RETRY)
        job.error_code = "post_primary_reconciliation_required"
        audit(session, job, "post_primary_evidence_pending", actor_id)
        await session.commit()
        return
    job.error_code = None
    job.primary_deleted_at = utcnow()
    transition(job, State.PRIMARY_WORKSPACE_DELETED)
    transition(job, State.BACKUP_EXPIRY_PENDING)
    # Discard paths and full inventory hashes once the primary cleanup is proven.
    job.manifest = {
        "requirements": [],
        "objects": [],
        "purged_manifest_sha256": fingerprint(job.manifest),
    }
    job.review = {}
    audit(session, job, "backup_expiry_pending", actor_id)
    await session.commit()


async def complete_backups(
    session: AsyncSession,
    job: WorkspaceDeletion,
    actor: User,
    evidence: str,
    verified_after: datetime,
):
    primary = job.primary_deleted_at
    if primary and primary.tzinfo is None:
        primary = primary.replace(tzinfo=timezone.utc)
    if job.state != State.BACKUP_EXPIRY_PENDING.value or not primary:
        raise HTTPException(409, "Primary cleanup must finish first")
    # Cutoff is the earliest recoverable data timestamp, NOT a scheduled expiry
    # date. A review must cover snapshots, versions, replicas and restore copies.
    if verified_after.tzinfo is None or not primary < verified_after <= utcnow():
        raise HTTPException(409, "Verified recoverable-data cutoff must follow primary deletion")
    job.receipts = {
        **job.receipts,
        "backup_expiry": {
            "evidence_sha256": evidence,
            "actor_id": str(actor.id),
            "verified_after": verified_after.isoformat(),
            "at": utcnow().isoformat(),
        },
    }
    audit(
        session,
        job,
        "backup_expiry_verified",
        str(actor.id),
        evidence_sha256=evidence,
        verified_after=verified_after.isoformat(),
    )
    transition(job, State.COMPLETE)
    job.completed_at = utcnow()
    await session.commit()
