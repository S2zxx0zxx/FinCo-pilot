"""Workspace-scoped, individually revocable external MCP credentials."""
from datetime import datetime, timedelta, timezone
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.agents.config import get_agent_settings
from app.agents.mcp.auth import mint_token
from app.core.auth import get_jwt_strategy
from app.core.database import get_async_session
from app.core.workspace_context import WorkspaceContext, current_writable_workspace
from app.models.mcp_token import ExternalMCPToken

router = APIRouter(prefix="/api/agents/mcp-tokens", tags=["agents"])


class TokenRequest(BaseModel):
    allow_writes: bool = False


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_mcp_token(
    body: TokenRequest = TokenRequest(),
    ctx: WorkspaceContext = Depends(current_writable_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    days = min(max(get_agent_settings().mcp_external_ttl_days, 1), 90)
    row = ExternalMCPToken(
        id=uuid.uuid4(), user_id=ctx.user_id, workspace_id=ctx.id,
        credential_stamp=get_jwt_strategy().stamp(ctx.user),
        allow_writes=body.allow_writes, revoked=False,
        expires_at=datetime.now(timezone.utc) + timedelta(days=days),
    )
    session.add(row)
    await session.commit()
    token = mint_token(user_id=ctx.user_id, workspace_id=ctx.id,
                       ttl_seconds=days * 86400, external=True, token_id=row.id)
    return {"id": str(row.id), "token": token, "expires_in_seconds": days * 86400,
            "expires_in_days": days, "allow_writes": row.allow_writes,
            "workspace_id": str(ctx.id), "workspace_name": ctx.workspace.name}


@router.get("")
async def list_mcp_tokens(
    ctx: WorkspaceContext = Depends(current_writable_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    rows = (await session.execute(select(ExternalMCPToken).where(
        ExternalMCPToken.user_id == ctx.user_id, ExternalMCPToken.workspace_id == ctx.id,
    ).order_by(ExternalMCPToken.created_at.desc()))).scalars().all()
    return [{"id": str(row.id), "allow_writes": row.allow_writes, "revoked": row.revoked,
             "created_at": row.created_at, "expires_at": row.expires_at} for row in rows]


@router.delete("/{token_id}", status_code=204)
async def revoke_mcp_token(
    token_id: uuid.UUID,
    ctx: WorkspaceContext = Depends(current_writable_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    row = await session.get(ExternalMCPToken, token_id)
    if row is None or row.user_id != ctx.user_id or row.workspace_id != ctx.id:
        raise HTTPException(404, "Token not found")
    row.revoked = True
    await session.commit()
