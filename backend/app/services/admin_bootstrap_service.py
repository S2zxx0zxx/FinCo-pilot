"""One-time first-admin provisioning; caller owns the transaction commit."""
import json
import logging
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException
from fastapi_users import schemas
from pydantic import BaseModel, EmailStr, Field, SecretStr, field_validator
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import UserManager
from app.core.config import get_settings
from app.models.account import Account
from app.models.app_settings import AppSetting
from app.models.user import User

logger = logging.getLogger(__name__)
BOOTSTRAP_RECORD_KEY = "security.first_admin_bootstrap.v1"


class CreateAdminRequest(BaseModel):
    email: EmailStr
    password: SecretStr
    currency: str = "INR"
    name: str = Field(default="", max_length=120)
    language: str = Field(default="pt-BR", min_length=2, max_length=20)

    @field_validator("currency")
    @classmethod
    def supported_currency(cls, value: str) -> str:
        code = value.strip().upper()
        if code not in get_settings().supported_currencies.split(","):
            raise ValueError("Unsupported currency")
        return code


def minimum_password_length() -> int:
    return 15 if get_settings().deployment_environment.lower() in {"staging", "production"} else 8


async def bootstrap_completed(session: AsyncSession) -> bool:
    return await session.get(AppSetting, BOOTSTRAP_RECORD_KEY) is not None


async def provision_first_admin(session: AsyncSession, manager: UserManager, body: CreateAdminRequest) -> User:
    """Flush complete provisioning and audit record, without intermediate commits.

    The fixed primary key serializes competing claims across processes. A loser
    waits for the winning transaction; rollback allows a clean retry. A committed
    record permanently closes setup even if users are later removed/restored.
    """
    if await bootstrap_completed(session) or await session.scalar(select(func.count(User.id))):
        raise HTTPException(status_code=403, detail="Setup already completed")
    password = body.password.get_secret_value()
    minimum = minimum_password_length()
    if not minimum <= len(password) <= 128:
        raise HTTPException(status_code=400, detail=f"Admin password must contain {minimum} to 128 characters")
    await manager.validate_password(password, schemas.BaseUserCreate(email=body.email, password=password))

    record = AppSetting(key=BOOTSTRAP_RECORD_KEY, value="pending")
    session.add(record)
    try:
        await session.flush()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=403, detail="Setup already completed") from None
    # Recheck after acquiring the unique claim; never promote an existing user.
    if await session.scalar(select(func.count(User.id))):
        raise HTTPException(status_code=403, detail="Setup already completed")
    preferences = {"currency_display": body.currency, "language": body.language, "onboarding_completed": False}
    if body.name:
        preferences["display_name"] = body.name
    user = User(email=str(body.email), hashed_password=manager.password_helper.hash(password),
                is_active=True, is_superuser=True, is_verified=False, preferences=preferences)
    session.add(user)
    await session.flush()

    from app.services.category_service import create_default_categories
    from app.services.rule_service import create_default_rules
    from app.services.workspace_service import create_personal_workspace_for_user

    workspace = await create_personal_workspace_for_user(session, user)
    session.add(Account(user_id=user.id, workspace_id=workspace.id,
                        name="Carteira" if body.language.startswith("pt") else "Wallet",
                        type="checking", balance=Decimal("0.00"), currency=body.currency))
    await create_default_categories(session, user.id, body.language, workspace_id=workspace.id, commit=False)
    await create_default_rules(session, user.id, body.language, workspace_id=workspace.id, commit=False)
    record.value = json.dumps({"event": "first_admin_bootstrapped", "version": 1,
                               "user_id": str(user.id), "completed_at": datetime.now(timezone.utc).isoformat()})
    await session.flush()
    return user


def log_bootstrap_success(user: User) -> None:
    # Only called after commit: no email, password, token, or false success log.
    logger.info("First admin bootstrap completed user_id=%s", user.id)
