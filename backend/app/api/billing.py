from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.billing.offer_schemas import FounderCampaignStatusRead
from app.billing.offer_service import campaign_status
from app.billing.pricing import PRICE_CATALOG, pro_annual_saving_minor
from app.billing.schemas import EntitlementsRead, PriceOptionRead, PricingCatalogRead
from app.core.config import get_settings
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
        tax_display_mode=get_settings().billing_tax_display_mode,
    )


@router.get("/founder-campaign", response_model=FounderCampaignStatusRead)
async def founder_campaign(
    session: AsyncSession = Depends(get_async_session),
) -> FounderCampaignStatusRead:
    """Public read-only founder campaign state backed by real server records."""
    return await campaign_status(session)


@router.get("/entitlements", response_model=EntitlementsRead)
async def current_entitlements(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> EntitlementsRead:
    """Server-authoritative plan/capability view for the signed-in user."""
    return await get_entitlements(session, user.id)


from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt  # noqa: E402


class RenewalEnrollment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    total_count: StrictInt = Field(ge=1, le=120)
    authorize: StrictBool


@router.get("/renewal")
async def renewal_status(user: User = Depends(current_active_user), session: AsyncSession = Depends(get_async_session)):
    from app.billing.renewal_mandates import preview
    return await preview(session, user.id)


@router.post("/renewal")
async def renewal_enrollment(body: RenewalEnrollment, user: User = Depends(current_active_user), session: AsyncSession = Depends(get_async_session)):
    from fastapi import HTTPException
    from app.billing.renewal_mandates import create_mandate, enabled
    if body.authorize is not True:
        raise HTTPException(422, "Explicit finite renewal enrollment is required.")
    if not enabled():
        raise HTTPException(503, "Renewal enrollment is disabled.")
    from app.api.checkout import _get_razorpay_client
    client = _get_razorpay_client()
    try:
        return await create_mandate(session, user.id, body.total_count, client)
    finally:
        client.session.close()
