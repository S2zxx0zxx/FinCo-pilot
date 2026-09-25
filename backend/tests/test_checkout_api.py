"""
Tests for backend/app/api/checkout.py

All Razorpay SDK calls are mocked — no real network calls required.
No real credentials are used: fake values only.
"""
from __future__ import annotations

import hashlib
import hmac
import uuid
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient

from app.billing.enums import BillingInterval, PlanId
from app.billing.pricing import PRICE_CATALOG
from app.core.config import get_settings
from app.models.user import User

# ---------------------------------------------------------------------------
# Shared fake credentials — NEVER real Razorpay keys
# ---------------------------------------------------------------------------
_FAKE_KEY_ID = "rzp_test_example_fake_key"
_FAKE_KEY_SECRET = "test-secret-not-real-xxxxxxxxxxxxxxxx"
_FAKE_ORDER_ID = "order_FakeRazorpayId12345"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sig(order_id: str, payment_id: str, secret: str = _FAKE_KEY_SECRET) -> str:
    """Reproduce Razorpay's HMAC-SHA256 signature."""
    body = f"{order_id}|{payment_id}"
    return hmac.new(
        key=secret.encode("utf-8"),
        msg=body.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()


def _mock_order(plan: PlanId, interval: BillingInterval) -> dict[str, Any]:
    price = PRICE_CATALOG[(plan, interval)]
    return {
        "id": _FAKE_ORDER_ID,
        "amount": price.amount_minor,
        "currency": "INR",
    }


# ---------------------------------------------------------------------------
# Fixture: patch settings to enable checkout + supply fake credentials
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=False)
def checkout_enabled(monkeypatch):
    """Patch settings so checkout is enabled with fake credentials."""
    from pydantic import SecretStr
    settings = get_settings()
    monkeypatch.setattr(settings, "billing_checkout_enabled", True)
    monkeypatch.setattr(settings, "razorpay_key_id", _FAKE_KEY_ID)
    monkeypatch.setattr(settings, "razorpay_key_secret", SecretStr(_FAKE_KEY_SECRET))
    yield settings


# ---------------------------------------------------------------------------
# 1. Checkout disabled → rejected
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_order_checkout_disabled(client: AsyncClient, auth_headers: dict):
    """When BILLING_CHECKOUT_ENABLED is false (default) requests must be rejected."""
    settings = get_settings()
    original = settings.billing_checkout_enabled
    settings.billing_checkout_enabled = False
    try:
        response = await client.post(
            "/api/checkout/create-order",
            json={"plan": "pro", "interval": "monthly"},
            headers=auth_headers,
        )
        assert response.status_code == 503, response.text
    finally:
        settings.billing_checkout_enabled = original


@pytest.mark.asyncio
async def test_verify_payment_checkout_disabled(client: AsyncClient, auth_headers: dict):
    settings = get_settings()
    original = settings.billing_checkout_enabled
    settings.billing_checkout_enabled = False
    try:
        response = await client.post(
            "/api/checkout/verify-payment",
            json={
                "razorpay_payment_id": "pay_x",
                "razorpay_order_id": "order_x",
                "razorpay_signature": "sig",
            },
            headers=auth_headers,
        )
        assert response.status_code == 503, response.text
    finally:
        settings.billing_checkout_enabled = original


# ---------------------------------------------------------------------------
# 2. Unauthenticated → rejected
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_order_unauthenticated(client: AsyncClient, checkout_enabled):
    response = await client.post(
        "/api/checkout/create-order",
        json={"plan": "pro", "interval": "monthly"},
    )
    assert response.status_code == 401, response.text


@pytest.mark.asyncio
async def test_verify_payment_unauthenticated(client: AsyncClient, checkout_enabled):
    response = await client.post(
        "/api/checkout/verify-payment",
        json={
            "razorpay_payment_id": "pay_x",
            "razorpay_order_id": "order_x",
            "razorpay_signature": "sig",
        },
    )
    assert response.status_code == 401, response.text


# ---------------------------------------------------------------------------
# 3–5. Valid authenticated orders — amount is server-calculated
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_order_pro_monthly(
    client: AsyncClient,
    auth_headers: dict,
    checkout_enabled,
):
    expected_amount = PRICE_CATALOG[(PlanId.PRO, BillingInterval.MONTHLY)].amount_minor
    mock_client = MagicMock()
    mock_client.order.create.return_value = _mock_order(PlanId.PRO, BillingInterval.MONTHLY)

    with patch("app.api.checkout._get_razorpay_client", return_value=mock_client):
        resp = await client.post(
            "/api/checkout/create-order",
            json={"plan": "pro", "interval": "monthly"},
            headers=auth_headers,
        )

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["amount"] == expected_amount
    assert data["currency"] == "INR"
    assert data["plan"] == "pro"
    assert data["interval"] == "monthly"
    assert data["order_id"] == _FAKE_ORDER_ID


