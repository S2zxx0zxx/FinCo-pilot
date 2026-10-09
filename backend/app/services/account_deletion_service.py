"""Evidence-gated, resumable personal deletion. Never reuse ORM user cascades."""
import hashlib
import json
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import delete, func, inspect, or_, select, text, true, update
from sqlalchemy.ext.asyncio import AsyncSession

import app.agents.models  # noqa: F401 -- include AI tables even when routes disabled
from app.core.account_deletion import (
    AccountDeletionState as State, WorkspaceDeletionFacts, WorkspaceExitMode,
    build_personal_account_deletion_plan, can_transition_account_deletion,
)
from app.core.config import get_settings
from app.core.deletion_files import delete_managed_file
from app.core.database import Base
from app.models.account_deletion import AccountDeletion, AccountDeletionHold, AccountDeletionEvent, utcnow
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember
from app.providers import get_storage_provider

PERSONAL_TABLES = {"external_auth_identities", "user_passkeys", "external_mcp_tokens", "mcp_approvals", "agent_llm_usage", "billing_usage_counters", "agent_llm_connections", "subscriptions"}
PAYMENT_TABLES = {"payment_refunds", "refund_observations", "payment_cancellations", "payment_recoveries", "renewal_mandates", "renewal_cycles", "payment_activations", "payment_webhook_events", "checkout_reservations", "founding_members", "pricing_audit_events", "pricing_campaigns"}
RECEIPT_TABLES = {"account_deletions", "account_deletion_holds", "account_deletion_events", "workspace_deletions", "workspace_deletion_holds", "workspace_deletion_events"}


def storage_namespace(kind: str) -> str:
    settings = get_settings()
    if kind == "knowledge":
        from app.agents.config import get_agent_settings
        return fingerprint(["knowledge_local", str(Path(get_agent_settings().knowledge_storage_path).absolute())])
    if settings.storage_provider == "local":
        return fingerprint(["local", str(Path(settings.storage_local_path).absolute())])
    return fingerprint([settings.storage_provider, settings.storage_s3_endpoint_url, settings.storage_s3_bucket,
        settings.storage_s3_prefix, settings.storage_s3_region])


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def fingerprint(value) -> str:
    return digest(json.dumps(value, sort_keys=True, default=str, separators=(",", ":")))


def transition(job: AccountDeletion, state: State):
    if not can_transition_account_deletion(State(job.state), state):
        raise HTTPException(409, "Invalid deletion transition")
    job.state = state.value


def audit(session: AsyncSession, job: AccountDeletion, action: str, actor: str | None = None, **details):
    session.add(AccountDeletionEvent(deletion_id=job.id, event_type=action, actor_id=actor, details=details))


def post_primary_requirement(key: str) -> bool:
    return key in {"unmapped_legacy_storage_review", "processor_cleanup_after_primary"} or key.startswith(("storage_versions:", "storage_namespace_versions:"))


def public_status(job: AccountDeletion):
    return {"id": str(job.id), "state": job.state, "blockers": job.blockers,
            "error_code": job.error_code, "requested_at": job.requested_at,
            "primary_deleted_at": job.primary_deleted_at, "completed_at": job.completed_at,
            "pending_external_count": sum(k not in job.receipts for k in job.manifest.get("requirements", [])),
            "pending_object_count": sum(not item.get("done") for item in job.manifest.get("objects", [])),
            "retained_data": ["shared_workspace_records", "payment_and_hold_evidence", "inactive_pseudonymous_actor", "backup_copies_until_verified_expiry"]}


async def locked_job(session: AsyncSession, identity: uuid.UUID):
    job = await session.scalar(select(AccountDeletion).where(AccountDeletion.id == identity)
        .with_for_update().execution_options(populate_existing=True))
    if not job:
        raise HTTPException(404, "Deletion request not found")
    return job


