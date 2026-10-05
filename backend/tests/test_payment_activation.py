"""Signed receipt to atomic finite grant; all provider reads are synthetic."""

import copy
import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock
import uuid

from pydantic import SecretStr
import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.billing import activation
from app.billing.checkout_orders import order_notes
from app.billing.service import effective_plan
from app.billing.webhook_inbox import persist_webhook
from app.core.config import get_settings
from app.models.account_deletion import AccountDeletion
from app.models.payment_activation import PaymentActivation
from app.models.payment_webhook import PaymentWebhookEvent
from app.models.pricing_offer import CheckoutReservation
from app.models.subscription import Subscription
from tests.conftest import TestSessionLocal

NOW = datetime.now(timezone.utc).replace(microsecond=0)
KEY_ID = "rzp_test_SyntheticActivation"
SECRET = "synthetic-activation-webhook-secret-0123456789"


@pytest.fixture
def enabled(monkeypatch):
    settings = get_settings()
    for key, value in dict(
        billing_activation_enabled=True,
        razorpay_webhook_enabled=True,
        deployment_environment="test",
        razorpay_key_id=KEY_ID,
        razorpay_key_secret=SecretStr("synthetic-api-key-secret"),
        razorpay_webhook_mode="test",
        razorpay_webhook_account_id="acc_Activation",
        razorpay_webhook_secret=SecretStr(SECRET),
    ).items():
        monkeypatch.setattr(settings, key, value)
    return settings


@pytest.fixture
async def purchase(session, test_user, enabled):
    sub = await session.scalar(select(Subscription).where(Subscription.user_id == test_user.id))
    assert sub is not None
    sub.plan, sub.status, sub.billing_interval = "free", "free", "none"
    row = CheckoutReservation(
        id=uuid.uuid4(),
        user_id=test_user.id,
        plan="pro",
        billing_interval="monthly",
        offer_code="pro_monthly_intro",
        campaign_version="v1",
        amount_minor=9900,
        currency="INR",
        renewal_amount_minor=9900,
        renewal_interval="monthly",
        service_period_days=60,
        reserved_at=NOW,
        expires_at=NOW + timedelta(minutes=10),
        provider_order_state="ready",
        provider_key_id=KEY_ID,
        provider_receipt="fp-" + uuid.uuid4().hex,
        provider_order_id="order_SyntheticActivation",
        status="reserved",
        service_starts_at=NOW,
    )
    session.add(row)
    await session.commit()
    order = dict(
        id=row.provider_order_id,
        entity="order",
        amount=row.amount_minor,
        currency="INR",
        receipt=row.provider_receipt,
        notes=order_notes(row),
        status="paid",
        amount_paid=9900,
        amount_due=0,
    )
    payment = dict(
        id="pay_SyntheticActivation",
        entity="payment",
        order_id=row.provider_order_id,
        amount=9900,
        currency="INR",
        captured=True,
        status="captured",
        amount_refunded=0,
        refund_status=None,
    )
    client = MagicMock()
    client.order.fetch.return_value = order
    client.payment.fetch.return_value = payment
    return row, client, order, payment


def event_for(payment, counter=0, kind="payment.captured"):
    payload = {"payment": {"entity": {**payment, "email": "private-pii-canary@example.com"}}}
    if kind == "order.paid":
        payload["order"] = {"entity": {"id": payment["order_id"], "entity": "order"}}
    return dict(
        entity="event",
        account_id="acc_Activation",
        event=kind,
        created_at=counter,
        payload=payload,
    )


async def receipt_for(payment, counter=0, kind="payment.captured"):
    event = event_for(payment, counter, kind)
    async with TestSessionLocal() as session:
        body = json.dumps(event).encode()
        await persist_webhook(
            session, body=body, event=event, delivery_id="evt_Unsigned", mode="test"
        )
        return await session.scalar(
            select(PaymentWebhookEvent.id).where(
                PaymentWebhookEvent.body_sha256 == hashlib.sha256(body).hexdigest()
            )
        )


