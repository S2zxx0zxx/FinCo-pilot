import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.services import agent_service, conversation_service, core_usage_service


@pytest.mark.asyncio
async def test_core_copilot_is_lazy_provisioned_per_user_workspace(
    session: AsyncSession, test_user, test_workspace
):
    first = await agent_service.ensure_core_copilot(
        session, test_workspace.id, test_user.id
    )
    second = await agent_service.ensure_core_copilot(
        session, test_workspace.id, test_user.id
    )
    assert first.id == second.id
    assert agent_service.is_core_copilot(first)
    assert first.provider is None
    assert first.model is None


@pytest.mark.asyncio
async def test_advanced_agent_list_hides_system_copilot(
    session: AsyncSession, test_user, test_workspace
):
    core = await agent_service.ensure_core_copilot(
        session, test_workspace.id, test_user.id
    )
    rows = await agent_service.list_agents(session, test_workspace.id)
    assert core.id not in {row.id for row in rows}


@pytest.mark.asyncio
async def test_conversation_queries_are_owner_scoped(
    session: AsyncSession, test_user, test_workspace
):
    core = await agent_service.ensure_core_copilot(
        session, test_workspace.id, test_user.id
    )
    conv = await conversation_service.create_conversation(
        session,
        workspace_id=test_workspace.id,
        user_id=test_user.id,
        agent_id=core.id,
        channel="web",
    )
    assert await conversation_service.get_conversation(
        session, conv.id, test_workspace.id, test_user.id
    ) is not None

    other_user_id = uuid.uuid4()
    assert await conversation_service.get_conversation(
        session, conv.id, test_workspace.id, other_user_id
    ) is None
    assert await conversation_service.list_conversations(
        session, test_workspace.id, other_user_id
    ) == []


@pytest.mark.asyncio
async def test_core_daily_quota_is_deletion_proof_and_enforced(
    session: AsyncSession, test_user
):
    first, limit = await core_usage_service.consume_core_message(
        session, user_id=test_user.id, limit=2
    )
    await session.commit()
    second, _ = await core_usage_service.consume_core_message(
        session, user_id=test_user.id, limit=2
    )
    await session.commit()
    assert (first, second, limit) == (1, 2, 2)

    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        await core_usage_service.consume_core_message(
            session, user_id=test_user.id, limit=2
        )
    assert exc.value.status_code == 429
    assert exc.value.headers is not None
    assert int(exc.value.headers["Retry-After"]) > 0
