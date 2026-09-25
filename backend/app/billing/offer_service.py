from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.billing.enums import BillingInterval, PlanId
from app.billing.offer_schemas import (
    FounderCampaignStatusRead,
    FounderWaveStatusRead,
)
from app.billing.offers import (
    CAMPAIGN_CODE,
    CAMPAIGN_VERSION,
    FOUNDER_TOTAL_CAPACITY,
    FOUNDER_WAVES,
    CampaignState,
    OfferCode,
    ReservationStatus,
    founder_wave_for_position,
    standard_offer_code,
    standard_service_days,
)
from app.billing.pricing import PRICE_CATALOG
from app.models.pricing_offer import (
    CheckoutReservation,
    FoundingMember,
    PricingAuditEvent,
    PricingCampaign,
)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Pricing campaign timestamps must include a timezone")
    return value.astimezone(timezone.utc)


async def _audit(
    session: AsyncSession,
    *,
    event_type: str,
    entity_type: str,
    entity_id: str,
    payload: dict[str, Any],
    actor_user_id: uuid.UUID | None = None,
) -> None:
    session.add(
        PricingAuditEvent(
            actor_user_id=actor_user_id,
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            payload=payload,
        )
    )


async def get_campaign(
    session: AsyncSession, *, for_update: bool = False
) -> PricingCampaign:
    stmt = select(PricingCampaign).where(PricingCampaign.code == CAMPAIGN_CODE)
    if for_update:
        stmt = stmt.with_for_update()
    campaign = (await session.execute(stmt)).scalar_one_or_none()
    if campaign is not None:
        return campaign

    # The migration seeds this row. Creating it here keeps fresh metadata-based
    # test databases deterministic without inventing dates or activating sales.
    campaign = PricingCampaign(
        code=CAMPAIGN_CODE,
        state=CampaignState.SCHEDULED.value,
        catalog_version=CAMPAIGN_VERSION,
        version=1,
    )
    session.add(campaign)
    await session.flush()
    return campaign


def campaign_is_live(
    campaign: PricingCampaign, *, now: datetime | None = None
) -> bool:
    current = now or utcnow()
    if campaign.state != CampaignState.ACTIVE.value:
        return False
    if campaign.public_launch_at is None:
        return False
    if current >= campaign.public_launch_at:
        return False
    if campaign.presale_starts_at is not None and current < campaign.presale_starts_at:
        return False
    if campaign.presale_ends_at is not None and current >= campaign.presale_ends_at:
        return False
    return True


async def _expire_stale_reservations(
    session: AsyncSession, *, now: datetime
) -> None:
    rows = (
        await session.execute(
            select(CheckoutReservation)
            .where(
                CheckoutReservation.status == ReservationStatus.RESERVED.value,
                CheckoutReservation.expires_at <= now,
            )
            .with_for_update()
        )
    ).scalars()
    for reservation in rows:
        reservation.status = ReservationStatus.EXPIRED.value
        reservation.founder_position = None
        reservation.updated_at = now
        await _audit(
            session,
            event_type="checkout_reservation_expired",
            entity_type="checkout_reservation",
            entity_id=str(reservation.id),
            payload={
                "offer_code": reservation.offer_code,
                "founder_wave": reservation.founder_wave,
            },
        )


async def _has_prior_paid_purchase(
    session: AsyncSession, user_id: uuid.UUID
) -> bool:
    count = await session.scalar(
        select(func.count(CheckoutReservation.id)).where(
            CheckoutReservation.user_id == user_id,
            CheckoutReservation.status == ReservationStatus.VERIFIED.value,
        )
    )
    return bool(count)


async def _active_reservation(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    plan: PlanId,
    interval: BillingInterval,
    now: datetime,
) -> CheckoutReservation | None:
    return (
        await session.execute(
            select(CheckoutReservation)
            .where(
                CheckoutReservation.user_id == user_id,
                CheckoutReservation.plan == plan.value,
                CheckoutReservation.billing_interval == interval.value,
                CheckoutReservation.status == ReservationStatus.RESERVED.value,
                CheckoutReservation.expires_at > now,
            )
            .order_by(CheckoutReservation.created_at.desc())
            .limit(1)
            .with_for_update()
        )
    ).scalar_one_or_none()


