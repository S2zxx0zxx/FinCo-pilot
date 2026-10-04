"""Generic recovery acceptance; email/provider details stay off the public response."""
import hashlib
import hmac
import logging

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
router.routes = [route for route in router.routes if getattr(route, 'path', None) != '/forgot-password']
_recipient_limit = RateLimiter(max_requests=3, window_seconds=3600)
_active_requests = 0
_MAX_ACTIVE = 8


async def _deliver(email: str) -> None:
    global _active_requests
    try:
        async with async_session_maker() as session:
            manager = UserManager(SQLAlchemyUserDatabase(session, User))
            try:
                user = await manager.get_by_email(email)
                await manager.forgot_password(user)
            except (exceptions.UserNotExists, exceptions.UserInactive):
                pass
    except Exception:
        # SMTP service emits bounded failure reasons; never log recipient,
        # bearer, provider response or raw exception/traceback here.
        logger.warning('Password recovery delivery could not be completed')
    finally:
        _active_requests -= 1


@router.post('/forgot-password', status_code=202)
async def forgot_password(background: BackgroundTasks, email: EmailStr = Body(..., embed=True)):
    global _active_requests
    settings = get_settings()
    # Configuration/capacity failure is identical for every submitted address.
    if settings.email_delivery_required and not settings.email_delivery_available:
        raise HTTPException(503, 'Account recovery is temporarily unavailable')
    digest = hmac.new(settings.secret_key.get_secret_value().encode(),
                      str(email).casefold().encode(), hashlib.sha256).hexdigest()
    await _recipient_limit.check_key('password_recovery:recipient:' + digest)
    if _active_requests >= _MAX_ACTIVE:
        raise HTTPException(503, 'Account recovery is temporarily unavailable', headers={'Retry-After': '60'})
    _active_requests += 1
    # Accept before account lookup/SMTP. 202 does not assert inbox delivery.
    # Independent session avoids using a closed request dependency in a task.
    background.add_task(_deliver, str(email))
