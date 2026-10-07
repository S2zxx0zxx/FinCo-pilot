"""Reviewed Test refunds; durable one-shot dispatch and fresh provider evidence."""
import asyncio
from datetime import datetime, timezone
import re
import uuid

from fastapi import HTTPException
from sqlalchemy import select, text
from starlette.concurrency import run_in_threadpool

from app.billing.activation import activation_enabled, RejectReceipt, RetryReceipt, disposition, processed
from app.billing.offer_service import _stored_utc
from app.billing.renewal_mandates import identifier
from app.billing.webhook_inbox import decrypt_snapshot
from app.core.config import get_settings
from app.models.account_deletion import AccountDeletion
from app.models.payment_activation import PaymentActivation
from app.models.payment_cancellation import PaymentCancellation
from app.models.payment_refund import PaymentRefund, RefundObservation
from app.models.payment_renewal import RenewalCycle, RenewalMandate
from app.models.payment_webhook import PaymentWebhookEvent
from app.models.subscription import Subscription
from app.models.user import User

EVENTS = ("refund.created", "refund.processed", "refund.failed", "refund.speed_changed")


def enabled():
    return activation_enabled() and get_settings().billing_refunds_enabled


async def fence(session, uid):
    if session.get_bind().dialect.name == "postgresql":
        await session.execute(text("SET LOCAL lock_timeout = '5s'"))
        await session.execute(text("SET LOCAL statement_timeout = '10s'"))
    return await session.scalar(select(User).where(User.id == uid).with_for_update()
        .execution_options(populate_existing=True))


async def source(session, kind, identity):
    model = {"activation": PaymentActivation, "renewal": RenewalCycle}.get(kind)
    if model is None:
        raise HTTPException(422, "Invalid payment source.")
    row = await session.get(model, identity, populate_existing=True)
    settings = get_settings()
    key = row.provider_key_id if isinstance(row, PaymentActivation) else None
    if isinstance(row, RenewalCycle):
        mandate = await session.get(RenewalMandate, row.mandate_id, populate_existing=True)
        if mandate is None or mandate.user_id != row.user_id or mandate.account_id != row.account_id:
            raise HTTPException(409, "Payment binding requires review.")
        key = mandate.provider_key_id
    if (row is None or row.mode != "test" or row.account_id != settings.razorpay_webhook_account_id
            or key != settings.razorpay_key_id or row.currency != "INR" or row.amount_minor <= 0
            or not identifier(row.payment_id, "pay")):
        raise HTTPException(409, "Payment binding requires review.")
    return row, key


async def source_for_payment(session, payment_id, account):
    for kind, model in (("activation", PaymentActivation), ("renewal", RenewalCycle)):
        row = await session.scalar(select(model).where(model.mode == "test", model.account_id == account,
            model.payment_id == payment_id))
        if row is not None:
            checked, key = await source(session, kind, row.id)
            return kind, checked, key
    raise RetryReceipt("refund_payment_binding_unavailable")


def validate_payment(row, payment):
    captured = payment.get("captured") if isinstance(payment, dict) else None
    captured_ok = captured is True or (type(captured) is int and captured == 1) or (type(captured) is str and captured == "1")
    if (not isinstance(payment, dict) or payment.get("entity") != "payment" or payment.get("id") != row.payment_id
            or type(payment.get("amount")) is not int or payment["amount"] != row.amount_minor
            or payment.get("currency") != row.currency or not captured_ok
            or payment.get("status") not in {"captured", "refunded"}
            or type(payment.get("amount_refunded")) is not int
            or not 0 <= payment["amount_refunded"] <= row.amount_minor):
        raise ValueError("Invalid refund payment evidence")
    refunded = payment["amount_refunded"]
    if payment.get("refund_status") != (None if refunded == 0 else "full" if refunded == row.amount_minor else "partial"):
        raise ValueError("Inconsistent refund aggregate")
    if payment["status"] != ("refunded" if refunded == row.amount_minor else "captured"):
        raise ValueError("Inconsistent payment status")
    if isinstance(row, PaymentActivation):
        if payment.get("order_id") != row.order_id or payment.get("invoice_id") is not None:
            raise ValueError("Wrong acquisition payment binding")
    elif (payment.get("invoice_id") != row.invoice_id
            or payment.get("subscription_id") not in (None, row.provider_subscription_id)):
        raise ValueError("Wrong renewal payment binding")


