from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import distinct, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.billing.catalog import PLAN_CATALOG, get_plan_spec
from app.billing.enums import Metric, PlanId
from app.billing.errors import PlanLimitReachedError
from app.billing.service import effective_plan
from app.models.account import Account
from app.models.asset import Asset
from app.models.billing_usage import BillingUsageCounter
from app.models.budget import Budget
from app.models.goal import Goal
from app.models.group import Group, GroupMember
from app.models.invoice_attachment import InvoiceAttachment
from app.models.recurring_transaction import RecurringTransaction
from app.models.rule import Rule
from app.models.subscription import Subscription
from app.models.transaction_attachment import TransactionAttachment
from app.models.workspace import Workspace


MONTHLY_METRICS = {
    Metric.IMPORTS_MONTHLY,
    Metric.INVOICES_MONTHLY,
    Metric.AI_ACTIONS_MONTHLY,
}


def month_bucket(now: datetime | None = None) -> date:
    current = now or datetime.now(timezone.utc)
    return date(current.year, current.month, 1)


def next_month_reset(now: datetime | None = None) -> datetime:
    current = now or datetime.now(timezone.utc)
    if current.month == 12:
        return datetime(current.year + 1, 1, 1, tzinfo=timezone.utc)
    return datetime(current.year, current.month + 1, 1, tzinfo=timezone.utc)


async def ensure_subscription_row(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    for_update: bool = False,
) -> Subscription:
    """Return the owner's billing row, creating a fail-safe Free row if absent.

    Migration 092 backfills existing users and registration creates future rows,
    so the create path is a repair path rather than the normal hot path.
    `FOR UPDATE` is the serialization primitive for all hard quota checks.
    """
    query = select(Subscription).where(Subscription.user_id == user_id)
    if for_update:
        query = query.with_for_update()
    result = await session.execute(query)
    subscription = result.scalar_one_or_none()
    if subscription is not None:
        return subscription

    subscription = Subscription(user_id=user_id)
    session.add(subscription)
    await session.flush()
    if for_update:
        # Newly inserted row is already write-locked by this transaction.
        return subscription
    return subscription


async def _owned_workspace_ids(session: AsyncSession, owner_id: uuid.UUID) -> list[uuid.UUID]:
    result = await session.execute(
        select(Workspace.id).where(
            Workspace.billing_owner_user_id == owner_id,
            Workspace.is_archived.is_(False),
        )
    )
    return list(result.scalars().all())


async def _monthly_usage(
    session: AsyncSession,
    owner_id: uuid.UUID,
    metric: Metric,
) -> int:
    result = await session.execute(
        select(BillingUsageCounter.used).where(
            BillingUsageCounter.user_id == owner_id,
            BillingUsageCounter.metric == metric.value,
            BillingUsageCounter.period_start == month_bucket(),
        )
    )
    return int(result.scalar_one_or_none() or 0)


async def current_usage(
    session: AsyncSession,
    owner_id: uuid.UUID,
    metric: Metric,
    *,
    group_id: uuid.UUID | None = None,
) -> int:
    """Compute server-owned usage for one plan metric.

    Resource quotas are counted across every non-archived workspace owned by
    the billing user. `group_members` is deliberately scoped to one group,
    matching its product meaning (members per group). Monthly counters are
    deletion-proof server counters rather than live row counts.
    """
    if metric in MONTHLY_METRICS:
        return await _monthly_usage(session, owner_id, metric)

    workspace_ids = await _owned_workspace_ids(session, owner_id)

    if metric is Metric.TOTAL_WORKSPACES:
        return len(workspace_ids)
    if metric in {Metric.PERSONAL_WORKSPACES, Metric.BUSINESS_WORKSPACES}:
        kind = "personal" if metric is Metric.PERSONAL_WORKSPACES else "business"
        result = await session.execute(
            select(func.count(Workspace.id)).where(
                Workspace.billing_owner_user_id == owner_id,
                Workspace.is_archived.is_(False),
                Workspace.kind == kind,
            )
        )
        return int(result.scalar() or 0)

    if not workspace_ids:
        return 0

    if metric is Metric.ACCOUNTS:
        query = select(func.count(Account.id)).where(
            Account.workspace_id.in_(workspace_ids), Account.is_closed.is_(False)
        )
    elif metric is Metric.ACTIVE_BUDGETS:
        start = date.today().replace(day=1)
        query = select(func.count(distinct(Budget.category_id))).where(
            Budget.workspace_id.in_(workspace_ids),
            or_(
                (Budget.is_recurring.is_(True) & (Budget.month <= start)),
                (Budget.is_recurring.is_(False) & (Budget.month == start)),
            ),
        )
    elif metric is Metric.ACTIVE_GOALS:
        query = select(func.count(Goal.id)).where(
            Goal.workspace_id.in_(workspace_ids), Goal.status == "active"
        )
    elif metric is Metric.ACTIVE_RECURRING:
        query = select(func.count(RecurringTransaction.id)).where(
            RecurringTransaction.workspace_id.in_(workspace_ids),
            RecurringTransaction.is_active.is_(True),
        )
    elif metric is Metric.ASSETS:
        query = select(func.count(Asset.id)).where(
            Asset.workspace_id.in_(workspace_ids), Asset.is_archived.is_(False)
        )
    elif metric is Metric.RULES:
        query = select(func.count(Rule.id)).where(Rule.workspace_id.in_(workspace_ids))
    elif metric is Metric.ACTIVE_SPLIT_GROUPS:
        query = select(func.count(Group.id)).where(
            Group.workspace_id.in_(workspace_ids), Group.is_archived.is_(False)
        )
    elif metric is Metric.GROUP_MEMBERS:
        if group_id is None:
            return 0
        query = select(func.count(GroupMember.id)).where(GroupMember.group_id == group_id)
    elif metric is Metric.STORAGE_BYTES:
        tx_result = await session.execute(
            select(func.coalesce(func.sum(TransactionAttachment.size), 0)).where(
                TransactionAttachment.workspace_id.in_(workspace_ids)
            )
        )
        inv_result = await session.execute(
            select(func.coalesce(func.sum(InvoiceAttachment.size), 0)).where(
                InvoiceAttachment.workspace_id.in_(workspace_ids)
            )
        )
        return int(tx_result.scalar() or 0) + int(inv_result.scalar() or 0)
    else:
        return 0

    result = await session.execute(query)
    return int(result.scalar() or 0)


