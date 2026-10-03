import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import UserManager, get_jwt_strategy, get_user_manager
from app.core.auth_policy import require_local_auth_enabled
from app.core.config import get_settings
from app.core.database import get_async_session
from app.models.user import User
from app.services.admin_bootstrap_service import (
    CreateAdminRequest, bootstrap_completed, log_bootstrap_success, minimum_password_length, provision_first_admin,
)
from app.core.rate_limit import login_rate_limit

router = APIRouter(prefix="/api/setup", tags=["setup"])


class SetupStatus(BaseModel):
    has_users: bool
    setup_available: bool
    minimum_password_length: int



def _require_setup_access(x_setup_token: str | None = Header(default=None)) -> None:
    """Protect the one-time bootstrap endpoint before any user exists.

    Development retains the historical no-token convenience. Staging and
    production require an explicit token whenever setup is enabled. Returning
    404 while disabled avoids advertising a privileged bootstrap surface.
    """
    settings = get_settings()
    if not settings.setup_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    configured = settings.setup_token.get_secret_value().strip()
    environment = settings.deployment_environment.strip().lower()
    if environment in {"staging", "production"} or configured:
        supplied = (x_setup_token or "").strip()
        if (environment in {"staging", "production"} and len(configured) < 32) or not configured or not supplied or not secrets.compare_digest(configured.encode(), supplied.encode()):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


@router.get("/status", response_model=SetupStatus)
async def get_setup_status(session: AsyncSession = Depends(get_async_session)):
    result = await session.execute(select(func.count(User.id)))
    count = result.scalar() or 0
    settings = get_settings()
    return SetupStatus(
        has_users=count > 0,
        setup_available=bool(settings.setup_enabled and settings.local_auth_enabled and count == 0
                             and not await bootstrap_completed(session)
                             and (settings.deployment_environment.lower() not in {"staging", "production"}
                                  or len(settings.setup_token.get_secret_value().strip()) >= 32)),
        minimum_password_length=minimum_password_length(),
    )


@router.post(
    "/create-admin",
    dependencies=[Depends(require_local_auth_enabled), Depends(_require_setup_access), Depends(login_rate_limit)],
)
async def create_admin(
    body: CreateAdminRequest,
    session: AsyncSession = Depends(get_async_session),
    user_manager: UserManager = Depends(get_user_manager),
):
    try:
        user = await provision_first_admin(session, user_manager, body)
        token = await get_jwt_strategy().write_token(user)
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    log_bootstrap_success(user)
    return {"access_token": token, "token_type": "bearer"}
