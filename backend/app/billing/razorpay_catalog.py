from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.billing.enums import BillingInterval, PlanId
from app.billing.offers import (
    CAMPAIGN_VERSION,
    PROVIDER_PLAN_SPECS,
    ProviderPlanSpec,
)
from app.core.config import get_settings


@dataclass(frozen=True)
class ProviderPlanValidation:
    plan: PlanId
    interval: BillingInterval
    provider_plan_id: str
    valid: bool
    errors: tuple[str, ...]


def configured_provider_plan_id(
    plan: PlanId, interval: BillingInterval
) -> str | None:
    spec = PROVIDER_PLAN_SPECS.get((plan, interval))
    if spec is None:
        return None
    settings = get_settings()
    mapping = {
        "RAZORPAY_PLAN_PRO_MONTHLY_ID": settings.razorpay_plan_pro_monthly_id,
        "RAZORPAY_PLAN_PRO_ANNUAL_ID": settings.razorpay_plan_pro_annual_id,
        "RAZORPAY_PLAN_MAX_MONTHLY_ID": settings.razorpay_plan_max_monthly_id,
    }
    value = mapping[spec.env_name].strip()
    return value or None


def provider_plan_create_payload(spec: ProviderPlanSpec) -> dict[str, Any]:
    """Return the exact Razorpay Plan payload for one canonical base plan."""
    return {
        "period": spec.period,
        "interval": spec.provider_interval,
        "item": {
            "name": spec.provider_name,
            "amount": spec.amount_minor,
            "currency": spec.currency,
            "description": spec.description,
        },
        "notes": {
            "product": "fincopilot",
            "catalog_version": CAMPAIGN_VERSION,
            "plan": spec.plan.value,
            "billing_interval": spec.interval.value,
        },
    }


def _notes_dict(value: Any) -> dict[str, str]:
    if isinstance(value, dict):
        return {str(key): str(item) for key, item in value.items()}
    return {}


def validate_provider_plan(
    *,
    spec: ProviderPlanSpec,
    provider_plan_id: str,
    provider_plan: dict[str, Any],
) -> ProviderPlanValidation:
    """Compare a fetched Razorpay Plan with FinCopilot's immutable catalog."""
    errors: list[str] = []

    if str(provider_plan.get("id", "")) != provider_plan_id:
        errors.append("provider plan id mismatch")
    if provider_plan.get("period") != spec.period:
        errors.append(
            f"period mismatch: expected {spec.period}, got {provider_plan.get('period')}"
        )
    if provider_plan.get("interval") != spec.provider_interval:
        errors.append(
            "interval mismatch: "
            f"expected {spec.provider_interval}, got {provider_plan.get('interval')}"
        )

    item = provider_plan.get("item")
    if not isinstance(item, dict):
        errors.append("provider plan item is missing")
        item = {}

    if item.get("amount") != spec.amount_minor:
        errors.append(
            f"amount mismatch: expected {spec.amount_minor}, got {item.get('amount')}"
        )
    if item.get("currency") != spec.currency:
        errors.append(
            f"currency mismatch: expected {spec.currency}, got {item.get('currency')}"
        )
    if item.get("name") != spec.provider_name:
        errors.append(
            f"name mismatch: expected {spec.provider_name}, got {item.get('name')}"
        )

    notes = _notes_dict(provider_plan.get("notes"))
    expected_notes = {
        "product": "fincopilot",
        "catalog_version": CAMPAIGN_VERSION,
        "plan": spec.plan.value,
        "billing_interval": spec.interval.value,
    }
    for key, expected in expected_notes.items():
        if notes.get(key) != expected:
            errors.append(
                f"note {key} mismatch: expected {expected}, got {notes.get(key)}"
            )

    return ProviderPlanValidation(
        plan=spec.plan,
        interval=spec.interval,
        provider_plan_id=provider_plan_id,
        valid=not errors,
        errors=tuple(errors),
    )


def find_exact_provider_plan(
    spec: ProviderPlanSpec,
    provider_plans: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Find a reusable exact match without creating duplicate Razorpay Plans."""
    for plan in provider_plans:
        provider_plan_id = str(plan.get("id", ""))
        if not provider_plan_id:
            continue
        validation = validate_provider_plan(
            spec=spec,
            provider_plan_id=provider_plan_id,
            provider_plan=plan,
        )
        if validation.valid:
            return plan
    return None