async def _other_active_reservation(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    plan: PlanId,
    interval: BillingInterval,
    now: datetime,
) -> CheckoutReservation | None:
    """Prevent parallel first-purchase quotes from minting multiple intro offers."""
    return (
        await session.execute(
            select(CheckoutReservation)
            .where(
                CheckoutReservation.user_id == user_id,
                CheckoutReservation.status == ReservationStatus.RESERVED.value,
                CheckoutReservation.expires_at > now,
                ~(
                    (CheckoutReservation.plan == plan.value)
                    & (CheckoutReservation.billing_interval == interval.value)
                ),
            )
            .order_by(CheckoutReservation.created_at.desc())
            .limit(1)
            .with_for_update()
        )
    ).scalar_one_or_none()


async def _founder_positions_in_use(
    session: AsyncSession, *, now: datetime
) -> set[int]:
    claimed = (
        await session.execute(
            select(FoundingMember.founder_position).where(
                FoundingMember.status == "active"
            )
        )
    ).scalars()
    held = (
        await session.execute(
            select(CheckoutReservation.founder_position).where(
                CheckoutReservation.status == ReservationStatus.RESERVED.value,
                CheckoutReservation.expires_at > now,
                CheckoutReservation.founder_position.is_not(None),
            )
        )
    ).scalars()
    return {int(position) for position in [*claimed, *held] if position is not None}


async def _wave_counts(
    session: AsyncSession, *, now: datetime
) -> dict[int, tuple[int, int]]:
    result: dict[int, tuple[int, int]] = {}
    for wave in FOUNDER_WAVES:
        claimed = int(
            await session.scalar(
                select(func.count(FoundingMember.user_id)).where(
                    FoundingMember.wave == wave.wave,
                    FoundingMember.status == "active",
                )
            )
            or 0
        )
        held = int(
            await session.scalar(
                select(func.count(CheckoutReservation.id)).where(
                    CheckoutReservation.founder_wave == wave.wave,
                    CheckoutReservation.status == ReservationStatus.RESERVED.value,
                    CheckoutReservation.expires_at > now,
                )
            )
            or 0
        )
        result[wave.wave] = (claimed, held)
    return result


async def campaign_status(
    session: AsyncSession, *, now: datetime | None = None
) -> FounderCampaignStatusRead:
    current = now or utcnow()
    campaign = await get_campaign(session)
    counts = await _wave_counts(session, now=current)

    waves: list[FounderWaveStatusRead] = []
    total_claimed = 0
    total_held = 0
    current_wave: int | None = None
    current_amount: int | None = None
    next_amount: int | None = None

    live = campaign_is_live(campaign, now=current)
    for wave in FOUNDER_WAVES:
        claimed, held = counts[wave.wave]
        available = max(0, wave.capacity - claimed - held)
        total_claimed += claimed
        total_held += held
        waves.append(
            FounderWaveStatusRead(
                wave=wave.wave,
                capacity=wave.capacity,
                claimed=claimed,
                held=held,
                available=available,
                amount_minor=wave.amount_minor,
                next_amount_minor=wave.next_amount_minor,
            )
        )
        if live and current_wave is None and available > 0:
            current_wave = wave.wave
            current_amount = wave.amount_minor
            next_amount = wave.next_amount_minor

    return FounderCampaignStatusRead(
        code=campaign.code,
        catalog_version=campaign.catalog_version,
        state=CampaignState(campaign.state),
        version=campaign.version,
        live=live and current_wave is not None,
        presale_starts_at=campaign.presale_starts_at,
        presale_ends_at=campaign.presale_ends_at,
        public_launch_at=campaign.public_launch_at,
        current_wave=current_wave,
        current_amount_minor=current_amount,
        next_amount_minor=next_amount,
        intro_service_days=60,
        total_capacity=FOUNDER_TOTAL_CAPACITY,
        total_claimed=total_claimed,
        total_held=total_held,
        total_available=max(0, FOUNDER_TOTAL_CAPACITY - total_claimed - total_held),
        waves=waves,
    )


