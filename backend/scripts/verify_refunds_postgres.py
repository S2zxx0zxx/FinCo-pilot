"""Disposable native PostgreSQL proof, invoked by the signed-payment CI harness."""
import asyncio
import copy
import hashlib
import hmac
import importlib.util
import json
from pathlib import Path
import threading
from types import SimpleNamespace
from alembic.migration import MigrationContext
from alembic.operations import Operations
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, func
from app.billing.activation import process_receipt
from app.billing.refunds import dispatch
from app.billing.service import effective_plan
from app.core.database import engine
from app.main import app
from app.models.payment_refund import PaymentRefund, RefundObservation
from app.models.payment_renewal import RenewalCycle
from app.models.payment_webhook import PaymentWebhookEvent
from app.models.subscription import Subscription
from app.models.user import User


async def verify(sessions, uid, settings, now, own_sessions):
    previous = settings.billing_refunds_enabled
    settings.billing_refunds_enabled = True
    posted, release = threading.Event(), threading.Event()
    posts = 0
    async with sessions() as session:
        row = await session.scalar(select(RenewalCycle).where(RenewalCycle.user_id == uid)
            .order_by(RenewalCycle.period_end.desc()).limit(1))
        actor = await session.get(User, uid)
        assert row and actor
        actor.is_superuser = True
        await session.commit()
    payment = dict(id=row.payment_id, entity="payment", invoice_id=row.invoice_id,
        amount=row.amount_minor, currency="INR", captured=True, status="captured", amount_refunded=0, refund_status=None)
    items = []
    def outside_sql():
        assert all(not session.in_transaction() for session in own_sessions.get()), "refund provider I/O held SQL"
    def fetch(pid):
        outside_sql()
        assert pid == row.payment_id
        return copy.deepcopy(payment)
    def inventory(pid, data):
        outside_sql()
        assert pid == row.payment_id and data == {"count":100,"skip":0}
        return {"entity":"collection", "count":len(items), "items":copy.deepcopy(items)}
    def refund(pid, data, **kwargs):
        nonlocal posts
        outside_sql()
        posts += 1
        assert posts == 1 and pid == row.payment_id and data["amount"] == row.amount_minor
        assert kwargs["headers"]["X-Refund-Idempotency"].replace("-", "") == data["receipt"][3:]
        posted.set()
        assert release.wait(20)
        items.append(dict(id="rfnd_CI"+uid.hex,entity="refund",payment_id=pid,amount=data["amount"],
            currency="INR",receipt=data["receipt"],status="processed"))
        payment.update(amount_refunded=row.amount_minor,refund_status="full",status="refunded")
        raise TimeoutError("synthetic accepted refund, response lost")
    provider=SimpleNamespace(payment=SimpleNamespace(fetch=fetch,fetch_multiple_refund=inventory,refund=refund))
    async def issue():
        async with sessions() as session:
            return await dispatch(session,uid,"renewal",row.id,row.amount_minor,"a"*64,provider,now=now)
    try:
        first=asyncio.create_task(issue())
        assert await asyncio.to_thread(posted.wait,10)
        second=await asyncio.wait_for(issue(),10)
        assert second["state"]=="sending" and posts==1
        release.set()
        assert (await asyncio.wait_for(first,20))["state"]=="processed"
        assert (await issue())["state"]=="processed" and posts==1
        async with AsyncClient(transport=ASGITransport(app=app),base_url="http://ci.test") as http:
            receipts=[]
            for counter in range(8):
                event=dict(entity="event",account_id=settings.razorpay_webhook_account_id,event="refund.processed",
                    created_at=counter,payload={"refund":{"entity":{**items[0],"notes":{"private":"private-ci-refund-canary"}}}})
                raw=json.dumps(event,separators=(",", ":")).encode()
                signature=hmac.new(settings.razorpay_webhook_secret.get_secret_value().encode(),raw,hashlib.sha256).hexdigest()
                response=await http.post("/api/webhooks/razorpay",content=raw,
                    headers={"X-Razorpay-Signature":signature,"Content-Type":"application/json"})
                assert response.status_code==200,response.text
                async with sessions() as session:
                    receipt=await session.scalar(select(PaymentWebhookEvent).where(PaymentWebhookEvent.body_sha256==hashlib.sha256(raw).hexdigest()))
                    assert receipt
                    receipts.append(receipt.id)
            results=await asyncio.gather(*(process_receipt(sessions,rid,provider,now=now) for rid in receipts))
            assert all(value=="refund_reconciled" for value in results),results
        async with sessions() as session:
            assert await session.scalar(select(func.count()).select_from(PaymentRefund).where(PaymentRefund.user_id==uid))==1
            assert await session.scalar(select(func.count()).select_from(RefundObservation).where(RefundObservation.user_id==uid))==1
            sub=await session.scalar(select(Subscription).where(Subscription.user_id==uid))
            assert sub and sub.paid_term_refunded and effective_plan(sub,now=row.period_start).value=="free"
            assert sub.current_period_end==row.period_end
        spec=importlib.util.spec_from_file_location("refund107",Path(__file__).resolve().parents[1]/"alembic/versions/107_payment_refunds.py")
        assert spec and spec.loader
        migration=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        async with engine.begin() as connection:
            def refuse(sync):
                with Operations.context(MigrationContext.configure(sync)):
                    try:
                        migration.downgrade()
                    except RuntimeError:
                        return
                    raise AssertionError("populated refund downgrade discarded evidence")
            await connection.run_sync(refuse)
        print("PASS: native refund; one durable POST under concurrent decisions; idempotency header/receipt exact; lost response confirmed only by fresh GET; eight signed HTTP refund receipts converge to one retained observation; full refund revokes only its paid term; no SQL during SDK; populated107 downgrade refused")
    finally:
        release.set()
        async with sessions() as session:
            actor=await session.get(User,uid)
            if actor:
                actor.is_superuser=False
                await session.commit()
        settings.billing_refunds_enabled=previous
