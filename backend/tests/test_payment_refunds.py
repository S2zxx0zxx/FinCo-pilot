"""Real SQL and signed inbox
synthetic provider network responses."""
import copy
import json
from datetime import timedelta
import uuid
from fastapi import HTTPException
import pytest
from sqlalchemy import select, func
from app.billing import activation, refunds
from app.billing.service import effective_plan
from app.billing.webhook_inbox import persist_webhook
from app.models.payment_activation import PaymentActivation
from app.models.payment_refund import PaymentRefund, RefundObservation
from app.models.subscription import Subscription
from tests.conftest import TestSessionLocal
from tests.test_payment_activation import enabled as enabled, purchase as purchase, receipt_for, NOW
EVIDENCE = "a" * 64


@pytest.fixture
async def refundable(purchase, enabled, monkeypatch, test_superuser):
    monkeypatch.setattr(enabled, "billing_refunds_enabled", True)
    reservation, client, _, payment = purchase
    receipt = await receipt_for(payment)
    assert await activation.process_receipt(TestSessionLocal, receipt, client, now=NOW) == "activated"
    async with TestSessionLocal() as session:
        grant = await session.scalar(select(PaymentActivation).where(PaymentActivation.reservation_id == reservation.id))
        assert grant is not None
    items = []
    client.payment.fetch.side_effect = lambda *_: copy.deepcopy(payment)
    client.payment.fetch_multiple_refund.side_effect = lambda *_: {"entity":"collection", "count":len(items), "items":copy.deepcopy(items)}
    def post(pid, data, **kwargs):
        assert pid == grant.payment_id and data["speed"] == "normal"
        assert kwargs["headers"]["X-Refund-Idempotency"] == str(uuid.UUID(data["receipt"][3:]))
        entity = dict(id="rfnd_TestRefund", entity="refund", payment_id=pid, amount=data["amount"],
            currency="INR", receipt=data["receipt"], status="processed")
        items.append(entity)
        payment.update(amount_refunded=data["amount"], refund_status="full" if data["amount"] == payment["amount"] else "partial",
            status="refunded" if data["amount"] == payment["amount"] else "captured")
        return copy.deepcopy(entity)
    client.payment.refund.side_effect = post
    return grant, client, payment, items, test_superuser.id


async def issue(data, amount=9900):
    grant, client, _, _, actor = data
    async with TestSessionLocal() as session:
        return await refunds.dispatch(session, actor, "activation", grant.id, amount, EVIDENCE, client, now=NOW)


async def refund_receipt(item, counter=0, kind="refund.processed"):
    event = dict(entity="event", account_id="acc_Activation", event=kind, created_at=int(NOW.timestamp())+counter,
        payload={"refund":{"entity":item}})
    async with TestSessionLocal() as session:
        await persist_webhook(session, body=json.dumps(event).encode(), event=event, delivery_id=None, mode="test")
        from app.models.payment_webhook import PaymentWebhookEvent
        row = await session.scalar(select(PaymentWebhookEvent).order_by(PaymentWebhookEvent.received_at.desc()).limit(1))
        assert row is not None
        return row.id


async def test_full_refund_revokes_once(refundable):
    grant, client, _, _, _ = refundable
    assert (await issue(refundable))["state"] == "processed"
    assert (await issue(refundable))["state"] == "processed"
    client.payment.refund.assert_called_once()
    async with TestSessionLocal() as session:
        sub = await session.scalar(select(Subscription).where(Subscription.user_id == grant.user_id))
        assert sub is not None and sub.paid_term_refunded
        assert effective_plan(sub, now=NOW).value == "free"
        assert await session.scalar(select(func.count()).select_from(PaymentRefund)) == 1
        assert await session.scalar(select(func.count()).select_from(RefundObservation)) == 1
        assert (await refunds.preview(session, uuid.uuid4()))["refunds"] == []


async def test_partial_preserves_service_and_changed_decision_conflicts(refundable):
    grant, _, _, _, _ = refundable
    assert (await issue(refundable, 1000))["state"] == "processed"
    async with TestSessionLocal() as session:
        sub = await session.scalar(select(Subscription).where(Subscription.user_id == grant.user_id))
        assert effective_plan(sub, now=NOW).value == "pro"
    with pytest.raises(HTTPException) as error:
        await issue(refundable, 9900)
    assert error.value.status_code == 409


