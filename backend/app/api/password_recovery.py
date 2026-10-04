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
from app.models.user import User

logger = logging.getLogger(__name__)
router = fastapi_users.get_reset_password_router()
router.routes = [
    route for route in router.routes if getattr(route, "path", None) != "/forgot-password"
]
_recipient_limit = RateLimiter(max_requests=3, window_seconds=3600)
_active_requests = 0
_MAX_ACTIVE = 8


async def _deliver(email: str, purpose: Literal["reset", "verify"] = "reset") -> None:
    global _active_requests
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
        _active_requests -= 1


async def queue_account_email(
    background: BackgroundTasks, email: str, purpose: Literal["reset", "verify"]
) -> None:
    global _active_requests
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
    if _active_requests >= _MAX_ACTIVE:
        raise HTTPException(
            503, "Account recovery is temporarily unavailable", headers={"Retry-After": "60"}
        )
    _active_requests += 1
    # Accept before account lookup/SMTP. 202 does not assert inbox delivery.
    # Independent session avoids using a closed request dependency in a task.
    background.add_task(_deliver, str(email), purpose)


@router.post("/forgot-password", status_code=202)
async def forgot_password(background: BackgroundTasks, email: EmailStr = Body(..., embed=True)):
    await queue_account_email(background, str(email), "reset")
