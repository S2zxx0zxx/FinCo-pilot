"""Real ownership/SQL/inbox; provider network responses are synthetic."""
import copy
from datetime import timedelta

from fastapi import HTTPException
import pytest
from sqlalchemy import select, func

from app.billing import activation, cancellation
from app.billing.offer_service import _stored_utc
from app.billing.service import effective_plan
from app.models.payment_cancellation import PaymentCancellation
from app.models.subscription import Subscription
from tests.conftest import TestSessionLocal
from tests.test_payment_activation import enabled as enabled, purchase as purchase
from tests.test_renewal_lifecycle import renewal as renewal, cycle_receipt
from tests.test_payment_recovery import failure_receipt


@pytest.fixture
async def cancellable(renewal, enabled, monkeypatch):
    monkeypatch.setattr(enabled, "billing_cancellation_enabled", True)
    row, provider, source, plan, invoice, payment, start = renewal
    source.update(paid_count=0)
    def stop(sid, data):
        assert sid == source["id"] and data == {"cancel_at_cycle_end": False}
        source["status"] = "cancelled"
        return copy.deepcopy(source)
    provider.subscription.cancel.side_effect = stop
    return row, provider, source, plan, invoice, payment, start


async def test_one_dispatch_replay_preserves_paid_access(cancellable):
    row, provider, _, _, _, _, end = cancellable
    async with TestSessionLocal() as session:
        result = await cancellation.cancel(session, row.user_id, provider)
        assert result["state"] == "confirmed" and result["paid_through"] == end
        assert (await cancellation.cancel(session, row.user_id, provider))["state"] == "confirmed"
    provider.subscription.cancel.assert_called_once()
    async with TestSessionLocal() as session:
        sub = await session.scalar(select(Subscription).where(Subscription.user_id == row.user_id))
        assert sub is not None
        assert sub.status == "canceled" and sub.cancel_at_period_end
        assert effective_plan(sub, now=end-timedelta(microseconds=1)).value == "pro"
        assert effective_plan(sub, now=end).value == "free"
        assert await session.scalar(select(func.count()).select_from(PaymentCancellation)) == 1


async def test_ambiguous_dispatch_never_reposts_and_webhook_confirms(cancellable):
    row, provider, source, _, _, _, _ = cancellable
    provider.subscription.cancel.side_effect = TimeoutError("synthetic unknown outcome")
    async with TestSessionLocal() as session:
        assert (await cancellation.cancel(session, row.user_id, provider))["state"] == "uncertain"
        assert (await cancellation.cancel(session, row.user_id, provider))["state"] == "uncertain"
    provider.subscription.cancel.assert_called_once()
    source["status"] = "cancelled"
    receipt = await failure_receipt(source, state="cancelled")
    assert await activation.process_receipt(TestSessionLocal, receipt, provider) == "cancelled"
    assert await activation.process_receipt(TestSessionLocal, receipt, provider) == "unchanged"
    provider.subscription.cancel.assert_called_once()


async def test_provider_cancelled_without_local_dispatch_requires_no_post(cancellable):
    row, provider, source, _, _, _, _ = cancellable
    source["status"] = "cancelled"
    receipt = await failure_receipt(source, state="cancelled")
    assert await activation.process_receipt(TestSessionLocal, receipt, provider) == "cancelled"
    provider.subscription.cancel.assert_not_called()
    async with TestSessionLocal() as session:
        assert (await cancellation.preview(session, row.user_id))["state"] == "confirmed"


@pytest.mark.parametrize("field,value", [("id","sub_Foreign"),("plan_id","plan_Foreign"),
    ("notes",{}),("paid_count",True),("quantity",2),("has_scheduled_changes",True),
    ("total_count",100),("status","expired"),("start_at",0)])
async def test_unproven_provider_cannot_cancel(cancellable, field, value):
    row, provider, source, _, _, _, _ = cancellable
    source[field] = value
    async with TestSessionLocal() as session:
        with pytest.raises(HTTPException):
            await cancellation.cancel(session, row.user_id, provider)
        assert await session.scalar(select(func.count()).select_from(PaymentCancellation)) == 0
    provider.subscription.cancel.assert_not_called()


async def test_false_post_response_is_not_confirmation(cancellable):
    row, provider, source, _, _, _, _ = cancellable
    provider.subscription.cancel.side_effect = lambda *_: {**source, "status":"cancelled"}
    async with TestSessionLocal() as session:
        assert (await cancellation.cancel(session, row.user_id, provider))["state"] == "uncertain"
        sub = await session.scalar(select(Subscription).where(Subscription.user_id == row.user_id))
        assert sub is not None
        assert sub.status == "active" and not sub.cancel_at_period_end