async def test_lost_response_never_reposts_signed_event_resolves(refundable):
    grant, client, payment, items, _ = refundable
    client.payment.refund.side_effect = TimeoutError("synthetic unknown outcome")
    assert (await issue(refundable))["state"] == "uncertain"
    assert (await issue(refundable))["state"] == "uncertain"
    async with TestSessionLocal() as session:
        intent = await session.scalar(select(PaymentRefund))
        assert intent is not None
        receipt = "fr-" + intent.id.hex
    item = dict(id="rfnd_Late", entity="refund", payment_id=grant.payment_id, amount=9900,currency="INR",status="processed",receipt=receipt)
    items.append(item)
    payment.update(amount_refunded=9900,refund_status="full",status="refunded")
    identity = await refund_receipt(item)
    assert await activation.process_receipt(TestSessionLocal,identity,client) == "refund_reconciled"
    assert (await issue(refundable))["state"] == "processed"
    client.payment.refund.assert_called_once()


async def test_post_body_not_confirmation(refundable):
    _,client,_,_,_=refundable
    client.payment.refund.side_effect=lambda *_args,**_kwargs:{"status":"processed"}
    assert (await issue(refundable))["state"]=="uncertain"


@pytest.mark.parametrize("state",["pending","failed"])
async def test_external_nonprocessed_never_revokes_or_posts(refundable,state):
    grant,client,_,items,_=refundable
    item=dict(id="rfnd_External",entity="refund",payment_id=grant.payment_id,amount=9900,currency="INR",status=state)
    items.append(item)
    identity=await refund_receipt(item,kind="refund.created" if state=="pending" else "refund.failed")
    assert await activation.process_receipt(TestSessionLocal,identity,client)=="refund_reconciled"
    client.payment.refund.assert_not_called()
    async with TestSessionLocal() as session:
        sub=await session.scalar(select(Subscription).where(Subscription.user_id==grant.user_id))
        assert effective_plan(sub,now=NOW).value=="pro"


async def test_external_cumulative_partials_and_replay(refundable):
    grant,client,payment,items,_=refundable
    for index,amount in enumerate((1000,8900)):
        item=dict(id=f"rfnd_External{index}",entity="refund",payment_id=grant.payment_id,amount=amount,currency="INR",status="processed")
        items.append(item)
        total=sum(row["amount"] for row in items)
        payment.update(amount_refunded=total,refund_status="full" if total==9900 else "partial",status="refunded" if total==9900 else "captured")
        identity=await refund_receipt(item,index)
        assert await activation.process_receipt(TestSessionLocal,identity,client)=="refund_reconciled"
        assert await activation.process_receipt(TestSessionLocal,identity,client)=="unchanged"
        async with TestSessionLocal() as session:
            sub=await session.scalar(select(Subscription).where(Subscription.user_id==grant.user_id))
            assert effective_plan(sub,now=NOW).value==("free" if total==9900 else "pro")
    client.payment.refund.assert_not_called()


@pytest.mark.parametrize("field,value",[("id","pay_Foreign"),("amount",True),("currency","USD"),("captured",False),
    ("amount_refunded",False),("refund_status","full"),("order_id","order_Foreign"),("status","failed")])
async def test_bad_payment_never_dispatches(refundable,field,value):
    _,client,payment,_,_=refundable
    payment[field]=value
    with pytest.raises(activation.RejectReceipt):
        await issue(refundable)
    client.payment.refund.assert_not_called()


@pytest.mark.parametrize("field,value",[("id","rfnd_bad!"),("payment_id","pay_Foreign"),("amount",True),("currency","USD"),("status","unknown")])
async def test_bad_refund_cannot_reconcile(refundable,field,value):
    grant,client,payment,items,_=refundable
    item=dict(id="rfnd_External",entity="refund",payment_id=grant.payment_id,amount=9900,currency="INR",status="processed")
    signed=copy.deepcopy(item)
    item[field]=value
    items.append(item)
    payment.update(amount_refunded=9900,refund_status="full",status="refunded")
    identity=await refund_receipt(signed)
    assert await activation.process_receipt(TestSessionLocal,identity,client)=="quarantined"
    async with TestSessionLocal() as session:
        assert await session.scalar(select(func.count()).select_from(RefundObservation))==0


