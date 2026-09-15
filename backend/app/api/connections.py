import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.workspace_context import (
    WorkspaceContext,
    current_workspace,
    current_writable_workspace,
)
from app.providers import all_known_providers
from app.providers.base import (
    ProviderNotConfiguredError,
    ProviderUserActionRequired,
    SessionExpiredError,
)
from app.schemas.bank_connection import (
    BankConnectionRead,
    ConnectionSettingsUpdate,
    ConnectTokenRequest,
    ConnectTokenResponse,
    InstitutionListResponse,
    OAuthCallbackRequest,
    OAuthUrlRequest,
    OAuthUrlResponse,
    ReauthUrlResponse,
    ReconnectTokenResponse,
    SyncDispatchResponse,
)
from app.services import connection_service
from app.services.transfer_detection_service import detect_transfer_pairs, unlink_transfer_pair
from app.worker import celery_app

router = APIRouter(prefix="/api/connections", tags=["connections"])


@router.get("/providers")
async def get_available_providers():
    """List all known open finance providers with configuration status."""
    return {"providers": all_known_providers()}


@router.post("/connect-token", response_model=ConnectTokenResponse)
async def create_connect_token(
    data: ConnectTokenRequest,
    ctx: WorkspaceContext = Depends(current_writable_workspace),
):
    """Create a connect token for widget-based bank connection flows."""
    try:
        token_data = await connection_service.create_connect_token(data.provider, ctx.user_id)
        return ConnectTokenResponse(**token_data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create connect token: {str(e)}",
        )


@router.get("", response_model=list[BankConnectionRead])
async def list_connections(
    ctx: WorkspaceContext = Depends(current_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    return await connection_service.get_connections(session, ctx.workspace.id)


@router.post("/oauth/url", response_model=OAuthUrlResponse)
async def get_oauth_url(
    data: OAuthUrlRequest,
    ctx: WorkspaceContext = Depends(current_writable_workspace),
):
    try:
        url = await connection_service.get_oauth_url(
            data.provider, ctx.user_id, ctx.workspace.id, flow_params=data.flow_params
        )
        return OAuthUrlResponse(url=url)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{provider}/institutions", response_model=InstitutionListResponse)
async def list_provider_institutions(
    provider: str,
    country: str | None = None,
    ctx: WorkspaceContext = Depends(current_workspace),
):
    try:
        return await connection_service.list_provider_institutions(provider, country)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to load institutions: {str(e)}",
        )


@router.post("/oauth/callback", response_model=BankConnectionRead)
async def oauth_callback(
    data: OAuthCallbackRequest,
    ctx: WorkspaceContext = Depends(current_writable_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    try:
        connection = await connection_service.handle_oauth_callback(
            session,
            ctx.workspace.id,
            ctx.user_id,
            data.code,
            provider_name=data.provider,
            state=data.state,
            sync_assets=data.sync_assets,
            reconnect_connection_id=data.reconnect_connection_id,
        )
        return connection
    except ProviderUserActionRequired as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": str(e),
                "code": e.code,
                "help_url": e.help_url,
            },
        )
    except SessionExpiredError as e:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to connect: {str(e)}",
        )


@router.post(
    "/{connection_id}/oauth/reauth-url", response_model=ReauthUrlResponse
)
async def get_reauth_url(
    connection_id: uuid.UUID,
    ctx: WorkspaceContext = Depends(current_writable_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    try:
        url = await connection_service.get_reauth_url(
            session, connection_id, ctx.workspace.id, ctx.user_id
        )
        return ReauthUrlResponse(url=url)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except NotImplementedError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to build reauth URL: {str(e)}",
        )


@router.post(
    "/{connection_id}/sync",
    response_model=SyncDispatchResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def sync_connection(
    connection_id: uuid.UUID,
    ctx: WorkspaceContext = Depends(current_writable_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    """Queue a fresh bank sync without keeping an HTTP request open for ~90s.

    The worker owns provider refresh/polling and a distributed per-connection
    lock. DB state lets every browser/tab observe the same job and prevents
    cached provider data from being presented as a confirmed bank refresh.
    """
    connection = await connection_service.get_connection(
        session, connection_id, ctx.workspace.id
    )
    if not connection:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connection not found")

    if connection.last_sync_status in {"queued", "running"}:
        return SyncDispatchResponse(
            connection_id=connection.id,
            task_id=f"existing:{connection.id}",
            status="already_running",
        )

    # Provider APIs have tight refresh quotas. A successful/error terminal job
    # can be retried after a short cooldown; repeated clicks inside that window
    # are rejected before they ever reach Celery/provider infrastructure.
    now = datetime.now(timezone.utc)
    if connection.last_sync_started_at:
        started = connection.last_sync_started_at
        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
        retry_after = timedelta(seconds=30) - (now - started)
        if retry_after.total_seconds() > 0:
            seconds = max(1, int(retry_after.total_seconds()))
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="A bank refresh was requested recently. Please wait before retrying.",
                headers={"Retry-After": str(seconds)},
            )

    connection.last_sync_status = "queued"
    connection.last_sync_error = None
    connection.last_sync_started_at = now
    await session.commit()

    try:
        task = celery_app.send_task(
            "app.tasks.sync_tasks.sync_single_connection",
            args=[str(connection.id), str(connection.user_id), True],
        )
    except Exception as exc:
        connection.last_sync_status = "error"
        connection.last_sync_error = "Unable to queue bank sync. Background worker is unavailable."
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Bank sync queue is temporarily unavailable. Please retry shortly.",
        ) from exc

    return SyncDispatchResponse(
        connection_id=connection.id,
        task_id=str(task.id),
        status="queued",
    )


@router.post("/{connection_id}/reconnect-token", response_model=ReconnectTokenResponse)
async def get_reconnect_token(
    connection_id: uuid.UUID,
    ctx: WorkspaceContext = Depends(current_writable_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    connection = await connection_service.get_connection(session, connection_id, ctx.workspace.id)
    if not connection:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connection not found")

    item_id = connection.credentials.get("item_id") if connection.credentials else None
    if not item_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Connection has no item_id for reconnection",
        )

    try:
        token_data = await connection_service.create_connect_token(
            connection.provider, ctx.user_id, item_id=item_id
        )
        return ReconnectTokenResponse(**token_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create reconnect token: {str(e)}",
        )


@router.patch("/{connection_id}/settings", response_model=BankConnectionRead)
async def update_settings(
    connection_id: uuid.UUID,
    data: ConnectionSettingsUpdate,
    ctx: WorkspaceContext = Depends(current_writable_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    connection = await connection_service.update_connection_settings(
        session, connection_id, ctx.workspace.id, data.model_dump(exclude_unset=True)
    )
    if not connection:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connection not found")
    return connection


@router.delete("/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_connection(
    connection_id: uuid.UUID,
    ctx: WorkspaceContext = Depends(current_writable_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    deleted = await connection_service.delete_connection(session, connection_id, ctx.workspace.id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connection not found")


@router.post("/transfers/detect")
async def detect_transfers(
    ctx: WorkspaceContext = Depends(current_writable_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    pairs_created = await detect_transfer_pairs(session, ctx.workspace.id)
    await session.commit()
    return {"pairs_created": pairs_created}


@router.delete("/transfers/{pair_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unlink_transfer(
    pair_id: uuid.UUID,
    ctx: WorkspaceContext = Depends(current_writable_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    unlinked = await unlink_transfer_pair(session, ctx.workspace.id, pair_id)
    if not unlinked:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transfer pair not found")
    await session.commit()
