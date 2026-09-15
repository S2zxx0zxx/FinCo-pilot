import secrets
from decimal import Decimal

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import func, select, update as sql_update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import UserManager, get_jwt_strategy, get_user_manager
from app.core.auth_policy import require_local_auth_enabled
from app.core.config import get_settings
from app.core.database import get_async_session
from app.models.account import Account
from app.models.user import User

router = APIRouter(prefix="/api/setup", tags=["setup"])


class SetupStatus(BaseModel):
    has_users: bool
    setup_available: bool


class CreateAdminRequest(BaseModel):
    email: EmailStr
    password: str
    currency: str = "INR"
    name: str = ""
    language: str = "pt-BR"


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
        if not configured or not supplied or not secrets.compare_digest(configured, supplied):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


@router.get("/status", response_model=SetupStatus)
async def get_setup_status(session: AsyncSession = Depends(get_async_session)):
    result = await session.execute(select(func.count(User.id)))
    count = result.scalar() or 0
    settings = get_settings()
    return SetupStatus(
        has_users=count > 0,
        setup_available=bool(settings.setup_enabled and count == 0),
    )


@router.post(
    "/create-admin",
    dependencies=[Depends(require_local_auth_enabled), Depends(_require_setup_access)],
)
async def create_admin(
    body: CreateAdminRequest,
    session: AsyncSession = Depends(get_async_session),
    user_manager: UserManager = Depends(get_user_manager),
):
    # Re-check immediately before creation. Database uniqueness still protects
    # the user row; production should provision exactly once and then disable
    # SETUP_ENABLED so this route disappears from the attack surface.
    result = await session.execute(select(func.count(User.id)))
    count = result.scalar() or 0
    if count > 0:
        raise HTTPException(status_code=403, detail="Setup already completed")

    from fastapi_users import schemas

    user_create = schemas.BaseUserCreate(
        email=body.email,
        password=body.password,
        is_superuser=True,
    )
    user = await user_manager.create(user_create)

    # Build preferences dict
    prefs = {
        "currency_display": body.currency,
        "language": body.language,
        "onboarding_completed": False,
    }
    if body.name:
        prefs["display_name"] = body.name

    # Use direct SQL update to avoid session expiry issues after user_manager.create() commits
    db_session = user_manager.user_db.session
    await db_session.execute(
        sql_update(User).where(User.id == user.id).values(preferences=prefs)
    )

    # Personal workspace gets auto-created here too (setup endpoint runs
    # programmatically, so the registration hook's `request is None` early
    # exit fires; we have to set up the workspace ourselves).
    from app.services.workspace_service import create_personal_workspace_for_user

    await db_session.refresh(user)
    workspace = await create_personal_workspace_for_user(db_session, user)

    # Create default wallet with the chosen currency
    wallet_name = "Carteira" if body.language.startswith("pt") else "Wallet"
    wallet = Account(
        user_id=user.id,
        workspace_id=workspace.id,
        name=wallet_name,
        type="checking",
        balance=Decimal("0.00"),
        currency=body.currency,
    )
    db_session.add(wallet)
    await db_session.commit()

    # Create default categories and rules for the new user
    from app.services.category_service import create_default_categories
    from app.services.rule_service import create_default_rules

    await create_default_categories(db_session, user.id, body.language, workspace_id=workspace.id)
    await create_default_rules(db_session, user.id, body.language, workspace_id=workspace.id)

    # Refresh user to get updated preferences for token generation
    await db_session.refresh(user)

    # Generate access token
    strategy = get_jwt_strategy()
    token = await strategy.write_token(user)

    return {"access_token": token, "token_type": "bearer"}
