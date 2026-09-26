import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.billing.enums import BillingInterval, Metric, PlanId, SubscriptionStatus
from app.billing.service import effective_plan
from app.billing.usage import consume_monthly
from app.models.subscription import Subscription
from app.models.user import User
from app.models.workspace import Workspace


async def _set_plan(
    session: AsyncSession,
    user: User,
    plan: PlanId,
    *,
    interval: BillingInterval = BillingInterval.MONTHLY,
) -> Subscription:
    result = await session.execute(select(Subscription).where(Subscription.user_id == user.id))
    sub = result.scalar_one_or_none()
    if sub is None:
        sub = Subscription(user_id=user.id)
        session.add(sub)
    sub.plan = plan.value
    sub.status = SubscriptionStatus.ACTIVE.value if plan is not PlanId.FREE else SubscriptionStatus.FREE.value
    sub.billing_interval = interval.value if plan is not PlanId.FREE else BillingInterval.NONE.value
    sub.current_period_start = datetime.now(timezone.utc)
    sub.current_period_end = datetime.now(timezone.utc) + timedelta(days=31)
    await session.commit()
    return sub


@pytest.mark.asyncio
async def test_public_pricing_catalog_uses_locked_launch_prices(client: AsyncClient):
    response = await client.get("/api/billing/catalog")
    assert response.status_code == 200
    data = response.json()
    prices = {(item["plan"], item["interval"]): item["amount_minor"] for item in data["prices"]}
    assert prices[("free", "none")] == 0
    assert prices[("pro", "monthly")] == 9_900
    assert prices[("pro", "annual")] == 99_900
    assert prices[("max", "monthly")] == 34_900
    assert ("max", "annual") not in prices
    assert data["pro_annual_saving_minor"] == 18_900


