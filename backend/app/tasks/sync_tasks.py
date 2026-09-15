import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.core.redis import get_redis
from app.models.bank_connection import BankConnection
from app.providers import get_provider
from app.providers.base import (
    ProviderNotConfiguredError,
    ProviderUserActionRequired,
    SessionExpiredError,
)
from app.services import connection_service
from app.worker import celery_app

logger = logging.getLogger(__name__)

STALE_THRESHOLD = timedelta(hours=4)


def _make_session_maker():
    """Create a fresh engine+session for the Celery worker event loop."""
    settings = get_settings()
    engine = create_async_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout=settings.db_pool_timeout_seconds,
        pool_recycle=settings.db_pool_recycle_seconds,
    )
    return engine, async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def _stale_connections() -> list[tuple[uuid.UUID, uuid.UUID]]:
    """Return stale connection/user pairs without doing any provider work."""
    engine, session_maker = _make_session_maker()
    try:
        cutoff = datetime.now(timezone.utc) - STALE_THRESHOLD
        async with session_maker() as session:
            result = await session.execute(
                select(BankConnection.id, BankConnection.user_id).where(
                    BankConnection.status.in_(["active", "error"]),
                    BankConnection.last_sync_status.notin_(["queued", "running"]),
                    (BankConnection.last_sync_at < cutoff)
                    | (BankConnection.last_sync_at.is_(None)),
                )
            )
            return list(result.all())
    finally:
        await engine.dispose()


async def _release_lock(redis, key: str, token: str) -> None:
    """Delete only the lock value this worker owns."""
    script = """
    if redis.call('get', KEYS[1]) == ARGV[1] then
        return redis.call('del', KEYS[1])
    end
    return 0
    """
    try:
        await redis.eval(script, 1, key, token)
    except Exception:
        logger.warning("Failed to release bank-sync lock %s", key, exc_info=True)


async def _sync_one_celery(
    connection_id: str,
    user_id: str,
    trigger_provider_refresh: bool,
) -> dict:
    """Run exactly one connection sync behind a distributed per-link lock."""
    settings = get_settings()
    conn_uuid = uuid.UUID(connection_id)
    user_uuid = uuid.UUID(user_id)
    lock_key = f"bank-sync:{connection_id}"
    lock_token = uuid.uuid4().hex
    redis = await get_redis()
    acquired = await redis.set(
        lock_key,
        lock_token,
        nx=True,
        ex=settings.bank_sync_lock_ttl_seconds,
    )
    if not acquired:
        logger.info("Bank sync already running for %s", connection_id)
        return {"status": "already_running", "connection_id": connection_id}

    engine, session_maker = _make_session_maker()
    provider_refresh_outcome = "not_requested"
    try:
        async with session_maker() as session:
            connection = await session.get(BankConnection, conn_uuid)
            if connection is None:
                return {"status": "missing", "connection_id": connection_id}

            connection.last_sync_started_at = datetime.now(timezone.utc)
            connection.last_sync_status = "running"
            connection.last_sync_error = None
            await session.commit()

            workspace_id = connection.workspace_id
            before_sync_at = connection.last_sync_at

            # Manual refresh happens here, outside the HTTP request. We record
            # whether the upstream provider actually refreshed so a cached read
            # can never masquerade as freshly fetched bank data.
            if trigger_provider_refresh:
                try:
                    provider = get_provider(connection.provider)
                    credentials = await provider.refresh_credentials(connection.credentials or {})
                    connection.credentials = credentials
                    provider_refresh_outcome = await provider.trigger_refresh(credentials)
                    if provider_refresh_outcome == "refreshed":
                        connection.last_provider_refresh_at = datetime.now(timezone.utc)
                    elif provider_refresh_outcome == "needs_user_action":
                        connection.status = "error"
                        connection.last_sync_status = "action_required"
                        connection.last_sync_error = (
                            "The bank/provider requires reconnection before fresh data can be fetched."
                        )
                        await session.commit()
                        return {
                            "status": "action_required",
                            "connection_id": connection_id,
                        }
                    await session.commit()
                except ValueError as exc:
                    raise ProviderNotConfiguredError(str(exc)) from exc

            connection, merged_count = await connection_service.sync_connection(
                session,
                conn_uuid,
                workspace_id,
                user_uuid,
                trigger_provider_refresh=False,
            )

            # connection_service intentionally treats provider throttling as a
            # soft skip. If last_sync_at did not advance, expose that truth.
            if connection.last_sync_at == before_sync_at:
                connection.last_sync_status = "rate_limited"
                connection.last_sync_error = "Provider rate limit prevented this sync; retry later."
            elif provider_refresh_outcome == "failed":
                connection.last_sync_status = "cached"
                connection.last_sync_error = (
                    "The provider refresh failed, so FinCo processed the provider's cached copy."
                )
            else:
                connection.last_sync_status = "success"
                connection.last_sync_error = None
            await session.commit()

            return {
                "status": connection.last_sync_status,
                "connection_id": connection_id,
                "merged_count": merged_count,
                "provider_refresh": provider_refresh_outcome,
            }

    except SessionExpiredError as exc:
        async with session_maker() as session:
            conn = await session.get(BankConnection, conn_uuid)
            if conn:
                conn.last_sync_status = "action_required"
                conn.last_sync_error = str(exc)[:1000]
                await session.commit()
        raise
    except ProviderUserActionRequired as exc:
        async with session_maker() as session:
            conn = await session.get(BankConnection, conn_uuid)
            if conn:
                conn.last_sync_status = "action_required"
                conn.last_sync_error = str(exc)[:1000]
                await session.commit()
        raise
    except Exception as exc:
        logger.exception("Bank sync failed for connection %s", connection_id)
        async with session_maker() as session:
            conn = await session.get(BankConnection, conn_uuid)
            if conn:
                conn.last_sync_status = "error"
                conn.last_sync_error = str(exc)[:1000] or type(exc).__name__
                await session.commit()
        raise
    finally:
        await engine.dispose()
        await _release_lock(redis, lock_key, lock_token)


@celery_app.task(name="app.tasks.sync_tasks.sync_all_connections")
def sync_all_connections() -> dict:
    """Fan out stale connections into independent idempotent Celery jobs."""
    stale = asyncio.run(_stale_connections())
    queued = 0
    for connection_id, user_id in stale:
        celery_app.send_task(
            "app.tasks.sync_tasks.sync_single_connection",
            args=[str(connection_id), str(user_id), False],
        )
        queued += 1
    logger.info("Background sync fan-out queued %d connections", queued)
    return {"queued": queued}


@celery_app.task(name="app.tasks.sync_tasks.sync_single_connection")
def sync_single_connection(
    connection_id: str,
    user_id: str,
    trigger_provider_refresh: bool = False,
) -> dict:
    """Sync a single connection, deduplicated across all workers."""
    try:
        return asyncio.run(
            _sync_one_celery(connection_id, user_id, trigger_provider_refresh)
        )
    except Exception as exc:
        # Keep the Celery result useful while DB state carries the user-facing
        # error. Re-raising would also mark the task failed, but the scheduler
        # should not retry credential/user-action failures blindly.
        return {
            "status": "error",
            "connection_id": connection_id,
            "error": str(exc),
        }