def validate_refund(row, refund):
    if (not isinstance(refund, dict) or refund.get("entity") != "refund"
            or not identifier(refund.get("id"), "rfnd") or refund.get("payment_id") != row.payment_id
            or refund.get("currency") != row.currency or type(refund.get("amount")) is not int
            or not 0 < refund["amount"] <= row.amount_minor
            or refund.get("status") not in {"pending", "processed", "failed"}):
        raise ValueError("Invalid refund identity or amount")


async def inventory(client, row):
    """Bounded complete inventory; no SQL open, no partial page called complete."""
    try:
        async with asyncio.timeout(110):
            payment = await run_in_threadpool(client.payment.fetch, row.payment_id)
            refunds = []
            for page in range(10):
                batch = await run_in_threadpool(client.payment.fetch_multiple_refund, row.payment_id,
                    {"count": 100, "skip": page * 100})
                if (not isinstance(batch, dict) or batch.get("entity") != "collection"
                        or not isinstance(batch.get("items"), list) or type(batch.get("count")) is not int
                        or batch["count"] != len(batch["items"]) or not 0 <= batch["count"] <= 100):
                    raise ValueError("Invalid refund inventory")
                refunds.extend(batch["items"])
                if batch["count"] < 100:
                    break
            else:
                raise ValueError("Refund inventory exceeds review bound")
        validate_payment(row, payment)
        for refund in refunds:
            validate_refund(row, refund)
        if len({refund["id"] for refund in refunds}) != len(refunds):
            raise ValueError("Duplicate refund inventory")
        total = sum(refund["amount"] for refund in refunds if refund["status"] == "processed")
        if total > payment["amount_refunded"]:
            raise ValueError("Refund aggregate is inconsistent")
        return payment, refunds
    except ValueError:
        raise RejectReceipt("refund_evidence_mismatch") from None
    except Exception:
        raise RetryReceipt("refund_provider_unavailable") from None


async def observe(session, row, key, payment, refunds, current):
    validate_payment(row, payment)
    if not enabled() or key != get_settings().razorpay_key_id or row.account_id != get_settings().razorpay_webhook_account_id:
        raise RejectReceipt("refund_scope_changed")
    for refund in refunds:
        validate_refund(row, refund)
        stored = await session.scalar(select(RefundObservation).where(RefundObservation.mode == row.mode,
            RefundObservation.account_id == row.account_id, RefundObservation.refund_id == refund["id"]).with_for_update())
        if stored is None:
            stored = RefundObservation(user_id=row.user_id, mode=row.mode, account_id=row.account_id,
                payment_id=row.payment_id, refund_id=refund["id"], amount_minor=refund["amount"],
                currency=row.currency, state=refund["status"], observed_at=current)
            session.add(stored)
        elif (stored.user_id != row.user_id or stored.payment_id != row.payment_id
                or stored.amount_minor != refund["amount"] or stored.currency != row.currency
                or (stored.state == "processed" and refund["status"] != "processed")):
            raise RejectReceipt("refund_observation_changed")
        else:
            stored.state = refund["status"]
    # Previously proven financial facts must not disappear from a later snapshot.
    await session.flush()
    known = list((await session.scalars(select(RefundObservation).where(RefundObservation.mode == row.mode,
        RefundObservation.account_id == row.account_id, RefundObservation.payment_id == row.payment_id))).all())
    listed = {refund["id"] for refund in refunds}
    if any(item.refund_id not in listed for item in known):
        raise RetryReceipt("refund_inventory_incomplete")
    intent = await session.scalar(select(PaymentRefund).where(PaymentRefund.mode == row.mode,
        PaymentRefund.account_id == row.account_id, PaymentRefund.payment_id == row.payment_id).with_for_update())
    if intent:
        expected_kind = "activation" if isinstance(row, PaymentActivation) else "renewal"
        if (intent.user_id != row.user_id or intent.source_id != row.id or intent.source_kind != expected_kind
                or intent.mode != row.mode or intent.account_id != row.account_id or intent.provider_key_id != key
                or intent.payment_id != row.payment_id or intent.currency != row.currency):
            raise RejectReceipt("refund_dispatch_binding_changed")
        candidates = [refund for refund in refunds if refund.get("receipt") == "fr-" + intent.id.hex]
        if len(candidates) > 1:
            raise RejectReceipt("refund_dispatch_duplicate")
        if intent.refund_id is not None and not candidates:
            raise RetryReceipt("refund_dispatch_not_visible")
        if candidates:
            refund = candidates[0]
            if (refund["amount"] != intent.amount_minor or intent.provider_key_id != key
                    or intent.user_id != row.user_id or intent.source_id != row.id
                    or (intent.refund_id is not None and intent.refund_id != refund["id"])):
                raise RejectReceipt("refund_dispatch_changed")
            if intent.state == "processed" and refund["status"] != "processed":
                raise RejectReceipt("refund_dispatch_regressed")
            intent.refund_id, intent.state = refund["id"], refund["status"]
    total = sum(item.amount_minor for item in known if item.state == "processed")
    if total > row.amount_minor:
        raise RejectReceipt("refund_total_exceeded")
    if total == row.amount_minor:
        # A full external refund closes an unknown decision without claiming its POST succeeded.
        if intent is not None and intent.state in {"sending", "uncertain"} and intent.refund_id is None and not candidates:
            intent.state = "external"
        sub = await session.scalar(select(Subscription).where(Subscription.user_id == row.user_id).with_for_update()
            .execution_options(populate_existing=True))
        # Revoke only this paid term; an older refund cannot erase a newer paid cycle.
        if (sub is not None and sub.provider == "razorpay"
                and _stored_utc(sub.current_period_end) == _stored_utc(row.period_end)):
            sub.paid_term_refunded = True
            sub.recovery_due_at, sub.grace_until = None, None
    return intent


