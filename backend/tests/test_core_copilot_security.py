import uuid
from unittest.mock import patch

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

@pytest.mark.asyncio
async def test_core_title_generation_is_local_and_does_not_call_provider(
    client, auth_headers, session: AsyncSession, test_user, test_workspace
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
    await conversation_service.append_message(
        session,
        conversation_id=conv.id,
        role="user",
        content="  How much   can I safely spend this weekend?  ",
    )

    with patch(
        "app.agents.runtime.executor._provider_and_model_for",
        side_effect=AssertionError("core title must not call provider"),
    ):
        response = await client.post(
            f"/api/agents/conversations/{conv.id}/generate-title",
            headers=auth_headers,
        )

    assert response.status_code == 200, response.text
    assert response.json()["title"] == "How much can I safely spend this weekend?"

@pytest.mark.asyncio
async def test_viewer_can_chat_with_core_but_gets_read_only_executor(
    client, viewer_auth_headers
):
    from app.agents.runtime.executor import ExecutorEvent

    core_response = await client.get(
        "/api/agents/copilot",
        headers=viewer_auth_headers,
    )
    assert core_response.status_code == 200, core_response.text
    core_id = core_response.json()["id"]

    observed: dict[str, bool] = {}

    async def fake_run(self, **kwargs):
        observed["allow_proposals"] = kwargs["allow_proposals"]
        yield ExecutorEvent(type="done", finish_reason="stop")

    with patch("app.agents.api.chat.AgentExecutor.run", new=fake_run):
        response = await client.post(
            f"/api/agents/{core_id}/chat",
            headers=viewer_auth_headers,
            json={"content": "What needs my attention?"},
        )

    assert response.status_code == 200, response.text
    assert observed["allow_proposals"] is False
    assert "event: conversation" in response.text
    assert "event: done" in response.text

@pytest.mark.asyncio
async def test_max_user_cannot_turn_core_into_custom_knowledge_agent(
    client, auth_headers
):
    core_response = await client.get(
        "/api/agents/copilot",
        headers=auth_headers,
    )
    assert core_response.status_code == 200, core_response.text
    core_id = core_response.json()["id"]

    response = await client.get(
        f"/api/agents/{core_id}/knowledge",
        headers=auth_headers,
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "system copilot knowledge is policy-managed"

