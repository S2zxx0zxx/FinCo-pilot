import logging
import hashlib
import hmac
import re

import jwt
from pwdlib.exceptions import PwdlibError
from fastapi_users import exceptions
from fastapi_users.jwt import generate_jwt
import uuid
from decimal import Decimal
from typing import Optional

from fastapi import Depends, HTTPException, Request
from fastapi_users import BaseUserManager, FastAPIUsers, UUIDIDMixin, schemas
from fastapi_users.authentication import (
    AuthenticationBackend,
    BearerTransport,
    JWTStrategy,
)
from fastapi_users.db import SQLAlchemyUserDatabase
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import EmailStr, SecretStr, TypeAdapter, ValidationError

from app.core.auth_policy import require_local_auth_enabled
from app.core.config import get_settings
from app.core.database import get_async_session
from app.models.user import User
from app.services.email_service import (
    send_password_reset_email,
    send_password_changed_email,
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

    async def on_before_delete(self, user: User, request: Request | None = None) -> None:
        # The generated /api/users/{id} route bypasses admin_service. Guard at
        # the manager boundary too, before its database adapter removes a row.
        if get_settings().is_production:
            raise HTTPException(status_code=409, detail="Account deletion requires the retention-aware deletion workflow")

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
        background = getattr(request.state, "registration_mail", None)
        if background is not None and not user.is_verified:
            from app.api.password_recovery import queue_account_email
            try:
                await queue_account_email(background, user.email, "verify")
            except HTTPException:
                # Account creation committed. Resend stays available; do not
                # report a failed registration or expose provider details.
                logger.warning("Initial verification request could not be scheduled for user %s", user.id)

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

    async def reset_password(self, token: str, password: str, request: Request | None = None) -> User:
        require_local_auth_enabled()
        try:
            data = jwt.decode(token, self.reset_password_token_secret.get_secret_value()
                              if isinstance(self.reset_password_token_secret, SecretStr)
                              else self.reset_password_token_secret,
                              algorithms=["HS256"], audience=self.reset_password_token_audience,
                              options={"require": ["sub", "aud", "exp", "password_fgpt"]})
            if type(data["exp"]) is not int or not isinstance(data["sub"], str):
                raise ValueError("Invalid reset claims")
            fingerprint = data["password_fgpt"]
            if not isinstance(fingerprint, str) or not 1 <= len(fingerprint) <= 1024:
                raise ValueError("Invalid reset fingerprint")
            identity = self.parse_id(data["sub"])
        except (jwt.PyJWTError, ValueError, TypeError, OverflowError, exceptions.InvalidID):
            raise exceptions.InvalidResetPasswordToken() from None
        # Lock and refresh before the library verifies the password fingerprint.
        # A second PostgreSQL reset waits, then sees the changed password hash.
        user = (await self.user_db.session.scalars(select(User).where(User.id == identity)
                .with_for_update().execution_options(populate_existing=True))).one_or_none()
        if user is None:
            raise exceptions.UserNotExists()
        try:
            valid, _ = self.password_helper.verify_and_update(user.hashed_password, fingerprint)
        except (ValueError, TypeError, PwdlibError):
            raise exceptions.InvalidResetPasswordToken() from None
        if not valid:
            raise exceptions.InvalidResetPasswordToken()
        return await super().reset_password(token, password, request)

    async def on_after_reset_password(self, user: User, request: Request | None = None) -> None:
        try:
            await send_password_changed_email(user.email)
        except Exception:
            # The password commit succeeded; a notification failure must not
            # invite the client to retry an already-consumed reset credential.
            logger.warning("Password change notification could not be completed for user %s", user.id)

    async def verify(self, token: str, request: Request | None = None) -> User:
        require_local_auth_enabled()
        try:
            key = self.verification_token_secret
            data = jwt.decode(token, key.get_secret_value() if isinstance(key, SecretStr) else key,
                              algorithms=["HS256"], audience=self.verification_token_audience,
                              options={"require": ["sub", "aud", "exp", "email"]})
            if type(data["exp"]) is not int or not isinstance(data["sub"], str):
                raise ValueError("Invalid verification claims")
            email = data["email"]
            if not isinstance(email, str) or len(email) > 320:
                raise ValueError("Invalid verification email")
            TypeAdapter(EmailStr).validate_python(email)
            identity = self.parse_id(data["sub"])
        except (jwt.PyJWTError, ValueError, TypeError, OverflowError, ValidationError, exceptions.InvalidID):
            raise exceptions.InvalidVerifyToken() from None
        user = (await self.user_db.session.scalars(select(User).where(User.id == identity)
                .with_for_update().execution_options(populate_existing=True))).one_or_none()
        if user is None or not user.is_active:
            raise exceptions.InvalidVerifyToken()
        # Preserve the installed library's current-email matching contract.
        # It rechecks expiry after the lock and updates only is_verified.
        return await super().verify(token, request)

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
        if token is None:
            return None
        try:
            data = jwt.decode(
                token, self.decode_key.get_secret_value() if isinstance(self.decode_key, SecretStr) else self.decode_key, audience=self.token_audience,
                algorithms=[self.algorithm],
                options={"require": ["sub", "aud", "exp", "credential_stamp"]},
            )
        except (jwt.PyJWTError, ValueError, OverflowError, TypeError):
            return None
        stamp = data.get("credential_stamp")
        expiry = data.get("exp")
        # Reject legacy/malformed stamps before DB lookup; non-ASCII strings
        # otherwise raise from compare_digest instead of producing a safe 401.
        if not isinstance(stamp, str) or re.fullmatch(r"[0-9a-f]{64}", stamp) is None:
            return None
        if isinstance(expiry, bool) or not isinstance(expiry, (int, float)):
            return None
        user = await super().read_token(token, user_manager)
        if user is None:
            return None
        if isinstance(user_manager, UserManager):
            await user_manager.user_db.session.refresh(user, attribute_names=["hashed_password", "auth_epoch", "is_active"])
        return user if user.is_active and hmac.compare_digest(stamp, self.stamp(user)) else None


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
