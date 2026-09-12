from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from app.billing.enums import BillingInterval, PlanId


@dataclass(frozen=True)
class PriceOption:
    plan: PlanId
    interval: BillingInterval
    amount_minor: int
    currency: str = "INR"


PRICE_CATALOG: Mapping[tuple[PlanId, BillingInterval], PriceOption] = MappingProxyType(
    {
        (PlanId.FREE, BillingInterval.NONE): PriceOption(
            PlanId.FREE, BillingInterval.NONE, 0
        ),
        (PlanId.PRO, BillingInterval.MONTHLY): PriceOption(
            PlanId.PRO, BillingInterval.MONTHLY, 9_900
        ),
        (PlanId.PRO, BillingInterval.ANNUAL): PriceOption(
            PlanId.PRO, BillingInterval.ANNUAL, 99_900
        ),
        (PlanId.MAX, BillingInterval.MONTHLY): PriceOption(
            PlanId.MAX, BillingInterval.MONTHLY, 34_900
        ),
    }
)


def pro_annual_saving_minor() -> int:
    monthly = PRICE_CATALOG[(PlanId.PRO, BillingInterval.MONTHLY)].amount_minor
    annual = PRICE_CATALOG[(PlanId.PRO, BillingInterval.ANNUAL)].amount_minor
    return monthly * 12 - annual
