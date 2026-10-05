"""Real signed inbox and authenticated APIs; provider requests are synthetic."""

import copy
from datetime import timedelta
import hashlib
import json

from fastapi import HTTPException
import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.billing import activation, renewal_mandates as mandates
from app.billing.offer_service import _stored_utc
from app.billing.razorpay_catalog import provider_plan_create_payload
from app.billing.offers import PROVIDER_PLAN_SPECS
from app.billing.enums import PlanId, BillingInterval
from app.billing.service import effective_plan
from app.billing.webhook_inbox import persist_webhook
from app.models.payment_renewal import RenewalCycle
from app.models.payment_webhook import PaymentWebhookEvent
from app.models.subscription import Subscription
from tests.conftest import TestSessionLocal
from tests.test_payment_activation import enabled as enabled, purchase as purchase, NOW, receipt_for


@pytest.fixture
async def renewal(purchase, enabled, monkeypatch):
    row, provider, _, first = purchase
    identity = await receipt_for(first)
    assert (
        await activation.process_receipt(TestSessionLocal, identity, provider, now=NOW)
        == "activated"
    )
    monkeypatch.setattr(enabled, "billing_renewal_enabled", True)
    monkeypatch.setattr(enabled, "razorpay_plan_pro_monthly_id", "plan_RenewalSynthetic")
    plan = {
        "id": "plan_RenewalSynthetic",
        "entity": "plan",
        **provider_plan_create_payload(PROVIDER_PLAN_SPECS[(PlanId.PRO, BillingInterval.MONTHLY)]),
    }
    provider.plan.fetch.return_value = plan
    subscription = {}

    def create(*, data):
        subscription.update(
            copy.deepcopy(data),
            id="sub_RenewalSynthetic",
            entity="subscription",
            status="created",
            has_scheduled_changes=False,
            paid_count=0,
        )
        return copy.deepcopy(subscription)

    provider.subscription.create.side_effect = create
    async with TestSessionLocal() as session:
        result = await mandates.create_mandate(session, row.user_id, 3, provider, now=NOW)
    assert result["state"] == "ready"
    start = result["starts_at"]
    invoice = dict(
        id="inv_RenewalSynthetic",
        entity="invoice",
        subscription_id=subscription["id"],
        payment_id="pay_RenewalSynthetic",
        status="paid",
        amount=9900,
        amount_paid=9900,
        amount_due=0,
        currency="INR",
        billing_start=int(start.timestamp()),
        billing_end=int((start + timedelta(days=30)).timestamp()),
    )
    payment = dict(
        id=invoice["payment_id"],
        entity="payment",
        invoice_id=invoice["id"],
        amount=9900,
        currency="INR",
        status="captured",
        captured=True,
        amount_refunded=0,
        refund_status=None,
    )
    subscription.update(status="active", paid_count=1)
    provider.subscription.fetch.side_effect = lambda _: copy.deepcopy(subscription)
    provider.invoice.fetch.side_effect = lambda _: copy.deepcopy(invoice)
    provider.payment.fetch.side_effect = lambda _: copy.deepcopy(payment)
    return row, provider, subscription, plan, invoice, payment, start


async def cycle_receipt(subscription, payment, counter=1):
    event = dict(
        entity="event",
        account_id="acc_Activation",
        event="subscription.charged",
        created_at=counter,
        payload={
            "subscription": {
                "entity": {**subscription, "notes": {"private": "private-cycle-canary"}}
            },
            "payment": {"entity": {**payment, "email": "private-cycle-canary@example.com"}},
        },
    )
    body = json.dumps(event).encode()
    async with TestSessionLocal() as session:
        await persist_webhook(session, body=body, event=event, delivery_id=None, mode="test")
        identity = await session.scalar(
            select(PaymentWebhookEvent.id).where(
                PaymentWebhookEvent.body_sha256 == hashlib.sha256(body).hexdigest()
            )
        )
        assert identity is not None
        return identity


