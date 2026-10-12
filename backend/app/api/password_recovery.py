"""Generic recovery acceptance; email/provider details stay off the public response."""

import hashlib
import hmac
import logging
from typing import Literal

from fastapi import BackgroundTasks, Body, HTTPException
from fastapi_users import exceptions
from fastapi_users.db import SQLAlchemyUserDatabase
from pydantic import EmailStr

from app.core.auth import UserManager, fastapi_users
from app.core.config import get_settings
from app.core.database import async_session_maker
from app.core.rate_limit import RateLimiter
from app.core.redis import get_redis
from app.models.user import User

logger = logging.getLogger(__name__)
router = fastapi_users.get_reset_password_router()
router.routes = [
    route for route in router.routes if getattr(route, "path", None) != "/forgot-password"
]
_recipient_limit = RateLimiter(max_requests=3, window_seconds=3600)

# Redis key that counts in-flight email background tasks across all workers.
# Using Redis INCR/DECR makes the limit process-safe for multi-worker deploys.
# The key carries a generous TTL so a crashed worker does not permanently block
# the counter — tasks complete in seconds, so 120 s is a very safe ceiling.
_ACTIVE_REQUESTS_KEY = "email_delivery:active_tasks"
_ACTIVE_REQUESTS_TTL = 120   # seconds — safety-net expiry only
_MAX_ACTIVE = 8


async def _active_count() -> int:
    """Return the current cross-worker in-flight task count from Redis."""
    try:
        r = await get_redis()
        val = await r.get(_ACTIVE_REQUESTS_KEY)
        return int(val) if val is not None else 0
    except Exception:
        # Redis unavailable — fail open so recoveries are not silently blocked.
        return 0


async def _increment_active() -> None:
    """Atomically increment and refresh the TTL safety net."""
    try:
        r = await get_redis()
        await r.incr(_ACTIVE_REQUESTS_KEY)
        # Refresh TTL on every increment so a burst of requests does not cause
        # the key to expire mid-flight.
        await r.expire(_ACTIVE_REQUESTS_KEY, _ACTIVE_REQUESTS_TTL)
    except Exception:
        logger.warning("Could not increment active email task counter in Redis")


async def _decrement_active() -> None:
    """Atomically decrement; clamp to 0 to guard against missed increments."""
    try:
        r = await get_redis()
        result = await r.decr(_ACTIVE_REQUESTS_KEY)
        if isinstance(result, int) and result < 0:
            await r.set(_ACTIVE_REQUESTS_KEY, 0)
    except Exception:
        logger.warning("Could not decrement active email task counter in Redis")


async def _deliver(email: str, purpose: Literal["reset", "verify"] = "reset") -> None:
    try:
        async with async_session_maker() as session:
            manager = UserManager(SQLAlchemyUserDatabase(session, User))
            try:
                user = await manager.get_by_email(email)
                if purpose == "verify":
                    await manager.request_verify(user)
                else:
                    await manager.forgot_password(user)
            except (
                exceptions.UserNotExists,
                exceptions.UserInactive,
                exceptions.UserAlreadyVerified,
            ):
                pass
    except Exception:
        # SMTP service emits bounded failure reasons; never log recipient,
        # bearer, provider response or raw exception/traceback here.
        logger.warning("Account email request could not be completed (%s)", purpose)
    finally:
        await _decrement_active()


async def queue_account_email(
    background: BackgroundTasks, email: str, purpose: Literal["reset", "verify"]
) -> None:
    settings = get_settings()
    # Configuration/capacity failure is identical for every submitted address.
    if settings.email_delivery_required and not settings.email_delivery_available:
        raise HTTPException(503, "Account recovery is temporarily unavailable")
    digest = hmac.new(
        settings.secret_key.get_secret_value().encode(),
        str(email).casefold().encode(),
        hashlib.sha256,
    ).hexdigest()
    await _recipient_limit.check_key(
        ("password_recovery" if purpose == "reset" else "email_verification")
        + ":recipient:"
        + digest
    )
    # Cross-worker concurrency limit: use Redis so every API replica shares the
    # same counter. The previous module-level integer was per-process only.
    if await _active_count() >= _MAX_ACTIVE:
        raise HTTPException(
            503, "Account recovery is temporarily unavailable", headers={"Retry-After": "60"}
        )
    await _increment_active()
    # Accept before account lookup/SMTP. 202 does not assert inbox delivery.
    # Independent session avoids using a closed request dependency in a task.
    background.add_task(_deliver, str(email), purpose)


@router.post("/forgot-password", status_code=202)
async def forgot_password(background: BackgroundTasks, email: EmailStr = Body(..., embed=True)):
    await queue_account_email(background, str(email), "reset")
