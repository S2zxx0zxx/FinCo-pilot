from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.billing.enums import BillingInterval, PlanId
from app.billing.offer_service import (
    campaign_status,
    cancel_reservation,
    mark_reservation_verified,
    reserve_checkout_offer,
    update_campaign,
)
from app.billing.offers import (
    FOUNDER_TOTAL_CAPACITY,
    CampaignState,
    OfferCode,
    ReservationStatus,
    founder_wave_for_position,
    provider_plan_spec,
    standard_service_days,
)
from app.billing.pricing import PRICE_CATALOG
from app.models.pricing_offer import FoundingMember, PricingCampaign
from app.models.user import User


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _activate_founder_campaign(
    session: AsyncSession,
    *,
    launch_in_days: int = 10,
) -> PricingCampaign:
    now = _now()
    campaign = PricingCampaign(
        code="founder_v1",
        state=CampaignState.ACTIVE.value,
        catalog_version="v1",
        version=1,
        presale_starts_at=now - timedelta(days=1),
        presale_ends_at=now + timedelta(days=5),
        public_launch_at=now + timedelta(days=launch_in_days),
    )
    session.add(campaign)
    await session.commit()
    return campaign


def test_founder_wave_boundaries_are_exact() -> None:
    first = founder_wave_for_position(1)
    last_wave_one = founder_wave_for_position(5_000)
    first_wave_two = founder_wave_for_position(5_001)
    last = founder_wave_for_position(25_000)

    assert first is not None and first.wave == 1 and first.amount_minor == 1_900
    assert last_wave_one is not None and last_wave_one.wave == 1
    assert first_wave_two is not None and first_wave_two.wave == 2
    assert first_wave_two.amount_minor == 4_900
    assert last is not None and last.wave == 2
    assert founder_wave_for_position(25_001) is None
    assert FOUNDER_TOTAL_CAPACITY == 25_000


def test_provider_catalog_contains_only_real_base_recurring_products() -> None:
    pro_monthly = provider_plan_spec(PlanId.PRO, BillingInterval.MONTHLY)
    pro_annual = provider_plan_spec(PlanId.PRO, BillingInterval.ANNUAL)
    max_monthly = provider_plan_spec(PlanId.MAX, BillingInterval.MONTHLY)

    assert pro_monthly is not None and pro_monthly.amount_minor == 9_900
    assert pro_monthly.period == "monthly"
    assert pro_annual is not None and pro_annual.amount_minor == 99_900
    assert pro_annual.period == "yearly"
    assert max_monthly is not None and max_monthly.amount_minor == 34_900
    assert provider_plan_spec(PlanId.FREE, BillingInterval.NONE) is None
    assert provider_plan_spec(PlanId.MAX, BillingInterval.ANNUAL) is None


def test_standard_first_monthly_service_period_is_60_days_only_once() -> None:
    assert standard_service_days(
        PlanId.PRO,
        BillingInterval.MONTHLY,
        has_prior_paid_purchase=False,
    ) == 60
    assert standard_service_days(
        PlanId.MAX,
        BillingInterval.MONTHLY,
        has_prior_paid_purchase=False,
    ) == 60
    assert standard_service_days(
        PlanId.PRO,
        BillingInterval.MONTHLY,
        has_prior_paid_purchase=True,
    ) == 30
    assert standard_service_days(
        PlanId.PRO,
        BillingInterval.ANNUAL,
        has_prior_paid_purchase=False,
    ) == 365


@pytest.mark.asyncio
async def test_campaign_defaults_scheduled_without_fake_dates(
    session: AsyncSession,
    test_user: User,
) -> None:
    status = await campaign_status(session)

    assert status.state is CampaignState.SCHEDULED
    assert status.live is False
    assert status.presale_starts_at is None
    assert status.presale_ends_at is None
    assert status.public_launch_at is None
    assert status.total_claimed == 0
    assert status.total_held == 0
    assert status.total_available == 25_000