def result(intent):
    return {"id": str(intent.id), "state": intent.state, "amount_minor": intent.amount_minor, "currency": intent.currency}


async def dispatch(session, actor_id, kind, source_id, amount, evidence, client, *, now=None, credential_stamp=None):
    if not enabled():
        raise HTTPException(503, "Refunds are disabled.")
    if type(amount) is not int or amount < 100 or amount > 2**31 - 1 or not re.fullmatch(r"[a-f0-9]{64}", evidence):
        raise HTTPException(422, "An exact amount and reviewed evidence digest are required.")
    from app.core.auth import get_jwt_strategy
    current = now or datetime.now(timezone.utc)
    row, key = await source(session, kind, source_id)
    uid = row.user_id
    await session.commit()
    payment, refunds = await inventory(client, row)
    owner = await fence(session, uid)
    actor = await session.get(User, actor_id, populate_existing=True)
    if (actor is None or not actor.is_active or not actor.is_superuser
            or (credential_stamp is not None and get_jwt_strategy().stamp(actor) != credential_stamp)):
        raise HTTPException(403, "Current operator authorization is required.")
    row, fresh_key = await source(session, kind, source_id)
    if key != fresh_key:
        raise HTTPException(409, "Refund payment scope changed.")
    intent = await observe(session, row, key, payment, refunds, current)
    if intent:
        if intent.amount_minor != amount or intent.evidence_sha256 != evidence:
            raise HTTPException(409, "Existing refund decision differs; contact support.")
        response = result(intent)
        await session.commit()
        return response  # No automatic repeat POST, even with the provider idempotency fence.
    if owner is None or not owner.is_active or await session.scalar(select(AccountDeletion.id).where(
            AccountDeletion.user_id == uid, AccountDeletion.state != "cancelled").limit(1)):
        raise HTTPException(409, "New refund dispatch requires an active account without pending deletion.")
    if amount > row.amount_minor or payment["amount_refunded"] != 0 or refunds:
        raise HTTPException(409, "Prior provider refunds or amount require operator reconciliation.")
    mandates = list((await session.scalars(select(RenewalMandate).where(RenewalMandate.user_id == uid,
        RenewalMandate.state.in_(("creating", "uncertain", "ready"))))).all())
    for mandate in mandates:
        cancellation = await session.scalar(select(PaymentCancellation).where(PaymentCancellation.mandate_id == mandate.id,
            PaymentCancellation.state == "confirmed"))
        if cancellation is None:
            raise HTTPException(409, "Confirm stopping renewal collection before issuing a refund.")
    intent = PaymentRefund(id=uuid.uuid4(), user_id=uid, source_id=row.id, source_kind=kind, mode=row.mode,
        account_id=row.account_id, provider_key_id=key, payment_id=row.payment_id, amount_minor=amount,
        currency=row.currency, operator_id=actor_id, evidence_sha256=evidence, state="sending", requested_at=current)
    session.add(intent)
    intent_id = intent.id
    await session.commit()
    try:
        async with asyncio.timeout(55):
            await run_in_threadpool(client.payment.refund, row.payment_id,
                {"amount": amount, "speed": "normal", "receipt": "fr-" + intent_id.hex},
                headers={"X-Refund-Idempotency": str(intent_id)})
    except Exception:
        pass  # Lost response is not a failed financial mutation, nor authorization to repost.
    try:
        payment, refunds = await inventory(client, row)
    except (RetryReceipt, RejectReceipt):
        payment = None
    await fence(session, uid)
    actor = await session.get(User, actor_id, populate_existing=True)
    row, fresh_key = await source(session, kind, source_id)
    intent = await session.get(PaymentRefund, intent_id, populate_existing=True)
    if (intent is None or not enabled() or fresh_key != key or actor is None or not actor.is_active or not actor.is_superuser
            or (credential_stamp is not None and get_jwt_strategy().stamp(actor) != credential_stamp)):
        raise HTTPException(409, "Refund requires reconciliation.")
    if payment is not None:
        intent = await observe(session, row, key, payment, refunds, current)
    if intent is None:
        raise HTTPException(409, "Refund requires reconciliation.")
    if intent.state == "sending":
        intent.state = "uncertain"
    response = result(intent)
    await session.commit()
    return response


