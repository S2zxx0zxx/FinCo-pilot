import pytest

from app.core.account_deletion import (
    DELETION_EXECUTION_ORDER,
    AccountDeletionAction,
    AccountDeletionBlocker,
    WorkspaceDeletionFacts,
    WorkspaceExitAction,
    WorkspaceExitMode,
    build_personal_account_deletion_plan,
    classify_workspace_exit,
)


def test_private_personal_workspace_is_deleted_with_account():
    plan = classify_workspace_exit(
        WorkspaceDeletionFacts(
            workspace_id="personal-1",
            kind="personal",
            role="owner",
            member_count=1,
            owner_count=1,
            is_billing_owner=True,
            is_creator=True,
        )
    )

    assert plan.mode is WorkspaceExitMode.DELETE_WITH_ACCOUNT
    assert plan.blockers == ()
    assert plan.actions == (
        WorkspaceExitAction.DELETE_WORKSPACE_WITH_ACCOUNT,
        WorkspaceExitAction.CANCEL_PERSONAL_BILLING,
    )


def test_personal_workspace_with_another_member_is_preserved():
    plan = classify_workspace_exit(
        WorkspaceDeletionFacts(
            workspace_id="shared-personal",
            kind="personal",
            role="owner",
            member_count=2,
            owner_count=2,
            is_creator=True,
        )
    )

    assert plan.mode is WorkspaceExitMode.PRESERVE_SHARED_DATA
    assert plan.blockers == ()
    assert WorkspaceExitAction.REMOVE_MEMBERSHIP in plan.actions
    assert WorkspaceExitAction.NULL_CREATOR_REFERENCE in plan.actions


def test_personal_workspace_with_external_manager_is_not_implicitly_destroyed():
    plan = classify_workspace_exit(
        WorkspaceDeletionFacts(
            workspace_id="managed-personal",
            kind="personal",
            role="owner",
            member_count=1,
            owner_count=1,
            has_external_manager=True,
        )
    )

    assert plan.mode is WorkspaceExitMode.PRESERVE_SHARED_DATA
    assert plan.blockers == (
        AccountDeletionBlocker.SOLE_OWNER_SHARED_WORKSPACE,
    )


def test_sole_owner_of_shared_workspace_blocks_account_deletion():
    plan = build_personal_account_deletion_plan(
        [
            WorkspaceDeletionFacts(
                workspace_id="business-1",
                kind="business",
                role="owner",
                member_count=4,
                owner_count=1,
                is_billing_owner=True,
                is_creator=True,
            )
        ]
    )

    assert plan.ready is False
    assert plan.blockers == (
        AccountDeletionBlocker.SOLE_OWNER_SHARED_WORKSPACE,
        AccountDeletionBlocker.SHARED_WORKSPACE_BILLING_OWNER,
    )
    assert plan.workspaces[0].mode is WorkspaceExitMode.PRESERVE_SHARED_DATA


def test_shared_workspace_with_another_owner_can_remove_member():
    plan = build_personal_account_deletion_plan(
        [
            WorkspaceDeletionFacts(
                workspace_id="business-2",
                kind="business",
                role="owner",
                member_count=3,
                owner_count=2,
                is_creator=True,
            )
        ]
    )

    assert plan.ready is True
    assert plan.blockers == ()
    assert plan.workspaces[0].actions == (
        WorkspaceExitAction.REMOVE_MEMBERSHIP,
        WorkspaceExitAction.NULL_CREATOR_REFERENCE,
    )


def test_billing_owner_must_transfer_even_when_not_an_owner_member():
    plan = build_personal_account_deletion_plan(
        [
            WorkspaceDeletionFacts(
                workspace_id="business-3",
                kind="business",
                role="editor",
                member_count=3,
                owner_count=1,
                is_billing_owner=True,
            )
        ]
    )

    assert plan.ready is False
    assert plan.blockers == (
        AccountDeletionBlocker.SHARED_WORKSPACE_BILLING_OWNER,
    )


def test_manager_only_relationship_detaches_without_deleting_workspace():
    plan = classify_workspace_exit(
        WorkspaceDeletionFacts(
            workspace_id="managed-business",
            kind="business",
            role=None,
            member_count=2,
            owner_count=1,
            is_manager=True,
        )
    )

    assert plan.mode is WorkspaceExitMode.PRESERVE_SHARED_DATA
    assert plan.blockers == ()
    assert plan.actions == (WorkspaceExitAction.DETACH_MANAGER_REFERENCE,)


def test_last_superuser_and_verified_hold_fail_closed():
    plan = build_personal_account_deletion_plan(
        [],
        is_last_active_superuser=True,
        verified_legal_hold=True,
    )

    assert plan.ready is False
    assert plan.blockers == (
        AccountDeletionBlocker.LAST_ACTIVE_SUPERUSER,
        AccountDeletionBlocker.VERIFIED_LEGAL_HOLD,
    )


def test_execution_order_revokes_access_before_primary_delete_and_waits_for_backups():
    assert DELETION_EXECUTION_ORDER.index(
        AccountDeletionAction.INVALIDATE_AUTH_SESSIONS
    ) < DELETION_EXECUTION_ORDER.index(
        AccountDeletionAction.DELETE_PRIMARY_DATABASE_ROWS
    )
    assert DELETION_EXECUTION_ORDER.index(
        AccountDeletionAction.REVOKE_PERSONAL_PROVIDER_ACCESS
    ) < DELETION_EXECUTION_ORDER.index(
        AccountDeletionAction.DELETE_PRIMARY_DATABASE_ROWS
    )
    assert DELETION_EXECUTION_ORDER[-1] is AccountDeletionAction.WAIT_FOR_BACKUP_EXPIRY


@pytest.mark.parametrize(
    "facts",
    [
        WorkspaceDeletionFacts(
            workspace_id="bad-kind",
            kind="team",
            role="owner",
            member_count=1,
            owner_count=1,
        ),
        WorkspaceDeletionFacts(
            workspace_id="bad-role",
            kind="personal",
            role="manager",
            member_count=1,
            owner_count=1,
        ),
        WorkspaceDeletionFacts(
            workspace_id="negative",
            kind="personal",
            role="viewer",
            member_count=-1,
            owner_count=0,
        ),
        WorkspaceDeletionFacts(
            workspace_id="owners",
            kind="business",
            role="editor",
            member_count=1,
            owner_count=2,
        ),
    ],
)
def test_invalid_workspace_facts_fail_closed(facts):
    with pytest.raises(ValueError):
        classify_workspace_exit(facts)
