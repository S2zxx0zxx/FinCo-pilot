"""Approval claims are durable before execution: uncertain failures cannot replay."""
from datetime import datetime, timedelta, timezone
import json
import uuid

from fastapi import HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mcp_approval import MCPApproval
from app.models.mcp_token import ExternalMCPToken


def utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


async def queue_approval(session: AsyncSession, ctx, name: str, arguments: dict) -> dict:
    # Serialize submissions per credential; cap input, pending queue and retained
    # history without touching the financial records an action may have created.
    encoded = json.dumps(arguments, sort_keys=True, allow_nan=False)
    if len(encoded.encode()) > 16384:
        raise HTTPException(422, 'Approval arguments exceed 16 KiB')
    await session.execute(select(ExternalMCPToken).where(ExternalMCPToken.id == ctx.token_id).with_for_update())
    now = datetime.now(timezone.utc)
    await session.execute(delete(MCPApproval).where(MCPApproval.token_id == ctx.token_id, MCPApproval.expires_at < now - timedelta(days=30)))
    count = await session.scalar(select(func.count()).select_from(MCPApproval).where(
        MCPApproval.token_id == ctx.token_id, MCPApproval.created_at > now - timedelta(hours=1),
    ))
    if count and count >= 50:
        raise HTTPException(429, 'Too many approval requests; wait before requesting another change')
    row = MCPApproval(id=uuid.uuid4(), token_id=ctx.token_id, user_id=ctx.user_id,
                      workspace_id=ctx.workspace_id, tool_name=name, arguments=arguments,
                      status='pending', expires_at=now + timedelta(minutes=10))
    session.add(row)
    await session.commit()
    return {'applied': False, 'requires_approval': True, 'approval_id': str(row.id),
            'expires_at': row.expires_at.isoformat(), 'tool': name,
            'message': 'Review and approve this exact action in FinCo-Pilot Agent Connections. No change has been applied.'}


async def validate_execution(session: AsyncSession, ctx, approval_id: uuid.UUID, name: str, arguments: dict) -> None:
    row = await session.get(MCPApproval, approval_id)
    if (row is None or row.status != 'executing' or row.token_id != ctx.token_id
            or row.user_id != ctx.user_id or row.workspace_id != ctx.workspace_id
            or row.tool_name != name or row.arguments != arguments
            or utc(row.expires_at) <= datetime.now(timezone.utc)):
        raise HTTPException(403, 'This action has no valid human approval')