@pytest.mark.asyncio
async def test_create_order_pro_annual(
    client: AsyncClient,
    auth_headers: dict,
    checkout_enabled,
):
    expected_amount = PRICE_CATALOG[(PlanId.PRO, BillingInterval.ANNUAL)].amount_minor
    mock_client = MagicMock()
    mock_client.order.create.return_value = _mock_order(PlanId.PRO, BillingInterval.ANNUAL)

    with patch("app.api.checkout._get_razorpay_client", return_value=mock_client):
        resp = await client.post(
            "/api/checkout/create-order",
            json={"plan": "pro", "interval": "annual"},
            headers=auth_headers,
        )

    assert resp.status_code == 200, resp.text
    assert resp.json()["amount"] == expected_amount


@pytest.mark.asyncio
async def test_create_order_max_monthly(
    client: AsyncClient,
    auth_headers: dict,
    checkout_enabled,
):
    expected_amount = PRICE_CATALOG[(PlanId.MAX, BillingInterval.MONTHLY)].amount_minor
    mock_client = MagicMock()
    mock_client.order.create.return_value = _mock_order(PlanId.MAX, BillingInterval.MONTHLY)

    with patch("app.api.checkout._get_razorpay_client", return_value=mock_client):
        resp = await client.post(
            "/api/checkout/create-order",
            json={"plan": "max", "interval": "monthly"},
            headers=auth_headers,
        )

    assert resp.status_code == 200, resp.text
    assert resp.json()["amount"] == expected_amount


# ---------------------------------------------------------------------------
# 6. Free plan checkout rejected
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_order_free_rejected(
    client: AsyncClient,
    auth_headers: dict,
    checkout_enabled,
):
    resp = await client.post(
        "/api/checkout/create-order",
        json={"plan": "free", "interval": "none"},
        headers=auth_headers,
    )
    assert resp.status_code == 400, resp.text


# ---------------------------------------------------------------------------
# 7. Max annual rejected
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_order_max_annual_rejected(
    client: AsyncClient,
    auth_headers: dict,
    checkout_enabled,
):
    resp = await client.post(
        "/api/checkout/create-order",
        json={"plan": "max", "interval": "annual"},
        headers=auth_headers,
    )
    assert resp.status_code == 400, resp.text


# ---------------------------------------------------------------------------
# 8. Unknown plan rejected
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_order_unknown_plan_rejected(
    client: AsyncClient,
    auth_headers: dict,
    checkout_enabled,
):
    resp = await client.post(
        "/api/checkout/create-order",
        json={"plan": "enterprise", "interval": "monthly"},
        headers=auth_headers,
    )
    # pydantic validation should reject this at 422
    assert resp.status_code == 422, resp.text


# ---------------------------------------------------------------------------
# 9–10. Browser cannot supply custom amount; server uses catalog amount
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_browser_cannot_supply_amount(
    client: AsyncClient,
    auth_headers: dict,
    checkout_enabled,
):
    """Extra 'amount' field from browser must be ignored; server uses catalog."""
    expected_amount = PRICE_CATALOG[(PlanId.PRO, BillingInterval.MONTHLY)].amount_minor
    mock_client = MagicMock()
    mock_client.order.create.return_value = _mock_order(PlanId.PRO, BillingInterval.MONTHLY)

    with patch("app.api.checkout._get_razorpay_client", return_value=mock_client):
        resp = await client.post(
            "/api/checkout/create-order",
            # Attacker tries to inject a custom amount
            json={"plan": "pro", "interval": "monthly", "amount": 1, "currency": "USD"},
            headers=auth_headers,
        )

    assert resp.status_code == 200, resp.text
    data = resp.json()
    # Catalog amount must be used, not the browser-supplied 1
    assert data["amount"] == expected_amount
    assert data["currency"] == "INR"

    # Verify the SDK was called with the catalog amount
    call_kwargs = mock_client.order.create.call_args[1]["data"]
    assert call_kwargs["amount"] == expected_amount
    assert call_kwargs["currency"] == "INR"