async def preview(session, uid):
    if not enabled():
        return {"available": False}
    intents = list((await session.scalars(select(PaymentRefund).where(PaymentRefund.user_id == uid, PaymentRefund.state != "external")
        .order_by(PaymentRefund.requested_at.desc()).limit(100))).all())
    observations = list((await session.scalars(select(RefundObservation).where(RefundObservation.user_id == uid)
        .order_by(RefundObservation.observed_at.desc()).limit(100))).all())
    return {"available": True, "refunds": [result(item) for item in intents],
        "provider_refunds": [{"id": str(item.id), "state": item.state, "amount_minor": item.amount_minor,
            "currency": item.currency} for item in observations if item.refund_id not in {intent.refund_id for intent in intents}]}


def receipt_identity(receipt):
    try:
        entity = decrypt_snapshot(receipt)["payload"]["refund"]["entity"]
        if receipt.event_type not in EVENTS or not identifier(entity.get("id"), "rfnd") or not identifier(entity.get("payment_id"), "pay"):
            raise ValueError("Invalid signed refund")
        return entity["id"], entity["payment_id"]
    except (KeyError, TypeError, ValueError):
        raise RejectReceipt("invalid_refund_receipt") from None


async def process_refund(sessions, receipt_id, client, *, now=None):
    if not enabled():
        return "disabled"
    current = now or datetime.now(timezone.utc)
    try:
        async with sessions() as session:
            receipt = await session.get(PaymentWebhookEvent, receipt_id)
            if receipt is None or receipt.state != "pending":
                return "unchanged"
            due = _stored_utc(receipt.next_attempt_at)
            if due and due > current:
                return "not_due"
            rid, pid = receipt_identity(receipt)
            account = get_settings().razorpay_webhook_account_id
            if receipt.mode != "test" or receipt.account_id != account:
                raise RejectReceipt("refund_receipt_scope_mismatch")
            kind, row, key = await source_for_payment(session, pid, account)
            uid, source_id = row.user_id, row.id
            await session.commit()
            payment, refunds = await inventory(client, row)
            if rid not in {item["id"] for item in refunds}:
                raise RetryReceipt("refund_receipt_not_visible")
            await fence(session, uid)  # Evidence reconciliation also works after real account purge.
            row, fresh_key = await source(session, kind, source_id)
            receipt = await session.scalar(select(PaymentWebhookEvent).where(PaymentWebhookEvent.id == receipt_id)
                .with_for_update().execution_options(populate_existing=True))
            if receipt is None or receipt.state != "pending":
                return "unchanged"
            if (receipt_identity(receipt) != (rid, pid) or receipt.account_id != row.account_id
                    or receipt.mode != row.mode or fresh_key != key):
                raise RejectReceipt("refund_receipt_changed")
            await observe(session, row, key, payment, refunds, current)
            processed(receipt, current)
            await session.commit()
            return "refund_reconciled"
    except HTTPException:
        return await disposition(sessions, receipt_id, code="refund_binding_changed", retry=False, now=current)
    except RetryReceipt as exc:
        return await disposition(sessions, receipt_id, code=str(exc), retry=True, now=current)
    except RejectReceipt as exc:
        return await disposition(sessions, receipt_id, code=str(exc), retry=False, now=current)
