"""Failure evidence is synthetic; state, SQL and receipt reconciliation are real."""
import copy
import hashlib
import json
from datetime import timedelta

import pytest
from sqlalchemy import select, func

from app.billing import activation
from app.billing.service import effective_plan
from app.billing.offer_service import _stored_utc
from app.billing.webhook_inbox import persist_webhook
from app.models.payment_recovery import PaymentRecovery
from app.models.payment_webhook import PaymentWebhookEvent
from app.models.subscription import Subscription
from tests.conftest import TestSessionLocal
from tests.test_renewal_lifecycle import renewal as renewal, cycle_receipt
from tests.test_payment_activation import enabled as enabled, purchase as purchase


async def failure_receipt(subscription, counter=1, state="pending"):
    event = dict(entity="event", account_id="acc_Activation", event=f"subscription.{state}", created_at=counter,
        payload={"subscription": {"entity": {**subscription, "status": state}}})
    body = json.dumps(event).encode()
    async with TestSessionLocal() as session:
        await persist_webhook(session, body=body, event=event, delivery_id=None, mode="test")
        return await session.scalar(select(PaymentWebhookEvent.id).where(PaymentWebhookEvent.body_sha256 == hashlib.sha256(body).hexdigest()))


@pytest.fixture
async def failure(renewal, enabled, monkeypatch):
    monkeypatch.setattr(enabled, "billing_recovery_enabled", True)
    row, provider, sub, plan, invoice, payment, start = renewal
    sub.update(status="pending", paid_count=0, charge_at=int((start + timedelta(days=1)).timestamp()))
    invoice.update(status="issued", amount_paid=0, amount_due=9900, payment_id=None)
    provider.invoice.all.side_effect = lambda _: dict(entity="collection", count=1, items=[copy.deepcopy(invoice)])
    return row, provider, sub, invoice, payment, start


@pytest.mark.parametrize("hours", [0, 24, 72])
async def test_replay_halted_and_config_change_never_restart_grace(failure, enabled, monkeypatch, hours):
    row, provider, source, invoice, _, start = failure
    monkeypatch.setattr(enabled, "billing_recovery_grace_hours", hours)
    first = await failure_receipt(source)
    assert await activation.process_receipt(TestSessionLocal, first, provider, now=start) == "recovery_recorded"
    async with TestSessionLocal() as session:
        sub = await session.scalar(select(Subscription).where(Subscription.user_id == row.user_id))
        assert sub is not None
        assert _stored_utc(sub.current_period_end) == start
        assert effective_plan(sub, now=start - timedelta(seconds=1)).value == "pro"
        assert effective_plan(sub, now=start + timedelta(hours=hours)).value == "free"
        if hours:
            assert effective_plan(sub, now=start + timedelta(hours=hours) - timedelta(microseconds=1)).value == "pro"
        deadline = _stored_utc(sub.grace_until)
    monkeypatch.setattr(enabled, "billing_recovery_grace_hours", 72)
    source.update(status="halted", charge_at=int((start + timedelta(days=30)).timestamp()))
    replay = await failure_receipt(source, 2, "halted")
    assert await activation.process_receipt(TestSessionLocal, replay, provider, now=start + timedelta(hours=73)) == "recovery_recorded"
    async with TestSessionLocal() as session:
        sub = await session.scalar(select(Subscription).where(Subscription.user_id == row.user_id))
        assert sub is not None
        assert sub.status == "past_due" and _stored_utc(sub.grace_until) == deadline
        assert await session.scalar(select(func.count()).select_from(PaymentRecovery)) == 1
        case = await session.scalar(select(PaymentRecovery))
        assert case is not None
        assert case.provider_state == "halted" and case.invoice_id == invoice["id"]
    provider.subscription.create.assert_called_once()


