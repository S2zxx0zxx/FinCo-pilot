import uuid
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.billing.enums import PlanId
from app.schemas.support import SupportCategory
from app.services import support_service


def test_high_severity_support_beats_commercial_tier():
    free_incident = support_service.support_routing(
        PlanId.FREE, SupportCategory.ACCOUNT_ACCESS
    )
    max_feature = support_service.support_routing(
        PlanId.MAX, SupportCategory.FEATURE_REQUEST
    )

    assert free_incident.provider_priority == "High"
    assert max_feature.provider_priority == "Medium"
    assert free_incident.support_tier == "standard"
    assert max_feature.support_tier == "highest_priority"


def test_sensitive_content_blocks_high_confidence_secrets():
    found = support_service.find_sensitive_content(
        "Login issue",
        "password=do-not-send-this and bearer abcdefghijklmnopqrstuvwxyz",
    )
    assert "authentication secret" in found
    assert "bearer token" in found


def test_zoho_api_domain_accepts_only_exact_documented_host():
    fallback = "https://desk.zoho.in"
    assert (
        support_service._trusted_zoho_api_domain("https://desk.zoho.eu", fallback)
        == "https://desk.zoho.eu"
    )
    assert (
        support_service._trusted_zoho_api_domain(
            "https://desk.zoho.evil.example", fallback
        )
        == fallback
    )
    assert (
        support_service._trusted_zoho_api_domain(
            "https://desk.zoho.in.evil.example", fallback
        )
        == fallback
    )


class _CounterRedis:
    def __init__(self):
        self.counts: dict[str, int] = {}
        self.expiries: dict[str, int] = {}

    async def incr(self, key: str) -> int:
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key]

    async def expire(self, key: str, seconds: int) -> None:
        self.expiries[key] = seconds


@pytest.mark.asyncio
async def test_support_rate_limit_is_bounded_to_hour_bucket(monkeypatch):
    redis = _CounterRedis()

    async def fake_redis():
        return redis

    monkeypatch.setattr(support_service, "get_redis", fake_redis)
    monkeypatch.setattr(
        support_service,
        "get_settings",
        lambda: SimpleNamespace(support_rate_limit_per_hour=2),
    )
    monkeypatch.setattr(support_service.time, "time", lambda: 3_610.0)

    user_id = uuid.uuid4()
    await support_service.enforce_support_rate_limit(user_id)
    await support_service.enforce_support_rate_limit(user_id)

    with pytest.raises(HTTPException) as exc:
        await support_service.enforce_support_rate_limit(user_id)

    assert exc.value.status_code == 429
    assert 1 <= int(exc.value.headers["Retry-After"]) <= 3600
    assert len(redis.counts) == 1