async def lock_inventory(session: AsyncSession):
    """Rare destructive operation: quiesce every registered table on PostgreSQL.

    FK row locks alone do not protect uploads, workspace membership or queued
    jobs. This transaction-wide lock waits for existing writers and fences new
    writers while the exact manifest and primary purge commit atomically.
    """
    expected = set("app_settings fx_rates users payment_refunds refund_observations payment_cancellations payment_recoveries renewal_mandates renewal_cycles payment_activations payment_webhook_events agent_llm_connections billing_usage_counters checkout_reservations pricing_audit_events pricing_campaigns subscriptions user_passkeys external_auth_identities workspaces agents bank_connections category_groups collections external_mcp_tokens founding_members groups invoice_settings loans payees reconciliation_rules rules workspace_members workspace_tax_ids agent_conversations agent_knowledge_docs agent_tools categories group_members institutions invoices mcp_approvals payee_mapping payee_tax_ids accounts agent_knowledge_chunks agent_messages asset_groups budgets invoice_attachments invoice_lines agent_llm_usage assets collection_accounts collection_asset_groups credit_card_bills import_logs recurring_transactions asset_transactions asset_values goals transactions group_settlements invoice_allocations reconciliation_events reconciliation_suggestions transaction_attachments transaction_splits account_deletions account_deletion_holds account_deletion_events workspace_deletions workspace_deletion_holds workspace_deletion_events".split())
    if set(Base.metadata.tables) != expected:
        raise HTTPException(409, "New model tables require deletion policy review")
    bind = session.get_bind()
    if bind.dialect.name == "postgresql":
        await session.execute(text("SET LOCAL lock_timeout = '5s'"))
        names = ', '.join('"' + name + '"' for name in sorted(Base.metadata.tables))
        await session.execute(text(f"LOCK TABLE {names} IN EXCLUSIVE MODE"))
    elif get_settings().is_production:
        raise HTTPException(409, "Production deletion requires PostgreSQL")
    connection = await session.connection()
    actual = set(await connection.run_sync(lambda conn: inspect(conn).get_table_names()))
    if actual - set(Base.metadata.tables) - {"alembic_version"}:
        raise HTTPException(409, "Unreviewed database schema blocks deletion")
    for name in sorted(actual & set(Base.metadata.tables)):
        columns = await connection.run_sync(lambda conn, table_name=name: {c["name"] for c in inspect(conn).get_columns(table_name)})
        if columns != set(Base.metadata.tables[name].c.keys()):
            raise HTTPException(409, "Unreviewed database columns block deletion")
    if set(Base.metadata.tables) - actual:
        raise HTTPException(409, "Database migrations are required before deletion")


