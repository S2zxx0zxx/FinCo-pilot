from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.billing.enums import BillingInterval, PlanId
from app.billing.offers import CampaignState, OfferCode


class FounderWaveStatusRead(BaseModel):
    wave: int
    capacity: int
    claimed: int
    held: int
    available: int
    amount_minor: int
    next_amount_minor: int
    currency: str = "INR"


class FounderCampaignStatusRead(BaseModel):
    code: str
    catalog_version: str
    state: CampaignState
    version: int
    live: bool
    presale_starts_at: datetime | None = None
    presale_ends_at: datetime | None = None
    public_launch_at: datetime | None = None
    current_wave: int | None = None
    current_amount_minor: int | None = None
    next_amount_minor: int | None = None
    intro_service_days: int
    total_capacity: int
    total_claimed: int
    total_held: int
    total_available: int
    waves: list[FounderWaveStatusRead]


class CheckoutOfferRead(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    reservation_id: str
    plan: PlanId
    interval: BillingInterval
    offer_code: OfferCode
    amount_minor: int
    currency: str
    renewal_amount_minor: int
    renewal_interval: BillingInterval
    service_period_days: int
    service_starts_at: datetime | None = None
    founder_wave: int | None = None
    founder_position: int | None = None
    expires_at: datetime


class CampaignAdminUpdate(BaseModel):
    expected_version: int = Field(ge=1)
    state: CampaignState | None = None
    presale_starts_at: datetime | None = None
    presale_ends_at: datetime | None = None
    public_launch_at: datetime | None = None


class CampaignAdminRead(FounderCampaignStatusRead):
    updated_by_user_id: str | None = None
    updated_at: datetime


class ProviderPlanStatusRead(BaseModel):
    plan: PlanId
    interval: BillingInterval
    configured: bool
    provider_plan_id: str | None = None
    valid: bool | None = None
    errors: list[str] = Field(default_factory=list)


class ProviderCatalogStatusRead(BaseModel):
    provider: str = "razorpay"
    catalog_version: str
    plans: list[ProviderPlanStatusRead]
