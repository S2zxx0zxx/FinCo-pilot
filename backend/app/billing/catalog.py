from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from app.billing.enums import Capability, Metric, PlanId


@dataclass(frozen=True)
class PlanSpec:
    plan: PlanId
    capabilities: frozenset[Capability]
    limits: Mapping[Metric, int]

    def has(self, capability: Capability) -> bool:
        return capability in self.capabilities

    def limit(self, metric: Metric) -> int:
        return self.limits[metric]


def _limits(**values: int) -> Mapping[Metric, int]:
    return MappingProxyType({Metric(key): value for key, value in values.items()})


PLAN_CATALOG: Mapping[PlanId, PlanSpec] = MappingProxyType(
    {
        PlanId.FREE: PlanSpec(
            plan=PlanId.FREE,
            capabilities=frozenset(),
            limits=_limits(
                total_workspaces=1,
                personal_workspaces=1,
                business_workspaces=0,
                accounts=3,
                active_budgets=2,
                active_goals=2,
                active_recurring=3,
                assets=3,
                imports_monthly=2,
                rules=0,
                active_split_groups=1,
                group_members=5,
                invoices_monthly=0,
                ai_actions_monthly=5,
                storage_bytes=100 * 1024 * 1024,
            ),
        ),
        PlanId.PRO: PlanSpec(
            plan=PlanId.PRO,
            capabilities=frozenset(
                {
                    Capability.ADVANCED_REPORTS,
                    Capability.RULES,
                    Capability.SMART_RECONCILIATION,
                }
            ),
            limits=_limits(
                total_workspaces=1,
                personal_workspaces=1,
                business_workspaces=0,
                accounts=25,
                active_budgets=25,
                active_goals=25,
                active_recurring=50,
                assets=50,
                imports_monthly=30,
                rules=25,
                active_split_groups=10,
                group_members=15,
                invoices_monthly=0,
                ai_actions_monthly=60,
                storage_bytes=1024 * 1024 * 1024,
            ),
        ),
        PlanId.MAX: PlanSpec(
            plan=PlanId.MAX,
            capabilities=frozenset(
                {
                    Capability.ADVANCED_REPORTS,
                    Capability.RULES,
                    Capability.SMART_RECONCILIATION,
                    Capability.BUSINESS_WORKSPACES,
                    Capability.INVOICES,
                    Capability.AGENTS_AUTOMATION,
                }
            ),
            limits=_limits(
                total_workspaces=3,
                personal_workspaces=3,
                business_workspaces=3,
                accounts=100,
                active_budgets=100,
                active_goals=100,
                active_recurring=250,
                assets=500,
                imports_monthly=200,
                rules=200,
                active_split_groups=50,
                group_members=50,
                invoices_monthly=500,
                ai_actions_monthly=300,
                storage_bytes=10 * 1024 * 1024 * 1024,
            ),
        ),
    }
)


def get_plan_spec(plan: PlanId | str) -> PlanSpec:
    try:
        plan_id = plan if isinstance(plan, PlanId) else PlanId(plan)
    except ValueError:
        plan_id = PlanId.FREE
    return PLAN_CATALOG[plan_id]
