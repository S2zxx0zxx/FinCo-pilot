"""Personal-account deletion behavior contract for FinCo-Pilot.

Roadmap #10 defines the product/security behavior that a later deletion
implementation must follow. It is intentionally side-effect free: roadmap #29
owns the durable workflow, provider calls, database/object deletion, retries and
end-to-end acceptance.

The contract exists now so no future endpoint can accidentally reuse the legacy
admin delete routine and destroy shared-workspace data or report deletion as
complete while provider/object/backup work is still outstanding.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable


POLICY_ID = "FINCO_PERSONAL_ACCOUNT_DELETION_V1"
POLICY_VERSION = "2026-10-02"


class AccountDeletionState(str, Enum):
    REQUESTED = "requested"
    BLOCKED = "blocked"
    READY = "ready"
    EXECUTING = "executing"
    EXTERNAL_RETRY = "external_retry"
    PRIMARY_DATA_DELETED = "primary_data_deleted"
    BACKUP_EXPIRY_PENDING = "backup_expiry_pending"
    COMPLETE = "complete"
    CANCELLED = "cancelled"


ALLOWED_STATE_TRANSITIONS: dict[
    AccountDeletionState, tuple[AccountDeletionState, ...]
] = {
    AccountDeletionState.REQUESTED: (
        AccountDeletionState.BLOCKED,
        AccountDeletionState.READY,
        AccountDeletionState.CANCELLED,
    ),
    AccountDeletionState.BLOCKED: (
        AccountDeletionState.READY,
        AccountDeletionState.CANCELLED,
    ),
    AccountDeletionState.READY: (
        AccountDeletionState.EXECUTING,
        AccountDeletionState.CANCELLED,
    ),
    AccountDeletionState.EXECUTING: (
        AccountDeletionState.EXTERNAL_RETRY,
        AccountDeletionState.PRIMARY_DATA_DELETED,
    ),
    AccountDeletionState.EXTERNAL_RETRY: (AccountDeletionState.EXECUTING,),
    AccountDeletionState.PRIMARY_DATA_DELETED: (
        AccountDeletionState.BACKUP_EXPIRY_PENDING,
    ),
    AccountDeletionState.BACKUP_EXPIRY_PENDING: (AccountDeletionState.COMPLETE,),
    AccountDeletionState.COMPLETE: (),
    AccountDeletionState.CANCELLED: (),
}


def can_transition_account_deletion(
    current: AccountDeletionState, target: AccountDeletionState
) -> bool:
    """Return whether the canonical lifecycle permits this state change."""

    return target in ALLOWED_STATE_TRANSITIONS[current]


class AccountDeletionBlocker(str, Enum):
    LAST_ACTIVE_SUPERUSER = "last_active_superuser"
    SOLE_OWNER_SHARED_WORKSPACE = "sole_owner_shared_workspace"
    SHARED_WORKSPACE_BILLING_OWNER = "shared_workspace_billing_owner"
    VERIFIED_LEGAL_HOLD = "verified_legal_hold"


class WorkspaceExitMode(str, Enum):
    DELETE_WITH_ACCOUNT = "delete_with_account"
    PRESERVE_SHARED_DATA = "preserve_shared_data"


class WorkspaceExitAction(str, Enum):
    DELETE_WORKSPACE_WITH_ACCOUNT = "delete_workspace_with_account"
    REMOVE_MEMBERSHIP = "remove_membership"
    DETACH_MANAGER_REFERENCE = "detach_manager_reference"
    NULL_CREATOR_REFERENCE = "null_creator_reference"
    CANCEL_PERSONAL_BILLING = "cancel_personal_billing"


class AccountDeletionAction(str, Enum):
    INVALIDATE_AUTH_SESSIONS = "invalidate_auth_sessions"
    REVOKE_PERSONAL_PROVIDER_ACCESS = "revoke_personal_provider_access"
    CANCEL_PERSONAL_SUBSCRIPTION = "cancel_personal_subscription"
    RESOLVE_VERIFIED_HOLDS = "resolve_verified_holds"
    DELETE_PRIMARY_DATABASE_ROWS = "delete_primary_database_rows"
    DELETE_OBJECT_AND_KNOWLEDGE_BYTES = "delete_object_and_knowledge_bytes"
    DELETE_OR_ANONYMIZE_PROCESSOR_COPIES = "delete_or_anonymize_processor_copies"
    WRITE_MINIMAL_DELETION_TOMBSTONE = "write_minimal_deletion_tombstone"
    WAIT_FOR_BACKUP_EXPIRY = "wait_for_backup_expiry"


DELETION_EXECUTION_ORDER: tuple[AccountDeletionAction, ...] = (
    AccountDeletionAction.INVALIDATE_AUTH_SESSIONS,
    AccountDeletionAction.REVOKE_PERSONAL_PROVIDER_ACCESS,
    AccountDeletionAction.CANCEL_PERSONAL_SUBSCRIPTION,
    AccountDeletionAction.RESOLVE_VERIFIED_HOLDS,
    AccountDeletionAction.DELETE_PRIMARY_DATABASE_ROWS,
    AccountDeletionAction.DELETE_OBJECT_AND_KNOWLEDGE_BYTES,
    AccountDeletionAction.DELETE_OR_ANONYMIZE_PROCESSOR_COPIES,
    AccountDeletionAction.WRITE_MINIMAL_DELETION_TOMBSTONE,
    AccountDeletionAction.WAIT_FOR_BACKUP_EXPIRY,
)


@dataclass(frozen=True)
class WorkspaceDeletionFacts:
    """Facts needed to classify one workspace relationship.

    has_external_manager means another user has manager access. A personal
    workspace with another member or external manager is not private enough to
    be destroyed implicitly as a side effect of deleting one account.
    """

    workspace_id: str
    kind: str
    role: str | None
    member_count: int
    owner_count: int
    is_billing_owner: bool = False
    is_manager: bool = False
    is_creator: bool = False
    has_external_manager: bool = False


@dataclass(frozen=True)
class WorkspaceExitPlan:
    workspace_id: str
    mode: WorkspaceExitMode
    blockers: tuple[AccountDeletionBlocker, ...]
    actions: tuple[WorkspaceExitAction, ...]


@dataclass(frozen=True)
class PersonalAccountDeletionPlan:
    ready: bool
    blockers: tuple[AccountDeletionBlocker, ...]
    workspaces: tuple[WorkspaceExitPlan, ...]
    execution_order: tuple[AccountDeletionAction, ...] = DELETION_EXECUTION_ORDER


def _validate_workspace_facts(facts: WorkspaceDeletionFacts) -> None:
    if facts.kind not in {"personal", "business"}:
        raise ValueError(f"Unsupported workspace kind: {facts.kind}")
    if facts.role not in {None, "owner", "editor", "viewer"}:
        raise ValueError(f"Unsupported workspace role: {facts.role}")
    if facts.member_count < 0 or facts.owner_count < 0:
        raise ValueError("Workspace counts cannot be negative")
    if facts.owner_count > facts.member_count:
        raise ValueError("Workspace owner count cannot exceed member count")
    if facts.role == "owner" and facts.owner_count < 1:
        raise ValueError("Owner relationship requires at least one owner")


def classify_workspace_exit(facts: WorkspaceDeletionFacts) -> WorkspaceExitPlan:
    """Classify one workspace without mutating it.

    Only a genuinely private personal workspace may be deleted implicitly with
    the account: the user must be its sole member/owner and no other user may
    have manager access. Every other workspace is preserved.
    """

    _validate_workspace_facts(facts)

    private_personal = (
        facts.kind == "personal"
        and facts.role == "owner"
        and facts.member_count == 1
        and facts.owner_count == 1
        and not facts.has_external_manager
    )

    if private_personal:
        actions = [WorkspaceExitAction.DELETE_WORKSPACE_WITH_ACCOUNT]
        if facts.is_billing_owner:
            actions.append(WorkspaceExitAction.CANCEL_PERSONAL_BILLING)
        return WorkspaceExitPlan(
            workspace_id=facts.workspace_id,
            mode=WorkspaceExitMode.DELETE_WITH_ACCOUNT,
            blockers=(),
            actions=tuple(actions),
        )

    blockers: list[AccountDeletionBlocker] = []
    actions: list[WorkspaceExitAction] = []

    if facts.role == "owner" and facts.owner_count <= 1:
        blockers.append(AccountDeletionBlocker.SOLE_OWNER_SHARED_WORKSPACE)
    if facts.is_billing_owner:
        blockers.append(AccountDeletionBlocker.SHARED_WORKSPACE_BILLING_OWNER)
    if facts.role is not None:
        actions.append(WorkspaceExitAction.REMOVE_MEMBERSHIP)
    if facts.is_manager:
        actions.append(WorkspaceExitAction.DETACH_MANAGER_REFERENCE)
    if facts.is_creator:
        actions.append(WorkspaceExitAction.NULL_CREATOR_REFERENCE)

    return WorkspaceExitPlan(
        workspace_id=facts.workspace_id,
        mode=WorkspaceExitMode.PRESERVE_SHARED_DATA,
        blockers=tuple(blockers),
        actions=tuple(actions),
    )


def build_personal_account_deletion_plan(
    workspaces: Iterable[WorkspaceDeletionFacts],
    *,
    is_last_active_superuser: bool = False,
    verified_legal_hold: bool = False,
) -> PersonalAccountDeletionPlan:
    """Build the fail-closed preflight plan for one account.

    A request may be recorded while blocked, but destructive execution must not
    begin until every blocker is resolved.
    """

    workspace_plans = tuple(classify_workspace_exit(item) for item in workspaces)
    blockers: list[AccountDeletionBlocker] = []

    if is_last_active_superuser:
        blockers.append(AccountDeletionBlocker.LAST_ACTIVE_SUPERUSER)
    if verified_legal_hold:
        blockers.append(AccountDeletionBlocker.VERIFIED_LEGAL_HOLD)

    for plan in workspace_plans:
        blockers.extend(plan.blockers)

    unique_blockers = tuple(dict.fromkeys(blockers))
    return PersonalAccountDeletionPlan(
        ready=not unique_blockers,
        blockers=unique_blockers,
        workspaces=workspace_plans,
    )
