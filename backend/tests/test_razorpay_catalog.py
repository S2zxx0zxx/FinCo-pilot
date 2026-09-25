from __future__ import annotations

from app.billing.enums import BillingInterval, PlanId
from app.billing.offers import PROVIDER_PLAN_SPECS
from app.billing.razorpay_catalog import (
    find_exact_provider_plan,
    provider_plan_create_payload,
    validate_provider_plan,
)


def _provider_plan(
    *,
    plan: PlanId = PlanId.PRO,
    interval: BillingInterval = BillingInterval.MONTHLY,
    provider_id: str = "plan_test_pro_monthly",
):
    spec = PROVIDER_PLAN_SPECS[(plan, interval)]
    payload = provider_plan_create_payload(spec)
    return {
        "id": provider_id,
        "period": payload["period"],
        "interval": payload["interval"],
        "item": payload["item"].copy(),
        "notes": payload["notes"].copy(),
    }


def test_create_payload_is_derived_from_canonical_base_catalog() -> None:
    pro_monthly = PROVIDER_PLAN_SPECS[(PlanId.PRO, BillingInterval.MONTHLY)]
    pro_annual = PROVIDER_PLAN_SPECS[(PlanId.PRO, BillingInterval.ANNUAL)]
    max_monthly = PROVIDER_PLAN_SPECS[(PlanId.MAX, BillingInterval.MONTHLY)]

    monthly = provider_plan_create_payload(pro_monthly)
    annual = provider_plan_create_payload(pro_annual)
    maximum = provider_plan_create_payload(max_monthly)

    assert monthly["item"]["amount"] == 9_900
    assert monthly["period"] == "monthly"
    assert annual["item"]["amount"] == 99_900
    assert annual["period"] == "yearly"
    assert maximum["item"]["amount"] == 34_900
    assert maximum["period"] == "monthly"

    for payload in (monthly, annual, maximum):
        assert payload["item"]["currency"] == "INR"
        assert payload["notes"]["product"] == "fincopilot"
        assert payload["notes"]["catalog_version"] == "v1"


def test_exact_provider_plan_validates() -> None:
    spec = PROVIDER_PLAN_SPECS[(PlanId.PRO, BillingInterval.MONTHLY)]
    provider = _provider_plan()
    result = validate_provider_plan(
        spec=spec,
        provider_plan_id="plan_test_pro_monthly",
        provider_plan=provider,
    )
    assert result.valid is True
    assert result.errors == ()


def test_provider_validation_rejects_every_financial_contract_mismatch() -> None:
    spec = PROVIDER_PLAN_SPECS[(PlanId.PRO, BillingInterval.MONTHLY)]
    cases = [
        ("amount", lambda plan: plan["item"].update(amount=1)),
        ("currency", lambda plan: plan["item"].update(currency="USD")),
        ("period", lambda plan: plan.update(period="yearly")),
        ("interval", lambda plan: plan.update(interval=2)),
        ("name", lambda plan: plan["item"].update(name="Wrong Product")),
        ("product note", lambda plan: plan["notes"].update(product="other")),
        ("catalog note", lambda plan: plan["notes"].update(catalog_version="v2")),
        ("plan note", lambda plan: plan["notes"].update(plan="max")),
        (
            "interval note",
            lambda plan: plan["notes"].update(billing_interval="annual"),
        ),
    ]

    for label, mutate in cases:
        provider = _provider_plan()
        mutate(provider)
        result = validate_provider_plan(
            spec=spec,
            provider_plan_id="plan_test_pro_monthly",
            provider_plan=provider,
        )
        assert result.valid is False, label
        assert result.errors, label


def test_find_exact_provider_plan_reuses_match_and_ignores_near_match() -> None:
    spec = PROVIDER_PLAN_SPECS[(PlanId.PRO, BillingInterval.MONTHLY)]
    wrong = _provider_plan(provider_id="plan_wrong")
    wrong["item"]["amount"] = 1
    exact = _provider_plan(provider_id="plan_exact")

    found = find_exact_provider_plan(spec, [wrong, exact])
    assert found is not None
    assert found["id"] == "plan_exact"


def test_founder_prices_are_not_provider_recurring_plans() -> None:
    amounts = {spec.amount_minor for spec in PROVIDER_PLAN_SPECS.values()}
    assert 1_900 not in amounts
    assert 4_900 not in amounts
