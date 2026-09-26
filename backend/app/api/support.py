from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import current_active_user
from app.core.config import get_settings
from app.core.database import get_async_session
from app.models.user import User
from app.schemas.support import (
    SupportCategory,
    SupportPublicInfo,
    SupportTicketCreate,
    SupportTicketRead,
)
from app.services.support_service import create_support_ticket

router = APIRouter(prefix="/api/support", tags=["support"])


def public_support_info() -> SupportPublicInfo:
    settings = get_settings()
    return SupportPublicInfo(
        enabled=settings.support_contact_available,
        email=settings.support_email.strip() or None,
        portal_url=settings.support_portal_url.strip() or None,
        help_center_url=settings.support_help_center_url.strip() or None,
        security_url=settings.support_security_url.strip() or None,
        direct_ticket_submission=settings.support_ticket_submission_available,
        categories=[category.value for category in SupportCategory],
    )


@router.get("/info", response_model=SupportPublicInfo)
async def get_support_info() -> SupportPublicInfo:
    """Public non-secret support destinations for logged-out and logged-in users."""
    return public_support_info()


@router.post(
    "/tickets",
    response_model=SupportTicketRead,
    status_code=status.HTTP_201_CREATED,
)
async def submit_support_ticket(
    body: SupportTicketCreate,
    request: Request,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> SupportTicketRead:
    """Create a helpdesk ticket for an authenticated user.

    The server supplies identity/plan data. The client can only contribute
    bounded diagnostic hints; no financial records or credentials are
    automatically attached.
    """
    created = await create_support_ticket(
        session=session,
        user=user,
        ticket=body,
        request_reference=getattr(request.state, "request_id", "unavailable"),
        user_agent=request.headers.get("user-agent", ""),
    )
    return SupportTicketRead(
        reference=created.reference,
        ticket_id=created.ticket_id,
        ticket_number=created.ticket_number,
        support_tier=created.support_tier,
        priority=created.priority,
    )
