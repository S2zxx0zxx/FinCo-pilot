import logging
import hashlib
import hmac

import jwt
from fastapi_users import exceptions
from fastapi_users.jwt import decode_jwt, generate_jwt
import uuid
from decimal import Decimal
from typing import Optional

from fastapi import Depends, Request
from fastapi_users import BaseUserManager, FastAPIUsers, UUIDIDMixin, schemas
from fastapi_users.authentication import (
    AuthenticationBackend,
    BearerTransport,
    JWTStrategy,
)
from fastapi_users.db import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_policy import require_local_auth_enabled
from app.core.config import get_settings
from app.core.database import get_async_session
from app.models.user import User
from app.services.email_service import (
    send_password_reset_email,
    send_verification_email,
)

logger = logging.getLogger(__name__)
settings = get_settings()


async def get_user_db(session: AsyncSession = Depends(get_async_session)):
    yield SQLAlchemyUserDatabase(session, User)


class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    user_db: SQLAlchemyUserDatabase
    reset_password_token_secret = settings.secret_key
    verification_token_secret = settings.secret_key

    async def validate_password(self, password: str, user) -> None:
        if len(password) < 8 or len(password) > 128:
            raise exceptions.InvalidPasswordException(reason="Password must contain 8 to 128 characters")

    async def update(
        self,
        user_update: schemas.BaseUserUpdate,
        user: User,
        safe: bool = False,
        request: Request | None = None,
    ) -> User:
        if user_update.password is not None:
            require_local_auth_enabled()
        return await super().update(user_update, user, safe=safe, request=request)

    async def on_after_register(self, user: User, request: Optional[Request] = None):
        logger.info("Registered user %s", user.id)
        # If request is None, this was called programmatically (e.g. setup)
        # which handles wallet/category/workspace creation itself.
        if request is None:
            return

        from app.models.account import Account
        from app.services.category_service import create_default_categories
        from app.services.rule_service import create_default_rules
        from app.services.workspace_service import create_personal_workspace_for_user

        session = self.user_db.session
        currency = user.primary_currency
        lang = (user.preferences or {}).get("language", "en")
        workspace = await create_personal_workspace_for_user(session, user)

        wallet_name = "Carteira" if lang.startswith("pt") else "Wallet"
        session.add(
            Account(
                user_id=user.id,
                workspace_id=workspace.id,
                name=wallet_name,
                type="checking",
                balance=Decimal("0.00"),
                currency=currency,
            )
        )
        await session.commit()
        await create_default_categories(session, user.id, lang, workspace_id=workspace.id)
        await create_default_rules(session, user.id, lang, workspace_id=workspace.id)

    async def on_after_forgot_password(
        self,
        user: User,
        token: str,
        request: Optional[Request] = None,
    ) -> None:
        # Never log reset tokens or the user's email address. Delivery failures
        # propagate only when production explicitly requires transactional mail.
        await send_password_reset_email(user.email, token)
        logger.info("Password reset email processed for user %s", user.id)

    async def on_after_request_verify(
        self,
        user: User,
        token: str,
        request: Optional[Request] = None,
    ) -> None:
        await send_verification_email(user.email, token)
        logger.info("Verification email processed for user %s", user.id)


async def get_user_manager(user_db: SQLAlchemyUserDatabase = Depends(get_user_db)):
    yield UserManager(user_db)


bearer_transport = BearerTransport(tokenUrl="api/auth/login")


class RevocableJWTStrategy(JWTStrategy):
    """Credentials-bound tokens; password/reset and logout invalidate old sessions.

    Legacy tokens without the credential stamp deliberately require re-login.
    The password hash is never put in a JWT, even in encoded form.
    """

    def stamp(self, user: User) -> str:
        value = f"{user.id}:{user.hashed_password}:{user.auth_epoch or ''}"
        return hmac.new(settings.secret_key.get_secret_value().encode(), value.encode(), hashlib.sha256).hexdigest()

    async def write_token(self, user: User) -> str:
        return generate_jwt(
            {"sub": str(user.id), "aud": self.token_audience, "credential_stamp": self.stamp(user)},
            self.encode_key, self.lifetime_seconds, algorithm=self.algorithm,
        )

    async def read_token(self, token, user_manager):
        user = await super().read_token(token, user_manager)
        if user is None or token is None:
            return None
        try:
            data = decode_jwt(token, self.decode_key, self.token_audience, algorithms=[self.algorithm])
        except jwt.PyJWTError:
            return None
        if isinstance(user_manager, UserManager):
            # Read current credential state even when a session identity map was
            # populated before a concurrent password change or logout.
            await user_manager.user_db.session.refresh(user, attribute_names=["hashed_password", "auth_epoch", "is_active"])
        stamp = data.get("credential_stamp")
        return user if isinstance(stamp, str) and hmac.compare_digest(stamp, self.stamp(user)) else None


def get_jwt_strategy() -> RevocableJWTStrategy:
    return RevocableJWTStrategy(
        secret=settings.secret_key.get_secret_value(),
        lifetime_seconds=settings.access_token_expire_minutes * 60,
    )


auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)

fastapi_users = FastAPIUsers[User, uuid.UUID](get_user_manager, [auth_backend])

current_active_user = fastapi_users.current_user(active=True)
current_superuser = fastapi_users.current_user(active=True, superuser=True)
