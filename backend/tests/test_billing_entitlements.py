from datetime import datetime, timedelta, timezone

import pytest

from app.billing.enums import BillingInterval, PlanId, SubscriptionStatus
from app.billing.service import effective_plan
from app.models.subscription import Subscription


@pytest.mark.asyncio
async def test_public_pricing_catalog_uses_locked_launch_prices(client):
    response = await client.get("/api/billing/catalog")
    assert response.status_code == 200
    data = response.json()

    prices = {
        (item["plan"], item["interval"]): item["amount_minor"]
        for item in data["prices"]
    }
    assert prices[("free", "none")] == 0
    assert prices[("pro", "monthly")] == 9_900
    assert prices[("pro", "annual")] == 99_900
    assert prices[("max", "monthly")] == 34_900
    assert ("max", "annual") not in prices
    assert data["pro_annual_saving_minor"] == 18_900


@pytest.mark.asyncio
async def test_user_without_subscription_is_free(client, auth_headers):
    response = await client.get("/api/billing/entitlements", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()

    assert data["plan"] == "free"
    assert data["status"] == "free"
    assert data["billing_interval"] == "none"
    assert data["capabilities"]["rules"] is False
    assert data["capabilities"]["advanced_reports"] is False
    assert data["limits"]["accounts"] == 3
    assert data["limits"]["ai_actions_monthly"] == 5


@pytest.mark.asyncio
async def test_active_pro_subscription_is_resolved_server_side(
    client, session, auth_headers, test_user
):
    subscription = Subscription(
        user_id=test_user.id,
        plan=PlanId.PRO.value,
        status=SubscriptionStatus.ACTIVE.value,
        billing_interval=BillingInterval.MONTHLY.value,
        current_period_start=datetime.now(timezone.utc),
        current_period_end=datetime.now(timezone.utc) + timedelta(days=30),
    )
    session.add(subscription)
    await session.commit()

    response = await client.get("/api/billing/entitlements", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()

    assert data["plan"] == "pro"
    assert data["capabilities"]["rules"] is True
    assert data["capabilities"]["advanced_reports"] is True
    assert data["capabilities"]["business_workspaces"] is False
    assert data["limits"]["accounts"] == 25


def test_expired_or_invalid_paid_state_fails_closed_to_free():
    expired = Subscription(
        plan=PlanId.MAX.value,
        status=SubscriptionStatus.EXPIRED.value,
        billing_interval=BillingInterval.MONTHLY.value,
    )
    assert effective_plan(expired) is PlanId.FREE

    past_due = Subscription(
        plan=PlanId.PRO.value,
        status=SubscriptionStatus.PAST_DUE.value,
        billing_interval=BillingInterval.MONTHLY.value,
    )
    assert effective_plan(past_due) is PlanId.FREE


def test_canceled_plan_only_remains_effective_until_paid_period_end():
    now = datetime.now(timezone.utc)
    still_paid = Subscription(
        plan=PlanId.PRO.value,
        status=SubscriptionStatus.CANCELED.value,
        billing_interval=BillingInterval.ANNUAL.value,
        current_period_end=now + timedelta(days=1),
    )
    expired = Subscription(
        plan=PlanId.PRO.value,
        status=SubscriptionStatus.CANCELED.value,
        billing_interval=BillingInterval.ANNUAL.value,
        current_period_end=now - timedelta(seconds=1),
    )

    assert effective_plan(still_paid, now=now) is PlanId.PRO
    assert effective_plan(expired, now=now) is PlanId.FREE
