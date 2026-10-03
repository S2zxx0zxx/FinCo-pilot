from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import current_active_user
from app.core.config import get_settings
from app.core.database import get_async_session
from app.models.fx_rate import FxRate
from app.providers.openexchangerates import FxProviderError
from app.models.user import User
from app.services.fx_rate_service import sync_rates

router = APIRouter(prefix="/api/fx-rates", tags=["fx-rates"])


@router.post("/refresh")
async def refresh_rates(
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
):
    """Trigger immediate FX rate sync."""
    today = datetime.now(timezone.utc).date()
    try:
        count = await sync_rates(session, today)
    except FxProviderError:
        raise HTTPException(status_code=503, detail="FX provider unavailable") from None
    published_date = await session.scalar(select(func.max(FxRate.date)).where(FxRate.date <= today))
    return {"synced": count > 0, "rates_count": count, "date": today.isoformat(),
            "publication_date": published_date.isoformat() if published_date else None}


@router.get("/status")
async def rates_status(
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
):
    """Return last sync date and total stored rates."""
    last_date = await session.scalar(
        select(func.max(FxRate.date))
    )
    total = await session.scalar(
        select(func.count()).select_from(FxRate)
    ) or 0

    settings = get_settings()
    return {
        "last_sync_date": last_date.isoformat() if last_date else None,
        "total_rates": total,
        "fx_sync_mode": settings.fx_sync_mode,
    }