async def inventory(session: AsyncSession, user: User, *, workspace_scope: list[uuid.UUID] | None = None):
    memberships = list((await session.scalars(select(WorkspaceMember))).all())
    own = {m.workspace_id: m for m in memberships if m.user_id == user.id}
    workspaces = list((await session.scalars(select(Workspace).where(or_(
        Workspace.id.in_(own), Workspace.created_by_user_id == user.id,
        Workspace.managed_by_user_id == user.id, Workspace.billing_owner_user_id == user.id)))).all())
    if workspace_scope is not None:
        workspaces = [w for w in workspaces if w.id in workspace_scope]
    active_users = set((await session.scalars(select(User.id).where(User.is_active.is_(True)))).all())
    facts = [WorkspaceDeletionFacts(str(w.id), w.kind, own[w.id].role if w.id in own else None,
        sum(m.workspace_id == w.id for m in memberships),
        sum(m.workspace_id == w.id and m.role == "owner" and m.user_id in active_users for m in memberships),
        w.billing_owner_user_id == user.id, w.managed_by_user_id == user.id,
        w.created_by_user_id == user.id, w.managed_by_user_id not in (None, user.id)) for w in workspaces]
    admin_count = await session.scalar(select(func.count()).select_from(User).where(User.is_active.is_(True), User.is_superuser.is_(True)))
    held = await session.scalar(select(AccountDeletionHold.id).where(AccountDeletionHold.user_id == user.id, AccountDeletionHold.released_at.is_(None)).limit(1))
    plan = build_personal_account_deletion_plan(facts, is_last_active_superuser=bool(user.is_superuser and admin_count == 1), verified_legal_hold=held is not None)
    private = workspace_scope if workspace_scope is not None else [uuid.UUID(w.workspace_id) for w in plan.workspaces if w.mode == WorkspaceExitMode.DELETE_WITH_ACCOUNT]
    from app.models.workspace_deletion import WorkspaceDeletionHold
    workspace_hold = await session.scalar(select(WorkspaceDeletionHold.id).where(WorkspaceDeletionHold.workspace_id.in_(private), WorkspaceDeletionHold.released_at.is_(None)).limit(1))
    conditions = {"workspaces": Workspace.__table__.c.id.in_(private)}
    tables = list(Base.metadata.sorted_tables)
    blockers = [b.value for b in plan.blockers] if workspace_scope is None else []
    if workspace_hold:
        blockers.append("verified_workspace_hold")
    # A linked external IdP remains capable of authenticating after local purge.
    # Until signed Clerk revocation/deprovisioning is implemented, deliberately
    # block personal deletion rather than leaving an orphaned active identity.
    if workspace_scope is None:
        external_table = Base.metadata.tables.get("external_auth_identities")
        if external_table is not None and await session.scalar(
            select(external_table.c.id).where(external_table.c.user_id == user.id).limit(1)
        ):
            blockers.append("external_identity_revocation_not_configured")
    if workspace_scope is None:
        from app.models.workspace_deletion import WorkspaceDeletion
        pending = await session.scalar(select(WorkspaceDeletion.id).where(WorkspaceDeletion.requester_id == user.id, WorkspaceDeletion.state.not_in(["cancelled", "complete", "backup_expiry_pending"])).limit(1))
        if pending:
            blockers.append("workspace_deletion_pending")
    hashes = {}
    objects = []
    requirements = ["operator_hold_and_retention_review", "processor_inventory_review", "backup_inventory_review", "unmapped_legacy_storage_review", "processor_cleanup_after_primary"]
    for table in tables:
        if table.name in (PERSONAL_TABLES - {"external_mcp_tokens", "mcp_approvals"}) | PAYMENT_TABLES | RECEIPT_TABLES | {"users", "fx_rates", "app_settings"}:
            continue
        parents = []
        for column in table.columns:
            for fk in column.foreign_keys:
                parent = fk.column.table
                if parent.name in conditions:
                    parents.append(column.in_(select(fk.column).where(conditions[parent.name])))
        workspace = table.c.get("workspace_id")
        if workspace is not None:
            predicate = workspace.in_(private)
            if parents and await session.scalar(select(func.count()).select_from(table).where(or_(*parents), or_(workspace.is_(None), ~predicate))):
                blockers.append("cross_workspace_reference")
        elif table.name == "workspaces":
            predicate = conditions["workspaces"]
        elif parents:
            predicate = or_(*parents)
        else:
            continue
        conditions[table.name] = predicate
        rows = list((await session.execute(select(table).where(predicate))).mappings())
        hashes[table.name] = fingerprint([dict(r) for r in sorted(rows, key=lambda r: str(tuple(r.values())))])
        for row in rows:
            key = row.get("storage_key")
            path = row.get("storage_path")
            if key:
                objects.append({"kind": "attachment", "key": key, "provider": get_settings().storage_provider, "namespace": storage_namespace("attachment"), "done": False})
            if path:
                objects.append({"kind": "knowledge", "key": path, "provider": "knowledge_local", "namespace": storage_namespace("knowledge"), "done": False})
        if workspace_scope is None and workspace is not None and "user_id" in table.c:
            if await session.scalar(select(func.count()).select_from(table).where(table.c.user_id == user.id, workspace.is_(None))):
                blockers.append("unscoped_legacy_data")
    from app.services.invoice_logo_service import storage_key as logo_key
    for name in ("invoice_settings", "invoices"):
        table = Base.metadata.tables[name]
        for row in (await session.execute(select(table).where(table.c.workspace_id.in_(private)))).mappings():
            logo = row.get("logo_id") if name == "invoice_settings" else ((row.get("snapshot") or {}).get("issuer") or {}).get("logo_id")
            if logo:
                try:
                    key = logo_key(row["workspace_id"], uuid.UUID(str(logo)))
                except (ValueError, TypeError):
                    blockers.append("invalid_logo_reference")
                    continue
                objects.append({"kind": "attachment", "key": key, "provider": get_settings().storage_provider,
                    "namespace": storage_namespace("attachment"), "done": False})
    # Enumerate only exact UUID workspace namespaces. This also discovers
    # replaced/unreferenced invoice logos and orphaned attachment uploads.
    for workspace_id in private:
        if get_settings().storage_provider == "s3":
            requirements.append("storage_namespace_versions:" + str(workspace_id))
        try:
            discovered = await get_storage_provider().list_keys(str(workspace_id) + "/")
        except Exception:
            blockers.append("storage_inventory_unavailable")
            discovered = []
        for key in discovered:
            objects.append({"kind": "attachment", "key": key, "provider": get_settings().storage_provider,
                "namespace": storage_namespace("attachment"), "done": False})
    for item in objects:
        try:
            key = item["key"]
            if not isinstance(key, str):
                raise ValueError("Invalid object key type")
            if item["kind"] == "attachment":
                if not key or key.startswith("/") or "\\" in key or "\x00" in key or any(part in {"", ".", ".."} for part in key.split("/")):
                    raise ValueError("Invalid exact object key")
            else:
                from app.agents.config import get_agent_settings
                base = Path(get_agent_settings().knowledge_storage_path).absolute()
                path = Path(key).absolute()
                path.relative_to(base)
                path.resolve().relative_to(base.resolve())
                if path == base or path.is_symlink():
                    raise ValueError("Unsafe knowledge path")
        except (ValueError, TypeError, OSError):
            blockers.append("unsafe_storage_reference")
    objects = list({(item["kind"], item["key"]): item for item in objects}.values())
    objects.sort(key=lambda item: (item["kind"], item["key"]))
    # Shared byte references are a pre-purge blocker, not an irreversible
    # dead-end discovered only after private rows have already disappeared.
    for item in objects:
        names = ("transaction_attachments", "invoice_attachments") if item["kind"] == "attachment" else ("agent_knowledge_docs",)
        for name in names:
            table = Base.metadata.tables[name]
            column = table.c.storage_key if item["kind"] == "attachment" else table.c.storage_path
            predicate = conditions.get(name)
            outside = ~predicate if predicate is not None else true()
            if "workspace_id" in table.c:
                outside = or_(table.c.workspace_id.is_(None), outside)
            if await session.scalar(select(table.c.id).where(column == item["key"], outside).limit(1)):
                blockers.append("shared_object_reference")
    transactions = Base.metadata.tables["transactions"]
    private_pairs = select(transactions.c.transfer_pair_id).where(transactions.c.workspace_id.in_(private), transactions.c.transfer_pair_id.is_not(None))
    if await session.scalar(select(func.count()).select_from(transactions).where(transactions.c.transfer_pair_id.in_(private_pairs), ~transactions.c.workspace_id.in_(private))):
        blockers.append("cross_workspace_transfer")
    # Recheck after the full graph is known, including self-referential invoice
    # corrections and edges whose parent sorts later in the graph.
    for table in tables:
        if table.name not in conditions or "workspace_id" not in table.c:
            continue
        outside = or_(table.c.workspace_id.is_(None), ~table.c.workspace_id.in_(private))
        for column in table.columns:
            for fk in column.foreign_keys:
                parent = fk.column.table
                if parent.name in conditions and await session.scalar(select(func.count()).select_from(table).where(
                    outside, column.in_(select(fk.column).where(conditions[parent.name])))):
                    blockers.append("cross_workspace_reference")
    # External access may remain even for a shared connection whose records are preserved.
    banks = Base.metadata.tables["bank_connections"]
    bank_rows = list((await session.execute(select(banks).where((or_(banks.c.user_id == user.id, banks.c.workspace_id.in_(private)) if workspace_scope is None else banks.c.workspace_id.in_(private))))).mappings())
    for row in bank_rows:
        requirements.append("bank_revoke:" + str(row["id"]))
    subscriptions = Base.metadata.tables["subscriptions"]
    subs = list((await session.execute(select(subscriptions).where(subscriptions.c.user_id == user.id))).mappings()) if workspace_scope is None else []
    for row in subs:
        if row["provider_subscription_id"] or row["provider_customer_id"] or row["status"] not in {"free", "cancelled", "canceled", "expired"}:
            requirements.append("billing_cancel:" + str(row["id"]))
    renewals = Base.metadata.tables["renewal_mandates"]
    renewal_rows = list((await session.execute(select(renewals).where(renewals.c.user_id == user.id))).mappings()) if workspace_scope is None else []
    for row in renewal_rows:
        if row["state"] in {"creating", "uncertain"}:
            blockers.append("renewal_outcome_unresolved")
        if row["state"] in {"creating", "uncertain", "ready"}:
            requirements.append("billing_renewal_cancel:" + str(row["id"]))
    cancellations = Base.metadata.tables["payment_cancellations"]
    cancellation_rows = list((await session.execute(select(cancellations).where(cancellations.c.user_id == user.id))).mappings()) if workspace_scope is None else []
    if any(row["state"] != "confirmed" for row in cancellation_rows):
        blockers.append("cancellation_outcome_unresolved")
    refunds = Base.metadata.tables["payment_refunds"]
    refund_rows = list((await session.execute(select(refunds).where(refunds.c.user_id == user.id))).mappings()) if workspace_scope is None else []
    observations = Base.metadata.tables["refund_observations"]
    refund_observations = list((await session.execute(select(observations).where(observations.c.user_id == user.id))).mappings()) if workspace_scope is None else []
    if any(row["state"] not in {"processed", "failed", "external"} for row in refund_rows) or any(row["state"] == "pending" for row in refund_observations):
        blockers.append("refund_outcome_unresolved")
    llm = Base.metadata.tables["agent_llm_connections"]
    llm_rows = list((await session.execute(select(llm).where(llm.c.user_id == user.id))).mappings()) if workspace_scope is None else []
    for row in llm_rows:
        requirements.append("llm_revoke_and_processor_cleanup:" + str(row["id"]))
    for item in objects:
        if item["provider"] == "s3":
            requirements.append("storage_versions:" + digest(str(item["key"])))
    manifest = {"private_workspaces": [str(w) for w in private],
        "preserved_workspaces": [w.workspace_id for w in plan.workspaces if w.mode == WorkspaceExitMode.PRESERVE_SHARED_DATA],
        "objects": objects, "requirements": sorted(set(requirements)), "table_hashes": hashes,
        "provider_hash": fingerprint([bank_rows, subs, renewal_rows, cancellation_rows, refund_rows, refund_observations, llm_rows]),
        "identity_stamp": fingerprint([user.id, user.hashed_password, user.auth_epoch]),
        "workspace_hash": fingerprint([facts, [(m.workspace_id, m.user_id, m.role) for m in memberships if m.workspace_id in {w.id for w in workspaces}]]),
        "hold_hash": fingerprint(list((await session.execute(select(AccountDeletionHold.__table__).where(AccountDeletionHold.user_id == user.id))).mappings()))}
    return manifest, sorted(set(blockers)), conditions


