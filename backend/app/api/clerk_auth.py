import logging
import secrets
import uuid
from decimal import Decimal
from typing import Any, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

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
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, headers={"Authorization": f"Bearer {secret_key}"})
            if resp.status_code != 200:
                logger.warning("Clerk API returned %s for user %s", resp.status_code, user_id)
                return None
            data = resp.json()
            primary_id = data.get("primary_email_address_id")
            for item in data.get("email_addresses", []):
                if item.get("id") == primary_id:
                    return item.get("email_address")
            # Fallback to first verified or first email
            emails = data.get("email_addresses", [])
            if emails:
                return emails[0].get("email_address")
    except Exception as exc:
        logger.exception("Error querying Clerk Backend API: %s", exc)
    return None


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
    if not settings.clerk_auth_available and not settings.clerk_issuer:
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

    # 2. Determine verified email address
    email: Optional[str] = None
    secret_key = settings.clerk_secret_key.get_secret_value()
    if secret_key.strip():
        email = await _fetch_verified_email_from_clerk(verified.user_id, secret_key.strip())

    if not email and payload.email:
        email = str(payload.email)

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
        # Not linked yet. Check if an existing local account has the matching email.
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email address is required for first-time account linking",
            )

        existing_res = await session.execute(
            select(User).where(func.lower(User.email) == email.lower())
        )
        existing_user = existing_res.scalar_one_or_none()

        if existing_user is not None:
            # Link existing local account to this Clerk identity
            ident = ExternalAuthIdentity(
                provider="clerk",
                issuer=verified.issuer,
                provider_subject=verified.user_id,
                user_id=existing_user.id,
            )
            session.add(ident)
            if not existing_user.oidc_issuer:
                existing_user.oidc_issuer = verified.issuer
                existing_user.oidc_subject = verified.user_id
                session.add(existing_user)
            await session.commit()
            await session.refresh(existing_user)
            user = existing_user
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
                hashed_password=secrets.token_urlsafe(32),
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
            await session.commit()

            await create_default_categories(session, user.id, lang, workspace_id=workspace.id)
            await create_default_rules(session, user.id, lang, workspace_id=workspace.id)
            await session.refresh(user)

    # 4. Issue standard FinCo-Pilot revocable JWT
    strategy = get_jwt_strategy()
    access_token = await strategy.write_token(user, fresh_auth=True)

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
