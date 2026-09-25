from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Mapping

from app.billing.enums import BillingInterval, PlanId
from app.billing.pricing import PRICE_CATALOG


CAMPAIGN_CODE = "founder_v1"
CAMPAIGN_VERSION = "v1"
INTRO_SERVICE_DAYS = 60
DEFAULT_MONTHLY_SERVICE_DAYS = 30
ANNUAL_SERVICE_DAYS = 365


class CampaignState(StrEnum):
    SCHEDULED = "scheduled"
    ACTIVE = "active"
    PAUSED = "paused"
    CLOSED = "closed"


class OfferCode(StrEnum):
    FOUNDER_WAVE_1 = "founder_wave_1"
    FOUNDER_WAVE_2 = "founder_wave_2"
    PRO_MONTHLY_INTRO = "pro_monthly_intro"
    MAX_MONTHLY_INTRO = "max_monthly_intro"
    STANDARD = "standard"


class ReservationStatus(StrEnum):
    RESERVED = "reserved"
    VERIFIED = "verified"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    CHARGEBACK = "chargeback"


@dataclass(frozen=True)
class FounderWaveSpec:
    wave: int
    offer_code: OfferCode
    capacity: int
    amount_minor: int
    next_amount_minor: int


FOUNDER_WAVES: tuple[FounderWaveSpec, ...] = (
    FounderWaveSpec(
        wave=1,
        offer_code=OfferCode.FOUNDER_WAVE_1,
        capacity=5_000,
        amount_minor=1_900,
        next_amount_minor=4_900,
    ),
    FounderWaveSpec(
        wave=2,
        offer_code=OfferCode.FOUNDER_WAVE_2,
        capacity=20_000,
        amount_minor=4_900,
        next_amount_minor=PRICE_CATALOG[
            (PlanId.PRO, BillingInterval.MONTHLY)
        ].amount_minor,
    ),
)

FOUNDER_TOTAL_CAPACITY = sum(wave.capacity for wave in FOUNDER_WAVES)


@dataclass(frozen=True)
class ProviderPlanSpec:
    plan: PlanId
    interval: BillingInterval
    env_name: str
    provider_name: str
    period: str
    provider_interval: int
    description: str

    @property
    def amount_minor(self) -> int:
        return PRICE_CATALOG[(self.plan, self.interval)].amount_minor

    @property
    def currency(self) -> str:
        return PRICE_CATALOG[(self.plan, self.interval)].currency


PROVIDER_PLAN_SPECS: Mapping[
    tuple[PlanId, BillingInterval], ProviderPlanSpec
] = MappingProxyType(
    {
        (PlanId.PRO, BillingInterval.MONTHLY): ProviderPlanSpec(
            plan=PlanId.PRO,
            interval=BillingInterval.MONTHLY,
            env_name="RAZORPAY_PLAN_PRO_MONTHLY_ID",
            provider_name="FinCopilot Pro Monthly",
            period="monthly",
            provider_interval=1,
            description="FinCopilot Pro — monthly subscription",
        ),
        (PlanId.PRO, BillingInterval.ANNUAL): ProviderPlanSpec(
            plan=PlanId.PRO,
            interval=BillingInterval.ANNUAL,
            env_name="RAZORPAY_PLAN_PRO_ANNUAL_ID",
            provider_name="FinCopilot Pro Annual",
            period="yearly",
            provider_interval=1,
            description="FinCopilot Pro — annual subscription",
        ),
        (PlanId.MAX, BillingInterval.MONTHLY): ProviderPlanSpec(
            plan=PlanId.MAX,
            interval=BillingInterval.MONTHLY,
            env_name="RAZORPAY_PLAN_MAX_MONTHLY_ID",
            provider_name="FinCopilot Max Monthly",
            period="monthly",
            provider_interval=1,
            description="FinCopilot Max — monthly subscription",
        ),
    }
)


def founder_wave_by_number(wave: int) -> FounderWaveSpec | None:
    return next((item for item in FOUNDER_WAVES if item.wave == wave), None)


def founder_wave_for_position(position: int) -> FounderWaveSpec | None:
    """Return the founder wave for a 1-based allocated position."""
    if position < 1:
        return None
    cursor = 0
    for wave in FOUNDER_WAVES:
        cursor += wave.capacity
        if position <= cursor:
            return wave
    return None


def provider_plan_spec(
    plan: PlanId, interval: BillingInterval
) -> ProviderPlanSpec | None:
    return PROVIDER_PLAN_SPECS.get((plan, interval))


def standard_service_days(
    plan: PlanId,
    interval: BillingInterval,
    *,
    has_prior_paid_purchase: bool,
) -> int:
    """Return the promised service period for a non-founder purchase.

    First monthly paid purchase receives 60 days. A later monthly purchase is a
    normal monthly period. Annual Pro stays a normal annual product and does not
    receive an extra 60-day extension.
    """
    if interval is BillingInterval.ANNUAL:
        return ANNUAL_SERVICE_DAYS
    if interval is BillingInterval.MONTHLY:
        return (
            DEFAULT_MONTHLY_SERVICE_DAYS
            if has_prior_paid_purchase
            else INTRO_SERVICE_DAYS
        )
    return 0


def standard_offer_code(
    plan: PlanId,
    interval: BillingInterval,
    *,
    has_prior_paid_purchase: bool,
) -> OfferCode:
    if has_prior_paid_purchase or interval is not BillingInterval.MONTHLY:
        return OfferCode.STANDARD
    if plan is PlanId.PRO:
        return OfferCode.PRO_MONTHLY_INTRO
    if plan is PlanId.MAX:
        return OfferCode.MAX_MONTHLY_INTRO
    return OfferCode.STANDARD
