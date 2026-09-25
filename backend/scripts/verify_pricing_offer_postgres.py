"""Disposable PostgreSQL concurrency proof for founder-wave allocation.

Runs only when FINCO_DISPOSABLE_DB_TEST=yes. It seeds 4,999 active holds,
then launches two concurrent checkout reservations. Correct row locking must
allocate position 5,000 at ₹19 and position 5,001 at ₹49 exactly once each.
"""

from __future__ import annotations

import asyncio
import os
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, insert

from app.billing.enums import BillingInterval, PlanId
from app.billing.offer_service import reserve_checkout_offer
from app.billing.offers import CampaignState
from app.core.database import async_session_maker, engine
from app.models.pricing_offer import (
    CheckoutReservation,
    FoundingMember,
    PricingAuditEvent,
    PricingCampaign,
)
from app.models.user import User


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _reserve(user_id: uuid.UUID) -> tuple[int | None, int, int | None]:
    async with async_session_maker() as session:
        row = await reserve_checkout_offer(
            session,
            user_id=user_id,
            plan=PlanId.PRO,
            interval=BillingInterval.MONTHLY,
            reservation_ttl_seconds=600,
        )
        await session.commit()
        return row.founder_position, row.amount_minor, row.founder_wave


async def main() -> None:
    if os.environ.get("FINCO_DISPOSABLE_DB_TEST") != "yes":
        raise SystemExit(
            "Refusing destructive concurrency proof without "
            "FINCO_DISPOSABLE_DB_TEST=yes"
        )

    now = _now()
    launch = now + timedelta(days=7)
    expires = now + timedelta(hours=1)

    seed_user_id = uuid.uuid4()
    user_a_id = uuid.uuid4()
    user_b_id = uuid.uuid4()

    async with async_session_maker() as session:
        # Only pricing-test state is reset. Other smoke-test data stays intact.
        await session.execute(delete(PricingAuditEvent))
        await session.execute(delete(FoundingMember))
        await session.execute(delete(CheckoutReservation))
        await session.execute(delete(PricingCampaign))

        for user_id, email in (
            (seed_user_id, f"pricing-seed-{seed_user_id.hex}@example.invalid"),
            (user_a_id, f"pricing-a-{user_a_id.hex}@example.invalid"),
            (user_b_id, f"pricing-b-{user_b_id.hex}@example.invalid"),
        ):
            session.add(
                User(
                    id=user_id,
                    email=email,
                    hashed_password="synthetic-not-a-login-password",
                    is_active=True,
                    is_superuser=False,
                    is_verified=True,
                )
            )

        session.add(
            PricingCampaign(
                code="founder_v1",
                state=CampaignState.ACTIVE.value,
                catalog_version="v1",
                version=1,
                presale_starts_at=now - timedelta(hours=1),
                presale_ends_at=now + timedelta(days=5),
                public_launch_at=launch,
            )
        )
        await session.flush()

        # Seed all positions before the wave-1 boundary with one synthetic user.
        await session.execute(
            insert(CheckoutReservation),
            [
                {
                    "id": uuid.uuid4(),
                    "user_id": seed_user_id,
                    "plan": "pro",
                    "billing_interval": "monthly",
                    "offer_code": "founder_wave_1",
                    "campaign_code": "founder_v1",
                    "campaign_version": "v1",
                    "founder_wave": 1,
                    "founder_position": position,
                    "amount_minor": 1_900,
                    "currency": "INR",
                    "renewal_amount_minor": 9_900,
                    "renewal_interval": "monthly",
                    "service_period_days": 60,
                    "service_starts_at": launch,
                    "status": "reserved",
                    "provider": "razorpay",
                    "reserved_at": now,
                    "expires_at": expires,
                    "created_at": now,
                    "updated_at": now,
                }
                for position in range(1, 5_000)
            ],
        )
        await session.commit()

    first, second = await asyncio.gather(
        _reserve(user_a_id),
        _reserve(user_b_id),
    )
    actual = {first, second}
    expected = {
        (5_000, 1_900, 1),
        (5_001, 4_900, 2),
    }
    if actual != expected:
        raise RuntimeError(
            f"Founder concurrency allocation mismatch: expected {expected}, got {actual}"
        )

    print(
        "PASS: concurrent founder boundary allocated position 5000 at ₹19 "
        "and position 5001 at ₹49 exactly once"
    )
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
