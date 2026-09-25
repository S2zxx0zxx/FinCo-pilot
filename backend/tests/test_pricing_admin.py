from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.pricing_offer import PricingAuditEvent


@pytest.mark.asyncio
async def test_founder_campaign_public_status_contains_only_real_zero_counts(
    client: AsyncClient,
    test_user,
) -> None:
    response = await client.get("/api/billing/founder-campaign")
    assert response.status_code == 200
    data = response.json()
    assert data["state"] == "scheduled"
    assert data["live"] is False
    assert data["total_capacity"] == 25_000
    assert data["total_claimed"] == 0
    assert data["total_held"] == 0
    assert data["presale_starts_at"] is None
    assert data["public_launch_at"] is None


@pytest.mark.asyncio
async def test_regular_user_cannot_mutate_pricing_campaign(
    client: AsyncClient,
    auth_headers: dict,
) -> None:
    response = await client.patch(
        "/api/admin/pricing/campaign",
        headers=auth_headers,
        json={"expected_version": 1, "state": "paused"},
    )
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_admin_can_schedule_and_activate_campaign_with_audit(
    client: AsyncClient,
    admin_auth_headers: dict,
    session: AsyncSession,
    test_superuser,
) -> None:
    current = await client.get(
        "/api/admin/pricing/campaign",
        headers=admin_auth_headers,
    )
    assert current.status_code == 200
    version = current.json()["version"]

    now = datetime.now(timezone.utc)
    body = {
        "expected_version": version,
        "state": "active",
        "presale_starts_at": (now + timedelta(hours=1)).isoformat(),
        "presale_ends_at": (now + timedelta(days=5)).isoformat(),
        "public_launch_at": (now + timedelta(days=7)).isoformat(),
    }
    updated = await client.patch(
        "/api/admin/pricing/campaign",
        headers=admin_auth_headers,
        json=body,
    )
    assert updated.status_code == 200, updated.text
    data = updated.json()
    assert data["state"] == "active"
    assert data["version"] == version + 1
    assert data["updated_by_user_id"] == str(test_superuser.id)

    events = (
        await session.execute(
            select(PricingAuditEvent).where(
                PricingAuditEvent.event_type == "pricing_campaign_updated"
            )
        )
    ).scalars().all()
    assert len(events) == 1
    assert events[0].actor_user_id == test_superuser.id


@pytest.mark.asyncio
async def test_stale_admin_campaign_version_is_rejected(
    client: AsyncClient,
    admin_auth_headers: dict,
    test_superuser,
) -> None:
    current = await client.get(
        "/api/admin/pricing/campaign",
        headers=admin_auth_headers,
    )
    version = current.json()["version"]
    now = datetime.now(timezone.utc)

    first = await client.patch(
        "/api/admin/pricing/campaign",
        headers=admin_auth_headers,
        json={
            "expected_version": version,
            "presale_starts_at": (now + timedelta(hours=1)).isoformat(),
            "presale_ends_at": (now + timedelta(days=4)).isoformat(),
            "public_launch_at": (now + timedelta(days=5)).isoformat(),
        },
    )
    assert first.status_code == 200

    stale = await client.patch(
        "/api/admin/pricing/campaign",
        headers=admin_auth_headers,
        json={"expected_version": version, "state": "closed"},
    )
    assert stale.status_code == 409


@pytest.mark.asyncio
async def test_provider_catalog_reports_missing_ids_without_fake_provider_state(
    client: AsyncClient,
    admin_auth_headers: dict,
    monkeypatch,
) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "razorpay_plan_pro_monthly_id", "")
    monkeypatch.setattr(settings, "razorpay_plan_pro_annual_id", "")
    monkeypatch.setattr(settings, "razorpay_plan_max_monthly_id", "")

    response = await client.get(
        "/api/admin/pricing/provider-catalog",
        headers=admin_auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["catalog_version"] == "v1"
    assert len(data["plans"]) == 3
    assert all(item["configured"] is False for item in data["plans"])
    assert all(item["valid"] is None for item in data["plans"])


@pytest.mark.asyncio
async def test_tax_display_mode_is_exposed_and_never_invented(
    client: AsyncClient,
    monkeypatch,
) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "billing_tax_display_mode", "unconfigured")
    response = await client.get("/api/billing/catalog")
    assert response.status_code == 200
    assert response.json()["tax_display_mode"] == "unconfigured"