async def test_actor_must_still_be_superuser(refundable):
    grant,client,_,_,_=refundable
    async with TestSessionLocal() as session:
        with pytest.raises(HTTPException) as error:
            await refunds.dispatch(session,grant.user_id,"activation",grant.id,9900,EVIDENCE,client)
        assert error.value.status_code==403
    client.payment.refund.assert_not_called()


async def test_disabled_gate(refundable,enabled,monkeypatch):
    grant,client,_,_,_=refundable
    monkeypatch.setattr(enabled,"billing_refunds_enabled",False)
    with pytest.raises(HTTPException) as error:
        await issue(refundable)
    assert error.value.status_code==503
    client.payment.refund.assert_not_called()
    async with TestSessionLocal() as session:
        assert await refunds.preview(session,grant.user_id)=={"available":False}


async def test_older_full_refund_preserves_newer_term(refundable):
    grant,_,_,_,_=refundable
    async with TestSessionLocal() as session:
        sub=await session.scalar(select(Subscription).where(Subscription.user_id==grant.user_id))
        assert sub is not None and sub.current_period_end is not None
        sub.current_period_end += timedelta(days=30)
        await session.commit()
    await issue(refundable)
    async with TestSessionLocal() as session:
        sub=await session.scalar(select(Subscription).where(Subscription.user_id==grant.user_id))
        assert sub is not None and not sub.paid_term_refunded and effective_plan(sub,now=NOW).value=="pro"


async def test_unknown_outcome_blocks_deletion_but_can_resolve(refundable, session, test_user):
    from app.services import account_deletion_service as deletion
    grant,client,payment,items,_=refundable
    client.payment.refund.side_effect=TimeoutError("synthetic")
    await issue(refundable)
    decision=await deletion.request_deletion(session,test_user)
    assert "refund_outcome_unresolved" in decision["blockers"]
    async with TestSessionLocal() as own:
        intent=await own.scalar(select(PaymentRefund))
        assert intent is not None
        receipt="fr-"+intent.id.hex
    items.append(dict(id="rfnd_Resolved",entity="refund",payment_id=grant.payment_id,amount=9900,currency="INR",status="processed",receipt=receipt))
    payment.update(amount_refunded=9900,refund_status="full",status="refunded")
    assert (await issue(refundable))["state"]=="processed"
    client.payment.refund.assert_called_once()


async def test_new_dispatch_blocked_by_deletion(refundable,session,test_user):
    from app.services import account_deletion_service as deletion
    _,client,_,_,_=refundable
    await deletion.request_deletion(session,test_user)
    with pytest.raises(HTTPException):
        await issue(refundable)
    client.payment.refund.assert_not_called()


async def test_refund_evidence_survives_actual_purge_and_late_webhook(refundable,session,test_user):
    from tests.test_account_deletion_workflow import operator,approved,finish_execution
    grant,client,_,items,_=refundable
    await issue(refundable)
    admin=await operator(session)
    job,_=await approved(session,test_user,admin)
    await finish_execution(session,job,admin)
    assert job.state=="backup_expiry_pending"
    assert await session.scalar(select(func.count()).select_from(PaymentRefund))==1
    assert await session.scalar(select(func.count()).select_from(RefundObservation))==1
    receipt=await refund_receipt(items[0],counter=9)
    assert await activation.process_receipt(TestSessionLocal,receipt,client)=="refund_reconciled"
    assert await session.scalar(select(Subscription).where(Subscription.user_id==grant.user_id)) is None


async def test_processed_provider_fact_cannot_regress(refundable):
    _,client,payment,items,_=refundable
    await issue(refundable)
    items[0]["status"]="failed"
    payment.update(amount_refunded=0,refund_status=None,status="captured")
    receipt=await refund_receipt(items[0],counter=20,kind="refund.failed")
    assert await activation.process_receipt(TestSessionLocal,receipt,client)=="quarantined"
    async with TestSessionLocal() as session:
        observation = await session.scalar(select(RefundObservation))
        intent = await session.scalar(select(PaymentRefund))
        assert observation is not None and observation.state == "processed"
        assert intent is not None and intent.state == "processed"


