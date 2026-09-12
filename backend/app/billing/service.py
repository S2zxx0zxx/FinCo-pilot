import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.billing.catalog import PLAN_CATALOG, get_plan_spec
from app.billing.enums import BillingInterval, Capability, PlanId, SubscriptionStatus
from app.billing.schemas import EntitlementsRead
from app.models.subscription import Subscription


_PAID_STATUSES = {
    SubscriptionStatus.ACTIVE,
    SubscriptionStatus.GRACE,
    SubscriptionStatus.CANCELED,
}


def _safe_plan(value: str) -> PlanId:
    try:
        return PlanId(value)
    except ValueError:
        return PlanId.FREE


def _safe_status(value: str) -> SubscriptionStatus:
    try:
        return SubscriptionStatus(value)
    except ValueError:
        return SubscriptionStatus.FREE


def _safe_interval(value: str) -> BillingInterval:
    try:
        return BillingInterval(value)
    except ValueError:
        return BillingInterval.NONE


def effective_plan(subscription: Subscription | None, *, now: datetime | None = None) -> PlanId:
    """Return the plan that may actually authorize paid capabilities.

    A missing/invalid row is always Free. A canceled paid subscription remains
    effective only through its paid period. `past_due` is deliberately not
    treated as paid here; payment-provider grace timing is a later billing
    integration decision, while the explicit `grace` state already models a
    provider-approved grace window.
    """
    if subscription is None:
        return PlanId.FREE

    status = _safe_status(subscription.status)
    plan = _safe_plan(subscription.plan)
    if plan is PlanId.FREE or status not in _PAID_STATUSES:
        return PlanId.FREE

    if status is SubscriptionStatus.CANCELED:
        current = now or datetime.now(timezone.utc)
        if subscription.current_period_end is None or subscription.current_period_end <= current:
            return PlanId.FREE

    return plan


async def get_subscription(session: AsyncSession, user_id: uuid.UUID) -> Subscription | None:
    result = await session.execute(select(Subscription).where(Subscription.user_id == user_id))
    return result.scalar_one_or_none()


async def ensure_free_subscription(session: AsyncSession, user_id: uuid.UUID) -> Subscription:
    """Create the server-owned Free billing row for a newly-created user.

    Registration/bootstrap paths call this inside their existing user/workspace
    transaction. Legacy users are backfilled by migration 091. Normal clients
    never call a plan-mutation endpoint.
    """
    existing = await get_subscription(session, user_id)
    if existing is not None:
        return existing

    subscription = Subscription(
        user_id=user_id,
        plan=PlanId.FREE.value,
        status=SubscriptionStatus.FREE.value,
        billing_interval=BillingInterval.NONE.value,
    )
    session.add(subscription)
    await session.flush()
    return subscription


async def get_effective_plan(session: AsyncSession, user_id: uuid.UUID) -> PlanId:
    return effective_plan(await get_subscription(session, user_id))


async def get_entitlements(session: AsyncSession, user_id: uuid.UUID) -> EntitlementsRead:
    subscription = await get_subscription(session, user_id)
    plan = effective_plan(subscription)
    spec = get_plan_spec(plan)

    if subscription is None:
        status = SubscriptionStatus.FREE
        interval = BillingInterval.NONE
        period_end = None
        cancel_at_period_end = False
    else:
        status = _safe_status(subscription.status)
        interval = _safe_interval(subscription.billing_interval)
        period_end = subscription.current_period_end
        cancel_at_period_end = subscription.cancel_at_period_end

    return EntitlementsRead(
        plan=plan,
        status=status,
        billing_interval=interval,
        current_period_end=period_end,
        cancel_at_period_end=cancel_at_period_end,
        capabilities={cap.value: spec.has(cap) for cap in Capability},
        limits={metric.value: int(limit) for metric, limit in spec.limits.items()},
        # Phase B wires server-owned live counters. Keeping this partial is
        # intentional: clients must never infer zero for absent metrics.
        usage={},
        resets_at={"imports_monthly": None, "ai_actions_monthly": None},
    )


def minimum_plan_for_capability(capability: Capability) -> PlanId:
    for plan in (PlanId.FREE, PlanId.PRO, PlanId.MAX):
        if PLAN_CATALOG[plan].has(capability):
            return plan
    return PlanId.MAX
