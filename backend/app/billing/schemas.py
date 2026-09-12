from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.billing.enums import BillingInterval, PlanId, SubscriptionStatus


class PriceOptionRead(BaseModel):
    plan: PlanId
    interval: BillingInterval
    amount_minor: int
    currency: str


class PricingCatalogRead(BaseModel):
    prices: list[PriceOptionRead]
    pro_annual_saving_minor: int


class EntitlementsRead(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    plan: PlanId
    status: SubscriptionStatus
    billing_interval: BillingInterval
    current_period_end: datetime | None = None
    cancel_at_period_end: bool = False
    capabilities: dict[str, bool]
    limits: dict[str, int]
    usage: dict[str, int]
    resets_at: dict[str, datetime | None]