@pytest.mark.asyncio
async def test_signed_http_to_worker_to_bounded_entitlements(client, auth_headers, purchase):
    row, provider, _, payment = purchase
    body = json.dumps(event_for(payment)).encode()
    response = await client.post(
        "/api/webhooks/razorpay",
        content=body,
        headers={
            "content-type": "application/json",
            "x-razorpay-signature": hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest(),
        },
    )
    assert response.status_code == 200
    before = await client.get("/api/billing/entitlements", headers=auth_headers)
    assert before.json()["plan"] == "free"
    assert await activation.scan_receipts(TestSessionLocal, provider, now=NOW) == {"activated": 1}
    after = await client.get("/api/billing/entitlements", headers=auth_headers)
    assert after.status_code == 200 and after.json()["plan"] == "pro"
    async with TestSessionLocal() as session:
        sub = await session.scalar(select(Subscription).where(Subscription.user_id == row.user_id))
        assert sub is not None
        evidence = await session.scalar(select(PaymentActivation))
        assert sub and evidence and effective_plan(sub, now=NOW).value == "pro"
        assert effective_plan(sub, now=NOW + timedelta(days=60)).value == "free"
        assert (
            evidence.amount_minor == 9900
            and evidence.period_end - evidence.period_start == timedelta(days=60)
        )
        assert "private-pii-canary" not in str(evidence.__dict__)
        stored = await session.get(CheckoutReservation, row.id)
        assert stored is not None
        assert stored.status == "verified" and stored.provider_payment_id == payment["id"]


@pytest.mark.asyncio
async def test_same_payment_distinct_signed_receipts_do_not_extend_or_reset_later_state(purchase):
    row, provider, _, payment = purchase
    identity = await receipt_for(payment)
    assert (
        await activation.process_receipt(TestSessionLocal, identity, provider, now=NOW)
        == "activated"
    )
    async with TestSessionLocal() as session:
        sub = await session.scalar(select(Subscription).where(Subscription.user_id == row.user_id))
        assert sub is not None
        sub.status, sub.cancel_at_period_end = "canceled", True
        end = sub.current_period_end
        await session.commit()
    duplicate = await receipt_for(payment, 1, "order.paid")
    assert (
        await activation.process_receipt(
            TestSessionLocal, duplicate, provider, now=NOW + timedelta(days=1)
        )
        == "duplicate"
    )
    assert (
        await activation.process_receipt(TestSessionLocal, duplicate, provider, now=NOW)
        == "unchanged"
    )
    async with TestSessionLocal() as session:
        assert await session.scalar(select(func.count()).select_from(PaymentActivation)) == 1
        sub = await session.scalar(select(Subscription).where(Subscription.user_id == row.user_id))
        assert sub is not None
        assert (
            sub.status == "canceled" and sub.cancel_at_period_end and sub.current_period_end == end
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "target,field,value",
    [
        ("payment", "captured", False),
        ("payment", "status", "authorized"),
        ("payment", "amount", True),
        ("payment", "amount", 1900),
        ("payment", "currency", "USD"),
        ("payment", "id", "pay_Another"),
        ("payment", "order_id", "order_Another"),
        ("payment", "amount_refunded", 1),
        ("payment", "amount_refunded", False),
        ("payment", "refund_status", "partial"),
        ("order", "status", "created"),
        ("order", "amount_paid", True),
        ("order", "amount_due", 1),
        ("order", "receipt", "wrong"),
        ("order", "notes", {"fincopilot_user_id": "wrong"}),
    ],
)
async def test_current_provider_mismatch_quarantines_without_grant(purchase, target, field, value):
    _, provider, order, payment = purchase
    identity = await receipt_for(copy.deepcopy(payment))
    (payment if target == "payment" else order)[field] = value
    assert (
        await activation.process_receipt(TestSessionLocal, identity, provider, now=NOW)
        == "quarantined"
    )
    async with TestSessionLocal() as session:
        assert await session.scalar(select(func.count()).select_from(PaymentActivation)) == 0
        receipt = await session.get(PaymentWebhookEvent, identity)
        assert receipt is not None
        assert receipt.processing_error in (
            "capture_mismatch",
            "order_mismatch",
        )


