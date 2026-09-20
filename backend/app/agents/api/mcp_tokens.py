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


@router.get('/approvals')
async def list_approvals(
    ctx: WorkspaceContext = Depends(current_writable_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    from app.models.mcp_approval import MCPApproval
    rows = (await session.scalars(select(MCPApproval).where(
        MCPApproval.user_id == ctx.user_id, MCPApproval.workspace_id == ctx.id,
    ).order_by(MCPApproval.created_at.desc()).limit(50))).all()
    return [{'id': str(row.id), 'tool': row.tool_name, 'arguments': row.arguments,
             'expires_at': row.expires_at, 'created_at': row.created_at, 'status': ('expired' if row.status == 'pending' and row.expires_at.replace(tzinfo=timezone.utc) <= datetime.now(timezone.utc) else row.status)} for row in rows]


@router.post('/approvals/{approval_id}/approve')
async def approve_action(
    approval_id: uuid.UUID,
    ctx: WorkspaceContext = Depends(current_writable_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    from app.models.mcp_approval import MCPApproval
    from app.services.mcp_approval_service import utc
    from mcp_server.auth import CallContext
    from mcp_server.registry import call_tool
    from mcp_server import tools as _tools  # noqa: F401  register handlers in API process
    row = (await session.scalars(select(MCPApproval).where(
        MCPApproval.id == approval_id, MCPApproval.user_id == ctx.user_id,
        MCPApproval.workspace_id == ctx.id,
    ).with_for_update())).one_or_none()
    if row is None:
        raise HTTPException(404, 'Approval not found')
    if row.status != 'pending' or utc(row.expires_at) <= datetime.now(timezone.utc):
        raise HTTPException(409, 'Approval already used or expired; inspect your records before requesting another action')
    row.status = 'executing'
    await session.commit()  # Claim once, even if the process fails during execution.
    try:
        result = await call_tool(session, CallContext(user_id=ctx.user_id, workspace_id=ctx.id,
                                external=True, token_id=row.token_id), row.tool_name,
                                row.arguments, approved_action_id=row.id)
    except Exception as exc:
        await session.rollback()
        # A handler could have committed before failing. Do not retry or claim
        # that no financial change occurred; the user must reconcile first.
        row = await session.get(MCPApproval, approval_id)
        if row:
            row.status = 'review_required'
            await session.commit()
        raise HTTPException(409, 'Action could not be confirmed. Review your records before requesting another action.') from exc
    row.status = 'executed'
    await session.commit()
    return {'status': 'executed', 'result': result}


@router.post('/approvals/{approval_id}/reject')
async def reject_action(
    approval_id: uuid.UUID,
    ctx: WorkspaceContext = Depends(current_writable_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    from app.models.mcp_approval import MCPApproval
    row = (await session.scalars(select(MCPApproval).where(
        MCPApproval.id == approval_id, MCPApproval.user_id == ctx.user_id,
        MCPApproval.workspace_id == ctx.id,
    ).with_for_update())).one_or_none()
    if row is None:
        raise HTTPException(404, 'Approval not found')
    if row.status != 'pending':
        raise HTTPException(409, 'Approval already used')
    row.status = 'rejected'
    await session.commit()
    return {'status': 'rejected'}