async def test_paid_exact_invoice_resolves_recovery_without_processing_bonus(failure):
    row, provider, source, invoice, payment, start = failure
    rid = await failure_receipt(source)
    assert await activation.process_receipt(TestSessionLocal, rid, provider, now=start) == "recovery_recorded"
    source.update(status="active", paid_count=1)
    invoice.update(status="paid", payment_id=payment["id"], amount_paid=9900, amount_due=0)
    paid = await cycle_receipt(source, payment)
    assert await activation.process_receipt(TestSessionLocal, paid, provider, now=start + timedelta(days=3)) == "renewed"
    async with TestSessionLocal() as session:
        sub = await session.scalar(select(Subscription).where(Subscription.user_id == row.user_id))
        assert sub is not None
        assert sub.status == "active" and sub.grace_until is None and sub.recovery_due_at is None
        assert _stored_utc(sub.current_period_end) == start + timedelta(days=30)
        case = await session.scalar(select(PaymentRecovery))
        assert case is not None
        assert _stored_utc(case.resolved_at) == start + timedelta(days=3)


@pytest.mark.parametrize("field,value", [("currency","USD"),("amount", True),("amount", 1),("amount_paid",True),
    ("amount_due",True),("payment_id","pay_Other"),("status","paid"),("billing_end",True),("billing_end",0),
    ("subscription_id","sub_Other"),("entity","payment")])
async def test_unproven_invoice_never_changes_access(failure, field, value):
    row, provider, source, invoice, _, start = failure
    invoice[field] = value
    rid = await failure_receipt(source)
    assert await activation.process_receipt(TestSessionLocal, rid, provider, now=start) == "quarantined"
    async with TestSessionLocal() as session:
        sub = await session.scalar(select(Subscription).where(Subscription.user_id == row.user_id))
        assert sub is not None
        assert sub.status == "active" and sub.grace_until is None
        assert await session.scalar(select(func.count()).select_from(PaymentRecovery)) == 0


@pytest.mark.parametrize("field,value", [("paid_count",True),("paid_count",-1),("plan_id","plan_Other"),
    ("quantity",True),("has_scheduled_changes",True),("notes",{})])
async def test_unproven_subscription_never_changes_access(failure, field, value):
    _, provider, source, _, _, start = failure
    source[field] = value
    rid = await failure_receipt(source)
    assert await activation.process_receipt(TestSessionLocal, rid, provider, now=start) == "quarantined"


async def test_activated_without_paid_evidence_does_not_clear_recovery(failure):
    row, provider, source, _, _, start = failure
    first = await failure_receipt(source)
    assert await activation.process_receipt(TestSessionLocal, first, provider, now=start) == "recovery_recorded"
    source.update(status="active")
    rid = await failure_receipt(source, 2)
    assert await activation.process_receipt(TestSessionLocal, rid, provider, now=start + timedelta(days=1)) == "retry"
    async with TestSessionLocal() as session:
        sub = await session.scalar(select(Subscription).where(Subscription.user_id == row.user_id))
        assert sub is not None
        assert sub.status == "past_due" and effective_plan(sub, now=start + timedelta(days=1)).value == "free"


async def test_disabled_failure_receipts_do_not_starve_scanner(failure, enabled, monkeypatch):
    _, provider, source, _, _, start = failure
    for n in range(7):
        await failure_receipt(source, n)
    monkeypatch.setattr(enabled, "billing_recovery_enabled", False)
    assert await activation.scan_receipts(TestSessionLocal, provider, now=start) == {}
    assert provider.invoice.all.call_count == 0

@pytest.mark.parametrize("page", [None, {}, {"entity":"collection","count":True,"items":[]},
    {"entity":"collection","count":2,"items":[]}, {"entity":"payment","count":0,"items":[]}])
async def test_malformed_inventory_is_retryable_not_access(failure, page):
    _, provider, source, _, _, start = failure
    provider.invoice.all.side_effect = lambda _: page
    rid = await failure_receipt(source)
    assert await activation.process_receipt(TestSessionLocal, rid, provider, now=start) == "retry"