async def test_delayed_paid_invoice_extends_paid_term_without_reactivation(cancellable):
    row, provider, source, _, _, payment, start = cancellable
    async with TestSessionLocal() as session:
        await cancellation.cancel(session, row.user_id, provider)
    source["paid_count"] = 1
    receipt = await cycle_receipt(source, payment)
    assert await activation.process_receipt(TestSessionLocal, receipt, provider, now=start) == "renewed"
    async with TestSessionLocal() as session:
        sub = await session.scalar(select(Subscription).where(Subscription.user_id == row.user_id))
        assert sub is not None
        assert sub.status == "canceled" and sub.cancel_at_period_end
        assert _stored_utc(sub.current_period_end) == start + timedelta(days=30)


async def test_disabled_gate_never_dispatches(cancellable, enabled, monkeypatch):
    row, provider, _, _, _, _, _ = cancellable
    monkeypatch.setattr(enabled, "billing_cancellation_enabled", False)
    async with TestSessionLocal() as session:
        assert await cancellation.preview(session, row.user_id) == {"available":False}
        with pytest.raises(HTTPException) as error:
            await cancellation.cancel(session, row.user_id, provider)
        assert error.value.status_code == 503
    provider.subscription.cancel.assert_not_called()


async def test_authenticated_api_strict_consent_and_owned_identity(client, auth_headers, cancellable, monkeypatch):
    from app.api import checkout
    _, provider, _, _, _, _, _ = cancellable
    monkeypatch.setattr(checkout, "_get_razorpay_client", lambda: provider)
    assert (await client.get("/api/billing/cancellation")).status_code == 401
    for body in [{"authorize":False}, {"authorize":"true"}, {"authorize":1},
                 {"authorize":True,"subscription_id":"sub_Foreign"}, {}]:
        assert (await client.post("/api/billing/cancellation", headers=auth_headers, json=body)).status_code == 422
    provider.subscription.cancel.assert_not_called()
    result = await client.post("/api/billing/cancellation", headers=auth_headers, json={"authorize":True})
    assert result.status_code == 200 and result.json()["state"] == "confirmed"
    assert "provider_subscription_id" not in result.json()
    provider.session.close.assert_called_once()


async def test_other_user_cannot_cancel(cancellable, session):
    import uuid
    from app.models.user import User
    _, provider, _, _, _, _, _ = cancellable
    other = User(id=uuid.uuid4(), email="other-cancel@example.invalid", hashed_password="unused", is_active=True)
    session.add(other)
    await session.commit()
    with pytest.raises(HTTPException):
        await cancellation.cancel(session, other.id, provider)
    provider.subscription.cancel.assert_not_called()


async def test_unresolved_cancellation_blocks_deletion(cancellable, session, test_user):
    from app.services import account_deletion_service as deletion
    row, provider, _, _, _, _, _ = cancellable
    provider.subscription.cancel.side_effect = TimeoutError("synthetic")
    async with TestSessionLocal() as own:
        await cancellation.cancel(own, row.user_id, provider)
    result = await deletion.request_deletion(session, test_user)
    assert result["state"] == "blocked" and "cancellation_outcome_unresolved" in result["blockers"]


async def test_confirmed_cancellation_retained_after_real_account_purge(cancellable, session, test_user):
    from tests.test_account_deletion_workflow import operator, approved, finish_execution
    row, provider, source, _, _, _, _ = cancellable
    async with TestSessionLocal() as own:
        await cancellation.cancel(own, row.user_id, provider)
    admin = await operator(session)
    job, _ = await approved(session, test_user, admin)
    await finish_execution(session, job, admin)
    assert job.state == "backup_expiry_pending"
    assert await session.scalar(select(func.count()).select_from(PaymentCancellation)) == 1
    receipt = await failure_receipt(source, 10, "cancelled")
    assert await activation.process_receipt(TestSessionLocal, receipt, provider) == "quarantined"


async def test_recovery_cannot_reopen_confirmed_cancelled_service(cancellable, enabled, monkeypatch):
    monkeypatch.setattr(enabled, "billing_recovery_enabled", True)
    row, provider, source, _, _, _, _ = cancellable
    async with TestSessionLocal() as own:
        await cancellation.cancel(own, row.user_id, provider)
    source["status"] = "pending"
    receipt = await failure_receipt(source)
    assert await activation.process_receipt(TestSessionLocal, receipt, provider) == "quarantined"


async def test_unresolved_cancel_does_not_grant_paid_cycle(cancellable):
    row, provider, source, _, _, payment, start = cancellable
    provider.subscription.cancel.side_effect = TimeoutError("synthetic")
    async with TestSessionLocal() as own:
        await cancellation.cancel(own, row.user_id, provider)
    source.update(paid_count=1)
    receipt = await cycle_receipt(source, payment)
    assert await activation.process_receipt(TestSessionLocal, receipt, provider, now=start) == "retry"
