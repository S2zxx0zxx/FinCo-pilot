"""Shared-workspace deletion policy contract for FinCo-Pilot.

Roadmap #11 defines irreversible workspace-deletion policy. It is deliberately
side-effect free: roadmap #30 owns the durable workflow, provider/object
cleanup, database hard deletion, retries and end-to-end acceptance.

The current product only archives workspaces. This contract therefore cannot
be used to reinterpret the existing archive endpoint as destructive deletion.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


POLICY_ID = "FINCO_SHARED_WORKSPACE_DELETION_V1"
POLICY_VERSION = "2026-10-02"

REQUIRE_ARCHIVE_BEFORE_HARD_DELETE = True
CANCEL_USER_SUBSCRIPTION_ON_WORKSPACE_DELETE = False


class WorkspaceDeletionState(str, Enum):
    REQUESTED = "requested"
    BLOCKED = "blocked"
    READY = "ready"
    EXECUTING = "executing"
    EXTERNAL_RETRY = "external_retry"
    PRIMARY_WORKSPACE_DELETED = "primary_workspace_deleted"
    BACKUP_EXPIRY_PENDING = "backup_expiry_pending"
    COMPLETE = "complete"
    CANCELLED = "cancelled"


ALLOWED_STATE_TRANSITIONS: dict[
    WorkspaceDeletionState, tuple[WorkspaceDeletionState, ...]
] = {
    WorkspaceDeletionState.REQUESTED: (
        WorkspaceDeletionState.BLOCKED,
        WorkspaceDeletionState.READY,
        WorkspaceDeletionState.CANCELLED,
    ),
    WorkspaceDeletionState.BLOCKED: (
        WorkspaceDeletionState.READY,
        WorkspaceDeletionState.CANCELLED,
    ),
    WorkspaceDeletionState.READY: (
        WorkspaceDeletionState.EXECUTING,
        WorkspaceDeletionState.CANCELLED,
    ),
    WorkspaceDeletionState.EXECUTING: (
        WorkspaceDeletionState.EXTERNAL_RETRY,
        WorkspaceDeletionState.PRIMARY_WORKSPACE_DELETED,
    ),
    WorkspaceDeletionState.EXTERNAL_RETRY: (WorkspaceDeletionState.EXECUTING,),
    WorkspaceDeletionState.PRIMARY_WORKSPACE_DELETED: (
        WorkspaceDeletionState.BACKUP_EXPIRY_PENDING,
    ),
    WorkspaceDeletionState.BACKUP_EXPIRY_PENDING: (
        WorkspaceDeletionState.COMPLETE,
    ),
    WorkspaceDeletionState.COMPLETE: (),
    WorkspaceDeletionState.CANCELLED: (),
}


def can_transition_workspace_deletion(
    current: WorkspaceDeletionState, target: WorkspaceDeletionState
) -> bool:
    return target in ALLOWED_STATE_TRANSITIONS[current]


class WorkspaceDeletionBlocker(str, Enum):
    REQUESTER_NOT_OWNER_MEMBER = "requester_not_owner_member"
    WORKSPACE_NOT_ARCHIVED = "workspace_not_archived"
    OTHER_OWNERS_PRESENT = "other_owners_present"
    OTHER_MEMBERS_PRESENT = "other_members_present"
    OTHER_EXTERNAL_MANAGER_PRESENT = "other_external_manager_present"
    BILLING_OWNER_UNRESOLVED = "billing_owner_unresolved"
    BILLING_OWNER_MISMATCH = "billing_owner_mismatch"
    REQUESTER_LAST_ACCESSIBLE_WORKSPACE = "requester_last_accessible_workspace"
    VERIFIED_LEGAL_HOLD = "verified_legal_hold"


class WorkspaceDeletionAction(str, Enum):
    FREEZE_WORKSPACE_WRITES = "freeze_workspace_writes"
    CAPTURE_DELETION_MANIFEST = "capture_deletion_manifest"
    CANCEL_PENDING_INVITATIONS = "cancel_pending_invitations"
    REVOKE_WORKSPACE_PROVIDER_ACCESS = "revoke_workspace_provider_access"
    DETACH_EXTERNAL_MANAGER = "detach_external_manager"
    DELETE_WORKSPACE_OBJECT_AND_KNOWLEDGE_BYTES = (
        "delete_workspace_object_and_knowledge_bytes"
    )
    DELETE_PRIMARY_WORKSPACE_ROWS = "delete_primary_workspace_rows"
    DELETE_OR_ANONYMIZE_PROCESSOR_COPIES = (
        "delete_or_anonymize_processor_copies"
    )
    WRITE_MINIMAL_DELETION_TOMBSTONE = "write_minimal_deletion_tombstone"
    WAIT_FOR_BACKUP_EXPIRY = "wait_for_backup_expiry"


BASE_DELETION_EXECUTION_ORDER: tuple[WorkspaceDeletionAction, ...] = (
    WorkspaceDeletionAction.FREEZE_WORKSPACE_WRITES,
    WorkspaceDeletionAction.CAPTURE_DELETION_MANIFEST,
    WorkspaceDeletionAction.CANCEL_PENDING_INVITATIONS,
    WorkspaceDeletionAction.REVOKE_WORKSPACE_PROVIDER_ACCESS,
    WorkspaceDeletionAction.DELETE_WORKSPACE_OBJECT_AND_KNOWLEDGE_BYTES,
    WorkspaceDeletionAction.DELETE_PRIMARY_WORKSPACE_ROWS,
    WorkspaceDeletionAction.DELETE_OR_ANONYMIZE_PROCESSOR_COPIES,
    WorkspaceDeletionAction.WRITE_MINIMAL_DELETION_TOMBSTONE,
    WorkspaceDeletionAction.WAIT_FOR_BACKUP_EXPIRY,
)


@dataclass(frozen=True)
class SharedWorkspaceDeletionFacts:
    workspace_id: str
    kind: str
    requester_role: str | None
    member_count: int
    owner_count: int
    is_archived: bool
    billing_owner_present: bool
    requester_is_billing_owner: bool
    has_external_manager: bool = False
    external_manager_is_requester: bool = False
    requester_last_accessible_workspace: bool = False
    verified_legal_hold: bool = False


@dataclass(frozen=True)
class SharedWorkspaceDeletionPlan:
    ready: bool
    blockers: tuple[WorkspaceDeletionBlocker, ...]
    execution_order: tuple[WorkspaceDeletionAction, ...]


def _validate_facts(facts: SharedWorkspaceDeletionFacts) -> None:
    if facts.kind not in {"personal", "business"}:
        raise ValueError(f"Unsupported workspace kind: {facts.kind}")
    if facts.requester_role not in {None, "owner", "editor", "viewer", "manager"}:
        raise ValueError(f"Unsupported requester role: {facts.requester_role}")
    if facts.member_count < 0 or facts.owner_count < 0:
        raise ValueError("Workspace counts cannot be negative")
    if facts.owner_count > facts.member_count:
        raise ValueError("Workspace owner count cannot exceed member count")
    if facts.requester_role == "owner":
        if facts.member_count < 1 or facts.owner_count < 1:
            raise ValueError("Owner requester requires member and owner rows")
    if facts.external_manager_is_requester and not facts.has_external_manager:
        raise ValueError(
            "Requester cannot be the external manager when no manager is attached"
        )
    if facts.requester_is_billing_owner and not facts.billing_owner_present:
        raise ValueError(
            "Requester cannot own billing when billing owner is unresolved"
        )


def build_shared_workspace_deletion_plan(
    facts: SharedWorkspaceDeletionFacts,
) -> SharedWorkspaceDeletionPlan:
    """Return a fail-closed hard-delete preflight without mutating state.

    V1 deliberately requires the deleting user to be the sole remaining actual
    owner/member and the resolved billing owner. Multi-party deletion approval
    is not guessed here; collaborators must be removed/transferred explicitly
    before destructive execution can become READY.
    """

    _validate_facts(facts)
    blockers: list[WorkspaceDeletionBlocker] = []

    # A virtual external manager has owner-like operating access today, but
    # that is not enough authority for irreversible destruction of shared data.
    if facts.requester_role != "owner":
        blockers.append(WorkspaceDeletionBlocker.REQUESTER_NOT_OWNER_MEMBER)

    if REQUIRE_ARCHIVE_BEFORE_HARD_DELETE and not facts.is_archived:
        blockers.append(WorkspaceDeletionBlocker.WORKSPACE_NOT_ARCHIVED)

    if facts.owner_count > 1:
        blockers.append(WorkspaceDeletionBlocker.OTHER_OWNERS_PRESENT)
    if facts.member_count > 1:
        blockers.append(WorkspaceDeletionBlocker.OTHER_MEMBERS_PRESENT)

    if facts.has_external_manager and not facts.external_manager_is_requester:
        blockers.append(
            WorkspaceDeletionBlocker.OTHER_EXTERNAL_MANAGER_PRESENT
        )

    if not facts.billing_owner_present:
        blockers.append(WorkspaceDeletionBlocker.BILLING_OWNER_UNRESOLVED)
    elif not facts.requester_is_billing_owner:
        blockers.append(WorkspaceDeletionBlocker.BILLING_OWNER_MISMATCH)

    if facts.requester_last_accessible_workspace:
        blockers.append(
            WorkspaceDeletionBlocker.REQUESTER_LAST_ACCESSIBLE_WORKSPACE
        )

    if facts.verified_legal_hold:
        blockers.append(WorkspaceDeletionBlocker.VERIFIED_LEGAL_HOLD)

    actions = list(BASE_DELETION_EXECUTION_ORDER)
    if facts.has_external_manager and facts.external_manager_is_requester:
        # Detach the same-user management edge before deleting the workspace.
        insert_at = actions.index(
            WorkspaceDeletionAction.DELETE_WORKSPACE_OBJECT_AND_KNOWLEDGE_BYTES
        )
        actions.insert(insert_at, WorkspaceDeletionAction.DETACH_EXTERNAL_MANAGER)

    return SharedWorkspaceDeletionPlan(
        ready=not blockers,
        blockers=tuple(dict.fromkeys(blockers)),
        execution_order=tuple(actions),
    )