@pytest.mark.asyncio
async def test_client_plan_fields_cannot_change_server_entitlements(
    client: AsyncClient,
    auth_headers: dict,
    session: AsyncSession,
    test_user: User,
):
    await _set_plan(session, test_user, PlanId.FREE)
    response = await client.get(
        "/api/billing/entitlements?plan=max&is_pro=true",
        headers={**auth_headers, "X-Plan": "max"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["plan"] == "free"
    assert data["status"] == "free"
    assert data["capabilities"]["rules"] is False
    assert data["capabilities"]["advanced_reports"] is False
    assert data["limits"]["accounts"] == 3
    assert data["limits"]["ai_actions_monthly"] == 0


@pytest.mark.asyncio
async def test_active_pro_subscription_is_resolved_server_side(
    client: AsyncClient,
    session: AsyncSession,
    auth_headers: dict,
    test_user: User,
):
    await _set_plan(session, test_user, PlanId.PRO)
    response = await client.get("/api/billing/entitlements", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["plan"] == "pro"
    assert data["capabilities"]["rules"] is True
    assert data["capabilities"]["advanced_reports"] is True
    assert data["capabilities"]["business_workspaces"] is False
    assert data["limits"]["accounts"] == 25


@pytest.mark.asyncio
async def test_free_account_quota_cannot_be_bypassed_via_direct_api(
    client: AsyncClient,
    auth_headers: dict,
    session: AsyncSession,
    test_user: User,
):
    await _set_plan(session, test_user, PlanId.FREE)
    for index in range(3):
        response = await client.post(
            "/api/accounts",
            headers=auth_headers,
            json={"name": f"Wallet {index}", "type": "checking", "balance": "0"},
        )
        assert response.status_code == 201, response.text

    blocked = await client.post(
        "/api/accounts?plan=max",
        headers={**auth_headers, "X-Plan": "max"},
        json={
            "name": "Fourth wallet",
            "type": "checking",
            "balance": "0",
            "plan": "max",
            "is_pro": True,
        },
    )
    assert blocked.status_code == 409
    detail = blocked.json()["detail"]
    assert detail["code"] == "PLAN_LIMIT_REACHED"
    assert detail["metric"] == "accounts"
    assert detail["current_plan"] == "free"
    assert detail["required_plan"] == "pro"


@pytest.mark.asyncio
async def test_free_core_copilot_is_available_without_unlocking_advanced_agents(
    client: AsyncClient,
    auth_headers: dict,
    session: AsyncSession,
    test_user: User,
):
    await _set_plan(session, test_user, PlanId.FREE)

    core = await client.get("/api/agents/copilot", headers=auth_headers)
    assert core.status_code == 200, core.text
    body = core.json()
    assert body["name"] == "FinCo Copilot"
    assert body["extra"]["kind"] == "core_copilot"
    assert body["extra"]["system_managed"] is True

    history = await client.get(
        "/api/agents/conversations",
        params={"agent_id": body["id"]},
        headers=auth_headers,
    )
    assert history.status_code == 200, history.text

    advanced = await client.get("/api/agents", headers=auth_headers)
    assert advanced.status_code == 403
    detail = advanced.json()["detail"]
    assert detail["code"] == "ENTITLEMENT_REQUIRED"
    assert detail["capability"] == "agents_automation"


@pytest.mark.asyncio
async def test_free_rule_mutation_is_blocked_but_read_is_available(
    client: AsyncClient,
    auth_headers: dict,
    session: AsyncSession,
    test_user: User,
):
    await _set_plan(session, test_user, PlanId.FREE)
    listing = await client.get("/api/rules", headers=auth_headers)
    assert listing.status_code == 200
    blocked = await client.post(
        "/api/rules",
        headers=auth_headers,
        json={
            "name": "Bypass attempt",
            "conditions_op": "and",
            "conditions": [{"field": "description", "op": "contains", "value": "coffee"}],
            "actions": [{"op": "append_notes", "value": "x"}],
            "is_pro": True,
            "plan": "max",
        },
    )
    assert blocked.status_code == 403
    detail = blocked.json()["detail"]
    assert detail["code"] == "ENTITLEMENT_REQUIRED"
    assert detail["capability"] == "rules"
    assert detail["required_plan"] == "pro"


@pytest.mark.asyncio
async def test_free_cannot_create_business_workspace_with_forged_plan(
    client: AsyncClient,
    auth_headers: dict,
    session: AsyncSession,
    test_user: User,
):
    await _set_plan(session, test_user, PlanId.FREE)
    blocked = await client.post(
        "/api/workspaces",
        headers=auth_headers,
        json={
            "name": "Forged business",
            "kind": "business",
            "self_membership": True,
            "plan": "max",
            "is_max": True,
        },
    )
    assert blocked.status_code == 403
    assert blocked.json()["detail"]["capability"] == "business_workspaces"


@pytest.mark.asyncio
async def test_pro_unlocks_advanced_reports(
    client: AsyncClient,
    auth_headers: dict,
    session: AsyncSession,
    test_user: User,
):
    await _set_plan(session, test_user, PlanId.PRO)
    response = await client.get("/api/reports/net-worth", headers=auth_headers)
    assert response.status_code == 200, response.text


@pytest.mark.asyncio
async def test_max_can_create_business_workspace(
    client: AsyncClient,
    auth_headers: dict,
    session: AsyncSession,
    test_user: User,
):
    await _set_plan(session, test_user, PlanId.MAX)
    response = await client.post(
        "/api/workspaces",
        headers=auth_headers,
        json={"name": "Studio", "kind": "business", "self_membership": True},
    )
    assert response.status_code == 201, response.text
    assert response.json()["kind"] == "business"


@pytest.mark.asyncio
async def test_monthly_counter_is_deletion_proof_server_state(
    session: AsyncSession,
    test_user: User,
    test_workspace: Workspace,
):
    await _set_plan(session, test_user, PlanId.FREE)
    test_workspace.billing_owner_user_id = test_user.id
    session.add(test_workspace)
    await session.commit()
    await consume_monthly(session, test_workspace, Metric.IMPORTS_MONTHLY)
    await consume_monthly(session, test_workspace, Metric.IMPORTS_MONTHLY)
    await session.commit()
    with pytest.raises(HTTPException) as exc:
        await consume_monthly(session, test_workspace, Metric.IMPORTS_MONTHLY)
    assert exc.value.status_code == 409
    detail = exc.value.detail
    assert isinstance(detail, dict)
    assert detail.get("metric") == "imports_monthly"


@pytest.mark.parametrize(
    ("status", "period_offset_days", "expected"),
    [
        (SubscriptionStatus.ACTIVE, 10, PlanId.PRO),
        (SubscriptionStatus.GRACE, 1, PlanId.PRO),
        (SubscriptionStatus.PAST_DUE, 10, PlanId.FREE),
        (SubscriptionStatus.EXPIRED, -1, PlanId.FREE),
        (SubscriptionStatus.CANCELED, 2, PlanId.PRO),
        (SubscriptionStatus.CANCELED, -1, PlanId.FREE),
    ],
)
def test_effective_plan_status_and_period_rules(status, period_offset_days, expected):
    sub = Subscription(
        user_id=uuid.uuid4(),
        plan=PlanId.PRO.value,
        status=status.value,
        billing_interval=BillingInterval.MONTHLY.value,
        current_period_end=datetime.now(timezone.utc) + timedelta(days=period_offset_days),
    )
    assert effective_plan(sub) is expected