@pytest.mark.asyncio
async def test_captured_cycle_extends_once_without_intro_replay_or_later_state_reset(renewal):
    row, provider, subscription, _, invoice, payment, start = renewal
    identity = await cycle_receipt(subscription, payment)
    assert (
        await activation.process_receipt(TestSessionLocal, identity, provider, now=start)
        == "renewed"
    )
    async with TestSessionLocal() as session:
        sub = await session.scalar(select(Subscription).where(Subscription.user_id == row.user_id))
        assert sub is not None and effective_plan(sub, now=start).value == "pro"
        assert effective_plan(sub, now=start + timedelta(days=30)).value == "free"
        ledger = await session.scalar(select(RenewalCycle))
        assert ledger is not None and ledger.amount_minor == 9900
        assert "private-cycle-canary" not in str(ledger.__dict__)
        end = _stored_utc(sub.current_period_end)
        sub.status, sub.cancel_at_period_end = "canceled", True
        await session.commit()
    replay = await cycle_receipt(subscription, payment, 2)
    assert (
        await activation.process_receipt(
            TestSessionLocal, replay, provider, now=start + timedelta(days=2)
        )
        == "duplicate"
    )
    async with TestSessionLocal() as session:
        sub = await session.scalar(select(Subscription).where(Subscription.user_id == row.user_id))
        assert sub is not None and sub.status == "canceled" and sub.cancel_at_period_end
        assert _stored_utc(sub.current_period_end) == end
        assert await session.scalar(select(func.count()).select_from(RenewalCycle)) == 1


@pytest.mark.asyncio
async def test_paid_future_invoice_preserves_existing_access_and_schedules_exact_start(renewal):
    row, provider, subscription, _, _, payment, start = renewal
    identity = await cycle_receipt(subscription, payment)
    assert (
        await activation.process_receipt(TestSessionLocal, identity, provider, now=NOW) == "retry"
    )
    async with TestSessionLocal() as session:
        receipt = await session.get(PaymentWebhookEvent, identity)
        sub = await session.scalar(select(Subscription).where(Subscription.user_id == row.user_id))
        assert receipt is not None and _stored_utc(receipt.next_attempt_at) == start
        assert sub is not None and effective_plan(sub, now=NOW).value == "pro"
        assert await session.scalar(select(func.count()).select_from(RenewalCycle)) == 0
    assert (
        await activation.process_receipt(TestSessionLocal, identity, provider, now=start)
        == "renewed"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "target,field,value",
    [
        ("invoice", "subscription_id", "sub_Foreign"),
        ("invoice", "payment_id", "pay_Foreign"),
        ("invoice", "amount", True),
        ("invoice", "amount_paid", 1900),
        ("invoice", "amount_due", 1),
        ("invoice", "currency", "USD"),
        ("invoice", "status", "issued"),
        ("invoice", "billing_start", True),
        ("invoice", "billing_end", 1),
        ("payment", "captured", False),
        ("payment", "captured", "true"),
        ("payment", "amount_refunded", 1),
        ("payment", "amount_refunded", False),
        ("payment", "invoice_id", "inv_Foreign"),
        ("payment", "amount", 1900),
        ("subscription", "plan_id", "plan_Foreign"),
        ("subscription", "quantity", True),
        ("subscription", "has_scheduled_changes", True),
        ("subscription", "status", "cancelled"),
        ("plan", "interval", True),
    ],
)
async def test_bad_current_provider_evidence_quarantines_without_extension(
    renewal, target, field, value
):
    row, provider, subscription, plan, invoice, payment, start = renewal
    identity = await cycle_receipt(subscription, payment)
    {"invoice": invoice, "payment": payment, "subscription": subscription, "plan": plan}[target][
        field
    ] = value
    assert (
        await activation.process_receipt(TestSessionLocal, identity, provider, now=start)
        == "quarantined"
    )
    async with TestSessionLocal() as session:
        assert await session.scalar(select(func.count()).select_from(RenewalCycle)) == 0
        sub = await session.scalar(select(Subscription).where(Subscription.user_id == row.user_id))
        assert sub is not None and _stored_utc(sub.current_period_end) <= start


@pytest.mark.asyncio
@pytest.mark.parametrize("captured", [True, 1, "1"])
async def test_documented_subscription_capture_encodings_are_verified_against_current_invoice(
    renewal, captured
):
    _, provider, subscription, _, _, payment, start = renewal
    payment["captured"] = captured
    identity = await cycle_receipt(subscription, payment)
    assert (
        await activation.process_receipt(TestSessionLocal, identity, provider, now=start)
        == "renewed"
    )


