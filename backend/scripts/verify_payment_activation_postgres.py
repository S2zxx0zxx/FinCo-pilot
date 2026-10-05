"""Real signed HTTP/PostgreSQL races with synthetic provider GETs; never real money."""
import asyncio
from contextvars import ContextVar
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import importlib.util
import json
import os
from pathlib import Path
from types import SimpleNamespace
import threading
import uuid

from alembic.migration import MigrationContext
from alembic.operations import Operations
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.billing.activation import process_receipt
from app.billing.checkout_orders import order_notes
from app.billing.service import effective_plan
from app.core.config import get_settings
from app.core.database import engine
from app.main import app
from app.models.payment_activation import PaymentActivation
from app.models.payment_webhook import PaymentWebhookEvent
from app.models.pricing_offer import CheckoutReservation, FoundingMember, PricingAuditEvent
from app.models.subscription import Subscription
from app.models.user import User


async def main():
    if os.environ.get("CI") != "true" or os.environ.get("FINCO_DISPOSABLE_DB_TEST") != "yes" or engine.dialect.name != "postgresql":
        raise SystemExit("Refusing outside disposable CI PostgreSQL")
    own_sessions: ContextVar[tuple[AsyncSession, ...]] = ContextVar("activation_proof_sessions", default=())
    ready, release = asyncio.Event(), asyncio.Event()
    hold = False

    class TrackedSession(AsyncSession):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            own_sessions.set((*own_sessions.get(), self))

        async def commit(self):
            nonlocal hold
            if hold and any(isinstance(row, PaymentActivation) for row in self.new):
                hold = False
                ready.set()
                await release.wait()
            await super().commit()

    sessions = async_sessionmaker(engine, class_=TrackedSession, expire_on_commit=False)
    settings = get_settings()
    previous = {k: getattr(settings, k) for k in ("billing_activation_enabled", "deployment_environment",
        "razorpay_key_id", "razorpay_key_secret", "razorpay_webhook_enabled", "razorpay_webhook_mode",
        "razorpay_webhook_account_id", "razorpay_webhook_secret")}
    uid, rid = uuid.uuid4(), uuid.uuid4()
    account, key = "acc_CI" + uid.hex, "rzp_test_CIActivation"
    secret = "synthetic-ci-activation-webhook-key-0123456789"
    for k, v in dict(billing_activation_enabled=True, deployment_environment="test", razorpay_key_id=key,
                    razorpay_key_secret=SecretStr("synthetic-api-secret"), razorpay_webhook_enabled=True,
                    razorpay_webhook_mode="test", razorpay_webhook_account_id=account,
                    razorpay_webhook_secret=SecretStr(secret)).items():
        setattr(settings, k, v)
    now = datetime.now(timezone.utc)
    order_id, payment_id = "order_CI" + rid.hex, "pay_CI" + rid.hex
    order, payment = {}, {}
    fetched_second, fetch_lock = threading.Event(), threading.Lock()
    payment_reads = 0

    def fetch_order(identity):
        assert identity == order_id
        assert all(not session.in_transaction() for session in own_sessions.get()), "provider I/O held a SQL transaction"
        return order.copy()

    def fetch_payment(identity):
        nonlocal payment_reads
        assert identity == payment_id
        assert all(not session.in_transaction() for session in own_sessions.get()), "provider I/O held a SQL transaction"
        with fetch_lock:
            payment_reads += 1
            if payment_reads == 2:
                fetched_second.set()
        return payment.copy()

    provider = SimpleNamespace(order=SimpleNamespace(fetch=fetch_order), payment=SimpleNamespace(fetch=fetch_payment))

    async def receive(counter):
        event = dict(entity="event", account_id=account, event="payment.captured", created_at=counter,
                     payload={"payment": {"entity": {**payment, "email": "private-ci-canary@example.com"}}})
        body = json.dumps(event).encode()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://synthetic-ci") as client:
            response = await client.post("/api/webhooks/razorpay", content=body,
                headers={"content-type": "application/json", "x-razorpay-signature": hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()})
            assert response.status_code == 200, response.status_code
        async with sessions() as session:
            identity = await session.scalar(select(PaymentWebhookEvent.id).where(
                PaymentWebhookEvent.account_id == account, PaymentWebhookEvent.body_sha256 == hashlib.sha256(body).hexdigest()))
            assert identity
            return identity

    try:
        async with sessions() as session:
            session.add(User(id=uid, email=f"activation-{uid.hex}@example.invalid", hashed_password="synthetic",
                             is_active=True, is_superuser=False, is_verified=True))
            await session.flush()
            session.add(Subscription(user_id=uid, plan="free", status="free", billing_interval="none"))
            row = CheckoutReservation(id=rid, user_id=uid, plan="pro", billing_interval="monthly",
                offer_code="pro_monthly_intro", campaign_version="v1", amount_minor=9900, currency="INR",
                renewal_amount_minor=9900, renewal_interval="monthly", service_period_days=60,
                service_starts_at=now + timedelta(days=1), reserved_at=now, expires_at=now + timedelta(minutes=10),
                provider_order_state="ready", provider_key_id=key, provider_receipt="fp-" + rid.hex,
                provider_order_id=order_id, status="reserved")
            session.add(row)
            await session.commit()
            order.update(id=order_id, entity="order", amount=9900, currency="INR", receipt=row.provider_receipt,
                         notes=order_notes(row), status="paid", amount_paid=9900, amount_due=0)
            payment.update(id=payment_id, entity="payment", order_id=order_id, amount=9900, currency="INR",
                           captured=True, status="captured", amount_refunded=0, refund_status=None)
        a, b = await receive(1), await receive(2)
        hold = True
        first = asyncio.create_task(process_receipt(sessions, a, provider, now=now))
        second = None
        try:
            await asyncio.wait_for(ready.wait(), 5)
            second = asyncio.create_task(process_receipt(sessions, b, provider, now=now))
            assert await asyncio.to_thread(fetched_second.wait, 2), "competing provider read did not complete"
            await asyncio.sleep(0.05)
            assert not second.done(), "competing activation bypassed the user/receipt transaction"
        finally:
            release.set()
            results = await asyncio.wait_for(asyncio.gather(first, *([second] if second else [])), 10)
        assert sorted(results) == ["activated", "duplicate"], results
        identities = [await receive(i) for i in range(3, 11)]
        assert all(result == "duplicate" for result in await asyncio.gather(*(
            process_receipt(sessions, identity, provider, now=now + timedelta(hours=1)) for identity in identities)))
        async with sessions() as session:
            assert await session.scalar(select(func.count()).select_from(PaymentActivation).where(PaymentActivation.user_id == uid)) == 1
            grant = await session.scalar(select(PaymentActivation).where(PaymentActivation.user_id == uid))
            sub = await session.scalar(select(Subscription).where(Subscription.user_id == uid))
            assert grant and sub and grant.period_end - grant.period_start == timedelta(days=60)
            assert effective_plan(sub, now=now).value == "free"
            assert effective_plan(sub, now=now + timedelta(days=1)).value == "pro"
            assert effective_plan(sub, now=now + timedelta(days=61)).value == "free"
            assert "private-ci-canary" not in str(grant.__dict__)
            # Later changes must not be undone by a captured-payment replay.
            sub.status, sub.cancel_at_period_end = "canceled", True
            await session.commit()
        replay = await receive(12)
        assert await process_receipt(sessions, replay, provider, now=now) == "duplicate"
        async with sessions() as session:
            sub = await session.scalar(select(Subscription).where(Subscription.user_id == uid))
            assert sub and sub.status == "canceled" and sub.cancel_at_period_end
            user = await session.get(User, uid)
            assert user
            user.is_active = False
            await session.commit()
        inactive = await receive(13)
        assert await process_receipt(sessions, inactive, provider, now=now) == "quarantined"
        spec = importlib.util.spec_from_file_location("activation103", Path(__file__).resolve().parents[1] / "alembic/versions/103_payment_activation.py")
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
                    raise AssertionError("populated downgrade discarded activation evidence")
            await connection.run_sync(refuse)
        print("PASS: native signed HTTP -> durable inbox -> synthetic provider GETs without SQL transaction -> concurrent first-purchase activation exactly once; eight distinct-body replays preserve term/state; future/expiry and inactive-user fences; minimal grant evidence and populated downgrade refusal")
    finally:
        release.set()
        async with sessions() as session:
            for model, predicate in ((PaymentActivation, PaymentActivation.user_id == uid),
                (PaymentWebhookEvent, PaymentWebhookEvent.account_id == account),
                (PricingAuditEvent, PricingAuditEvent.actor_user_id == uid), (FoundingMember, FoundingMember.user_id == uid),
                (CheckoutReservation, CheckoutReservation.user_id == uid), (Subscription, Subscription.user_id == uid), (User, User.id == uid)):
                await session.execute(delete(model).where(predicate))
            await session.commit()
        for k, v in previous.items():
            setattr(settings, k, v)
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
