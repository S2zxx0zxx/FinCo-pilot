from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.models.agent import Agent, AgentTool
from app.agents.models.conversation import Conversation
from app.agents.models.knowledge import KnowledgeDoc
from app.agents.schemas.agent import AgentCreate, AgentUpdate
from app.models.workspace import Workspace


CORE_COPILOT_KIND = "core_copilot"
CORE_COPILOT_VERSION = 1
CORE_COPILOT_NAME = "FinCo Copilot"
CORE_COPILOT_SYSTEM_PROMPT = """You are FinCo Copilot, the built-in assistant for this FinCo-Pilot workspace.

Use FinCo-Pilot tools for user-specific facts. Never invent balances, transactions, budgets, goals, Safe-to-Spend, loan values, or other financial facts. Retrieve only the minimum data needed for the current request. Treat page context as orientation and re-read live values through tools. Read authorized data proactively so the user does not have to repeat what FinCo-Pilot already knows. For changes, prepare proposals for user review. Never move money, expose secrets, bypass workspace permissions, or claim a change happened unless FinCo-Pilot confirms it. Be concise, actionable, and answer in the user's language.
"""


def is_core_copilot(agent: Agent) -> bool:
    extra = agent.extra if isinstance(agent.extra, dict) else {}
    return extra.get("kind") == CORE_COPILOT_KIND and extra.get("system_managed") is True


def can_access_agent(agent: Agent, user_id: uuid.UUID) -> bool:
    """Workspace agents are shared; the system core copilot is per-user."""
    return not is_core_copilot(agent) or agent.user_id == user_id


