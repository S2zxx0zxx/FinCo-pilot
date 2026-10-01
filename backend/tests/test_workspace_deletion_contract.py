import pytest

from app.core.workspace_deletion import (
    BASE_DELETION_EXECUTION_ORDER,
    CANCEL_USER_SUBSCRIPTION_ON_WORKSPACE_DELETE,
    REQUIRE_ARCHIVE_BEFORE_HARD_DELETE,
    SharedWorkspaceDeletionFacts,
    WorkspaceDeletionAction,
    WorkspaceDeletionBlocker,
    WorkspaceDeletionState,
    build_shared_workspace_deletion_plan,
    can_transition_workspace_deletion,
)


def ready_facts(**overrides):
    values = {
        "workspace_id": "ws-1",
        "kind": "business",
        "requester_role": "owner",
        "member_count": 1,
        "owner_count": 1,
        "is_archived": True,
        "billing_owner_present": True,
        "requester_is_billing_owner": True,
    }
    values.update(overrides)
    return SharedWorkspaceDeletionFacts(**values)


def test_clean_archived_sole_owner_workspace_can_become_ready():
    plan = build_shared_workspace_deletion_plan(ready_facts())
    assert plan.ready is True
    assert plan.blockers == ()
    assert plan.execution_order == BASE_DELETION_EXECUTION_ORDER


def test_manager_only_access_is_not_destructive_owner_authority():
    plan = build_shared_workspace_deletion_plan(
        ready_facts(
            requester_role="manager",
            member_count=2,
            owner_count=1,
            has_external_manager=True,
            external_manager_is_requester=True,
        )
    )
    assert plan.ready is False
    assert WorkspaceDeletionBlocker.REQUESTER_NOT_OWNER_MEMBER in plan.blockers
    assert WorkspaceDeletionBlocker.OTHER_MEMBERS_PRESENT in plan.blockers


def test_workspace_must_be_archived_before_hard_delete():
    assert REQUIRE_ARCHIVE_BEFORE_HARD_DELETE is True
    plan = build_shared_workspace_deletion_plan(
        ready_facts(is_archived=False)
    )
    assert plan.ready is False
    assert plan.blockers == (
        WorkspaceDeletionBlocker.WORKSPACE_NOT_ARCHIVED,
    )


def test_other_owners_and_members_block_irreversible_deletion():
    plan = build_shared_workspace_deletion_plan(
        ready_facts(member_count=4, owner_count=2)
    )
    assert plan.ready is False
    assert plan.blockers == (
        WorkspaceDeletionBlocker.OTHER_OWNERS_PRESENT,
        WorkspaceDeletionBlocker.OTHER_MEMBERS_PRESENT,
    )


def test_other_external_manager_must_be_detached_first():
    plan = build_shared_workspace_deletion_plan(
        ready_facts(
            has_external_manager=True,
            external_manager_is_requester=False,
        )
    )
    assert plan.ready is False
    assert plan.blockers == (
        WorkspaceDeletionBlocker.OTHER_EXTERNAL_MANAGER_PRESENT,
    )


def test_same_requester_manager_edge_is_detached_during_execution():
    plan = build_shared_workspace_deletion_plan(
        ready_facts(
            has_external_manager=True,
            external_manager_is_requester=True,
        )
    )
    assert plan.ready is True
    assert WorkspaceDeletionAction.DETACH_EXTERNAL_MANAGER in plan.execution_order
    assert plan.execution_order.index(
        WorkspaceDeletionAction.DETACH_EXTERNAL_MANAGER
    ) < plan.execution_order.index(
        WorkspaceDeletionAction.DELETE_PRIMARY_WORKSPACE_ROWS
    )


def test_billing_owner_must_be_resolved_and_match_requester():
    unresolved = build_shared_workspace_deletion_plan(
        ready_facts(
            billing_owner_present=False,
            requester_is_billing_owner=False,
        )
    )
    mismatch = build_shared_workspace_deletion_plan(
        ready_facts(
            billing_owner_present=True,
            requester_is_billing_owner=False,
        )
    )
    assert unresolved.blockers == (
        WorkspaceDeletionBlocker.BILLING_OWNER_UNRESOLVED,
    )
    assert mismatch.blockers == (
        WorkspaceDeletionBlocker.BILLING_OWNER_MISMATCH,
    )


