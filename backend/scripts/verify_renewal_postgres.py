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
from app.models.payment_renewal import RenewalCycle, RenewalMandate
from app.models.payment_webhook import PaymentWebhookEvent
from app.models.subscription import Subscription


async def verify(sessions, uid, settings, now, own_sessions):
    previous = settings.billing_renewal_enabled, settings.razorpay_plan_pro_monthly_id
    settings.billing_renewal_enabled = True
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
        subscription.update(copy.deepcopy(data), id="sub_CI" + uid.hex, entity="subscription", status="created", paid_count=0, has_scheduled_changes=False)
        posted.set()
        assert release.wait(10)
        return copy.deepcopy(subscription)

    provider = SimpleNamespace(plan=SimpleNamespace(fetch=lambda i: fetch(plan, i)), subscription=SimpleNamespace(create=create, fetch=lambda i: fetch(subscription, i)), invoice=SimpleNamespace(fetch=lambda i: fetch(invoice, i)), payment=SimpleNamespace(fetch=lambda i: fetch(payment, i)))

    async def receive(counter):
        event = {"entity": "event", "account_id": settings.razorpay_webhook_account_id, "event": "subscription.charged", "created_at": counter,
                 "payload": {"subscription": {"entity": subscription.copy()}, "payment": {"entity": {**payment, "email": "private-renewal-canary@example.invalid"}}}}
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
        future = await receive(100)
        assert await process_receipt(sessions, future, provider, now=now) == "pending"
        async with sessions() as session:
            assert await session.scalar(select(Subscription.current_period_end).where(Subscription.user_id == uid)) == before
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
        print("PASS: native signed renewal HTTP; one POST under concurrent enrollment; authorization does not grant access; provider I/O outside SQL; eight concurrent paid receipts grant exactly once; future cycle deferred; finite completion; minimal retained evidence; populated renewal downgrade refused")
    finally:
        release.set()
        settings.billing_renewal_enabled, settings.razorpay_plan_pro_monthly_id = previous