@pytest.mark.parametrize("mutation", ["inactive", "cancel", "plan", "paid_end", "key", "flag"])
async def test_revalidate_local_state_after_network(failure, enabled, monkeypatch, mutation):
    from app.billing.payment_recovery import invoices_for as original
    from app.billing import payment_recovery
    from app.models.user import User
    from app.models.payment_renewal import RenewalMandate
    row, provider, source, _, _, start = failure
    async def mutate(client, sid):
        result = await original(client, sid)
        async with TestSessionLocal() as session:
            sub = await session.scalar(select(Subscription).where(Subscription.user_id == row.user_id))
            assert sub is not None
            if mutation == "inactive":
                user = await session.get(User, row.user_id)
                assert user is not None
                user.is_active = False
            elif mutation == "cancel":
                sub.cancel_at_period_end = True
            elif mutation == "plan":
                sub.plan = "max"
            elif mutation == "paid_end":
                sub.current_period_end = start + timedelta(days=1)
            elif mutation == "key":
                mandate = await session.scalar(select(RenewalMandate))
                assert mandate is not None
                mandate.provider_key_id = "rzp_test_Other"
            else:
                monkeypatch.setattr(enabled, "billing_recovery_enabled", False)
            await session.commit()
        return result
    monkeypatch.setattr(payment_recovery, "invoices_for", mutate)
    rid = await failure_receipt(source)
    assert await activation.process_receipt(TestSessionLocal, rid, provider, now=start) == "quarantined"
    async with TestSessionLocal() as session:
        assert await session.scalar(select(func.count()).select_from(PaymentRecovery)) == 0


async def test_future_failure_does_not_shorten_paid_term(failure):
    row, provider, source, _, _, start = failure
    rid = await failure_receipt(source)
    assert await activation.process_receipt(TestSessionLocal, rid, provider, now=start - timedelta(seconds=1)) == "retry"
    async with TestSessionLocal() as session:
        sub = await session.scalar(select(Subscription).where(Subscription.user_id == row.user_id))
        assert sub is not None
        assert sub.status == "active" and effective_plan(sub, now=start - timedelta(seconds=1)).value == "pro"


async def test_pending_missing_paid_cycle_waits_for_reconciliation(failure):
    _, provider, source, _, _, start = failure
    source["paid_count"] = 1
    rid = await failure_receipt(source)
    assert await activation.process_receipt(TestSessionLocal, rid, provider, now=start) == "retry"


async def test_changed_invoice_cannot_replace_original_recovery(failure):
    _, provider, source, invoice, _, start = failure
    first = await failure_receipt(source)
    assert await activation.process_receipt(TestSessionLocal, first, provider, now=start) == "recovery_recorded"
    invoice["id"] = "inv_Replacement"
    replay = await failure_receipt(source, 2)
    assert await activation.process_receipt(TestSessionLocal, replay, provider, now=start + timedelta(hours=1)) == "quarantined"


@pytest.mark.parametrize("hours,due_offset", [(73,0),(24,1),(24,-1)])
async def test_corrupt_grace_projection_never_grants_unbounded_access(failure, hours, due_offset):
    row, _, _, _, _, start = failure
    async with TestSessionLocal() as session:
        sub = await session.scalar(select(Subscription).where(Subscription.user_id == row.user_id))
        assert sub is not None
        sub.status = "grace"
        sub.recovery_due_at = start + timedelta(seconds=due_offset)
        sub.grace_until = start + timedelta(hours=hours)
        assert effective_plan(sub, now=start + timedelta(hours=1)).value == "free"

async def test_delayed_failure_of_paid_period_does_not_regress_or_starve(failure):
    row, provider, source, invoice, payment, start = failure
    source["current_start"] = int(start.timestamp())
    old = await failure_receipt(source)
    source.update(status="active", paid_count=1)
    invoice.update(status="paid", payment_id=payment["id"], amount_paid=9900, amount_due=0)
    paid = await cycle_receipt(source, payment)
    assert await activation.process_receipt(TestSessionLocal, paid, provider, now=start) == "renewed"
    assert await activation.process_receipt(TestSessionLocal, old, provider, now=start + timedelta(days=1)) == "failure_superseded"
    async with TestSessionLocal() as session:
        sub = await session.scalar(select(Subscription).where(Subscription.user_id == row.user_id))
        assert sub is not None and sub.status == "active" and sub.grace_until is None