@pytest.mark.asyncio
async def test_out_of_order_cycles_retry_then_converge_without_period_jump(renewal):
    row, provider, subscription, _, invoice, payment, start = renewal
    first_invoice, first_payment = copy.deepcopy(invoice), copy.deepcopy(payment)
    invoice.update(
        id="inv_Cycle2",
        payment_id="pay_Cycle2",
        billing_start=int((start + timedelta(days=30)).timestamp()),
        billing_end=int((start + timedelta(days=60)).timestamp()),
    )
    payment.update(id="pay_Cycle2", invoice_id="inv_Cycle2")
    subscription["paid_count"] = 2
    second = await cycle_receipt(subscription, payment, 2)
    late = start + timedelta(days=61)
    assert await activation.process_receipt(TestSessionLocal, second, provider, now=late) == "retry"
    invoice.clear()
    invoice.update(first_invoice)
    payment.clear()
    payment.update(first_payment)
    first = await cycle_receipt(subscription, payment)
    assert (
        await activation.process_receipt(TestSessionLocal, first, provider, now=late) == "renewed"
    )
    invoice.update(
        id="inv_Cycle2",
        payment_id="pay_Cycle2",
        billing_start=int((start + timedelta(days=30)).timestamp()),
        billing_end=int((start + timedelta(days=60)).timestamp()),
    )
    payment.update(id="pay_Cycle2", invoice_id="inv_Cycle2")
    assert (
        await activation.process_receipt(
            TestSessionLocal, second, provider, now=late + timedelta(minutes=2)
        )
        == "renewed"
    )
    async with TestSessionLocal() as session:
        sub = await session.scalar(select(Subscription).where(Subscription.user_id == row.user_id))
        assert sub is not None and effective_plan(sub, now=late).value == "free"
        assert await session.scalar(select(func.count()).select_from(RenewalCycle)) == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("lost", [True, False])
async def test_renewal_failed_or_lost_commit_converges(renewal, monkeypatch, lost):
    _, provider, subscription, _, _, payment, start = renewal
    identity = await cycle_receipt(subscription, payment)
    original = AsyncSession.commit

    async def fail(self):
        if any(isinstance(row, RenewalCycle) for row in self.new):
            if lost:
                await original(self)
            raise RuntimeError("synthetic ambiguous commit")
        await original(self)

    monkeypatch.setattr(AsyncSession, "commit", fail)
    with pytest.raises(RuntimeError):
        await activation.process_receipt(TestSessionLocal, identity, provider, now=start)
    monkeypatch.setattr(AsyncSession, "commit", original)
    assert await activation.process_receipt(TestSessionLocal, identity, provider, now=start) == (
        "unchanged" if lost else "renewed"
    )
    async with TestSessionLocal() as session:
        assert await session.scalar(select(func.count()).select_from(RenewalCycle)) == 1


@pytest.mark.asyncio
async def test_authenticated_enrollment_is_finite_explicit_and_reuses_original_mandate(
    client, auth_headers, renewal, monkeypatch
):
    from app.api import checkout

    _, provider, _, _, _, _, _ = renewal
    monkeypatch.setattr(checkout, "_get_razorpay_client", lambda: provider)
    result = await client.get("/api/billing/renewal", headers=auth_headers)
    assert result.status_code == 200 and result.json()["amount_minor"] == 9900
    assert (await client.get("/api/billing/renewal")).status_code == 401
    for body in [
        {"total_count": 3, "authorize": False},
        {"total_count": True, "authorize": True},
        {"total_count": 0, "authorize": True},
        {"total_count": 121, "authorize": True},
        {"total_count": 3, "authorize": True, "plan": "max"},
    ]:
        assert (
            await client.post("/api/billing/renewal", headers=auth_headers, json=body)
        ).status_code == 422
    result = await client.post(
        "/api/billing/renewal", headers=auth_headers, json={"total_count": 3, "authorize": True}
    )
    assert result.status_code == 200 and result.json()["subscription_id"] == "sub_RenewalSynthetic"
    provider.subscription.create.assert_called_once()
    provider.session.close.assert_called_once()
    result = await client.post(
        "/api/billing/renewal", headers=auth_headers, json={"total_count": 4, "authorize": True}
    )
    assert result.status_code == 409
    provider.subscription.create.assert_called_once()