def _base_price(plan: PlanId, interval: BillingInterval) -> int:
    price = PRICE_CATALOG.get((plan, interval))
    if price is None or price.amount_minor <= 0 or price.currency != "INR":
        raise ValueError("Requested plan and billing interval are not purchasable")
    return price.amount_minor


async def reserve_checkout_offer(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    plan: PlanId,
    interval: BillingInterval,
    reservation_ttl_seconds: int,
    now: datetime | None = None,
) -> CheckoutReservation:
    """Atomically allocate a real checkout quote and, if eligible, founder slot."""
    current = now or utcnow()
    if plan is PlanId.FREE:
        raise ValueError("Free plan does not require checkout")
    base_amount = _base_price(plan, interval)

    campaign = await get_campaign(session, for_update=True)
    await _expire_stale_reservations(session, now=current)

    existing = await _active_reservation(
        session,
        user_id=user_id,
        plan=plan,
        interval=interval,
        now=current,
    )
    if existing is not None:
        return existing

    other_active = await _other_active_reservation(
        session,
        user_id=user_id,
        plan=plan,
        interval=interval,
        now=current,
    )
    if other_active is not None:
        raise ValueError(
            "Another checkout reservation is active for this account. "
            "Finish or cancel it before choosing a different plan."
        )

    has_prior = await _has_prior_paid_purchase(session, user_id)

    offer_code = standard_offer_code(
        plan,
        interval,
        has_prior_paid_purchase=has_prior,
    )
    amount_minor = base_amount
    service_days = standard_service_days(
        plan,
        interval,
        has_prior_paid_purchase=has_prior,
    )
    founder_wave: int | None = None
    founder_position: int | None = None
    service_starts_at: datetime | None = None
    campaign_code: str | None = None

    # Any eligible first monthly purchase made before the configured public
    # launch starts its service clock at launch, so pre-release buyers never
    # lose promised access days while the product is not yet public.
    if (
        not has_prior
        and interval is BillingInterval.MONTHLY
        and campaign.public_launch_at is not None
        and current < campaign.public_launch_at
    ):
        service_starts_at = campaign.public_launch_at

    founder_eligible = (
        not has_prior
        and plan is PlanId.PRO
        and interval is BillingInterval.MONTHLY
        and campaign_is_live(campaign, now=current)
    )
    if founder_eligible:
        used_positions = await _founder_positions_in_use(session, now=current)
        for position in range(1, FOUNDER_TOTAL_CAPACITY + 1):
            if position not in used_positions:
                wave = founder_wave_for_position(position)
                if wave is not None:
                    founder_position = position
                    founder_wave = wave.wave
                    offer_code = wave.offer_code
                    amount_minor = wave.amount_minor
                    service_days = 60
                    service_starts_at = campaign.public_launch_at
                    campaign_code = campaign.code
                break

    reservation = CheckoutReservation(
        user_id=user_id,
        plan=plan.value,
        billing_interval=interval.value,
        offer_code=offer_code.value,
        campaign_code=campaign_code,
        campaign_version=campaign.catalog_version,
        founder_wave=founder_wave,
        founder_position=founder_position,
        amount_minor=amount_minor,
        currency="INR",
        renewal_amount_minor=base_amount,
        renewal_interval=interval.value,
        service_period_days=service_days,
        service_starts_at=service_starts_at,
        status=ReservationStatus.RESERVED.value,
        reserved_at=current,
        expires_at=current + timedelta(seconds=reservation_ttl_seconds),
    )
    session.add(reservation)
    await session.flush()

    await _audit(
        session,
        event_type="checkout_reservation_created",
        entity_type="checkout_reservation",
        entity_id=str(reservation.id),
        actor_user_id=user_id,
        payload={
            "plan": plan.value,
            "interval": interval.value,
            "offer_code": reservation.offer_code,
            "amount_minor": reservation.amount_minor,
            "currency": reservation.currency,
            "founder_wave": founder_wave,
            "founder_position": founder_position,
            "expires_at": reservation.expires_at.isoformat(),
        },
    )
    return reservation


