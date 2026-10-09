"""Read-only Clerk → existing FinCo-Pilot identity bridge.

Disabled by default. No just-in-time user creation or email-based account linking.
Existing FastAPI Users auth, its session cookies/tokens and all domain routes
remain unchanged. This endpoint is for authenticated integration tests only.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clerk_sessions import ClerkTokenError, verify_clerk_session
from app.core.config import get_settings
from app.core.database import get_async_session
from app.models.account_deletion import AccountDeletion
from app.models.external_auth_identity import ExternalAuthIdentity
from app.models.user import User
from app.schemas.user import UserRead

router = APIRouter(prefix="/api/auth/clerk", tags=["auth"])

DELETION_LOCKED_STATES = (
    "executing", "external_retry", "primary_data_deleted",
    "backup_expiry_pending", "complete",
)


async def current_linked_clerk_user(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
) -> User:
    settings = get_settings()
    if not settings.clerk_bridge_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    authorization = request.headers.get("authorization", "")
    parts = authorization.split(" ", 1)
    if (len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1]
            or len(parts[1]) > 8192 or any(ch.isspace() for ch in parts[1])):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    try:
        clerk = verify_clerk_session(
            parts[1],
            issuer=settings.clerk_issuer,
            public_key_pem=settings.clerk_jwt_public_key,
            authorized_parties=tuple(
                party.strip() for party in settings.clerk_authorized_parties.split(",")
                if party.strip()
            ),
            audience=settings.clerk_audience or None,
        )
    except ClerkTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized") from None

    user = await session.scalar(
        select(User)
        .join(ExternalAuthIdentity, ExternalAuthIdentity.user_id == User.id)
        .where(
            ExternalAuthIdentity.provider == "clerk",
            ExternalAuthIdentity.issuer == clerk.issuer,
            ExternalAuthIdentity.provider_subject == clerk.user_id,
            User.is_active.is_(True),
        )
    )
    if user is None:
        # Never authenticate based on equal emails or untrusted token metadata.
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    locked = await session.scalar(
        select(AccountDeletion.id).where(
            AccountDeletion.user_id == user.id,
            AccountDeletion.state.in_(DELETION_LOCKED_STATES),
        ).limit(1)
    )
    if locked is not None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    return user


@router.get("/me", response_model=UserRead)
async def clerk_me(user: User = Depends(current_linked_clerk_user)) -> User:
    """Read-only probe: confirms Clerk identity maps to existing internal UUID."""
    return user