async def request_deletion(session: AsyncSession, user: User):
    user = (await session.scalars(select(User).where(User.id == user.id).with_for_update().execution_options(populate_existing=True))).one()
    existing = await session.scalar(select(AccountDeletion).where(AccountDeletion.active_user_id == user.id))
    if existing:
        raise HTTPException(409, "An active deletion request already exists; use its saved receipt")
    manifest, blockers, _ = await inventory(session, user)
    token = secrets.token_urlsafe(32)
    job = AccountDeletion(user_id=user.id, active_user_id=user.id, tracking_digest=digest(token),
        state=State.REQUESTED.value, manifest=manifest, blockers=blockers, review={}, receipts={})
    session.add(job)
    await session.flush()
    transition(job, State.BLOCKED if blockers else State.READY)
    audit(session, job, "requested", str(user.id), blockers=blockers, manifest_sha256=fingerprint(manifest))
    await session.commit()
    return {**public_status(job), "tracking_token": token}


async def review_deletion(session: AsyncSession, job: AccountDeletion, actor: User, evidence: str):
    if job.lease_token or job.state not in {State.READY.value, State.BLOCKED.value}:
        raise HTTPException(409, "Review is only possible before execution")
    await lock_inventory(session)
    user = (await session.scalars(select(User).where(User.id == job.user_id).execution_options(populate_existing=True))).one()
    manifest, blockers, _ = await inventory(session, user)
    job.manifest, job.blockers = manifest, blockers
    # Every review is fresh and invalidates earlier external attestations.
    job.review = {"fingerprint": fingerprint(manifest), "evidence_sha256": evidence,
                  "actor_id": str(actor.id), "at": utcnow().isoformat()}
    job.receipts = {}
    audit(session, job, "reviewed", str(actor.id), manifest_sha256=fingerprint(manifest), evidence_sha256=evidence, blockers=blockers)
    if blockers:
        if job.state == State.READY.value:
            # READY cannot transition to BLOCKED in the #10 contract. Keep the
            # state and expose blockers; execution always rechecks them.
            pass
    elif job.state == State.BLOCKED.value:
        transition(job, State.READY)
    await session.commit()