@pytest.mark.asyncio
async def test_provider_outage_backoff_then_recovery(purchase):
    _, provider, _, payment = purchase
    identity = await receipt_for(payment)
    provider.payment.fetch.side_effect = RuntimeError("private-provider-response")
    assert (
        await activation.process_receipt(TestSessionLocal, identity, provider, now=NOW) == "retry"
    )
    assert (
        await activation.process_receipt(TestSessionLocal, identity, provider, now=NOW) == "not_due"
    )
    async with TestSessionLocal() as session:
        row = await session.get(PaymentWebhookEvent, identity)
        assert row is not None
        assert row.state == "pending" and row.processing_error == "provider_unavailable"
        assert "private" not in str(row.__dict__)
    provider.payment.fetch.side_effect = None
    assert (
        await activation.process_receipt(
            TestSessionLocal, identity, provider, now=NOW + timedelta(minutes=2)
        )
        == "activated"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "blocked", ["inactive", "deletion", "paid", "key", "production", "disabled", "live"]
)
async def test_fences_and_configuration_fail_closed(purchase, enabled, blocked):
    row, provider, _, payment = purchase
    identity = await receipt_for(payment)
    async with TestSessionLocal() as session:
        if blocked == "inactive":
            from app.models.user import User

            user = await session.get(User, row.user_id)
            assert user is not None
            user.is_active = False
        if blocked == "deletion":
            session.add(
                AccountDeletion(
                    user_id=row.user_id, active_user_id=row.user_id, tracking_digest="a" * 64
                )
            )
        if blocked == "paid":
            sub = await session.scalar(
                select(Subscription).where(Subscription.user_id == row.user_id)
            )
            if sub is None:
                sub = Subscription(user_id=row.user_id)
                session.add(sub)
            sub.plan, sub.status = "max", "active"
        await session.commit()
    if blocked == "key":
        enabled.razorpay_key_id = "rzp_test_Rotated"
    if blocked == "production":
        enabled.deployment_environment = "production"
    if blocked == "disabled":
        enabled.billing_activation_enabled = False
    if blocked == "live":
        enabled.razorpay_webhook_mode = "live"
    result = await activation.process_receipt(TestSessionLocal, identity, provider, now=NOW)
    assert result == (
        "disabled" if blocked in ("production", "disabled", "live") else "quarantined"
    )
    async with TestSessionLocal() as session:
        assert await session.scalar(select(func.count()).select_from(PaymentActivation)) == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("future", [True, False])
async def test_future_and_expired_reserved_periods_never_authorize(purchase, future):
    row, provider, _, payment = purchase
    async with TestSessionLocal() as session:
        stored = await session.get(CheckoutReservation, row.id)
        assert stored is not None
        stored.service_starts_at = NOW + timedelta(days=30) if future else NOW - timedelta(days=90)
        await session.commit()
    identity = await receipt_for(payment)
    assert (
        await activation.process_receipt(TestSessionLocal, identity, provider, now=NOW)
        == "activated"
    )
    async with TestSessionLocal() as session:
        sub = await session.scalar(select(Subscription).where(Subscription.user_id == row.user_id))
        assert sub is not None
        assert effective_plan(sub, now=NOW).value == "free"
        if future:
            assert effective_plan(sub, now=NOW + timedelta(days=30)).value == "pro"


@pytest.mark.asyncio
@pytest.mark.parametrize("lost", [True, False])
async def test_activation_commit_failure_or_lost_response_converges(purchase, monkeypatch, lost):
    _, provider, _, payment = purchase
    identity = await receipt_for(payment)
    original = AsyncSession.commit

    async def ambiguous(self):
        grant = any(isinstance(row, PaymentActivation) for row in self.new)
        if grant:
            if lost:
                await original(self)
            raise RuntimeError("synthetic-db-response-lost")
        await original(self)

    monkeypatch.setattr(AsyncSession, "commit", ambiguous)
    with pytest.raises(RuntimeError):
        await activation.process_receipt(TestSessionLocal, identity, provider, now=NOW)
    monkeypatch.setattr(AsyncSession, "commit", original)
    assert await activation.process_receipt(TestSessionLocal, identity, provider, now=NOW) == (
        "unchanged" if lost else "activated"
    )
    async with TestSessionLocal() as session:
        assert await session.scalar(select(func.count()).select_from(PaymentActivation)) == 1
        stored = await session.get(PaymentWebhookEvent, identity)
        assert stored is not None and stored.state == "processed"


