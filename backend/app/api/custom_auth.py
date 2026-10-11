import secrets
import uuid
import json

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import current_active_user, get_jwt_strategy, get_user_manager
from app.models.user import User
from app.core.auth_policy import require_local_auth_enabled
from app.core.config import get_settings
from app.schemas.user import UserCreate
from app.core.database import get_async_session
from app.core.redis import get_redis
from app.models.passkey import UserPasskey

router = APIRouter()

TEMP_TOKEN_TTL = 300  # 5 minutes
DEMO_EMAIL = "finco-temporary-demo@example.com"
DEMO_EPOCH_PREFIX = "devdemo-"


def _is_temporary_demo_request(request: Request) -> bool:
    """Require the opt-in local configuration and the browser's local origin.

    The demo has its own non-admin account and isolated workspace; this is
    never a shortcut to a real user's credentials or a production endpoint.
    """
    settings = get_settings()
    return bool(
        settings.temporary_demo_login_available
        and settings.local_auth_enabled
        and request.headers.get("origin") == settings.frontend_url.rstrip("/")
    )


async def _temporary_demo_token(user_manager, session: AsyncSession, request: Request) -> str:
    user = await session.scalar(select(User).where(User.email == DEMO_EMAIL))
    if user is None:
        # Never use the supplied username/password to create a real account.
        user = await user_manager.create(
            UserCreate(
                email=DEMO_EMAIL,
                password=secrets.token_urlsafe(32),
                is_active=True,
                is_verified=True,
                is_superuser=False,
            ),
            safe=False,
            request=request,
        )
        user.auth_epoch = DEMO_EPOCH_PREFIX + uuid.uuid4().hex[:24]
        await session.commit()
    if (
        not user.is_active or user.is_superuser
        or not (user.auth_epoch or "").startswith(DEMO_EPOCH_PREFIX)
    ):
        # Never claim a preexisting (possibly real) account as the demo.
        raise HTTPException(status_code=409, detail="DEVELOPMENT_DEMO_ACCOUNT_CONFLICT")
    return await get_jwt_strategy().write_token(user, fresh_auth=True)


@router.post("/login", dependencies=[Depends(require_local_auth_enabled)])
async def login(
    request: Request,
    credentials: OAuth2PasswordRequestForm = Depends(),
    user_manager=Depends(get_user_manager),
    session: AsyncSession = Depends(get_async_session),
):
    if _is_temporary_demo_request(request):
        token = await _temporary_demo_token(user_manager, session, request)
        return {"access_token": token, "token_type": "bearer"}

    user = await user_manager.authenticate(credentials)
    if user is None or not user.is_active:
        raise HTTPException(status_code=400, detail="LOGIN_BAD_CREDENTIALS")

    available_methods = []
    if user.is_2fa_enabled and user.totp_secret:
        available_methods.append("totp")
        # A passkey doubles as a second factor only when the user explicitly
        # enabled 2FA. On its own it is a passwordless login alternative —
        # requiring it on top of the password would permanently lock the
        # account if the passkey is lost (there are no recovery codes).
        passkey_count = await session.scalar(
            select(func.count()).select_from(UserPasskey).where(UserPasskey.user_id == user.id)
        )
        if passkey_count and passkey_count > 0:
            available_methods.append("passkey")

    if available_methods:
        # Store temp token in Redis, return 2FA challenge
        r = await get_redis()
        temp_token = secrets.token_urlsafe(32)
        await r.set(
            f"2fa_temp:{temp_token}",
            json.dumps({"user_id": str(user.id), "available_methods": available_methods, "credential_stamp": get_jwt_strategy().stamp(user)}),
            ex=TEMP_TOKEN_TTL,
        )
        return {"requires_2fa": True, "temp_token": temp_token, "available_methods": available_methods}

    # Normal login — generate JWT
    strategy = get_jwt_strategy()
    token = await strategy.write_token(user, fresh_auth=True)
    return {"access_token": token, "token_type": "bearer"}


@router.post("/logout")
async def logout(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    # Explicitly sign out all sessions. Rotation is durable across workers/restarts.
    if (user.auth_epoch or "").startswith(DEMO_EPOCH_PREFIX):
        user.auth_epoch = DEMO_EPOCH_PREFIX + uuid.uuid4().hex[:24]
    else:
        user.auth_epoch = str(uuid.uuid4())
    session.add(user)
    await session.commit()
    return {"detail": "All sessions signed out"}