async def record_receipt(session: AsyncSession, job: AccountDeletion, actor: User, requirement: str, evidence: str):
    post = post_primary_requirement(requirement)
    allowed = (job.state == State.READY.value and not post) or (
        job.state == State.EXTERNAL_RETRY.value and post and job.error_code == "post_primary_reconciliation_required"
        and job.manifest.get("primary_database_purged") is True)
    if job.lease_token or not allowed or not job.review or requirement not in job.manifest.get("requirements", []):
        raise HTTPException(409, "Reviewed request and exact required receipt are necessary")
    audit(session, job, "external_receipt", str(actor.id), requirement=requirement, evidence_sha256=evidence, manifest_sha256=job.review["fingerprint"])
    job.receipts = {**job.receipts, requirement: {"evidence_sha256": evidence,
        "actor_id": str(actor.id), "fingerprint": job.review["fingerprint"], "at": utcnow().isoformat()}}
    await session.commit()


async def purge_primary(session: AsyncSession, job: AccountDeletion, actor_id: str | None):
    await lock_inventory(session)
    if actor_id is not None:
        operator = await session.scalar(select(User).where(User.id == uuid.UUID(actor_id)).execution_options(populate_existing=True))
        if not operator or not operator.is_active or not operator.is_superuser or operator.id == job.user_id:
            raise HTTPException(403, "A different current active operator is required")
    user = (await session.scalars(select(User).where(User.id == job.user_id).execution_options(populate_existing=True))).one()
    manifest, blockers, conditions = await inventory(session, user)
    if blockers:
        raise HTTPException(409, {"blockers": blockers})
    current = fingerprint(manifest)
    if not job.review or job.review.get("fingerprint") != current:
        raise HTTPException(409, "Inventory changed; a new operator review is required")
    review_at = datetime.fromisoformat(job.review["at"])
    if (utcnow() - review_at).total_seconds() > 86400:
        raise HTTPException(409, "Operator review expired")
    if any(job.receipts.get(key, {}).get("fingerprint") != current for key in manifest["requirements"] if not post_primary_requirement(key)):
        raise HTTPException(409, "External cleanup and retention receipts are still required")
    transition(job, State.EXECUTING)
    # Rotation and deactivation commit in the SAME transaction as the purge.
    user.is_active, user.is_superuser, user.is_verified = False, False, False
    user.auth_epoch = str(uuid.uuid4())
    user.hashed_password = "!deleted:" + secrets.token_hex(32)
    user.email = f"deleted-{user.id.hex}@invalid.example"
    user.preferences, user.recovery_code_hashes = {}, []
    user.totp_secret, user.is_2fa_enabled = None, False
    user.oidc_issuer, user.oidc_subject = None, None
    await session.flush()
    # Detach shared agents from personal keys without falling back silently to
    # environment credentials. Their content survives, but they need reconfiguration.
    llm = Base.metadata.tables["agent_llm_connections"]
    agents = Base.metadata.tables["agents"]
    await session.execute(update(agents).where(agents.c.connection_id.in_(select(llm.c.id).where(llm.c.user_id == user.id))).values(connection_id=None, is_archived=True))
    banks = Base.metadata.tables["bank_connections"]
    await session.execute(update(banks).where(banks.c.user_id == user.id).values(credentials=None, settings={}, status="revoked", last_sync_error=None))
    for table in reversed(Base.metadata.sorted_tables):
        if table.name in conditions and table.name != "workspaces":
            await session.execute(delete(table).where(conditions[table.name]))
    for table in reversed(Base.metadata.sorted_tables):
        if table.name in PERSONAL_TABLES:
            await session.execute(delete(table).where(table.c.user_id == user.id))
    await session.execute(delete(WorkspaceMember).where(WorkspaceMember.user_id == user.id))
    for column in (Workspace.created_by_user_id, Workspace.managed_by_user_id, Workspace.billing_owner_user_id):
        await session.execute(update(Workspace).where(column == user.id).values({column.key: None}))
    await session.execute(update(WorkspaceMember).where(WorkspaceMember.invited_by_user_id == user.id).values(invited_by_user_id=None))
    await session.execute(delete(Workspace).where(conditions["workspaces"]))
    job.manifest = {**manifest, "primary_database_purged": True}
    audit(session, job, "primary_purged", actor_id, manifest_sha256=current)
    await session.commit()