@pytest.mark.asyncio
async def test_unknown_creation_outcome_reconciles_without_second_post(
    purchase, enabled, monkeypatch
):
    row, provider, _, first = purchase
    identity = await receipt_for(first)
    await activation.process_receipt(TestSessionLocal, identity, provider, now=NOW)
    monkeypatch.setattr(enabled, "billing_renewal_enabled", True)
    monkeypatch.setattr(enabled, "razorpay_plan_pro_monthly_id", "plan_RenewalSynthetic")
    provider.plan.fetch.return_value = {
        "id": "plan_RenewalSynthetic",
        "entity": "plan",
        **provider_plan_create_payload(PROVIDER_PLAN_SPECS[(PlanId.PRO, BillingInterval.MONTHLY)]),
    }
    created = {}

    def lost(*, data):
        created.update(
            copy.deepcopy(data), id="sub_RenewalSynthetic", entity="subscription", status="created", paid_count=0
        )
        raise RuntimeError("private provider failure")

    provider.subscription.create.side_effect = lost
    async with TestSessionLocal() as session:
        with pytest.raises(HTTPException) as result:
            await mandates.create_mandate(session, row.user_id, 3, provider, now=NOW)
        assert result.value.status_code == 502 and "private" not in result.value.detail
    provider.subscription.all.return_value = {
        "entity": "collection",
        "count": 1,
        "items": [created],
    }
    async with TestSessionLocal() as session:
        response = await mandates.create_mandate(
            session, row.user_id, 3, provider, now=NOW + timedelta(minutes=2)
        )
        assert response["state"] == "ready"
    provider.subscription.create.assert_called_once()


@pytest.mark.asyncio
async def test_transient_plan_get_failure_can_retry_before_any_post(purchase, enabled, monkeypatch):
    row, provider, _, first = purchase
    identity = await receipt_for(first)
    await activation.process_receipt(TestSessionLocal, identity, provider, now=NOW)
    monkeypatch.setattr(enabled, "billing_renewal_enabled", True)
    monkeypatch.setattr(enabled, "razorpay_plan_pro_monthly_id", "plan_RenewalSynthetic")
    provider.plan.fetch.side_effect = RuntimeError("private provider error")
    async with TestSessionLocal() as session:
        with pytest.raises(HTTPException):
            await mandates.create_mandate(session, row.user_id, 3, provider, now=NOW)
    provider.subscription.create.assert_not_called()
    provider.plan.fetch.side_effect = None
    provider.plan.fetch.return_value = {
        "id": "plan_RenewalSynthetic",
        "entity": "plan",
        **provider_plan_create_payload(PROVIDER_PLAN_SPECS[(PlanId.PRO, BillingInterval.MONTHLY)]),
    }
    provider.subscription.create.side_effect = lambda *, data: {
        **data,
        "id": "sub_RenewalSynthetic",
        "entity": "subscription",
        "status": "created",
        "paid_count": 0,
    }
    async with TestSessionLocal() as session:
        response = await mandates.create_mandate(session, row.user_id, 3, provider, now=NOW)
        assert response["state"] == "ready"
    provider.subscription.create.assert_called_once()

@pytest.mark.asyncio
async def test_deletion_requires_cleanup_of_unknown_provider_mandate(renewal):
    from app.models.payment_renewal import RenewalMandate
    from app.models.user import User
    from app.services.account_deletion_service import inventory

    row, _, _, _, _, _, _ = renewal
    async with TestSessionLocal() as session:
        user = await session.get(User, row.user_id)
        mandate = await session.scalar(select(RenewalMandate).where(RenewalMandate.user_id == row.user_id))
        assert user and mandate
        mandate.state = "uncertain"
        mandate.provider_subscription_id = None
        subscription = await session.get(Subscription, mandate.subscription_id)
        assert subscription
        subscription.status = "canceled"
        subscription.provider_subscription_id = None
        await session.commit()
        manifest, _, _ = await inventory(session, user)
        assert "billing_renewal_cancel:" + str(mandate.id) in manifest["requirements"]
        previous = manifest["provider_hash"]
        mandate.state = "unstarted"
        await session.commit()
        fresh, _, _ = await inventory(session, user)
        assert "billing_renewal_cancel:" + str(mandate.id) not in fresh["requirements"]
        assert fresh["provider_hash"] != previous

