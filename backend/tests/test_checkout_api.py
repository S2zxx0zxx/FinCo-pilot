"""Security and offer-reservation tests for Razorpay checkout.

All provider calls are mocked. The suite never performs a real payment and never
contains real credentials.
"""

from __future__ import annotations

import hashlib
import hmac
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient
from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.billing.offers import CampaignState, ReservationStatus
from app.core.config import get_settings
from app.models.pricing_offer import (
    CheckoutReservation,
    FoundingMember,
    PricingCampaign,
)
from app.models.subscription import Subscription
from app.models.user import User

_FAKE_KEY_ID = "rzp_test_example_fake_key"
_FAKE_SECRET = "test-secret-not-real-xxxxxxxxxxxxxxxx"
_ORDER_ID = "order_FincoSynthetic123"
_PAYMENT_ID = "pay_FincoSynthetic123"


def _sig(
    order_id: str = _ORDER_ID,
    payment_id: str = _PAYMENT_ID,
    secret: str = _FAKE_SECRET,
) -> str:
    return hmac.new(
        secret.encode(),
        f"{order_id}|{payment_id}".encode(),
        hashlib.sha256,
    ).hexdigest()


@pytest.fixture
def checkout_enabled(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "billing_checkout_enabled", True)
    monkeypatch.setattr(settings, "billing_offer_reservation_ttl_seconds", 600)
    monkeypatch.setattr(settings, "razorpay_key_id", _FAKE_KEY_ID)
    monkeypatch.setattr(settings, "razorpay_key_secret", SecretStr(_FAKE_SECRET))
    return settings


def _creation_client(order_id: str = _ORDER_ID) -> MagicMock:
    client = MagicMock()

    def create(*, data: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": order_id,
            "amount": data["amount"],
            "currency": data["currency"],
            "notes": data.get("notes", {}),
        }

    client.order.create.side_effect = create
    return client


async def _start_order(
    client: AsyncClient,
    auth_headers: dict,
    *,
    plan: str = "pro",
    interval: str = "monthly",
    provider_client: MagicMock | None = None,
    extra: dict[str, Any] | None = None,
):
    provider = provider_client or _creation_client()
    body: dict[str, Any] = {"plan": plan, "interval": interval}
    if extra:
        body.update(extra)
    with patch("app.api.checkout._get_razorpay_client", return_value=provider):
        response = await client.post(
            "/api/checkout/create-order",
            json=body,
            headers=auth_headers,
        )
    return response, provider


async def _reservation(
    session: AsyncSession,
    reservation_id: str,
) -> CheckoutReservation:
    row = await session.get(CheckoutReservation, uuid.UUID(reservation_id))
    assert row is not None
    return row


def _provider_order(
    reservation: CheckoutReservation,
    user: User,
    *,
    amount: int | None = None,
    currency: str = "INR",
    notes_override: dict[str, str] | None = None,
) -> dict[str, Any]:
    notes = {
        "fincopilot_reservation_id": str(reservation.id),
        "fincopilot_user_id": str(user.id),
        "fincopilot_plan": reservation.plan,
        "fincopilot_interval": reservation.billing_interval,
        "fincopilot_offer_code": reservation.offer_code,
        "fincopilot_campaign_version": reservation.campaign_version,
    }
    if notes_override:
        notes.update(notes_override)
    return {
        "id": reservation.provider_order_id,
        "amount": reservation.amount_minor if amount is None else amount,
        "currency": currency,
        "notes": notes,
    }


def _provider_payment(
    reservation: CheckoutReservation,
    *,
    amount: int | None = None,
    currency: str = "INR",
    status: str = "captured",
    order_id: str | None = None,
) -> dict[str, Any]:
    return {
        "id": _PAYMENT_ID,
        "order_id": order_id or reservation.provider_order_id,
        "amount": reservation.amount_minor if amount is None else amount,
        "currency": currency,
        "status": status,
    }


def _verification_client(
    reservation: CheckoutReservation,
    user: User,
    *,
    order: dict[str, Any] | None = None,
    payment: dict[str, Any] | None = None,
) -> MagicMock:
    provider = MagicMock()
    provider.order.fetch.return_value = order or _provider_order(reservation, user)
    provider.payment.fetch.return_value = payment or _provider_payment(reservation)
    return provider


async def _activate_founder_campaign(session: AsyncSession) -> PricingCampaign:
    now = datetime.now(timezone.utc)
    row = PricingCampaign(
        code="founder_v1",
        state=CampaignState.ACTIVE.value,
        catalog_version="v1",
        version=1,
        presale_starts_at=now - timedelta(hours=1),
        presale_ends_at=now + timedelta(days=5),
        public_launch_at=now + timedelta(days=7),
    )
    session.add(row)
    await session.commit()
    return row