async def cleanup_objects(session: AsyncSession, job: AccountDeletion, lease: str):
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
                if await session.scalar(select(table.c.id).where(table.c.storage_key == item["key"]).limit(1)):
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
            if await session.scalar(select(table.c.id).where(table.c.storage_path == item["key"]).limit(1)):
                raise HTTPException(409, "Knowledge bytes are still referenced")
            delete_managed_file(base, str(candidate.relative_to(base)))
        manifest = {**job.manifest, "objects": [dict(obj) for obj in job.manifest["objects"]]}
        manifest["objects"][index]["done"] = True
        job.manifest = manifest
        audit(session, job, "object_deleted", object_sha256=digest(str(item["key"])))
        job.lease_until = utcnow() + timedelta(minutes=10)
        await session.commit()
        job = await locked_job(session, identity)


async def execute_deletion(session: AsyncSession, job: AccountDeletion, actor_id: str | None = None):
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
    if any(job.receipts.get(key, {}).get("fingerprint") != job.review.get("fingerprint")
           for key in job.manifest.get("requirements", []) if post_primary_requirement(key)):
        transition(job, State.EXTERNAL_RETRY)
        job.error_code = "post_primary_reconciliation_required"
        audit(session, job, "post_primary_evidence_pending", actor_id)
        await session.commit()
        return
    job.error_code = None
    job.primary_deleted_at = utcnow()
    transition(job, State.PRIMARY_DATA_DELETED)
    transition(job, State.BACKUP_EXPIRY_PENDING)
    # Discard paths and full inventory hashes once the primary cleanup is proven.
    job.manifest = {"requirements": [], "objects": [], "purged_manifest_sha256": fingerprint(job.manifest)}
    job.review = {}
    audit(session, job, "backup_expiry_pending", actor_id)
    await session.commit()


async def complete_backups(session: AsyncSession, job: AccountDeletion, actor: User,
                           evidence: str, verified_after: datetime):
    primary = job.primary_deleted_at
    if primary and primary.tzinfo is None:
        primary = primary.replace(tzinfo=timezone.utc)
    if job.state != State.BACKUP_EXPIRY_PENDING.value or not primary:
        raise HTTPException(409, "Primary cleanup must finish first")
    # Cutoff is the earliest recoverable data timestamp, NOT a scheduled expiry
    # date. A review must cover snapshots, versions, replicas and restore copies.
    if verified_after.tzinfo is None or not primary < verified_after <= utcnow():
        raise HTTPException(409, "Verified recoverable-data cutoff must follow primary deletion")
    job.receipts = {**job.receipts, "backup_expiry": {"evidence_sha256": evidence,
        "actor_id": str(actor.id), "verified_after": verified_after.isoformat(), "at": utcnow().isoformat()}}
    audit(session, job, "backup_expiry_verified", str(actor.id), evidence_sha256=evidence, verified_after=verified_after.isoformat())
    transition(job, State.COMPLETE)
    job.completed_at = utcnow()
    await session.commit()
