import logging
import secrets
import uuid
from decimal import Decimal
from typing import Any, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi_users.password import PasswordHelper
from pydantic import BaseModel, EmailStr, TypeAdapter, ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.core.auth import get_jwt_strategy
from app.core.clerk_sessions import ClerkTokenError, verify_clerk_session_auto
from app.core.config import get_settings
from app.core.database import get_async_session
from app.models.account import Account
from app.models.external_auth_identity import ExternalAuthIdentity
from app.models.user import User
from app.services import admin_service
from app.services.category_service import create_default_categories
from app.services.rule_service import create_default_rules
from app.services.workspace_service import create_personal_workspace_for_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth/clerk", tags=["clerk_auth"])


class ClerkConfigResponse(BaseModel):
    enabled: bool
    publishable_key: str


class ClerkExchangePayload(BaseModel):
    token: str
    email: Optional[EmailStr] = None
    preferences: Optional[dict[str, Any]] = None


class ClerkExchangeResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict[str, Any]


@router.get("/config", response_model=ClerkConfigResponse)
async def get_clerk_config():
    """Return Clerk public availability and publishable key for client initialization."""
    settings = get_settings()
    return ClerkConfigResponse(
        enabled=settings.clerk_auth_available,
        publishable_key=settings.clerk_publishable_key,
    )


async def _fetch_verified_email_from_clerk(user_id: str, secret_key: str) -> Optional[str]:
    """Query Clerk's Backend API to get the authoritative primary email address."""
    url = f"https://api.clerk.com/v1/users/{user_id}"
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=False) as client:
            resp = await client.get(url, headers={"Authorization": f"Bearer {secret_key}"})
            if resp.status_code != 200:
                return None
            data = resp.json()
            if not isinstance(data, dict) or data.get("id") != user_id:
                return None
            primary_id = data.get("primary_email_address_id")
            emails = data.get("email_addresses")
            if not primary_id or not isinstance(emails, list):
                return None
            for item in emails:
                if not isinstance(item, dict) or item.get("id") != primary_id:
                    continue
                verification = item.get("verification")
                if not isinstance(verification, dict) or verification.get("status") != "verified":
                    return None
                return str(TypeAdapter(EmailStr).validate_python(item.get("email_address")))
    except (httpx.HTTPError, ValueError, TypeError, ValidationError):
        logger.warning("Clerk verified email lookup unavailable")
    return None


async def _verify_active_clerk_session(session_id: str, user_id: str, secret_key: str) -> bool:
    """Check provider revocation and subject before exchanging into a local token."""
    if not secret_key:
        return False
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=False) as client:
            response = await client.get(
                f"https://api.clerk.com/v1/sessions/{session_id}",
                headers={"Authorization": f"Bearer {secret_key}"},
            )
            if response.status_code != 200:
                return False
            data = response.json()
            return bool(isinstance(data, dict) and data.get("id") == session_id
                        and data.get("user_id") == user_id and data.get("status") == "active")
    except (httpx.HTTPError, ValueError, TypeError):
        logger.warning("Clerk active session lookup unavailable")
        return False


@router.post("/exchange", response_model=ClerkExchangeResponse)
async def exchange_clerk_session(
    payload: ClerkExchangePayload,
    session: AsyncSession = Depends(get_async_session),
):
    """Exchange a verified Clerk session JWT for a FinCo-Pilot revocable access token.

    Verifies the RS256 token signature, issuer, and claims, links or provisions
    the user record, and issues an internal JWT bound to local session management.
    """
    settings = get_settings()
    if not settings.clerk_auth_available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Clerk authentication is not configured on this server",
        )

    # 1. Verify Clerk session token cryptographically
    try:
        verified = await verify_clerk_session_auto(payload.token)
    except ClerkTokenError as exc:
        logger.warning("Clerk session token verification failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired Clerk session token",
        ) from exc

    secret_key = settings.clerk_secret_key.get_secret_value().strip()
    if not await _verify_active_clerk_session(verified.session_id, verified.user_id, secret_key):
        raise HTTPException(401, "Clerk session is inactive or cannot be verified")

    # 3. Check existing ExternalAuthIdentity mapping
    stmt = select(ExternalAuthIdentity).where(
        ExternalAuthIdentity.provider == "clerk",
        ExternalAuthIdentity.issuer == verified.issuer,
        ExternalAuthIdentity.provider_subject == verified.user_id,
    )
    res = await session.execute(stmt)
    ident = res.scalar_one_or_none()

    user: Optional[User] = None
    if ident is not None:
        user = await session.get(User, ident.user_id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Mapped user account no longer exists",
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is deactivated",
            )
    else:
        # Client-supplied email is only a UI hint, never proof of ownership.
        email = await _fetch_verified_email_from_clerk(verified.user_id, secret_key) if secret_key else None
        if not email:
            raise HTTPException(403, "A verified primary Clerk email is required")

        existing_res = await session.execute(
            select(User).where(func.lower(User.email) == email.lower())
        )
        existing_user = existing_res.scalar_one_or_none()

        if existing_user is not None:
            # Legacy financial identities require an independently proved mapping.
            # Matching even a verified email cannot grant access to an existing UUID.
            raise HTTPException(403, "Existing account requires an approved identity mapping")
        else:
            # Brand new user -> verify registration policy, then provision
            if not await admin_service.is_registration_enabled(session):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Registration is currently disabled",
                )

            prefs = payload.preferences or {}
            currency = str(prefs.get("currency_display") or settings.default_currency)
            lang = str(prefs.get("language") or "en")

            user = User(
                id=uuid.uuid4(),
                email=email.lower(),
                hashed_password=PasswordHelper().hash(secrets.token_urlsafe(32)),
                is_active=True,
                is_verified=True,
                is_superuser=False,
                preferences={
                    "language": lang,
                    "date_format": "MM/DD/YYYY",
                    "timezone": "UTC",
                    "currency_display": currency,
                    "auth_provider": "clerk",
                },
                oidc_issuer=verified.issuer,
                oidc_subject=verified.user_id,
            )
            try:
                session.add(user)
                await session.flush()

                ident = ExternalAuthIdentity(
                    provider="clerk",
                    issuer=verified.issuer,
                    provider_subject=verified.user_id,
                    user_id=user.id,
                )
                session.add(ident)

                # Provision personal workspace, initial wallet, default categories and rules
                workspace = await create_personal_workspace_for_user(session, user)
                wallet_name = "Carteira" if lang.startswith("pt") else "Wallet"
                wallet = Account(
                    user_id=user.id,
                    workspace_id=workspace.id,
                    name=wallet_name,
                    type="checking",
                    balance=Decimal("0.00"),
                    currency=currency,
                )
                session.add(wallet)
                await create_default_categories(session, user.id, lang, workspace_id=workspace.id, commit=False)
                await create_default_rules(session, user.id, lang, workspace_id=workspace.id, commit=False)
                await session.commit()
                await session.refresh(user)
            except IntegrityError as exc:
                await session.rollback()
                raise HTTPException(409, "Account creation conflicted; please sign in again") from exc
            except Exception:
                await session.rollback()
                raise

    # 4. Issue standard FinCo-Pilot revocable JWT
    strategy = get_jwt_strategy()
    access_token = await strategy.write_token(user, fresh_auth=False)

    return ClerkExchangeResponse(
        access_token=access_token,
        token_type="bearer",
        user={
            "id": str(user.id),
            "email": user.email,
            "is_active": user.is_active,
            "is_superuser": user.is_superuser,
            "is_verified": user.is_verified,
            "preferences": user.preferences,
        },
    )
