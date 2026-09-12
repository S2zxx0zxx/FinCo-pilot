"""Server-authoritative FinCo-Pilot billing and entitlement primitives."""

from app.billing.catalog import PLAN_CATALOG, PlanSpec, get_plan_spec
from app.billing.enums import BillingInterval, Capability, Metric, PlanId, SubscriptionStatus
# Import models as a side effect so Base.metadata sees them before test/create_all
# and Alembic/autogenerate paths inspect the complete billing schema.
from app.models.billing_usage import BillingUsageCounter
from app.models.subscription import Subscription

__all__ = [
    "BillingInterval",
    "BillingUsageCounter",
    "Capability",
    "Metric",
    "PLAN_CATALOG",
    "PlanId",
    "PlanSpec",
    "Subscription",
    "SubscriptionStatus",
    "get_plan_spec",
]
