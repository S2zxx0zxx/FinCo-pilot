"""Non-granting failure recovery; all provider responses are synthetic."""

import copy
from unittest.mock import patch
import pytest
from sqlalchemy import select, func
from app.billing import activation
from app.billing.checkout_status import owned_status
from app.core.config import get_settings
from app.models.payment_activation import PaymentActivation
from app.models.payment_webhook import PaymentWebhookEvent
from app.models.pricing_offer import CheckoutReservation
from app.models.subscription import Subscription
from tests.conftest import TestSessionLocal
from tests import test_payment_activation as activation_fixtures
from tests.test_payment_activation import receipt_for, NOW

purchase = activation_fixtures.purchase
enabled = activation_fixtures.enabled


@pytest.fixture(autouse=True)
def checkout_gate(monkeypatch):
    monkeypatch.setattr(get_settings(), "billing_checkout_enabled", True)


def setup(purchase, state="failed"):
    row, provider, order, payment = purchase
    captured = state in {"captured", "refunded"}
    payment.update(
        status=state,
        captured=captured,
        amount_refunded=9900 if state == "refunded" else 0,
        refund_status="full" if state == "refunded" else None,
    )
    order.update(
        status="paid" if captured else "attempted",
        attempts=1,
        amount_paid=9900 if captured else 0,
        amount_due=0 if captured else 9900,
    )
    provider.order.payments.return_value = {"entity": "collection", "count": 1, "items": [payment]}
    return row, provider, order, payment


@pytest.mark.parametrize(
    "state,expected",
    [
        ("failed", "failed"),
        ("created", "created"),
        ("authorized", "authorized"),
        ("captured", "captured"),
        ("refunded", "refund_review"),
    ],
)
async def test_fresh_states_are_observations_without_activation(purchase, state, expected):
    row, provider, _, _ = setup(purchase, state)
    async with TestSessionLocal() as session:
        result = await owned_status(session, row.user_id, provider)
        assert result["checkout"]["state"] == expected
        assert result["checkout"]["activation_confirmed"] is False
        assert await session.scalar(select(func.count()).select_from(PaymentActivation)) == 0
        sub = await session.scalar(select(Subscription).where(Subscription.user_id == row.user_id))
        assert sub is not None and sub.plan == "free"
    provider.order.create.assert_not_called()
    provider.payment.capture.assert_not_called()


@pytest.mark.parametrize(
    "change",
    [
        "count_bool",
        "missing",
        "duplicate",
        "foreign",
        "amount_bool",
        "wrong_currency",
        "captured_failed",
        "invoice",
        "wrong_receipt",
        "wrong_paid",
        "wrong_due",
        "wrong_attempts",
        "unknown_state",
        "over_refund",
        "refund_flag",
        "wrong_order_state",
    ],
)
async def test_invalid_inventory_stays_unresolved_and_never_posts(purchase, change):
    row, provider, order, payment = setup(purchase)
    collection = provider.order.payments.return_value
    if change == "count_bool":
        collection["count"] = True
    elif change == "missing":
        collection["items"] = []
    elif change == "duplicate":
        collection["items"].append(copy.deepcopy(payment))
        collection["count"] = 2
        order["attempts"] = 2
    elif change == "foreign":
        payment["order_id"] = "order_Other"
    elif change == "amount_bool":
        payment["amount"] = True
    elif change == "wrong_currency":
        payment["currency"] = "USD"
    elif change == "captured_failed":
        payment["captured"] = True
    elif change == "invoice":
        payment["invoice_id"] = "inv_Other"
    elif change == "wrong_receipt":
        order["receipt"] = "foreign"
    elif change == "wrong_paid":
        order["amount_paid"] = 9900
    elif change == "wrong_due":
        order["amount_due"] = 0
    elif change == "wrong_attempts":
        order["attempts"] = 2
    elif change == "unknown_state":
        payment["status"] = "unknown"
    elif change == "over_refund":
        payment["amount_refunded"] = 9901
    elif change == "refund_flag":
        payment["refund_status"] = "full"
    elif change == "wrong_order_state":
        order["status"] = "created"
    async with TestSessionLocal() as session:
        result = await owned_status(session, row.user_id, provider)
    assert result["checkout"]["state"] == "unresolved"
    provider.order.create.assert_not_called()


async def test_provider_reads_outside_sql_and_binding_change_is_unresolved(purchase, monkeypatch):
    row, provider, _, _ = setup(purchase)
    monkeypatch.setattr(get_settings(), "billing_checkout_enabled", True)
    async with TestSessionLocal() as session:
        fetch = provider.order.fetch.return_value

        def change(identifier):
            assert not session.in_transaction()
            get_settings().razorpay_key_id = "rzp_test_Changed"
            return fetch

        provider.order.fetch.side_effect = change
        assert (await owned_status(session, row.user_id, provider))["checkout"][
            "state"
        ] == "unresolved"