@pytest.mark.asyncio
async def test_first_founder_quote_is_real_19_rupees_and_starts_at_launch(
    session: AsyncSession,
    test_user: User,
) -> None:
    campaign = await _activate_founder_campaign(session)

    reservation = await reserve_checkout_offer(
        session,
        user_id=test_user.id,
        plan=PlanId.PRO,
        interval=BillingInterval.MONTHLY,
        reservation_ttl_seconds=600,
    )
    await session.commit()

    assert reservation.offer_code == OfferCode.FOUNDER_WAVE_1.value
    assert reservation.amount_minor == 1_900
    assert reservation.renewal_amount_minor == 9_900
    assert reservation.service_period_days == 60
    assert reservation.founder_wave == 1
    assert reservation.founder_position == 1
    assert reservation.service_starts_at == campaign.public_launch_at


@pytest.mark.asyncio
async def test_first_max_monthly_quote_gets_60_days_but_not_founder_price(
    session: AsyncSession,
    test_user: User,
) -> None:
    campaign = await _activate_founder_campaign(session)

    reservation = await reserve_checkout_offer(
        session,
        user_id=test_user.id,
        plan=PlanId.MAX,
        interval=BillingInterval.MONTHLY,
        reservation_ttl_seconds=600,
    )
    await session.commit()

    assert reservation.offer_code == OfferCode.MAX_MONTHLY_INTRO.value
    assert reservation.amount_minor == 34_900
    assert reservation.renewal_amount_minor == 34_900
    assert reservation.service_period_days == 60
    assert reservation.founder_wave is None
    assert reservation.service_starts_at == campaign.public_launch_at


@pytest.mark.asyncio
async def test_pro_annual_never_receives_fake_founder_or_60_day_extension(
    session: AsyncSession,
    test_user: User,
) -> None:
    await _activate_founder_campaign(session)

    reservation = await reserve_checkout_offer(
        session,
        user_id=test_user.id,
        plan=PlanId.PRO,
        interval=BillingInterval.ANNUAL,
        reservation_ttl_seconds=600,
    )
    await session.commit()

    assert reservation.offer_code == OfferCode.STANDARD.value
    assert reservation.amount_minor == 99_900
    assert reservation.service_period_days == 365
    assert reservation.founder_wave is None
    assert reservation.service_starts_at is None


@pytest.mark.asyncio
async def test_one_user_cannot_hold_parallel_intro_quotes(
    session: AsyncSession,
    test_user: User,
) -> None:
    await _activate_founder_campaign(session)
    await reserve_checkout_offer(
        session,
        user_id=test_user.id,
        plan=PlanId.PRO,
        interval=BillingInterval.MONTHLY,
        reservation_ttl_seconds=600,
    )
    await session.commit()

    with pytest.raises(ValueError, match="Another checkout reservation"):
        await reserve_checkout_offer(
            session,
            user_id=test_user.id,
            plan=PlanId.MAX,
            interval=BillingInterval.MONTHLY,
            reservation_ttl_seconds=600,
        )


@pytest.mark.asyncio
async def test_same_active_quote_is_reused_without_consuming_second_slot(
    session: AsyncSession,
    test_user: User,
) -> None:
    await _activate_founder_campaign(session)

    first = await reserve_checkout_offer(
        session,
        user_id=test_user.id,
        plan=PlanId.PRO,
        interval=BillingInterval.MONTHLY,
        reservation_ttl_seconds=600,
    )
    await session.commit()
    second = await reserve_checkout_offer(
        session,
        user_id=test_user.id,
        plan=PlanId.PRO,
        interval=BillingInterval.MONTHLY,
        reservation_ttl_seconds=600,
    )

    assert second.id == first.id
    assert second.founder_position == 1


