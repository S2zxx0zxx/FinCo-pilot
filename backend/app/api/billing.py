from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.billing.pricing import PRICE_CATALOG, pro_annual_saving_minor
from app.billing.schemas import EntitlementsRead, PriceOptionRead, PricingCatalogRead
from app.billing.service import get_entitlements
from app.core.auth import current_active_user
from app.core.database import get_async_session
from app.models.user import User

router = APIRouter(prefix="/api/billing", tags=["billing"])


@router.get("/catalog", response_model=PricingCatalogRead)
async def pricing_catalog() -> PricingCatalogRead:
    """Public, non-checkout pricing metadata used by the Pricing page.

    This endpoint is intentionally read-only. It cannot activate a plan.
    """
    prices = [
        PriceOptionRead(
            plan=option.plan,
            interval=option.interval,
            amount_minor=option.amount_minor,
            currency=option.currency,
        )
        for option in PRICE_CATALOG.values()
    ]
    return PricingCatalogRead(
        prices=prices,
        pro_annual_saving_minor=pro_annual_saving_minor(),
    )


@router.get("/entitlements", response_model=EntitlementsRead)
async def current_entitlements(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> EntitlementsRead:
    """Server-authoritative plan/capability view for the signed-in user."""
    return await get_entitlements(session, user.id)
