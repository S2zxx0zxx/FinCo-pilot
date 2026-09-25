from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.billing.offer_schemas import (
    CampaignAdminRead,
    CampaignAdminUpdate,
    PricingAuditRead,
    ProviderCatalogStatusRead,
    ProviderPlanStatusRead,
)
from app.billing.offer_service import (
    campaign_status,
    get_campaign,
    update_campaign,
)
from app.billing.offers import CAMPAIGN_VERSION, PROVIDER_PLAN_SPECS
from app.billing.razorpay_catalog import (
    configured_provider_plan_id,
    validate_provider_plan,
)
from app.core.auth import current_superuser
from app.core.config import get_settings
from app.core.database import get_async_session
from app.models.pricing_offer import PricingAuditEvent
from app.models.user import User

router = APIRouter(prefix="/api/admin/pricing", tags=["admin-pricing"])


def _razorpay_client():
    try:
        import razorpay  # type: ignore[import-untyped]
    except ImportError as exc:
        raise RuntimeError("Razorpay package is not installed") from exc

    settings = get_settings()
    key_id = settings.razorpay_key_id.strip()
    secret = settings.razorpay_key_secret.get_secret_value().strip()
    if not key_id or not secret:
        raise RuntimeError("Razorpay credentials are not configured")
    return razorpay.Client(auth=(key_id, secret))


async def _campaign_admin_read(session: AsyncSession) -> CampaignAdminRead:
    status = await campaign_status(session)
    row = await get_campaign(session)
    return CampaignAdminRead(
        **status.model_dump(),
        updated_by_user_id=(
            str(row.updated_by_user_id) if row.updated_by_user_id else None
        ),
        updated_at=row.updated_at,
    )


@router.get("/campaign", response_model=CampaignAdminRead)
async def read_campaign(
    session: AsyncSession = Depends(get_async_session),
    _admin: User = Depends(current_superuser),
) -> CampaignAdminRead:
    return await _campaign_admin_read(session)


@router.patch("/campaign", response_model=CampaignAdminRead)
async def patch_campaign(
    data: CampaignAdminUpdate,
    session: AsyncSession = Depends(get_async_session),
    admin: User = Depends(current_superuser),
) -> CampaignAdminRead:
    changes = data.model_dump(
        exclude_unset=True,
        exclude={"expected_version"},
    )
    try:
        await update_campaign(
            session,
            actor_user_id=admin.id,
            expected_version=data.expected_version,
            changes=changes,
        )
        await session.commit()
    except ValueError as exc:
        await session.rollback()
        message = str(exc)
        status_code = 409 if "changed by another request" in message else 400
        raise HTTPException(status_code=status_code, detail=message) from exc
    return await _campaign_admin_read(session)


@router.get("/provider-catalog", response_model=ProviderCatalogStatusRead)
async def provider_catalog_status(
    _admin: User = Depends(current_superuser),
) -> ProviderCatalogStatusRead:
    configured = [
        (
            spec,
            configured_provider_plan_id(spec.plan, spec.interval),
        )
        for spec in PROVIDER_PLAN_SPECS.values()
    ]
    need_provider = any(provider_id for _, provider_id in configured)
    client = None
    client_error: str | None = None
    if need_provider:
        try:
            client = _razorpay_client()
        except RuntimeError as exc:
            client_error = str(exc)

    results: list[ProviderPlanStatusRead] = []
    for spec, provider_id in configured:
        if provider_id is None:
            results.append(
                ProviderPlanStatusRead(
                    plan=spec.plan,
                    interval=spec.interval,
                    configured=False,
                )
            )
            continue
        if client is None:
            results.append(
                ProviderPlanStatusRead(
                    plan=spec.plan,
                    interval=spec.interval,
                    configured=True,
                    provider_plan_id=provider_id,
                    valid=False,
                    errors=[client_error or "Payment provider is unavailable"],
                )
            )
            continue

        try:
            fetched = client.plan.fetch(provider_id)
        except Exception as exc:
            results.append(
                ProviderPlanStatusRead(
                    plan=spec.plan,
                    interval=spec.interval,
                    configured=True,
                    provider_plan_id=provider_id,
                    valid=False,
                    errors=[f"provider fetch failed ({type(exc).__name__})"],
                )
            )
            continue

        if not isinstance(fetched, dict):
            results.append(
                ProviderPlanStatusRead(
                    plan=spec.plan,
                    interval=spec.interval,
                    configured=True,
                    provider_plan_id=provider_id,
                    valid=False,
                    errors=["provider returned an unexpected plan response"],
                )
            )
            continue

        validation = validate_provider_plan(
            spec=spec,
            provider_plan_id=provider_id,
            provider_plan=fetched,
        )
        results.append(
            ProviderPlanStatusRead(
                plan=spec.plan,
                interval=spec.interval,
                configured=True,
                provider_plan_id=provider_id,
                valid=validation.valid,
                errors=list(validation.errors),
            )
        )

    return ProviderCatalogStatusRead(
        catalog_version=CAMPAIGN_VERSION,
        plans=results,
    )


@router.get("/audit", response_model=list[PricingAuditRead])
async def pricing_audit(
    limit: int = Query(100, ge=1, le=500),
    session: AsyncSession = Depends(get_async_session),
    _admin: User = Depends(current_superuser),
) -> list[PricingAuditRead]:
    rows = (
        await session.execute(
            select(PricingAuditEvent)
            .order_by(PricingAuditEvent.created_at.desc())
            .limit(limit)
        )
    ).scalars()
    return [
        PricingAuditRead(
            id=str(row.id),
            actor_user_id=str(row.actor_user_id) if row.actor_user_id else None,
            event_type=row.event_type,
            entity_type=row.entity_type,
            entity_id=row.entity_id,
            payload=row.payload,
            created_at=row.created_at,
        )
        for row in rows
    ]
