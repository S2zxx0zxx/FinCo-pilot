"""Deletion-proof, concurrency-safe operational usage for FinCo Copilot."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.billing_usage import BillingUsageCounter
from app.models.user import User

CORE_DAILY_METRIC = "core_copilot_daily_messages"


def _utc_day(now: datetime) -> date:
    return now.astimezone(timezone.utc).date()


def _retry_after_seconds(now: datetime) -> int:
    current = now.astimezone(timezone.utc)
    tomorrow = datetime.combine(
        current.date() + timedelta(days=1),
        datetime.min.time(),
        tzinfo=timezone.utc,
    )
    return max(1, int((tomorrow - current).total_seconds()))


async def consume_core_message(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    limit: int,
    now: datetime | None = None,
) -> tuple[int, int]:
    """Atomically reserve one accepted core-Copilot message for the UTC day.

    Locking the authenticated User row serializes first-use as well as updates,
    so two concurrent requests cannot both consume the last slot. The counter
    is independent of conversation deletion and does not alter plan metrics.
    Caller commits before streaming starts.
    """
    if limit <= 0:
        raise ValueError("core Copilot daily limit must be positive")

    current = now or datetime.now(timezone.utc)
    bucket = _utc_day(current)

    locked_user = (
        await session.execute(
            select(User.id).where(User.id == user_id).with_for_update()
        )
    ).scalar_one_or_none()
    if locked_user is None:
        raise HTTPException(status_code=403, detail="Access denied")

    counter = (
        await session.execute(
            select(BillingUsageCounter).where(
                BillingUsageCounter.user_id == user_id,
                BillingUsageCounter.metric == CORE_DAILY_METRIC,
                BillingUsageCounter.period_start == bucket,
            )
        )
    ).scalar_one_or_none()
    used = int(counter.used if counter else 0)
    if used >= limit:
        raise HTTPException(
            status_code=429,
            detail="Daily FinCo Copilot message limit reached",
            headers={"Retry-After": str(_retry_after_seconds(current))},
        )

    desired = used + 1
    if counter is None:
        session.add(
            BillingUsageCounter(
                user_id=user_id,
                metric=CORE_DAILY_METRIC,
                period_start=bucket,
                used=desired,
            )
        )
    else:
        counter.used = desired
    await session.flush()
    return desired, limit