@pytest.mark.parametrize("table", ["renewal_mandates", "renewal_cycles"])
def test_renewal_migration_refuses_to_discard_either_evidence_table(table):
    from contextlib import closing
    import importlib.util
    from pathlib import Path
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from sqlalchemy import create_engine, inspect, text
    from sqlalchemy.pool import NullPool

    path = Path(__file__).resolve().parents[1] / "alembic/versions/104_renewal_lifecycle.py"
    spec = importlib.util.spec_from_file_location("renewal_migration", path)
    assert spec and spec.loader
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    engine = create_engine("sqlite://", poolclass=NullPool)
    with closing(engine.connect()) as connection, connection.begin():
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
            migration.downgrade()
            assert "renewal_mandates" not in inspect(connection).get_table_names()
            migration.upgrade()
            columns = inspect(connection).get_columns(table)
            values: dict[str, object] = {column["name"]: "a" * 32 for column in columns}
            values.update(mode="test", currency="INR", amount_minor=9900)
            if table == "renewal_mandates":
                values.update(plan="pro", billing_interval="monthly", state="unstarted", total_count=3, starts_at="2027-01-01", requested_at="2026-01-01")
            else:
                values.update(period_start="2027-01-01", period_end="2027-02-01", applied_at="2027-01-01")
            names = list(values)
            connection.execute(text("INSERT INTO " + table + " (" + ",".join(names) + ") VALUES (" + ",".join(":" + name for name in names) + ")"), values)
            with pytest.raises(RuntimeError, match="evidence"):
                migration.downgrade()
            assert connection.scalar(text("SELECT count(*) FROM " + table)) == 1
            assert "renewal_mandates" in inspect(connection).get_table_names()
            assert "renewal_cycles" in inspect(connection).get_table_names()

@pytest.mark.asyncio
async def test_proven_unpaid_expiry_releases_claim_without_granting_access(renewal):
    from app.models.payment_renewal import RenewalMandate
    row, provider, subscription, _, _, _, start = renewal
    subscription.update(status="expired", paid_count=0)
    async with TestSessionLocal() as session:
        with pytest.raises(HTTPException, match="expired"):
            await mandates.create_mandate(session, row.user_id, 3, provider, now=start + timedelta(seconds=1))
        claim = await session.scalar(select(RenewalMandate).where(RenewalMandate.user_id == row.user_id))
        sub = await session.scalar(select(Subscription).where(Subscription.user_id == row.user_id))
        assert claim and sub
        assert claim.state == "expired" and claim.active_user_id is None
        assert sub.provider_subscription_id is None
        assert _stored_utc(sub.current_period_end) < start + timedelta(seconds=1)
        assert not await session.scalar(select(RenewalCycle.id).where(RenewalCycle.user_id == row.user_id))
    provider.subscription.create.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["flag", "key", "account"])
async def test_dispatch_rechecks_flags_and_scope_after_plan_get(purchase, enabled, monkeypatch, change):
    row, provider, _, first = purchase
    identity = await receipt_for(first)
    await activation.process_receipt(TestSessionLocal, identity, provider, now=NOW)
    monkeypatch.setattr(enabled, "billing_renewal_enabled", True)
    monkeypatch.setattr(enabled, "razorpay_plan_pro_monthly_id", "plan_RenewalSynthetic")
    plan = {"id": "plan_RenewalSynthetic", "entity": "plan", **provider_plan_create_payload(PROVIDER_PLAN_SPECS[(PlanId.PRO, BillingInterval.MONTHLY)])}
    def fetch(_):
        field, value = {"flag": ("billing_renewal_enabled", False), "key": ("razorpay_key_id", "rzp_test_Changed"), "account": ("razorpay_webhook_account_id", "acc_Changed")}[change]
        monkeypatch.setattr(enabled, field, value)
        return plan
    provider.plan.fetch.side_effect = fetch
    async with TestSessionLocal() as session:
        with pytest.raises(HTTPException) as result:
            await mandates.create_mandate(session, row.user_id, 3, provider, now=NOW)
        assert result.value.status_code == 409
    provider.subscription.create.assert_not_called()
