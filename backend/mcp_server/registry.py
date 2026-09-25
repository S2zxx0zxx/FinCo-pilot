"""Tool registry for the MCP server.

Each tool is a Python coroutine registered via the @tool decorator. The
registry holds (name → ToolSpec) for /mcp's `tools/list` and `tools/call`.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from mcp_server.auth import CallContext


ToolHandler = Callable[..., Awaitable[Any]]


@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema (object)
    handler: ToolHandler
    # Optional. When True, the tool produces a preview (no DB writes); the
    # frontend asks the user to confirm before applying. Drives UI hints.
    is_proposal: bool = False
    tags: list[str] = field(default_factory=list)


REGISTRY: dict[str, ToolSpec] = {}


def tool(
    name: str,
    *,
    description: str,
    parameters: dict[str, Any],
    is_proposal: bool = False,
    tags: list[str] | None = None,
) -> Callable[[ToolHandler], ToolHandler]:
    """Decorator. The handler must be an async function with signature
    `async def handler(session: AsyncSession, ctx: CallContext, **kwargs)`.
    """
    def deco(fn: ToolHandler) -> ToolHandler:
        if name in REGISTRY:
            raise RuntimeError(f"duplicate tool registration: {name}")
        REGISTRY[name] = ToolSpec(
            name=name,
            description=description,
            parameters=parameters,
            handler=fn,
            is_proposal=is_proposal,
            tags=list(tags or []),
        )
        return fn
    return deco


def list_tools() -> list[dict[str, Any]]:
    """MCP-compatible tool list payload."""
    return [
        {
            "name": s.name,
            "description": s.description,
            "inputSchema": s.parameters,
            "_fincopilot": {"is_proposal": s.is_proposal, "tags": s.tags},
        }
        for s in REGISTRY.values()
    ]


async def call_tool(
    session: AsyncSession,
    ctx: CallContext,
    name: str,
    arguments: dict[str, Any] | None,
    *,
    approved_action_id: uuid.UUID | None = None,
) -> Any:
    spec = REGISTRY.get(name)
    if spec is None:
        raise KeyError(f"unknown tool: {name}")
    if arguments and "apply" in arguments and not isinstance(arguments["apply"], bool):
        raise ValueError("apply must be a JSON boolean")
    await authorize_tool(session, ctx, spec, arguments or {})
    if ctx.external and spec.is_proposal and (arguments or {}).get('apply') is True:
        from app.services.mcp_approval_service import queue_approval, validate_execution
        if approved_action_id is None:
            return await queue_approval(session, ctx, name, arguments or {})
        await validate_execution(session, ctx, approved_action_id, name, arguments or {})
    return await spec.handler(session=session, ctx=ctx, **(arguments or {}))


async def authorize_tool(session, ctx, spec, arguments):
    from datetime import datetime, timezone
    import hmac
    from fastapi import HTTPException
    from app.core.auth import get_jwt_strategy
    from app.core.workspace_context import current_workspace
    from app.models.user import User
    from app.models.mcp_token import ExternalMCPToken
    from app.billing.dependencies import require_workspace_capability
    from app.billing.enums import Capability, Metric
    from app.billing.usage import enforce_limit

    user = await session.get(User, ctx.user_id)
    if user is None or not user.is_active:
        raise HTTPException(403, "Access denied")
    resolved = await current_workspace(
        x_workspace_id=str(ctx.workspace_id) if ctx.workspace_id else None,
        user=user, session=session,
    )
    # Advanced/custom agents remain a Max capability. The built-in core
    # Copilot is a separate first-party surface: internal calls from the
    # caller's own system-managed Copilot may use FinCo tools without
    # granting external MCP or custom-agent entitlement.
    core_internal = False
    if not ctx.external and ctx.agent_id is not None:
        from app.agents.models.agent import Agent
        from app.agents.services.agent_service import is_core_copilot

        agent = await session.get(Agent, ctx.agent_id)
        core_internal = bool(
            agent is not None
            and agent.user_id == user.id
            and agent.workspace_id == resolved.id
            and is_core_copilot(agent)
        )
    if not core_internal:
        await require_workspace_capability(
            session, resolved.workspace, Capability.AGENTS_AUTOMATION
        )

    writing = spec.is_proposal and arguments.get("apply") is True and ctx.external
    if ctx.external:
        row = await session.get(ExternalMCPToken, ctx.token_id) if ctx.token_id else None
        if row is None or row.revoked or row.user_id != user.id or row.workspace_id != resolved.id:
            raise HTTPException(403, "External credential revoked or invalid; create a new token")
        expiry = row.expires_at.replace(tzinfo=timezone.utc) if row.expires_at.tzinfo is None else row.expires_at
        if expiry <= datetime.now(timezone.utc) or not hmac.compare_digest(row.credential_stamp, get_jwt_strategy().stamp(user)):
            raise HTTPException(403, "External credential expired or invalid")
        if writing and not row.allow_writes:
            raise HTTPException(403, "This external credential is read-only")
    if writing:
        resolved.require_write()
        metric = {
            "propose_create_budget": Metric.ACTIVE_BUDGETS,
            "propose_create_goal": Metric.ACTIVE_GOALS,
            "propose_create_recurring_transaction": Metric.ACTIVE_RECURRING,
            "propose_create_payee_rule": Metric.RULES,
        }.get(spec.name)
        if metric:
            await enforce_limit(session, resolved.workspace, metric)