async def attach_provider_order(
    session: AsyncSession,
    *,
    reservation: CheckoutReservation,
    provider_order_id: str,
) -> None:
    if reservation.status != ReservationStatus.RESERVED.value:
        raise ValueError("Checkout reservation is no longer active")
    if reservation.provider_order_id and reservation.provider_order_id != provider_order_id:
        raise ValueError("Checkout reservation already has a different provider order")
    reservation.provider_order_id = provider_order_id
    reservation.updated_at = utcnow()
    await _audit(
        session,
        event_type="provider_order_attached",
        entity_type="checkout_reservation",
        entity_id=str(reservation.id),
        actor_user_id=reservation.user_id,
        payload={"provider": reservation.provider, "provider_order_id": provider_order_id},
    )


async def cancel_reservation(
    session: AsyncSession,
    *,
    reservation: CheckoutReservation,
    reason: str,
) -> None:
    if reservation.status != ReservationStatus.RESERVED.value:
        return
    reservation.status = ReservationStatus.CANCELLED.value
    reservation.founder_position = None
    reservation.updated_at = utcnow()
    await _audit(
        session,
        event_type="checkout_reservation_cancelled",
        entity_type="checkout_reservation",
        entity_id=str(reservation.id),
        actor_user_id=reservation.user_id,
        payload={"reason": reason},
    )


async def reservation_for_verification(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    provider_order_id: str,
) -> CheckoutReservation | None:
    return (
        await session.execute(
            select(CheckoutReservation)
            .where(
                CheckoutReservation.user_id == user_id,
                CheckoutReservation.provider_order_id == provider_order_id,
            )
            .with_for_update()
        )
    ).scalar_one_or_none()


async def mark_reservation_verified(
    session: AsyncSession,
    *,
    reservation: CheckoutReservation,
    provider_payment_id: str,
    now: datetime | None = None,
) -> CheckoutReservation:
    current = now or utcnow()

    if reservation.status == ReservationStatus.VERIFIED.value:
        if reservation.provider_payment_id != provider_payment_id:
            raise ValueError("Reservation is already verified with a different payment")
        return reservation

    if reservation.status != ReservationStatus.RESERVED.value:
        raise ValueError("Checkout reservation is no longer verifiable")
    if reservation.expires_at <= current:
        reservation.status = ReservationStatus.EXPIRED.value
        reservation.founder_position = None
        raise ValueError("Checkout reservation expired before payment verification")

    reservation.status = ReservationStatus.VERIFIED.value
    reservation.provider_payment_id = provider_payment_id
    reservation.verified_at = current
    reservation.updated_at = current
    if reservation.service_starts_at is None:
        reservation.service_starts_at = current

    if reservation.founder_wave is not None:
        if reservation.founder_position is None:
            raise ValueError("Founder reservation lost its reserved position")
        existing = await session.get(
            FoundingMember, reservation.user_id, with_for_update=True
        )
        if existing is None:
            session.add(
                FoundingMember(
                    user_id=reservation.user_id,
                    wave=reservation.founder_wave,
                    founder_position=reservation.founder_position,
                    offer_code=reservation.offer_code,
                    reservation_id=reservation.id,
                    status="active",
                    claimed_at=current,
                )
            )
        elif existing.reservation_id != reservation.id:
            raise ValueError("User already has a different founding-member claim")

    await _audit(
        session,
        event_type="payment_captured_verified",
        entity_type="checkout_reservation",
        entity_id=str(reservation.id),
        actor_user_id=reservation.user_id,
        payload={
            "provider_payment_id": provider_payment_id,
            "offer_code": reservation.offer_code,
            "amount_minor": reservation.amount_minor,
            "founder_wave": reservation.founder_wave,
            "founder_position": reservation.founder_position,
        },
    )
    return reservation