async def test_unknown_dispatch_and_provider_timeout_do_not_repeat_creation(purchase):
    row, provider, _, _ = setup(purchase)
    provider.order.fetch.side_effect = TimeoutError("private-provider-error")
    async with TestSessionLocal() as session:
        assert (await owned_status(session, row.user_id, provider))["checkout"][
            "state"
        ] == "unresolved"
        stored = await session.get(CheckoutReservation, row.id)
        assert stored is not None
        stored.provider_order_state = "uncertain"
        stored.provider_order_id = None
        await session.commit()
        assert (await owned_status(session, row.user_id, provider))["checkout"][
            "state"
        ] == "unresolved"
    provider.order.create.assert_not_called()


async def test_failed_then_authorized_then_captured_signals_never_grant_but_capture_event_does(
    purchase,
):
    row, provider, _, payment = setup(purchase)
    for counter, state in enumerate(("failed", "authorized", "captured")):
        setup(purchase, state)
        rid = await receipt_for(
            payment,
            counter=counter,
            kind="payment.failed" if counter != 1 else "payment.authorized",
        )
        assert (
            await activation.process_receipt(TestSessionLocal, rid, provider, now=NOW)
            == "checkout_signal_reconciled"
        )
        async with TestSessionLocal() as session:
            receipt = await session.get(PaymentWebhookEvent, rid)
            assert receipt is not None and receipt.state == "processed"
            assert await session.scalar(select(func.count()).select_from(PaymentActivation)) == 0
    rid = await receipt_for(payment, counter=4, kind="payment.captured")
    assert await activation.process_receipt(TestSessionLocal, rid, provider, now=NOW) == "activated"
    async with TestSessionLocal() as session:
        assert (await owned_status(session, row.user_id, provider))["checkout"][
            "activation_confirmed"
        ] is True


async def test_status_api_owned_no_store_and_no_foreign_target(client, auth_headers, purchase):
    row, provider, _, _ = setup(purchase)
    with patch("app.api.checkout._get_razorpay_client", return_value=provider):
        response = await client.get(
            "/api/checkout/status?user_id=foreign&order_id=order_Foreign", headers=auth_headers
        )
    assert response.status_code == 200
    assert response.json()["checkout"]["reservation_id"] == str(row.id)
    assert response.headers["cache-control"] == "no-store"
    assert "order_Foreign" not in response.text
    assert (await client.get("/api/checkout/status")).status_code == 401


async def test_prior_capture_cannot_regress_to_failed(purchase):
    row, provider, _, payment = setup(purchase, "captured")
    rid = await receipt_for(payment, counter=20)
    assert await activation.process_receipt(TestSessionLocal, rid, provider, now=NOW) == "activated"
    setup(purchase, "failed")
    async with TestSessionLocal() as session:
        status = await owned_status(session, row.user_id, provider)
    assert status["checkout"]["state"] == "unresolved"
    assert status["checkout"]["activation_confirmed"] is True


async def test_actor_revoked_during_get_cannot_read_status(purchase, monkeypatch):
    from app.billing import checkout_status
    from app.models.user import User
    from fastapi import HTTPException

    row, provider, _, _ = setup(purchase)

    async def revoke(*args):
        async with TestSessionLocal() as other:
            owner = await other.get(User, row.user_id)
            assert owner is not None
            owner.is_active = False
            await other.commit()
        return "failed", set()

    monkeypatch.setattr(checkout_status, "fetch_status", revoke)
    async with TestSessionLocal() as session:
        with pytest.raises(HTTPException) as exc:
            await owned_status(session, row.user_id, provider)
    assert exc.value.status_code == 403


async def test_empty_or_foreign_status_does_not_read_provider(purchase):
    import uuid

    _, provider, _, _ = setup(purchase)
    async with TestSessionLocal() as session:
        assert (await owned_status(session, uuid.uuid4(), provider))["checkout"] is None
    provider.order.fetch.assert_not_called()


@pytest.mark.parametrize("expired", [False, True])
async def test_unattempted_order_ready_or_expired_never_releases_quote(purchase, expired):
    from datetime import timedelta

    row, provider, order, _ = setup(purchase)
    order.update(status="created", attempts=0, amount_paid=0, amount_due=9900)
    provider.order.payments.return_value = {"entity": "collection", "count": 0, "items": []}
    async with TestSessionLocal() as session:
        stored = await session.get(CheckoutReservation, row.id)
        assert stored is not None
        stored.expires_at = NOW + timedelta(days=-1 if expired else 1)
        await session.commit()
        status = await owned_status(session, row.user_id, provider)
        assert status["checkout"]["state"] == ("expired" if expired else "ready")
        stored = await session.get(CheckoutReservation, row.id)
        assert stored is not None and stored.status == "reserved"
    provider.order.create.assert_not_called()


async def test_different_capture_cannot_replace_retained_payment(purchase):
    row, provider, order, payment = setup(purchase, "captured")
    rid = await receipt_for(payment, counter=25)
    assert await activation.process_receipt(TestSessionLocal, rid, provider, now=NOW) == "activated"
    old = copy.deepcopy(payment)
    old.update(status="failed", captured=False)
    payment["id"] = "pay_DifferentCapture"
    order["attempts"] = 2
    provider.order.payments.return_value = {
        "entity": "collection",
        "count": 2,
        "items": [old, payment],
    }
    async with TestSessionLocal() as session:
        assert (await owned_status(session, row.user_id, provider))["checkout"][
            "state"
        ] == "unresolved"