async def ensure_core_copilot(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Agent:
    """Lazily create one system-managed FinCo Copilot per user/workspace.

    Lock the workspace row while checking/creating so concurrent first-open
    requests cannot race into duplicate system agents in PostgreSQL.
    """
    await session.execute(
        select(Workspace.id)
        .where(Workspace.id == workspace_id)
        .with_for_update()
    )
    rows = list((await session.execute(
        select(Agent)
        .where(
            Agent.workspace_id == workspace_id,
            Agent.user_id == user_id,
            Agent.is_archived.is_(False),
        )
        .order_by(Agent.created_at.asc())
    )).scalars().all())
    for row in rows:
        if not is_core_copilot(row):
            continue
        extra = row.extra if isinstance(row.extra, dict) else {}
        if int(extra.get("version") or 0) < CORE_COPILOT_VERSION:
            row.name = CORE_COPILOT_NAME
            row.description = "Your context-aware FinCo-Pilot assistant"
            row.system_prompt = CORE_COPILOT_SYSTEM_PROMPT
            row.icon = "sparkles"
            row.color = "#6366F1"
            row.provider = None
            row.model = None
            row.temperature = 0.2
            row.max_history_messages = 30
            row.top_n = 6
            row.similarity_threshold = 0.25
            row.auto_context = True
            row.extra = {
                **extra,
                "kind": CORE_COPILOT_KIND,
                "system_managed": True,
                "version": CORE_COPILOT_VERSION,
            }
            await session.commit()
            await session.refresh(row)
        return row

    agent = Agent(
        user_id=user_id,
        workspace_id=workspace_id,
        name=CORE_COPILOT_NAME,
        description="Your context-aware FinCo-Pilot assistant",
        system_prompt=CORE_COPILOT_SYSTEM_PROMPT,
        icon="sparkles",
        color="#6366F1",
        provider=None,
        model=None,
        temperature=0.2,
        max_history_messages=30,
        top_n=6,
        similarity_threshold=0.25,
        auto_context=True,
        is_default=False,
        extra={
            "kind": CORE_COPILOT_KIND,
            "system_managed": True,
            "version": CORE_COPILOT_VERSION,
        },
    )
    session.add(agent)
    await session.commit()
    await session.refresh(agent)
    return agent


async def list_agents(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    *,
    include_archived: bool = False,
) -> list[Agent]:
    q = select(Agent).where(Agent.workspace_id == workspace_id).order_by(Agent.created_at.desc())
    if not include_archived:
        q = q.where(Agent.is_archived.is_(False))
    rows = [
        row
        for row in (await session.execute(q)).scalars().all()
        if not is_core_copilot(row)
    ]
    # System-managed core copilots stay out of advanced-agent management.
    # One scalar query per (conv, kb) so the agents list page can show
    # counts without N+1. Cheap on small fan-out; if agent counts grow
    # we should switch to a single GROUP BY join.
    if rows:
        ids = [a.id for a in rows]
        conv_counts = dict(
            (r[0], r[1])
            for r in (
                await session.execute(
                    select(Conversation.agent_id, func.count(Conversation.id))
                    .where(Conversation.agent_id.in_(ids))
                    .group_by(Conversation.agent_id)
                )
            ).all()
        )
        kb_counts = dict(
            (r[0], r[1])
            for r in (
                await session.execute(
                    select(KnowledgeDoc.agent_id, func.count(KnowledgeDoc.id))
                    .where(KnowledgeDoc.agent_id.in_(ids))
                    .group_by(KnowledgeDoc.agent_id)
                )
            ).all()
        )
        # Stash on the model instances; pydantic AgentRead reads them.
        for a in rows:
            a.conversation_count = int(conv_counts.get(a.id, 0))  # type: ignore[attr-defined]
            a.knowledge_count = int(kb_counts.get(a.id, 0))  # type: ignore[attr-defined]
    return rows


async def get_agent(
    session: AsyncSession,
    agent_id: uuid.UUID,
    workspace_id: uuid.UUID,
) -> Optional[Agent]:
    return (await session.execute(
        select(Agent).where(Agent.id == agent_id, Agent.workspace_id == workspace_id)
    )).scalar_one_or_none()


async def create_agent(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    data: AgentCreate,
) -> Agent:
    agent = Agent(
        user_id=user_id,
        workspace_id=workspace_id,
        name=data.name,
        description=data.description,
        system_prompt=data.system_prompt,
        icon=data.icon,
        color=data.color,
        connection_id=data.connection_id,
        provider=data.provider,
        model=data.model,
        temperature=data.temperature,
        max_history_messages=data.max_history_messages,
        top_n=data.top_n,
        similarity_threshold=data.similarity_threshold,
        extra=data.extra or {},
        auto_context=data.auto_context,
    )
    session.add(agent)
    await session.commit()
    await session.refresh(agent)
    return agent


async def update_agent(
    session: AsyncSession,
    agent_id: uuid.UUID,
    workspace_id: uuid.UUID,
    data: AgentUpdate,
) -> Optional[Agent]:
    agent = await get_agent(session, agent_id, workspace_id)
    if agent is None:
        return None
    payload = data.model_dump(exclude_unset=True)
    # If turning this agent into the default, clear the flag on every
    # other agent in the same workspace first — the partial unique
    # index would otherwise reject the commit.
    if payload.get("is_default") is True:
        await session.execute(
            update(Agent)
            .where(
                Agent.workspace_id == workspace_id,
                Agent.id != agent_id,
                Agent.is_default.is_(True),
            )
            .values(is_default=False)
        )
    for field, value in payload.items():
        setattr(agent, field, value)
    await session.commit()
    await session.refresh(agent)
    return agent


async def get_default_agent(
    session: AsyncSession, workspace_id: uuid.UUID
) -> Optional[Agent]:
    """The default agent is what the global slide-over chat panel uses.
    Falls back to the most-recently-created non-archived agent so the
    panel still works for workspaces that haven't picked one yet."""
    explicit_rows = list((await session.execute(
        select(Agent).where(
            Agent.workspace_id == workspace_id,
            Agent.is_default.is_(True),
            Agent.is_archived.is_(False),
        )
    )).scalars().all())
    explicit = next(
        (row for row in explicit_rows if not is_core_copilot(row)),
        None,
    )
    if explicit is not None:
        return explicit
    rows = list((await session.execute(
        select(Agent)
        .where(Agent.workspace_id == workspace_id, Agent.is_archived.is_(False))
        .order_by(Agent.created_at.desc())
    )).scalars().all())
    return next((row for row in rows if not is_core_copilot(row)), None)


async def delete_agent(
    session: AsyncSession, agent_id: uuid.UUID, workspace_id: uuid.UUID
) -> bool:
    agent = await get_agent(session, agent_id, workspace_id)
    if agent is None:
        return False
    await session.delete(agent)
    await session.commit()
    return True


async def list_tools(session: AsyncSession, agent_id: uuid.UUID) -> list[AgentTool]:
    return list((await session.execute(
        select(AgentTool).where(AgentTool.agent_id == agent_id)
    )).scalars().all())


async def set_tool_enabled(
    session: AsyncSession, agent_id: uuid.UUID, server: str, tool_name: str, enabled: bool
) -> AgentTool:
    existing = (await session.execute(
        select(AgentTool).where(
            AgentTool.agent_id == agent_id,
            AgentTool.server == server,
            AgentTool.tool_name == tool_name,
        )
    )).scalar_one_or_none()
    if existing is None:
        existing = AgentTool(agent_id=agent_id, server=server, tool_name=tool_name, enabled=enabled)
        session.add(existing)
    else:
        existing.enabled = enabled
    await session.commit()
    return existing


async def allowed_tool_pairs(session: AsyncSession, agent_id: uuid.UUID) -> Optional[set[tuple[str, str]]]:
    """Returns the set of (server, tool_name) pairs the agent is permitted
    to call. Returns None when no rows exist — interpreted as 'allow all'
    so first-run agents work without setup."""
    rows = await list_tools(session, agent_id)
    if not rows:
        return None
    return {(r.server, r.tool_name) for r in rows if r.enabled}


async def replace_tool_enablement(
    session: AsyncSession, agent_id: uuid.UUID, items: list[tuple[str, str, bool]]
) -> None:
    await session.execute(delete(AgentTool).where(AgentTool.agent_id == agent_id))
    for server, name, enabled in items:
        session.add(AgentTool(agent_id=agent_id, server=server, tool_name=name, enabled=enabled))
    await session.commit()