def minimum_plan_for_metric(metric: Metric, required_usage: int) -> PlanId | None:
    for plan in (PlanId.FREE, PlanId.PRO, PlanId.MAX):
        if PLAN_CATALOG[plan].limit(metric) >= required_usage:
            return plan
    return None


def _owner_id(workspace: Workspace) -> uuid.UUID:
    if workspace.billing_owner_user_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "BILLING_OWNER_REQUIRED"},
        )
    return workspace.billing_owner_user_id


async def enforce_limit(
    session: AsyncSession,
    workspace: Workspace,
    metric: Metric,
    *,
    increment: int = 1,
    group_id: uuid.UUID | None = None,
) -> tuple[int, int, PlanId]:
    """Serialize, inspect and enforce a live-resource quota.

    Keep the returned subscription-row lock in the caller's transaction until
    the resource mutation commits. Existing service methods generally commit
    the create themselves, so the lock and insert share the same transaction.
    """
    if increment < 0:
        raise ValueError("increment must be non-negative")
    if metric in MONTHLY_METRICS:
        raise ValueError("Use consume_monthly for resettable metrics")

    owner_id = _owner_id(workspace)
    subscription = await ensure_subscription_row(session, owner_id, for_update=True)
    plan = effective_plan(subscription)
    limit = get_plan_spec(plan).limit(metric)
    usage = await current_usage(session, owner_id, metric, group_id=group_id)
    desired = usage + increment
    if desired > limit:
        error = PlanLimitReachedError(
            metric=metric,
            usage=usage,
            limit=limit,
            current_plan=plan,
            required_plan=minimum_plan_for_metric(metric, desired),
        )
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error.detail())
    return usage, limit, plan


async def consume_monthly(
    session: AsyncSession,
    workspace: Workspace,
    metric: Metric,
    *,
    amount: int = 1,
) -> tuple[int, int, PlanId]:
    """Reserve monthly usage inside the caller's current transaction.

    If the subsequent mutation fails before commit, SQLAlchemy rolls the
    reservation back with it. If it succeeds and commits, the deletion-proof
    counter remains consumed even if the created resource is later deleted.
    """
    if metric not in MONTHLY_METRICS:
        raise ValueError("consume_monthly only accepts resettable metrics")
    if amount <= 0:
        raise ValueError("amount must be positive")

    owner_id = _owner_id(workspace)
    subscription = await ensure_subscription_row(session, owner_id, for_update=True)
    plan = effective_plan(subscription)
    limit = get_plan_spec(plan).limit(metric)
    bucket = month_bucket()

    result = await session.execute(
        select(BillingUsageCounter).where(
            BillingUsageCounter.user_id == owner_id,
            BillingUsageCounter.metric == metric.value,
            BillingUsageCounter.period_start == bucket,
        )
    )
    counter = result.scalar_one_or_none()
    used = int(counter.used if counter else 0)
    desired = used + amount
    if desired > limit:
        error = PlanLimitReachedError(
            metric=metric,
            usage=used,
            limit=limit,
            current_plan=plan,
            required_plan=minimum_plan_for_metric(metric, desired),
        )
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error.detail())

    if counter is None:
        counter = BillingUsageCounter(
            user_id=owner_id,
            metric=metric.value,
            period_start=bucket,
            used=desired,
        )
        session.add(counter)
    else:
        counter.used = desired
    await session.flush()
    return used, limit, plan


async def usage_snapshot(session: AsyncSession, owner_id: uuid.UUID) -> dict[str, int]:
    metrics = (
        Metric.TOTAL_WORKSPACES,
        Metric.PERSONAL_WORKSPACES,
        Metric.BUSINESS_WORKSPACES,
        Metric.ACCOUNTS,
        Metric.ACTIVE_BUDGETS,
        Metric.ACTIVE_GOALS,
        Metric.ACTIVE_RECURRING,
        Metric.ASSETS,
        Metric.IMPORTS_MONTHLY,
        Metric.RULES,
        Metric.ACTIVE_SPLIT_GROUPS,
        Metric.INVOICES_MONTHLY,
        Metric.AI_ACTIONS_MONTHLY,
        Metric.STORAGE_BYTES,
    )
    return {metric.value: await current_usage(session, owner_id, metric) for metric in metrics}