_ALLOWED_TRANSITIONS: dict[CampaignState, set[CampaignState]] = {
    CampaignState.SCHEDULED: {CampaignState.SCHEDULED, CampaignState.ACTIVE, CampaignState.CLOSED},
    CampaignState.ACTIVE: {CampaignState.ACTIVE, CampaignState.PAUSED, CampaignState.CLOSED},
    CampaignState.PAUSED: {CampaignState.PAUSED, CampaignState.ACTIVE, CampaignState.CLOSED},
    CampaignState.CLOSED: {CampaignState.CLOSED},
}


async def update_campaign(
    session: AsyncSession,
    *,
    actor_user_id: uuid.UUID,
    expected_version: int,
    changes: dict[str, Any],
) -> PricingCampaign:
    campaign = await get_campaign(session, for_update=True)
    if campaign.version != expected_version:
        raise ValueError("Pricing campaign was changed by another request; refresh and retry")

    before = {
        "state": campaign.state,
        "presale_starts_at": campaign.presale_starts_at.isoformat()
        if campaign.presale_starts_at
        else None,
        "presale_ends_at": campaign.presale_ends_at.isoformat()
        if campaign.presale_ends_at
        else None,
        "public_launch_at": campaign.public_launch_at.isoformat()
        if campaign.public_launch_at
        else None,
        "version": campaign.version,
    }

    if "presale_starts_at" in changes:
        campaign.presale_starts_at = _as_utc(changes["presale_starts_at"])
    if "presale_ends_at" in changes:
        campaign.presale_ends_at = _as_utc(changes["presale_ends_at"])
    if "public_launch_at" in changes:
        campaign.public_launch_at = _as_utc(changes["public_launch_at"])

    if "state" in changes and changes["state"] is not None:
        new_state = (
            changes["state"]
            if isinstance(changes["state"], CampaignState)
            else CampaignState(changes["state"])
        )
        current_state = CampaignState(campaign.state)
        if new_state not in _ALLOWED_TRANSITIONS[current_state]:
            raise ValueError(
                f"Campaign transition {current_state.value} -> {new_state.value} is not allowed"
            )
        campaign.state = new_state.value

    if (
        campaign.presale_starts_at
        and campaign.presale_ends_at
        and campaign.presale_starts_at >= campaign.presale_ends_at
    ):
        raise ValueError("Pre-sale start must be earlier than pre-sale end")
    if campaign.public_launch_at is not None:
        if (
            campaign.presale_starts_at is not None
            and campaign.presale_starts_at >= campaign.public_launch_at
        ):
            raise ValueError("Pre-sale start must be before public launch")
        if (
            campaign.presale_ends_at is not None
            and campaign.presale_ends_at > campaign.public_launch_at
        ):
            raise ValueError("Pre-sale end cannot be after public launch")

    if campaign.state == CampaignState.ACTIVE.value:
        if campaign.public_launch_at is None:
            raise ValueError("Public launch timestamp is required before activation")
        if campaign.public_launch_at <= utcnow():
            raise ValueError("Founder pre-sale cannot activate after public launch")

    campaign.version += 1
    campaign.updated_by_user_id = actor_user_id
    campaign.updated_at = utcnow()

    after = {
        "state": campaign.state,
        "presale_starts_at": campaign.presale_starts_at.isoformat()
        if campaign.presale_starts_at
        else None,
        "presale_ends_at": campaign.presale_ends_at.isoformat()
        if campaign.presale_ends_at
        else None,
        "public_launch_at": campaign.public_launch_at.isoformat()
        if campaign.public_launch_at
        else None,
        "version": campaign.version,
    }
    await _audit(
        session,
        event_type="pricing_campaign_updated",
        entity_type="pricing_campaign",
        entity_id=campaign.code,
        actor_user_id=actor_user_id,
        payload={"before": before, "after": after},
    )
    await session.flush()
    return campaign