@pytest.mark.asyncio
async def test_oldest_unavailable_event_does_not_starve_next_and_corruption_quarantines(purchase):
    _, provider, _, payment = purchase
    other = {**payment, "order_id": "order_NotYetAttached"}
    missing = await receipt_for(other)
    valid = await receipt_for(payment, 1)
    result = await activation.scan_receipts(TestSessionLocal, provider, now=NOW)
    assert result == {"retry": 1, "activated": 1}
    async with TestSessionLocal() as session:
        row = await session.get(PaymentWebhookEvent, missing)
        assert row is not None
        row.snapshot_ciphertext = "payment-inbox:v1:invalid-token"
        row.next_attempt_at = None
        await session.commit()
    assert (
        await activation.process_receipt(TestSessionLocal, missing, provider, now=NOW)
        == "quarantined"
    )
    assert (
        await activation.process_receipt(TestSessionLocal, valid, provider, now=NOW) == "unchanged"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "plan,interval,days,wave",
    [
        ("max", "monthly", 30, None),
        ("pro", "annual", 365, None),
        ("pro", "annual", 365, 1),
        ("pro", "annual", 365, 2),
    ],
)
async def test_reserved_catalog_and_founder_launch_survive_activation(
    purchase, plan, interval, days, wave
):
    from app.models.pricing_offer import FoundingMember

    row, provider, order, payment = purchase
    start = NOW + timedelta(days=7) if wave else NOW
    async with TestSessionLocal() as session:
        stored = await session.get(CheckoutReservation, row.id)
        assert stored is not None
        stored.plan, stored.billing_interval = plan, interval
        stored.service_period_days, stored.service_starts_at = days, start
        stored.founder_wave = wave
        stored.founder_position = 1 if wave == 1 else 5001 if wave else None
        order["notes"] = order_notes(stored)
        await session.commit()
    identity = await receipt_for(payment)
    assert (
        await activation.process_receipt(TestSessionLocal, identity, provider, now=NOW)
        == "activated"
    )
    async with TestSessionLocal() as session:
        sub = await session.scalar(select(Subscription).where(Subscription.user_id == row.user_id))
        grant = await session.scalar(select(PaymentActivation))
        assert sub is not None and grant is not None
        assert grant.plan == plan and grant.billing_interval == interval
        assert grant.period_end - grant.period_start == timedelta(days=days)
        assert effective_plan(sub, now=start).value == plan
        assert effective_plan(sub, now=start + timedelta(days=days)).value == "free"
        member = await session.get(FoundingMember, row.user_id)
        assert (member is None) if wave is None else (member is not None and member.wave == wave)
        if wave:
            assert effective_plan(sub, now=NOW).value == "free"


@pytest.mark.asyncio
async def test_second_purchase_cannot_replace_existing_grant(purchase):
    row, provider, order, payment = purchase
    first = await receipt_for(payment)
    assert (
        await activation.process_receipt(TestSessionLocal, first, provider, now=NOW) == "activated"
    )
    async with TestSessionLocal() as session:
        original = await session.get(CheckoutReservation, row.id)
        assert original is not None
        values = {
            column.name: getattr(original, column.name)
            for column in CheckoutReservation.__table__.columns
        }
        values.update(
            id=uuid.uuid4(),
            provider_order_id="order_SecondPurchase",
            provider_payment_id=None,
            provider_receipt="fp-" + uuid.uuid4().hex,
            status="reserved",
            verified_at=None,
        )
        second = CheckoutReservation(**values)
        session.add(second)
        await session.commit()
        order.update(
            id=second.provider_order_id, receipt=second.provider_receipt, notes=order_notes(second)
        )
    payment.update(id="pay_SecondPurchase", order_id="order_SecondPurchase")
    identity = await receipt_for(payment, 1)
    assert (
        await activation.process_receipt(TestSessionLocal, identity, provider, now=NOW)
        == "quarantined"
    )
    async with TestSessionLocal() as session:
        assert await session.scalar(select(func.count()).select_from(PaymentActivation)) == 1
        receipt = await session.get(PaymentWebhookEvent, identity)
        assert receipt is not None and receipt.processing_error == "lifecycle_review_required"


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["key", "amount", "inactive"])
async def test_locked_recheck_rejects_changes_during_provider_io(
    purchase, enabled, monkeypatch, change
):
    from app.models.user import User

    row, provider, order, payment = purchase
    identity = await receipt_for(payment)

    async def provider_read(*args):
        if change == "key":
            enabled.razorpay_key_id = "rzp_test_RotatedDuringFetch"
        else:
            async with TestSessionLocal() as session:
                if change == "amount":
                    stored = await session.get(CheckoutReservation, row.id)
                    assert stored is not None
                    stored.amount_minor += 1
                else:
                    user = await session.get(User, row.user_id)
                    assert user is not None
                    user.is_active = False
                await session.commit()
        return order, payment

    monkeypatch.setattr(activation, "fetch_capture", provider_read)
    assert (
        await activation.process_receipt(TestSessionLocal, identity, provider, now=NOW)
        == "quarantined"
    )
    async with TestSessionLocal() as session:
        assert await session.scalar(select(func.count()).select_from(PaymentActivation)) == 0