@pytest.mark.asyncio
async def test_cancelled_founder_quote_releases_temporary_position(
    session: AsyncSession,
    test_user: User,
) -> None:
    await _activate_founder_campaign(session)
    reservation = await reserve_checkout_offer(
        session,
        user_id=test_user.id,
        plan=PlanId.PRO,
        interval=BillingInterval.MONTHLY,
        reservation_ttl_seconds=600,
    )
    assert reservation.founder_position == 1

    await cancel_reservation(
        session,
        reservation=reservation,
        reason="test_cancel",
    )
    await session.commit()

    assert reservation.status == ReservationStatus.CANCELLED.value
    assert reservation.founder_position is None

    status = await campaign_status(session)
    assert status.total_held == 0
    assert status.total_available == 25_000


@pytest.mark.asyncio
async def test_captured_founder_purchase_creates_persistent_identity_once(
    session: AsyncSession,
    test_user: User,
) -> None:
    await _activate_founder_campaign(session)
    reservation = await reserve_checkout_offer(
        session,
        user_id=test_user.id,
        plan=PlanId.PRO,
        interval=BillingInterval.MONTHLY,
        reservation_ttl_seconds=600,
    )
    await mark_reservation_verified(
        session,
        reservation=reservation,
        provider_payment_id="pay_founder_1",
    )
    await session.commit()

    founder = await session.get(FoundingMember, test_user.id)
    assert founder is not None
    assert founder.wave == 1
    assert founder.founder_position == 1
    assert founder.reservation_id == reservation.id

    # A replay of the same captured payment is idempotent.
    await mark_reservation_verified(
        session,
        reservation=reservation,
        provider_payment_id="pay_founder_1",
    )
    await session.commit()
    rows = (
        await session.execute(
            select(FoundingMember).where(FoundingMember.user_id == test_user.id)
        )
    ).scalars().all()
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_second_paid_purchase_does_not_get_intro_again(
    session: AsyncSession,
    test_user: User,
) -> None:
    await _activate_founder_campaign(session)
    first = await reserve_checkout_offer(
        session,
        user_id=test_user.id,
        plan=PlanId.PRO,
        interval=BillingInterval.MONTHLY,
        reservation_ttl_seconds=600,
    )
    await mark_reservation_verified(
        session,
        reservation=first,
        provider_payment_id="pay_first",
    )
    await session.commit()

    second = await reserve_checkout_offer(
        session,
        user_id=test_user.id,
        plan=PlanId.MAX,
        interval=BillingInterval.MONTHLY,
        reservation_ttl_seconds=600,
    )

    assert second.offer_code == OfferCode.STANDARD.value
    assert second.amount_minor == PRICE_CATALOG[
        (PlanId.MAX, BillingInterval.MONTHLY)
    ].amount_minor
    assert second.service_period_days == 30


@pytest.mark.asyncio
async def test_campaign_update_is_versioned_audited_and_requires_real_dates(
    session: AsyncSession,
    test_user: User,
) -> None:
    status = await campaign_status(session)
    launch = _now() + timedelta(days=15)
    start = _now() + timedelta(days=1)
    end = _now() + timedelta(days=10)

    updated = await update_campaign(
        session,
        actor_user_id=test_user.id,
        expected_version=status.version,
        changes={
            "presale_starts_at": start,
            "presale_ends_at": end,
            "public_launch_at": launch,
            "state": CampaignState.ACTIVE,
        },
    )
    await session.commit()

    assert updated.state == CampaignState.ACTIVE.value
    assert updated.version == status.version + 1
    assert updated.updated_by_user_id == test_user.id

    with pytest.raises(ValueError, match="changed by another request"):
        await update_campaign(
            session,
            actor_user_id=test_user.id,
            expected_version=status.version,
            changes={"state": CampaignState.PAUSED},
        )


@pytest.mark.asyncio
async def test_campaign_rejects_invalid_timeline(
    session: AsyncSession,
    test_user: User,
) -> None:
    status = await campaign_status(session)
    launch = _now() + timedelta(days=10)

    with pytest.raises(ValueError, match="Pre-sale start must be earlier"):
        await update_campaign(
            session,
            actor_user_id=test_user.id,
            expected_version=status.version,
            changes={
                "presale_starts_at": launch,
                "presale_ends_at": launch - timedelta(days=1),
                "public_launch_at": launch + timedelta(days=1),
            },
        )
