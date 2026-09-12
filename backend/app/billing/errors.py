from dataclasses import dataclass

from app.billing.enums import Capability, Metric, PlanId


@dataclass(frozen=True)
class EntitlementRequiredError(Exception):
    capability: Capability
    current_plan: PlanId
    required_plan: PlanId

    def detail(self) -> dict[str, str]:
        return {
            "code": "ENTITLEMENT_REQUIRED",
            "capability": self.capability.value,
            "current_plan": self.current_plan.value,
            "required_plan": self.required_plan.value,
        }


@dataclass(frozen=True)
class PlanLimitReachedError(Exception):
    metric: Metric
    usage: int
    limit: int
    current_plan: PlanId
    required_plan: PlanId | None = None

    def detail(self) -> dict[str, str | int | None]:
        return {
            "code": "PLAN_LIMIT_REACHED",
            "metric": self.metric.value,
            "usage": self.usage,
            "limit": self.limit,
            "current_plan": self.current_plan.value,
            "required_plan": self.required_plan.value if self.required_plan else None,
        }