@pytest.mark.asyncio
async def test_checkout_disabled_fails_closed(
    client: AsyncClient,
    auth_headers: dict,
) -> None:
    settings = get_settings()
    old = settings.billing_checkout_enabled
    settings.billing_checkout_enabled = False
    try:
        response = await client.post(
            "/api/checkout/create-order",
            json={"plan": "pro", "interval": "monthly"},
            headers=auth_headers,
        )
        assert response.status_code == 503
    finally:
        settings.billing_checkout_enabled = old


@pytest.mark.asyncio
async def test_unauthenticated_create_order_is_rejected(
    client: AsyncClient,
    checkout_enabled,
) -> None:
    response = await client.post(
        "/api/checkout/create-order",
        json={"plan": "pro", "interval": "monthly"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_server_owns_price_and_ignores_browser_amount(
    client: AsyncClient,
    auth_headers: dict,
    checkout_enabled,
) -> None:
    response, provider = await _start_order(
        client,
        auth_headers,
        extra={"amount": 1, "currency": "USD", "receipt": "forged"},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["amount"] == 9_900
    assert data["currency"] == "INR"
    assert data["service_period_days"] == 60

    payload = provider.order.create.call_args.kwargs["data"]
    assert payload["amount"] == 9_900
    assert payload["currency"] == "INR"
    assert payload["receipt"] != "forged"


@pytest.mark.asyncio
async def test_free_and_max_annual_cannot_be_checked_out(
    client: AsyncClient,
    auth_headers: dict,
    checkout_enabled,
) -> None:
    free, _ = await _start_order(
        client, auth_headers, plan="free", interval="none"
    )
    assert free.status_code == 400

    max_annual, _ = await _start_order(
        client, auth_headers, plan="max", interval="annual"
    )
    assert max_annual.status_code == 400


@pytest.mark.asyncio
async def test_founder_wave_one_uses_real_19_rupee_reserved_price(
    client: AsyncClient,
    auth_headers: dict,
    checkout_enabled,
    session: AsyncSession,
    test_user: User,
) -> None:
    campaign = await _activate_founder_campaign(session)

    response, provider = await _start_order(client, auth_headers)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["amount"] == 1_900
    assert data["founder_wave"] == 1
    assert data["founder_position"] == 1
    assert data["renewal_amount_minor"] == 9_900
    assert data["service_period_days"] == 60
    assert campaign.public_launch_at is not None
    assert data["service_starts_at"] == campaign.public_launch_at.isoformat()

    payload = provider.order.create.call_args.kwargs["data"]
    assert payload["amount"] == 1_900
    assert payload["notes"]["fincopilot_offer_code"] == "founder_wave_1"
    assert "fincopilot_reservation_id" in payload["notes"]


@pytest.mark.asyncio
async def test_same_active_order_is_reused_without_provider_duplicate(
    client: AsyncClient,
    auth_headers: dict,
    checkout_enabled,
) -> None:
    first_provider = _creation_client()
    first, _ = await _start_order(
        client, auth_headers, provider_client=first_provider
    )
    assert first.status_code == 200

    second_provider = _creation_client("order_should_not_be_created")
    second, _ = await _start_order(
        client, auth_headers, provider_client=second_provider
    )
    assert second.status_code == 200
    assert second.json()["reservation_id"] == first.json()["reservation_id"]
    assert second.json()["order_id"] == first.json()["order_id"]
    second_provider.order.create.assert_not_called()


@pytest.mark.asyncio
async def test_provider_create_failure_releases_reservation(
    client: AsyncClient,
    auth_headers: dict,
    checkout_enabled,
    session: AsyncSession,
) -> None:
    provider = MagicMock()
    provider.order.create.side_effect = RuntimeError("synthetic provider outage")
    response, _ = await _start_order(
        client, auth_headers, provider_client=provider
    )
    assert response.status_code == 502

    rows = (
        await session.execute(select(CheckoutReservation))
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].status == ReservationStatus.CANCELLED.value
    assert rows[0].founder_position is None


@pytest.mark.asyncio
async def test_live_razorpay_key_is_fail_closed_until_webhook_fulfilment_exists(
    client: AsyncClient,
    auth_headers: dict,
    monkeypatch,
    session: AsyncSession,
) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "billing_checkout_enabled", True)
    monkeypatch.setattr(settings, "razorpay_key_id", "rzp_live_synthetic_not_real")
    monkeypatch.setattr(settings, "razorpay_key_secret", SecretStr("synthetic-live-secret-not-real"))

    response = await client.post(
        "/api/checkout/create-order",
        json={"plan": "pro", "interval": "monthly"},
        headers=auth_headers,
    )

    assert response.status_code == 503
    assert "live payment collection" in response.json()["detail"].lower()
    count = len((await session.execute(select(CheckoutReservation))).scalars().all())
    assert count == 0


@pytest.mark.asyncio
async def test_missing_provider_credentials_do_not_hold_capacity(
    client: AsyncClient,
    auth_headers: dict,
    monkeypatch,
    session: AsyncSession,
) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "billing_checkout_enabled", True)
    monkeypatch.setattr(settings, "razorpay_key_id", "")
    monkeypatch.setattr(settings, "razorpay_key_secret", SecretStr(""))

    response = await client.post(
        "/api/checkout/create-order",
        json={"plan": "pro", "interval": "monthly"},
        headers=auth_headers,
    )
    assert response.status_code == 503
    count = len((await session.execute(select(CheckoutReservation))).scalars().all())
    assert count == 0


@pytest.mark.asyncio
async def test_modal_cancel_releases_quote(
    client: AsyncClient,
    auth_headers: dict,
    checkout_enabled,
    session: AsyncSession,
) -> None:
    response, _ = await _start_order(client, auth_headers)
    assert response.status_code == 200

    cancelled = await client.post(
        "/api/checkout/cancel-reservation",
        json={"reservation_id": response.json()["reservation_id"]},
        headers=auth_headers,
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"

    reservation = await _reservation(session, response.json()["reservation_id"])
    assert reservation.status == ReservationStatus.CANCELLED.value


@pytest.mark.asyncio
async def test_invalid_signature_stops_before_provider_fetch(
    client: AsyncClient,
    auth_headers: dict,
    checkout_enabled,
) -> None:
    response, _ = await _start_order(client, auth_headers)
    assert response.status_code == 200

    provider = MagicMock()
    with patch("app.api.checkout._get_razorpay_client", return_value=provider):
        verified = await client.post(
            "/api/checkout/verify-payment",
            json={
                "razorpay_payment_id": _PAYMENT_ID,
                "razorpay_order_id": _ORDER_ID,
                "razorpay_signature": "wrong",
            },
            headers=auth_headers,
        )
    assert verified.status_code == 400
    provider.order.fetch.assert_not_called()


@pytest.mark.asyncio
async def test_captured_payment_full_verification_succeeds_without_entitlement_change(
    client: AsyncClient,
    auth_headers: dict,
    checkout_enabled,
    session: AsyncSession,
    test_user: User,
) -> None:
    created, _ = await _start_order(client, auth_headers)
    assert created.status_code == 200
    reservation = await _reservation(session, created.json()["reservation_id"])
    provider = _verification_client(reservation, test_user)

    sub_before = (
        await session.execute(
            select(Subscription).where(Subscription.user_id == test_user.id)
        )
    ).scalar_one()
    plan_before = sub_before.plan

    with patch("app.api.checkout._get_razorpay_client", return_value=provider):
        verified = await client.post(
            "/api/checkout/verify-payment",
            json={
                "razorpay_payment_id": _PAYMENT_ID,
                "razorpay_order_id": _ORDER_ID,
                "razorpay_signature": _sig(),
            },
            headers=auth_headers,
        )

    assert verified.status_code == 200, verified.text
    assert verified.json()["status"] == "verified"

    await session.refresh(reservation)
    assert reservation.status == ReservationStatus.VERIFIED.value
    assert reservation.provider_payment_id == _PAYMENT_ID

    await session.refresh(sub_before)
    assert sub_before.plan == plan_before


@pytest.mark.asyncio
async def test_authorized_but_not_captured_payment_does_not_claim_offer(
    client: AsyncClient,
    auth_headers: dict,
    checkout_enabled,
    session: AsyncSession,
    test_user: User,
) -> None:
    created, _ = await _start_order(client, auth_headers)
    reservation = await _reservation(session, created.json()["reservation_id"])
    provider = _verification_client(
        reservation,
        test_user,
        payment=_provider_payment(reservation, status="authorized"),
    )

    with patch("app.api.checkout._get_razorpay_client", return_value=provider):
        response = await client.post(
            "/api/checkout/verify-payment",
            json={
                "razorpay_payment_id": _PAYMENT_ID,
                "razorpay_order_id": _ORDER_ID,
                "razorpay_signature": _sig(),
            },
            headers=auth_headers,
        )
    assert response.status_code == 400
    assert "captured" in response.json()["detail"].lower()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("mutation", "expected_fragment"),
    [
        ("order_amount", "amount"),
        ("payment_amount", "amount"),
        ("order_currency", "currency"),
        ("payment_currency", "currency"),
        ("wrong_payment_order", "order"),
        ("wrong_user_note", "metadata"),
        ("wrong_reservation_note", "metadata"),
        ("wrong_offer_note", "metadata"),
    ],
)
async def test_verification_rejects_provider_or_metadata_mismatch(
    mutation: str,
    expected_fragment: str,
    client: AsyncClient,
    auth_headers: dict,
    checkout_enabled,
    session: AsyncSession,
    test_user: User,
) -> None:
    created, _ = await _start_order(client, auth_headers)
    reservation = await _reservation(session, created.json()["reservation_id"])

    order = _provider_order(reservation, test_user)
    payment = _provider_payment(reservation)

    if mutation == "order_amount":
        order["amount"] = 1
    elif mutation == "payment_amount":
        payment["amount"] = 1
    elif mutation == "order_currency":
        order["currency"] = "USD"
    elif mutation == "payment_currency":
        payment["currency"] = "USD"
    elif mutation == "wrong_payment_order":
        payment["order_id"] = "order_wrong"
    elif mutation == "wrong_user_note":
        order["notes"]["fincopilot_user_id"] = str(uuid.uuid4())
    elif mutation == "wrong_reservation_note":
        order["notes"]["fincopilot_reservation_id"] = str(uuid.uuid4())
    elif mutation == "wrong_offer_note":
        order["notes"]["fincopilot_offer_code"] = "forged_offer"

    provider = _verification_client(
        reservation,
        test_user,
        order=order,
        payment=payment,
    )
    with patch("app.api.checkout._get_razorpay_client", return_value=provider):
        response = await client.post(
            "/api/checkout/verify-payment",
            json={
                "razorpay_payment_id": _PAYMENT_ID,
                "razorpay_order_id": _ORDER_ID,
                "razorpay_signature": _sig(),
            },
            headers=auth_headers,
        )
    assert response.status_code == 400
    assert expected_fragment in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_provider_fetch_failure_is_generic_502(
    client: AsyncClient,
    auth_headers: dict,
    checkout_enabled,
) -> None:
    created, _ = await _start_order(client, auth_headers)
    assert created.status_code == 200

    provider = MagicMock()
    provider.order.fetch.side_effect = RuntimeError("private upstream detail")
    with patch("app.api.checkout._get_razorpay_client", return_value=provider):
        response = await client.post(
            "/api/checkout/verify-payment",
            json={
                "razorpay_payment_id": _PAYMENT_ID,
                "razorpay_order_id": _ORDER_ID,
                "razorpay_signature": _sig(),
            },
            headers=auth_headers,
        )
    assert response.status_code == 502
    assert "private upstream detail" not in response.text


@pytest.mark.asyncio
async def test_verification_is_idempotent_for_same_captured_payment(
    client: AsyncClient,
    auth_headers: dict,
    checkout_enabled,
    session: AsyncSession,
    test_user: User,
) -> None:
    created, _ = await _start_order(client, auth_headers)
    reservation = await _reservation(session, created.json()["reservation_id"])
    provider = _verification_client(reservation, test_user)
    payload = {
        "razorpay_payment_id": _PAYMENT_ID,
        "razorpay_order_id": _ORDER_ID,
        "razorpay_signature": _sig(),
    }

    with patch("app.api.checkout._get_razorpay_client", return_value=provider):
        first = await client.post(
            "/api/checkout/verify-payment",
            json=payload,
            headers=auth_headers,
        )
        second = await client.post(
            "/api/checkout/verify-payment",
            json=payload,
            headers=auth_headers,
        )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["reservation_id"] == second.json()["reservation_id"]


@pytest.mark.asyncio
async def test_founder_capture_creates_real_member_and_updates_public_counter(
    client: AsyncClient,
    auth_headers: dict,
    checkout_enabled,
    session: AsyncSession,
    test_user: User,
) -> None:
    await _activate_founder_campaign(session)
    created, _ = await _start_order(client, auth_headers)
    assert created.status_code == 200
    assert created.json()["amount"] == 1_900

    reservation = await _reservation(session, created.json()["reservation_id"])
    provider = _verification_client(reservation, test_user)
    with patch("app.api.checkout._get_razorpay_client", return_value=provider):
        verified = await client.post(
            "/api/checkout/verify-payment",
            json={
                "razorpay_payment_id": _PAYMENT_ID,
                "razorpay_order_id": _ORDER_ID,
                "razorpay_signature": _sig(),
            },
            headers=auth_headers,
        )
    assert verified.status_code == 200

    founder = await session.get(FoundingMember, test_user.id)
    assert founder is not None
    assert founder.wave == 1
    assert founder.founder_position == 1

    status = await client.get("/api/billing/founder-campaign")
    assert status.status_code == 200
    wave = status.json()["waves"][0]
    assert wave["claimed"] == 1
    assert wave["held"] == 0
    assert wave["available"] == 4_999
