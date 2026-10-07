"""Native signed failure signals stay non-granting and fresh status never collects."""
import asyncio
import hashlib
import hmac
import json
from types import SimpleNamespace
from unittest.mock import patch
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, func
from app.billing.activation import process_receipt
from app.billing.checkout_orders import order_notes
from app.core.auth import get_jwt_strategy
from app.main import app
from app.models.payment_activation import PaymentActivation
from app.models.payment_webhook import PaymentWebhookEvent
from app.models.pricing_offer import CheckoutReservation
from app.models.subscription import Subscription
from app.models.user import User


async def verify(sessions, uid, settings, now, own_sessions):
    previous=settings.billing_checkout_enabled
    settings.billing_checkout_enabled=True
    async with sessions() as session:
        row=await session.scalar(select(CheckoutReservation).where(CheckoutReservation.user_id==uid))
        sub=await session.scalar(select(Subscription).where(Subscription.user_id==uid))
        user=await session.get(User,uid)
        assert row and sub and user
        end=sub.current_period_end
        token=await get_jwt_strategy().write_token(user)
        payment_id=row.provider_payment_id
    order=dict(id=row.provider_order_id,entity="order",receipt=row.provider_receipt,notes=order_notes(row),
        amount=row.amount_minor,currency="INR",status="paid",attempts=1,amount_paid=row.amount_minor,amount_due=0)
    payment=dict(id=payment_id,entity="payment",order_id=row.provider_order_id,amount=row.amount_minor,
        currency="INR",status="captured",captured=True,amount_refunded=0,refund_status=None)
    def outside():
        assert all(not session.in_transaction() for session in own_sessions.get()), "checkout status provider I/O held SQL"
    def fetch(identity):
        outside()
        assert identity==row.provider_order_id
        return order.copy()
    def inventory(identity):
        outside()
        assert identity==row.provider_order_id
        return dict(entity="collection",count=1,items=[payment.copy()])
    def forbidden(*args,**kwargs):
        raise AssertionError("status/failure reconciliation attempted a financial POST")
    provider=SimpleNamespace(order=SimpleNamespace(fetch=fetch,payments=inventory,create=forbidden),session=SimpleNamespace(close=lambda:None))
    try:
        async with AsyncClient(transport=ASGITransport(app=app),base_url="http://ci.test") as http:
            ids=[]
            for counter in range(8):
                event=dict(entity="event",account_id=settings.razorpay_webhook_account_id,event="payment.failed",created_at=counter,
                    payload={"payment":{"entity":{**payment,"status":"failed","captured":False,"email":"private-failure-canary"}}})
                raw=json.dumps(event,separators=(",",":")).encode()
                signature=hmac.new(settings.razorpay_webhook_secret.get_secret_value().encode(),raw,hashlib.sha256).hexdigest()
                response=await http.post('/api/webhooks/razorpay',content=raw,headers={"Content-Type":"application/json","X-Razorpay-Signature":signature})
                assert response.status_code==200,response.text
                async with sessions() as session:
                    receipt=await session.scalar(select(PaymentWebhookEvent).where(PaymentWebhookEvent.body_sha256==hashlib.sha256(raw).hexdigest()))
                    assert receipt
                    ids.append(receipt.id)
            results=await asyncio.gather(*(process_receipt(sessions,rid,provider,now=now) for rid in ids))
            assert all(value=="checkout_signal_reconciled" for value in results),results
            with patch('app.api.checkout._get_razorpay_client',return_value=provider):
                response=await http.get('/api/checkout/status',headers={"Authorization":"Bearer "+token})
                assert response.status_code==200,response.text
                assert response.json()["checkout"]["state"]=="captured"
                assert response.json()["checkout"]["activation_confirmed"] is True
                assert response.headers["cache-control"]=="no-store"
                payment.update(status="failed",captured=False)
                order.update(status="attempted",amount_paid=0,amount_due=row.amount_minor)
                response=await http.get('/api/checkout/status',headers={"Authorization":"Bearer "+token})
                assert response.json()["checkout"]["state"]=="unresolved",response.text
        async with sessions() as session:
            assert await session.scalar(select(func.count()).select_from(PaymentActivation).where(PaymentActivation.user_id==uid))==1
            sub=await session.scalar(select(Subscription).where(Subscription.user_id==uid))
            assert sub and sub.current_period_end==end
        print("PASS: native checkout failures; eight signed HTTP failed signals reconcile latest capture without granting/releasing/reposting; authenticated own no-store status; captured evidence cannot regress to failed; provider I/O outside SQL; immutable paid term")
    finally:
        settings.billing_checkout_enabled=previous