async def test_paginated_inventory_duplicates_are_rejected(refundable):
    grant,client,payment,items,_=refundable
    item=dict(id="rfnd_Duplicate",entity="refund",payment_id=grant.payment_id,amount=100,currency="INR",status="pending")
    items.extend([copy.deepcopy(item),copy.deepcopy(item)])
    receipt=await refund_receipt(item)
    assert await activation.process_receipt(TestSessionLocal,receipt,client)=="quarantined"
    client.payment.refund.assert_not_called()


async def test_operator_route_auth_and_strict_decision(refundable,client,auth_headers,admin_auth_token,monkeypatch):
    grant,provider,_,_,_=refundable
    monkeypatch.setattr("app.api.checkout._get_razorpay_client",lambda:provider)
    path="/api/billing/refunds/operator"
    body=dict(source_kind="activation",source_id=str(grant.id),amount_minor=9900,evidence_sha256=EVIDENCE,authorize=True)
    assert (await client.post(path,json=body)).status_code in {401,403}
    assert (await client.post(path,headers=auth_headers,json=body)).status_code==403
    headers={"Authorization":"Bearer "+admin_auth_token}
    for invalid in ({**body,"authorize":False},{**body,"amount_minor":True},{**body,"authorize":"true"},
            {**body,"payment_id":"pay_Foreign"},{**body,"evidence_sha256":"not-reviewed"}):
        assert (await client.post(path,headers=headers,json=invalid)).status_code==422
    provider.payment.refund.assert_not_called()
    response=await client.post(path,headers=headers,json=body)
    assert response.status_code==200,response.text
    assert response.json()["state"]=="processed"
    provider.session.close.assert_called_once()


async def test_disabled_refunds_do_not_starve_enabled_acquisition(refundable,enabled,monkeypatch):
    grant,client,_,items,_=refundable
    monkeypatch.setattr(enabled,"billing_refunds_enabled",False)
    for counter in range(6):
        await refund_receipt(dict(id=f"rfnd_Disabled{counter}",entity="refund",payment_id=grant.payment_id),counter)
    assert (await activation.scan_receipts(TestSessionLocal,client)).get("quarantined",0)==0
    client.payment.fetch_multiple_refund.reset_mock()
    assert await refunds.process_refund(TestSessionLocal,uuid.uuid4(),client)=="disabled"
    client.payment.fetch_multiple_refund.assert_not_called()


@pytest.mark.parametrize("change",["key","account","gate","actor"])
async def test_scope_changes_during_provider_read_never_dispatch(refundable,enabled,change):
    from app.models.user import User
    grant,provider,_,_,actor=refundable
    old_fetch=provider.payment.fetch
    original=old_fetch.side_effect
    def altered(pid):
        result=original(pid)
        if change=="key":
            enabled.razorpay_key_id="rzp_test_Changed"
        elif change=="account":
            enabled.razorpay_webhook_account_id="acc_Changed"
        elif change=="gate":
            enabled.billing_refunds_enabled=False
        return result
    if change=="actor":
        async with TestSessionLocal() as session:
            operator=await session.get(User,actor)
            assert operator is not None
            operator.is_superuser=False
            await session.commit()
    else:
        provider.payment.fetch.side_effect=altered
    with pytest.raises((HTTPException,activation.RejectReceipt)):
        await issue(refundable)
    provider.payment.refund.assert_not_called()


async def test_operator_credential_revocation_is_rechecked(refundable):
    from app.core.auth import get_jwt_strategy
    from app.models.user import User
    grant,provider,_,_,actor=refundable
    async with TestSessionLocal() as session:
        operator=await session.get(User,actor)
        assert operator is not None
        stamp=get_jwt_strategy().stamp(operator)
        operator.auth_epoch="revoked"
        await session.commit()
    async with TestSessionLocal() as session:
        with pytest.raises(HTTPException):
            await refunds.dispatch(session,actor,"activation",grant.id,9900,EVIDENCE,provider,credential_stamp=stamp)
    provider.payment.refund.assert_not_called()


async def test_capture_replay_cannot_regrant_fully_refunded_term(refundable):
    _,provider,payment,_,_=refundable
    await issue(refundable)
    stale={**payment,"status":"captured","amount_refunded":0,"refund_status":None}
    receipt=await receipt_for(stale,counter=123)
    assert await activation.process_receipt(TestSessionLocal,receipt,provider)=="quarantined"


