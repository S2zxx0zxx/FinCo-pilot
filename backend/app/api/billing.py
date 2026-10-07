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


class CancellationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    authorize: StrictBool


@router.get("/cancellation")
async def cancellation_status(user: User = Depends(current_active_user), session: AsyncSession = Depends(get_async_session)):
    from app.billing.cancellation import preview
    return await preview(session, user.id)


@router.post("/cancellation")
async def cancellation_request(body: CancellationRequest, user: User = Depends(current_active_user), session: AsyncSession = Depends(get_async_session)):
    from fastapi import HTTPException
    from app.billing.cancellation import cancel, enabled
    if body.authorize is not True:
        raise HTTPException(422, "Explicit cancellation consent is required.")
    if not enabled():
        raise HTTPException(503, "Cancellation is disabled.")
    from app.api.checkout import _get_razorpay_client
    client = _get_razorpay_client()
    try:
        return await cancel(session, user.id, client)
    finally:
        client.session.close()


@router.get("/refunds")
async def refund_status(user: User = Depends(current_active_user), session: AsyncSession = Depends(get_async_session)):
    from app.billing.refunds import preview
    return await preview(session, user.id)


from typing import Literal  # noqa: E402
import uuid  # noqa: E402
from app.core.auth import current_superuser  # noqa: E402
from app.api.account_deletion import require_fresh  # noqa: E402


class RefundDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_kind: Literal["activation", "renewal"]
    source_id: uuid.UUID
    amount_minor: StrictInt = Field(ge=100, le=2147483647)
    evidence_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    authorize: StrictBool


@router.post("/refunds/operator", dependencies=[Depends(require_fresh)])
async def issue_refund(body: RefundDecision, user: User = Depends(current_superuser), session: AsyncSession = Depends(get_async_session)):
    from fastapi import HTTPException
    from sqlalchemy.exc import SQLAlchemyError
    from app.core.auth import get_jwt_strategy
    from app.billing.refunds import dispatch, enabled
    from app.billing.activation import RetryReceipt, RejectReceipt
    if body.authorize is not True:
        raise HTTPException(422, "Explicit reviewed refund authorization is required.")
    if not enabled():
        raise HTTPException(503, "Refunds are disabled.")
    from app.api.checkout import _get_razorpay_client
    client = _get_razorpay_client()
    try:
        return await dispatch(session, user.id, body.source_kind, body.source_id, body.amount_minor,
            body.evidence_sha256, client, credential_stamp=get_jwt_strategy().stamp(user))
    except (RetryReceipt, RejectReceipt):
        raise HTTPException(502, "Refund evidence cannot be verified. Reconcile before continuing.") from None
    except SQLAlchemyError:
        await session.rollback()
        raise HTTPException(503, "Refund requires reconciliation. Check the existing decision before continuing.") from None
    finally:
        client.session.close()


@router.get("/refunds/operator/payments", dependencies=[Depends(require_fresh)])
async def refundable_payments(user: User = Depends(current_superuser), session: AsyncSession = Depends(get_async_session)):
    from sqlalchemy import select
    from app.billing.refunds import enabled
    from app.models.payment_activation import PaymentActivation
    from app.models.payment_renewal import RenewalCycle
    if not enabled():
        return {"available": False, "payments": []}
    rows = []
    for kind, model in (("activation", PaymentActivation), ("renewal", RenewalCycle)):
        records = (await session.scalars(select(model).where(model.mode == "test", model.account_id == get_settings().razorpay_webhook_account_id)
            .order_by(model.applied_at.desc()).limit(100))).all()
        rows.extend({"source_kind": kind, "source_id": str(item.id), "user_id": str(item.user_id),
            "amount_minor": item.amount_minor, "currency": item.currency,
            "period_end": item.period_end} for item in records)
    return {"available": True, "payments": rows}
