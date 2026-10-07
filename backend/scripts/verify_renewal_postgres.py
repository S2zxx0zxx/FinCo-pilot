"""Native renewal proof invoked only by disposable signed-HTTP PostgreSQL CI."""
import asyncio
import copy
from datetime import timedelta
import hashlib
import hmac
import json
import threading
from fastapi import HTTPException
import importlib.util
from pathlib import Path
from alembic.migration import MigrationContext
from alembic.operations import Operations
from app.core.database import engine
from types import SimpleNamespace

from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from app.billing.activation import process_receipt
from app.billing.enums import BillingInterval, PlanId
from app.billing.offers import PROVIDER_PLAN_SPECS
from app.billing.razorpay_catalog import provider_plan_create_payload
from app.billing.renewal_mandates import create_mandate
from app.main import app
from app.models.payment_recovery import PaymentRecovery
from app.billing.service import effective_plan
from app.models.payment_renewal import RenewalCycle, RenewalMandate
from app.models.payment_webhook import PaymentWebhookEvent
from app.models.subscription import Subscription


async def verify(sessions, uid, settings, now, own_sessions):
    previous = settings.billing_renewal_enabled, settings.razorpay_plan_pro_monthly_id, settings.billing_recovery_enabled, settings.billing_recovery_grace_hours
    settings.billing_renewal_enabled = True
    settings.billing_recovery_enabled = True
    settings.billing_recovery_grace_hours = 24
    settings.razorpay_plan_pro_monthly_id = "plan_CIRenewal"
    plan = {"id": "plan_CIRenewal", "entity": "plan", **provider_plan_create_payload(PROVIDER_PLAN_SPECS[(PlanId.PRO, BillingInterval.MONTHLY)])}
    subscription, invoice, payment = {}, {}, {}
    posts = 0
    posted, release = threading.Event(), threading.Event()

    def fetch(value, identity):
        assert all(not session.in_transaction() for session in own_sessions.get()), "provider I/O held SQL transaction"
        assert value["id"] == identity
        return copy.deepcopy(value)

    def create(*, data):
        nonlocal posts
        assert all(not session.in_transaction() for session in own_sessions.get()), "provider POST held SQL transaction"
        posts += 1
        subscription.update(copy.deepcopy(data), id="sub_CI" + uid.hex + "N" + str(posts), entity="subscription", status="created", paid_count=0, has_scheduled_changes=False)
        posted.set()
        assert release.wait(10)
        return copy.deepcopy(subscription)

    provider = SimpleNamespace(plan=SimpleNamespace(fetch=lambda i: fetch(plan, i)), subscription=SimpleNamespace(create=create, fetch=lambda i: fetch(subscription, i)), invoice=SimpleNamespace(fetch=lambda i: fetch(invoice, i)), payment=SimpleNamespace(fetch=lambda i: fetch(payment, i)))

    def invoice_inventory(params):
        assert all(not session.in_transaction() for session in own_sessions.get())
        assert params == {"subscription_id": subscription["id"], "count": 100, "skip": 0}
        return {"entity": "collection", "count": 1, "items": [copy.deepcopy(invoice)]}
    provider.invoice.all = invoice_inventory

    async def receive(counter, event_type="subscription.charged"):
        event = {"entity": "event", "account_id": settings.razorpay_webhook_account_id, "event": event_type, "created_at": counter,
                 "payload": {"subscription": {"entity": subscription.copy()}, "payment": {"entity": {**payment, "email": "private-renewal-canary@example.invalid"}}}}
        if event_type != "subscription.charged":
            del event["payload"]["payment"]
        body = json.dumps(event).encode()
        secret = settings.razorpay_webhook_secret.get_secret_value()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://synthetic-ci") as client:
            result = await client.post("/api/webhooks/razorpay", content=body, headers={"content-type": "application/json", "x-razorpay-signature": hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()})
            assert result.status_code == 200
        async with sessions() as session:
            identity = await session.scalar(select(PaymentWebhookEvent.id).where(PaymentWebhookEvent.account_id == settings.razorpay_webhook_account_id, PaymentWebhookEvent.body_sha256 == hashlib.sha256(body).hexdigest()))
            assert identity
            return identity

    try:
        async with sessions() as session:
            before = await session.scalar(select(Subscription.current_period_end).where(Subscription.user_id == uid))
        async def enroll():
            async with sessions() as session:
                return await create_mandate(session, uid, 1, provider, now=now)
        first = asyncio.create_task(enroll())
        try:
            assert await asyncio.to_thread(posted.wait, 5)
            try:
                await enroll()
            except HTTPException as exc:
                assert exc.status_code == 409
            else:
                raise AssertionError("concurrent enrollment was not fenced")
        finally:
            release.set()
            result = await asyncio.wait_for(first, 10)
        async with sessions() as session:
            assert (await create_mandate(session, uid, 1, provider, now=now))["subscription_id"] == result["subscription_id"]
            assert await session.scalar(select(Subscription.current_period_end).where(Subscription.user_id == uid)) == before
        assert posts == 1
        start, end = result["starts_at"], result["starts_at"] + timedelta(days=30)
        subscription.update(status="completed", paid_count=1)
        invoice.update(id="inv_CI" + uid.hex, entity="invoice", subscription_id=subscription["id"], payment_id="pay_CIRenewal" + uid.hex, status="paid", amount=9900, amount_paid=9900, amount_due=0, currency="INR", billing_start=int(start.timestamp()), billing_end=int(end.timestamp()))
        payment.update(id=invoice["payment_id"], entity="payment", invoice_id=invoice["id"], captured="1", status="captured", amount=9900, currency="INR", amount_refunded=0, refund_status=None)
        subscription.update(status="pending", paid_count=0)
        invoice.update(status="issued", amount_paid=0, amount_due=9900, payment_id=None)
        failed = [await receive(i, "subscription.pending") for i in range(80, 88)]
        outcomes = await asyncio.gather(*(process_receipt(sessions, i, provider, now=start) for i in failed))
        if outcomes != ["recovery_recorded"] * 8:
            async with sessions() as session:
                codes = list((await session.scalars(select(PaymentWebhookEvent.processing_error).where(PaymentWebhookEvent.id.in_(failed)))).all())
            raise AssertionError((outcomes, codes))
        async with sessions() as session:
            assert await session.scalar(select(func.count()).select_from(PaymentRecovery).where(PaymentRecovery.user_id == uid)) == 1
            sub = await session.scalar(select(Subscription).where(Subscription.user_id == uid))
            assert sub.current_period_end == before and sub.grace_until == before + timedelta(hours=24)
            assert effective_plan(sub, now=before + timedelta(hours=24) - timedelta(microseconds=1)).value == "pro"
            assert effective_plan(sub, now=before + timedelta(hours=24)).value == "free"
        settings.billing_recovery_grace_hours = 72
        subscription.update(status="halted")
        halted = await receive(89, "subscription.halted")
        assert await process_receipt(sessions, halted, provider, now=start + timedelta(hours=25)) == "recovery_recorded"
        async with sessions() as session:
            sub = await session.scalar(select(Subscription).where(Subscription.user_id == uid))
            assert sub.status == "past_due" and sub.grace_until == before + timedelta(hours=24)
        subscription.update(status="completed", paid_count=1)
        invoice.update(status="paid", amount_paid=9900, amount_due=0, payment_id=payment["id"])
        future = await receive(100)
        outcome = await process_receipt(sessions, future, provider, now=now)
        assert outcome == "retry", outcome
        async with sessions() as session:
            assert await session.scalar(select(Subscription.current_period_end).where(Subscription.user_id == uid)) == before
            receipt = await session.get(PaymentWebhookEvent, future)
            assert receipt and receipt.state == "pending" and receipt.next_attempt_at == start
        identities = [await receive(i) for i in range(101, 109)]
        results = await asyncio.gather(*(process_receipt(sessions, identity, provider, now=start) for identity in identities))
        assert results.count("renewed") == 1 and results.count("duplicate") == 7, results
        assert await process_receipt(sessions, future, provider, now=start) == "duplicate"
        async with sessions() as session:
            assert await session.scalar(select(func.count()).select_from(RenewalCycle).where(RenewalCycle.user_id == uid)) == 1
            mandate = await session.scalar(select(RenewalMandate).where(RenewalMandate.user_id == uid))
            assert mandate and mandate.state == "completed" and mandate.active_user_id is None
            assert await session.scalar(select(Subscription.current_period_end).where(Subscription.user_id == uid)) == end
            cycle = await session.scalar(select(RenewalCycle).where(RenewalCycle.user_id == uid))
            assert cycle and "private-renewal-canary" not in str(cycle.__dict__)
            case = await session.scalar(select(PaymentRecovery).where(PaymentRecovery.user_id == uid))
            assert case and case.resolved_at == start
            sub = await session.scalar(select(Subscription).where(Subscription.user_id == uid))
            assert sub.status == "active" and sub.grace_until is None and sub.recovery_due_at is None
        spec = importlib.util.spec_from_file_location("renewal104", Path(__file__).resolve().parents[1] / "alembic/versions/104_renewal_lifecycle.py")
        assert spec and spec.loader
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        async with engine.begin() as connection:
            def refuse(sync):
                with Operations.context(MigrationContext.configure(sync)):
                    try:
                        migration.downgrade()
                    except RuntimeError:
                        return
                    raise AssertionError("populated downgrade discarded renewal evidence")
            await connection.run_sync(refuse)
        recovery_spec = importlib.util.spec_from_file_location("recovery105", Path(__file__).resolve().parents[1] / "alembic/versions/105_payment_recovery.py")
        assert recovery_spec and recovery_spec.loader
        recovery_migration = importlib.util.module_from_spec(recovery_spec)
        recovery_spec.loader.exec_module(recovery_migration)
        async with engine.begin() as connection:
            def refuse_recovery(sync):
                with Operations.context(MigrationContext.configure(sync)):
                    try:
                        recovery_migration.downgrade()
                    except RuntimeError:
                        return
                    raise AssertionError("populated downgrade discarded failure evidence")
            await connection.run_sync(refuse_recovery)
        # A separately authorized mandate after finite completion exercises cancellation.
        from app.billing.cancellation import cancel
        from app.models.payment_cancellation import PaymentCancellation
        previous_cancellation = settings.billing_cancellation_enabled
        settings.billing_cancellation_enabled = True
        cancelled_posted, cancelled_release = threading.Event(), threading.Event()
        cancellation_posts = 0
        def stop(sid, data):
            nonlocal cancellation_posts
            assert all(not session.in_transaction() for session in own_sessions.get())
            assert sid == subscription["id"] and data == {"cancel_at_cycle_end": False}
            cancellation_posts += 1
            cancelled_posted.set()
            assert cancelled_release.wait(10)
            subscription["status"] = "cancelled"
            raise TimeoutError("synthetic ambiguous provider outcome")
        provider.subscription.cancel = stop
        try:
            async with sessions() as session:
                await create_mandate(session, uid, 2, provider, now=start)
            async def stop_owned():
                async with sessions() as session:
                    return await cancel(session, uid, provider, now=start)
            stopping = asyncio.create_task(stop_owned())
            try:
                assert await asyncio.to_thread(cancelled_posted.wait, 5)
                assert (await stop_owned())["state"] == "sending"
            finally:
                cancelled_release.set()
                stopped = await asyncio.wait_for(stopping, 10)
            assert stopped["state"] == "uncertain" and cancellation_posts == 1
            receipts = [await receive(i, "subscription.cancelled") for i in range(200,208)]
            outcomes = await asyncio.gather(*(process_receipt(sessions, i, provider, now=start) for i in receipts))
            assert outcomes == ["cancelled"] * 8, outcomes
            async with sessions() as session:
                claims = list((await session.scalars(select(PaymentCancellation).where(PaymentCancellation.user_id == uid))).all())
                assert len(claims) == 1 and claims[0].state == "confirmed"
                sub = await session.scalar(select(Subscription).where(Subscription.user_id == uid))
                assert sub.status == "canceled" and sub.cancel_at_period_end and sub.current_period_end == end
                assert effective_plan(sub, now=end-timedelta(microseconds=1)).value == "pro"
                assert effective_plan(sub, now=end).value == "free"
                await session.commit()
                assert (await stop_owned())["state"] == "confirmed"
            assert cancellation_posts == 1
            spec106 = importlib.util.spec_from_file_location("cancellation106", Path(__file__).resolve().parents[1] / "alembic/versions/106_payment_cancellation.py")
            assert spec106 and spec106.loader
            migration106 = importlib.util.module_from_spec(spec106)
            spec106.loader.exec_module(migration106)
            async with engine.begin() as connection:
                def refuse106(sync):
                    with Operations.context(MigrationContext.configure(sync)):
                        try:
                            migration106.downgrade()
                        except RuntimeError:
                            return
                        raise AssertionError("populated cancellation downgrade discarded evidence")
                await connection.run_sync(refuse106)
            print("PASS: native cancellation; one POST under concurrent requests; ambiguous outcome never reposted; eight signed HTTP cancellation receipts confirm one retained claim; paid service preserved with exact expiry; provider I/O outside SQL; populated106 downgrade refused")
        finally:
            cancelled_release.set()
            settings.billing_cancellation_enabled = previous_cancellation
        print("PASS: native signed recovery HTTP; eight concurrent subscription-only failures create one recovery; immutable replay/halted grace; exact expiry; captured invoice atomically restores access; provider I/O outside SQL; populated recovery downgrade refused")
        print("PASS: native signed renewal HTTP; one POST under concurrent enrollment; authorization does not grant access; provider I/O outside SQL; eight concurrent paid receipts grant exactly once; future cycle deferred; finite completion; minimal retained evidence; populated renewal downgrade refused")
    finally:
        release.set()
        settings.billing_renewal_enabled, settings.razorpay_plan_pro_monthly_id, settings.billing_recovery_enabled, settings.billing_recovery_grace_hours = previous
