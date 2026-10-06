import uuid
from datetime import datetime, timedelta, timezone

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


def _utc(value: datetime | None) -> datetime | None:
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


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
    effective only through its paid period. Razorpay past-due preserves already
    paid coverage. Explicit bounded grace requires a recovery deadline anchored
    to that paid-through boundary; provider retry state cannot grant access.
    """
    if subscription is None:
        return PlanId.FREE

    status = _safe_status(subscription.status)
    plan = _safe_plan(subscription.plan)
    recovery = subscription.provider == "razorpay" and status is SubscriptionStatus.PAST_DUE
    if plan is PlanId.FREE or (status not in _PAID_STATUSES and not recovery):
        return PlanId.FREE

    # Provider grants are finite prepaid terms, including active/grace state.
    if subscription.provider == "razorpay":
        current = now or datetime.now(timezone.utc)
        start, end = _utc(subscription.current_period_start), _utc(subscription.current_period_end)
        if start is None or end is None or end <= start or current < start:
            return PlanId.FREE
        if current >= end:
            due, grace = _utc(subscription.recovery_due_at), _utc(subscription.grace_until)
            if (status is not SubscriptionStatus.GRACE or subscription.cancel_at_period_end
                    or due != end or grace is None or not end < grace <= end + timedelta(hours=72)
                    or current >= grace):
                return PlanId.FREE

    if status is SubscriptionStatus.CANCELED:
        current = now or datetime.now(timezone.utc)
        end = _utc(subscription.current_period_end)
        if end is None or end <= current:
            return PlanId.FREE

    return plan


async def get_subscription(session: AsyncSession, user_id: uuid.UUID) -> Subscription | None:
    result = await session.execute(select(Subscription).where(Subscription.user_id == user_id))
    return result.scalar_one_or_none()


async def ensure_free_subscription(session: AsyncSession, user_id: uuid.UUID) -> Subscription:
    """Ensure a user has a stable server-owned Free billing row.

    This helper never upgrades or downgrades an existing row. It is used by all
    user/workspace bootstrap paths so quota code always has a row it can lock.
    """
    existing = await get_subscription(session, user_id)
    if existing is not None:
        return existing
    subscription = Subscription(user_id=user_id)
    session.add(subscription)
    await session.flush()
    return subscription


async def get_effective_plan(session: AsyncSession, user_id: uuid.UUID) -> PlanId:
    return effective_plan(await get_subscription(session, user_id))


async def get_entitlements(session: AsyncSession, user_id: uuid.UUID) -> EntitlementsRead:
    # Local import prevents a module cycle: usage.py deliberately reuses the
    # pure `effective_plan` function above while this read model includes usage.
    from app.billing.usage import next_month_reset, usage_snapshot

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
        grace = _utc(subscription.grace_until)
        if (subscription.provider == "razorpay" and status is SubscriptionStatus.GRACE
                and subscription.recovery_due_at is not None
                and (grace is None or grace <= datetime.now(timezone.utc))):
            status = SubscriptionStatus.PAST_DUE
        interval = _safe_interval(subscription.billing_interval)
        period_end = subscription.current_period_end
        cancel_at_period_end = subscription.cancel_at_period_end

    reset = next_month_reset()
    return EntitlementsRead(
        plan=plan,
        status=status,
        billing_interval=interval,
        current_period_end=period_end,
        cancel_at_period_end=cancel_at_period_end,
        recovery_due_at=subscription.recovery_due_at if subscription else None,
        grace_until=subscription.grace_until if subscription else None,
        capabilities={cap.value: spec.has(cap) for cap in Capability},
        limits={metric.value: int(limit) for metric, limit in spec.limits.items()},
        usage=await usage_snapshot(session, user_id),
        resets_at={
            "imports_monthly": reset,
            "invoices_monthly": reset,
            "ai_actions_monthly": reset,
        },
    )


def minimum_plan_for_capability(capability: Capability) -> PlanId:
    for plan in (PlanId.FREE, PlanId.PRO, PlanId.MAX):
        if PLAN_CATALOG[plan].has(capability):
            return plan
    return PlanId.MAX