def test_migration103_empty_roundtrip_and_processed_evidence_refusal():
    import importlib.util
    from contextlib import closing
    from pathlib import Path
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from sqlalchemy import create_engine, inspect, text
    from sqlalchemy.pool import NullPool

    def load(number, filename):
        path = Path(__file__).resolve().parents[1] / "alembic/versions" / filename
        spec = importlib.util.spec_from_file_location("activation_migration" + number, path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    previous = load("102", "102_payment_webhook_events.py")
    migration = load("103", "103_payment_activation.py")
    engine = create_engine("sqlite://", poolclass=NullPool)
    with closing(engine.connect()) as connection, connection.begin():
        with Operations.context(MigrationContext.configure(connection)):
            previous.upgrade()
            migration.upgrade()
            migration.downgrade()
            assert "payment_activations" not in inspect(connection).get_table_names()
            migration.upgrade()
            connection.execute(
                text(
                    "INSERT INTO payment_webhook_events (id,provider,mode,account_id,body_sha256,event_type,state,snapshot_ciphertext,received_at,processing_attempts) VALUES (:id,'razorpay','test','acc_Synthetic',:hash,'payment.captured','pending','payment-inbox:v1:synthetic',CURRENT_TIMESTAMP,1)"
                ),
                {"id": "a" * 32, "hash": "b" * 64},
            )
            with pytest.raises(RuntimeError, match="evidence"):
                migration.downgrade()
            assert "payment_activations" in inspect(connection).get_table_names()
            assert (
                connection.scalar(text("SELECT processing_attempts FROM payment_webhook_events"))
                == 1
            )


@pytest.mark.parametrize("status", ["active", "grace", "canceled"])
@pytest.mark.parametrize("term", ["missing", "future", "expired", "current_naive"])
def test_every_provider_paid_state_requires_an_in_force_term(status, term):
    start, end = NOW - timedelta(days=1), NOW + timedelta(days=1)
    if term == "missing":
        start = None
    elif term == "future":
        start = NOW + timedelta(seconds=1)
    elif term == "expired":
        end = NOW
    else:
        start, end = start.replace(tzinfo=None), end.replace(tzinfo=None)
    sub = Subscription(
        user_id=uuid.uuid4(),
        provider="razorpay",
        plan="pro",
        status=status,
        billing_interval="monthly",
        current_period_start=start,
        current_period_end=end,
    )
    assert effective_plan(sub, now=NOW).value == ("pro" if term == "current_naive" else "free")


@pytest.mark.asyncio
async def test_disabled_worker_never_constructs_provider_or_database(monkeypatch):
    from app.tasks import payment_tasks
    from app.api import checkout

    monkeypatch.setattr(payment_tasks, "activation_enabled", lambda: False)
    provider, database = MagicMock(), MagicMock()
    monkeypatch.setattr(checkout, "_get_razorpay_client", provider)
    monkeypatch.setattr(payment_tasks, "create_database_engine", database)
    assert await payment_tasks.reconcile() == {"disabled": 1}
    provider.assert_not_called()
    database.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["create", "scan", "dispose"])
async def test_worker_closes_provider_session_even_on_database_failure(monkeypatch, failure):
    from unittest.mock import AsyncMock
    from app.tasks import payment_tasks
    from app.api import checkout

    monkeypatch.setattr(payment_tasks, "activation_enabled", lambda: True)
    provider = MagicMock()
    monkeypatch.setattr(checkout, "_get_razorpay_client", lambda: provider)
    engine = MagicMock()
    engine.dispose = AsyncMock(
        side_effect=RuntimeError("synthetic") if failure == "dispose" else None
    )
    create = MagicMock(
        return_value=engine, side_effect=RuntimeError("synthetic") if failure == "create" else None
    )
    scan = AsyncMock(
        return_value={"activated": 1},
        side_effect=RuntimeError("synthetic") if failure == "scan" else None,
    )
    monkeypatch.setattr(payment_tasks, "create_database_engine", create)
    monkeypatch.setattr(payment_tasks, "scan_receipts", scan)
    with pytest.raises(RuntimeError, match="synthetic"):
        await payment_tasks.reconcile()
    provider.session.close.assert_called_once()
    if failure != "create":
        engine.dispose.assert_awaited_once()


@pytest.mark.asyncio
async def test_signed_order_paid_requires_matching_order_entity(purchase):
    _, provider, _, payment = purchase
    event = event_for(payment, kind="order.paid")
    event["payload"]["order"]["entity"]["id"] = "order_DifferentSignedOrder"
    body = json.dumps(event).encode()
    async with TestSessionLocal() as session:
        await persist_webhook(session, body=body, event=event, delivery_id=None, mode="test")
        identity = await session.scalar(
            select(PaymentWebhookEvent.id).where(
                PaymentWebhookEvent.body_sha256 == hashlib.sha256(body).hexdigest()
            )
        )
        assert identity is not None
    assert (
        await activation.process_receipt(TestSessionLocal, identity, provider, now=NOW)
        == "quarantined"
    )
    provider.order.fetch.assert_not_called()
    async with TestSessionLocal() as session:
        assert await session.scalar(select(func.count()).select_from(PaymentActivation)) == 0