# ---------------------------------------------------------------------------
# 11. Razorpay provider auth failure → 502, no secret in response
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_provider_auth_failure(
    client: AsyncClient,
    auth_headers: dict,
    checkout_enabled,
):
    mock_client = MagicMock()
    mock_client.order.create.side_effect = Exception("AuthenticationError: key invalid")

    with patch("app.api.checkout._get_razorpay_client", return_value=mock_client):
        resp = await client.post(
            "/api/checkout/create-order",
            json={"plan": "pro", "interval": "monthly"},
            headers=auth_headers,
        )

    assert resp.status_code == 502, resp.text
    body = resp.text
    # Must not leak the fake secret or key
    assert _FAKE_KEY_SECRET not in body
    assert _FAKE_KEY_ID not in body


# ---------------------------------------------------------------------------
# 12. Provider / network failure → 502
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_provider_network_failure(
    client: AsyncClient,
    auth_headers: dict,
    checkout_enabled,
):
    mock_client = MagicMock()
    mock_client.order.create.side_effect = Exception("ConnectionError: timed out")

    with patch("app.api.checkout._get_razorpay_client", return_value=mock_client):
        resp = await client.post(
            "/api/checkout/create-order",
            json={"plan": "pro", "interval": "monthly"},
            headers=auth_headers,
        )

    assert resp.status_code == 502, resp.text


# ---------------------------------------------------------------------------
# 13. Valid payment signature
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_verify_valid_signature(
    client: AsyncClient,
    auth_headers: dict,
    checkout_enabled,
):
    payment_id = "pay_FakeValidPayment123"
    order_id = _FAKE_ORDER_ID
    sig = _sig(order_id, payment_id)

    resp = await client.post(
        "/api/checkout/verify-payment",
        json={
            "razorpay_payment_id": payment_id,
            "razorpay_order_id": order_id,
            "razorpay_signature": sig,
        },
        headers=auth_headers,
    )

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "verified"


# ---------------------------------------------------------------------------
# 14. Invalid payment signature → 400
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_verify_invalid_signature(
    client: AsyncClient,
    auth_headers: dict,
    checkout_enabled,
):
    resp = await client.post(
        "/api/checkout/verify-payment",
        json={
            "razorpay_payment_id": "pay_something",
            "razorpay_order_id": _FAKE_ORDER_ID,
            "razorpay_signature": "totally-wrong-signature",
        },
        headers=auth_headers,
    )

    assert resp.status_code == 400, resp.text


# ---------------------------------------------------------------------------
# 15. Missing signature fields → 422
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_verify_missing_fields(
    client: AsyncClient,
    auth_headers: dict,
    checkout_enabled,
):
    resp = await client.post(
        "/api/checkout/verify-payment",
        json={"razorpay_payment_id": "pay_x"},
        headers=auth_headers,
    )
    assert resp.status_code == 422, resp.text


# ---------------------------------------------------------------------------
# 20. Verified payment does NOT mutate user entitlement
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_verified_payment_does_not_activate_plan(
    client: AsyncClient,
    auth_headers: dict,
    auth_token: str,
    checkout_enabled,
    test_user: User,
):
    """Successful verify-payment must not change the user's subscription plan."""
    payment_id = "pay_FakeDoNotActivate"
    order_id = _FAKE_ORDER_ID
    sig = _sig(order_id, payment_id)

    resp = await client.post(
        "/api/checkout/verify-payment",
        json={
            "razorpay_payment_id": payment_id,
            "razorpay_order_id": order_id,
            "razorpay_signature": sig,
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text

    # Entitlements endpoint should still return the plan from the DB (max,
    # set by the shared test_user fixture), not a new pro/max upgrade.
    ent_resp = await client.get(
        "/api/billing/entitlements",
        headers=auth_headers,
    )
    assert ent_resp.status_code == 200
    ent_data = ent_resp.json()
    # test_user fixture uses "max" plan; verify-payment must not change it
    assert ent_data["plan"] == "max"


# ---------------------------------------------------------------------------
# 21. Credentials absent → fail closed
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_missing_credentials_fail_closed(
    client: AsyncClient,
    auth_headers: dict,
    monkeypatch,
):
    """checkout is enabled but credentials are absent → 503."""
    from pydantic import SecretStr
    settings = get_settings()
    monkeypatch.setattr(settings, "billing_checkout_enabled", True)
    monkeypatch.setattr(settings, "razorpay_key_id", "")
    monkeypatch.setattr(settings, "razorpay_key_secret", SecretStr(""))

    with patch("app.api.checkout.razorpay", None, create=True):
        resp = await client.post(
            "/api/checkout/create-order",
            json={"plan": "pro", "interval": "monthly"},
            headers=auth_headers,
        )

    assert resp.status_code == 503, resp.text
    # Must not expose secrets in error body
    assert "secret" not in resp.text.lower()