async def test_pending_external_refund_can_later_process(refundable):
    grant,provider,payment,items,_=refundable
    item=dict(id="rfnd_Pending",entity="refund",payment_id=grant.payment_id,amount=9900,currency="INR",status="pending")
    items.append(item)
    initial=await refund_receipt(item,kind="refund.created")
    assert await activation.process_receipt(TestSessionLocal,initial,provider)=="refund_reconciled"
    item["status"]="processed"
    payment.update(amount_refunded=9900,refund_status="full",status="refunded")
    final=await refund_receipt(item,counter=1)
    assert await activation.process_receipt(TestSessionLocal,final,provider)=="refund_reconciled"
    async with TestSessionLocal() as session:
        sub=await session.scalar(select(Subscription).where(Subscription.user_id==grant.user_id))
        assert sub is not None and effective_plan(sub,now=NOW).value=="free"


from tests.test_renewal_lifecycle import renewal as renewal, cycle_receipt  # noqa: E402


async def test_new_paid_cycle_restores_only_its_own_service_after_refund(renewal,enabled,monkeypatch):
    from app.models.payment_renewal import RenewalCycle
    monkeypatch.setattr(enabled,"billing_refunds_enabled",True)
    reservation,provider,subscription,_,invoice,payment,start=renewal
    receipt=await cycle_receipt(subscription,payment)
    assert await activation.process_receipt(TestSessionLocal,receipt,provider,now=start)=="renewed"
    async with TestSessionLocal() as session:
        cycle=await session.scalar(select(RenewalCycle).where(RenewalCycle.user_id==reservation.user_id))
        assert cycle is not None
    item=dict(id="rfnd_PaidCycle",entity="refund",payment_id=payment["id"],amount=9900,currency="INR",status="processed")
    provider.payment.fetch_multiple_refund.return_value={"entity":"collection","count":1,"items":[item]}
    payment.update(amount_refunded=9900,refund_status="full",status="refunded")
    refunded=await refund_receipt(item)
    assert await activation.process_receipt(TestSessionLocal,refunded,provider,now=start)=="refund_reconciled"
    async with TestSessionLocal() as session:
        sub=await session.scalar(select(Subscription).where(Subscription.user_id==reservation.user_id))
        assert sub is not None and effective_plan(sub,now=start).value=="free"
    next_start=start+timedelta(days=30)
    invoice.update(id="inv_NextPaid",payment_id="pay_NextPaid",billing_start=int(next_start.timestamp()),billing_end=int((next_start+timedelta(days=30)).timestamp()))
    payment.update(id=invoice["payment_id"],invoice_id=invoice["id"],amount_refunded=0,refund_status=None,status="captured")
    subscription.update(paid_count=2)
    paid=await cycle_receipt(subscription,payment,counter=8)
    assert await activation.process_receipt(TestSessionLocal,paid,provider,now=next_start)=="renewed"
    async with TestSessionLocal() as session:
        sub=await session.scalar(select(Subscription).where(Subscription.user_id==reservation.user_id))
        assert sub is not None and not sub.paid_term_refunded
        assert effective_plan(sub,now=start).value=="free"
        assert effective_plan(sub,now=next_start).value=="pro"


async def test_unstopped_renewal_prevents_new_refund_dispatch(renewal,enabled,monkeypatch,test_superuser):
    from app.models.payment_activation import PaymentActivation
    monkeypatch.setattr(enabled,"billing_refunds_enabled",True)
    reservation,provider,_,_,_,_,_=renewal
    async with TestSessionLocal() as session:
        grant=await session.scalar(select(PaymentActivation).where(PaymentActivation.reservation_id==reservation.id))
        assert grant is not None
    # Return the bound acquisition payment, not the fixture's later renewal payment.
    provider.payment.fetch.side_effect=lambda _:dict(entity="payment",id=grant.payment_id,order_id=grant.order_id,
        amount=grant.amount_minor,currency="INR",captured=True,status="captured",amount_refunded=0,refund_status=None)
    provider.payment.fetch_multiple_refund.return_value={"entity":"collection","count":0,"items":[]}
    async with TestSessionLocal() as session:
        with pytest.raises(HTTPException) as error:
            await refunds.dispatch(session,test_superuser.id,"activation",grant.id,9900,EVIDENCE,provider)
        assert error.value.status_code==409
    provider.payment.refund.assert_not_called()