def test_workspace_delete_never_cancels_global_user_subscription():
    assert CANCEL_USER_SUBSCRIPTION_ON_WORKSPACE_DELETE is False


def test_last_accessible_workspace_and_verified_hold_fail_closed():
    plan = build_shared_workspace_deletion_plan(
        ready_facts(
            requester_last_accessible_workspace=True,
            verified_legal_hold=True,
        )
    )
    assert plan.ready is False
    assert plan.blockers == (
        WorkspaceDeletionBlocker.REQUESTER_LAST_ACCESSIBLE_WORKSPACE,
        WorkspaceDeletionBlocker.VERIFIED_LEGAL_HOLD,
    )


def test_manifest_and_provider_revocation_precede_destructive_rows():
    order = BASE_DELETION_EXECUTION_ORDER
    assert order[0] is WorkspaceDeletionAction.FREEZE_WORKSPACE_WRITES
    assert order.index(
        WorkspaceDeletionAction.CAPTURE_DELETION_MANIFEST
    ) < order.index(
        WorkspaceDeletionAction.DELETE_PRIMARY_WORKSPACE_ROWS
    )
    assert order.index(
        WorkspaceDeletionAction.REVOKE_WORKSPACE_PROVIDER_ACCESS
    ) < order.index(
        WorkspaceDeletionAction.DELETE_PRIMARY_WORKSPACE_ROWS
    )
    assert order.index(
        WorkspaceDeletionAction.DELETE_WORKSPACE_OBJECT_AND_KNOWLEDGE_BYTES
    ) < order.index(
        WorkspaceDeletionAction.DELETE_PRIMARY_WORKSPACE_ROWS
    )
    assert order[-1] is WorkspaceDeletionAction.WAIT_FOR_BACKUP_EXPIRY


def test_deletion_can_cancel_only_before_execution():
    assert can_transition_workspace_deletion(
        WorkspaceDeletionState.REQUESTED, WorkspaceDeletionState.CANCELLED
    )
    assert can_transition_workspace_deletion(
        WorkspaceDeletionState.BLOCKED, WorkspaceDeletionState.CANCELLED
    )
    assert can_transition_workspace_deletion(
        WorkspaceDeletionState.READY, WorkspaceDeletionState.CANCELLED
    )
    assert not can_transition_workspace_deletion(
        WorkspaceDeletionState.EXECUTING, WorkspaceDeletionState.CANCELLED
    )


def test_primary_delete_cannot_jump_directly_to_complete():
    assert not can_transition_workspace_deletion(
        WorkspaceDeletionState.PRIMARY_WORKSPACE_DELETED,
        WorkspaceDeletionState.COMPLETE,
    )
    assert can_transition_workspace_deletion(
        WorkspaceDeletionState.PRIMARY_WORKSPACE_DELETED,
        WorkspaceDeletionState.BACKUP_EXPIRY_PENDING,
    )
    assert can_transition_workspace_deletion(
        WorkspaceDeletionState.BACKUP_EXPIRY_PENDING,
        WorkspaceDeletionState.COMPLETE,
    )


@pytest.mark.parametrize(
    "facts",
    [
        ready_facts(kind="team"),
        ready_facts(requester_role="admin"),
        ready_facts(member_count=-1, owner_count=0),
        ready_facts(member_count=1, owner_count=2),
        ready_facts(
            has_external_manager=False,
            external_manager_is_requester=True,
        ),
        ready_facts(
            billing_owner_present=False,
            requester_is_billing_owner=True,
        ),
    ],
)
def test_invalid_workspace_deletion_facts_fail_closed(facts):
    with pytest.raises(ValueError):
        build_shared_workspace_deletion_plan(facts)
