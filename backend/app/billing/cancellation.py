"""Owned immediate collection stop; one durable dispatch, fresh GET confirmation."""
import asyncio
from datetime import datetime, timezone
import uuid

from fastapi import HTTPException
from sqlalchemy import select, text
from starlette.concurrency import run_in_threadpool

from app.billing.activation import activation_enabled, RejectReceipt, RetryReceipt, disposition, processed
from app.billing.offer_service import _stored_utc
from app.billing.renewal_mandates import identifier, validate_plan, validate_subscription
from app.billing.webhook_inbox import decrypt_snapshot
from app.core.config import get_settings
from app.models.account_deletion import AccountDeletion
from app.models.payment_activation import PaymentActivation
from app.models.payment_cancellation import PaymentCancellation
from app.models.payment_renewal import RenewalCycle, RenewalMandate
from app.models.payment_webhook import PaymentWebhookEvent
from app.models.subscription import Subscription
from app.models.user import User


def enabled():
    return activation_enabled() and get_settings().billing_cancellation_enabled


async def source(session, uid, *, lock=False, reconcile=False):
    if lock and session.get_bind().dialect.name == "postgresql":
        await session.execute(text("SET LOCAL lock_timeout = '5s'"))
        await session.execute(text("SET LOCAL statement_timeout = '10s'"))
    def query(model, predicate):
        result = select(model).where(predicate)
        return result.with_for_update().execution_options(populate_existing=True) if lock else result
    user = await session.scalar(query(User, User.id == uid))
    if user is None or not user.is_active:
        raise HTTPException(409, "An active account is required.")
    if not reconcile and await deletion_pending(session, uid):
        raise HTTPException(409, "Account deletion requires operator reconciliation.")
    sub = await session.scalar(query(Subscription, Subscription.user_id == uid))
    if sub is None or sub.provider != "razorpay" or sub.status not in {"active", "grace", "past_due", "canceled"}:
        raise HTTPException(409, "A bound renewal subscription is required.")
    row = await session.scalar(query(RenewalMandate, (RenewalMandate.user_id == uid)
        & (RenewalMandate.subscription_id == sub.id)
        & (RenewalMandate.provider_subscription_id == sub.provider_subscription_id)))
    settings = get_settings()
    if (row is None or row.state != "ready" or row.mode != "test"
            or row.account_id != settings.razorpay_webhook_account_id
            or row.provider_key_id != settings.razorpay_key_id
            or (row.plan, row.billing_interval) != (sub.plan, sub.billing_interval)
            or not identifier(row.provider_subscription_id, "sub")
            or _stored_utc(sub.current_period_end) is None):
        raise HTTPException(409, "Renewal binding requires review.")
    grant = await session.get(PaymentActivation, row.activation_id)
    last = await session.scalar(select(RenewalCycle).where(RenewalCycle.user_id == uid)
        .order_by(RenewalCycle.period_end.desc()).limit(1))
    if (grant is None or grant.user_id != uid or grant.account_id != row.account_id
            or grant.provider_key_id != row.provider_key_id or grant.mode != "test"
            or _stored_utc(sub.current_period_end) != _stored_utc(last.period_end if last else grant.period_end)):
        raise HTTPException(409, "Paid coverage requires reconciliation.")
    return sub, row


async def deletion_pending(session, uid):
    return await session.scalar(select(AccountDeletion.id).where(AccountDeletion.user_id == uid,
        AccountDeletion.state != "cancelled").limit(1)) is not None


def response(sub, claim):
    return {"available": True, "state": claim.state if claim else "available",
        "paid_through": _stored_utc(sub.current_period_end), "paid_term_refunded": bool(sub.paid_term_refunded)}


async def preview(session, uid):
    if not enabled():
        return {"available": False}
    try:
        sub, row = await source(session, uid, reconcile=True)
    except HTTPException:
        return {"available": False}
    claim = await session.scalar(select(PaymentCancellation).where(PaymentCancellation.mandate_id == row.id))
    if claim is None and await deletion_pending(session, uid):
        return {"available": False}
    return response(sub, claim)


def validate(row, provider, plan):
    validate_plan(row, plan)
    validate_subscription(row, provider, statuses={"created", "authenticated", "active", "pending", "halted", "cancelled"})
    if provider.get("has_scheduled_changes") is not False:
        raise ValueError("Scheduled provider changes require review")


def claim_matches(claim, row):
    return (claim.user_id == row.user_id and claim.mandate_id == row.id
        and claim.mode == row.mode and claim.account_id == row.account_id
        and claim.provider_key_id == row.provider_key_id
        and claim.provider_subscription_id == row.provider_subscription_id)


def new_claim(row, current, state):
    return PaymentCancellation(id=uuid.uuid4(), user_id=row.user_id, mandate_id=row.id,
        mode=row.mode, account_id=row.account_id, provider_key_id=row.provider_key_id,
        provider_subscription_id=row.provider_subscription_id, state=state, requested_at=current)


async def cancel(session, uid, client, *, now=None):
    if not enabled():
        raise HTTPException(503, "Cancellation is disabled.")
    current = now or datetime.now(timezone.utc)
    sub, row = await source(session, uid, lock=True, reconcile=True)
    existing = await session.scalar(select(PaymentCancellation.id).where(PaymentCancellation.mandate_id == row.id))
    if existing is None and await deletion_pending(session, uid):
        raise HTTPException(409, "Account deletion requires operator reconciliation.")
    mid, sid, pid = row.id, row.provider_subscription_id, row.provider_plan_id
    await session.commit()
    try:
        async with asyncio.timeout(110):
            provider = await run_in_threadpool(client.subscription.fetch, sid)
            plan = await run_in_threadpool(client.plan.fetch, pid)
        validate(row, provider, plan)
    except Exception:
        raise HTTPException(502, "Cancellation cannot be verified. Contact support or check again.") from None
    sub, row = await source(session, uid, lock=True, reconcile=True)
    if not enabled() or row.id != mid or row.provider_plan_id != pid:
        raise HTTPException(409, "Cancellation binding changed.")
    validate(row, provider, plan)
    claim = await session.scalar(select(PaymentCancellation).where(PaymentCancellation.mandate_id == mid).with_for_update())
    if claim and not claim_matches(claim, row):
        raise HTTPException(409, "Cancellation evidence requires review.")
    dispatch = claim is None and provider["status"] != "cancelled"
    if dispatch and await deletion_pending(session, uid):
        raise HTTPException(409, "Account deletion prevents a new cancellation dispatch.")
    if claim is None:
        claim = new_claim(row, current, "sending" if dispatch else "uncertain")
        session.add(claim)
    if provider["status"] == "cancelled":
        confirm(sub, claim, current)
        result = response(sub, claim)
        await session.commit()
        return result
    if not dispatch:
        result = response(sub, claim)
        await session.commit()
        return result
    cid = claim.id
    await session.commit()  # Dispatch survives timeout, process death and ambiguous commits.
    try:
        async with asyncio.timeout(110):
            await run_in_threadpool(client.subscription.cancel, sid, {"cancel_at_cycle_end": False})
            provider = await run_in_threadpool(client.subscription.fetch, sid)
        validate(row, provider, plan)
    except Exception:
        provider = None
    sub, row = await source(session, uid, lock=True, reconcile=True)
    claim = await session.scalar(select(PaymentCancellation).where(PaymentCancellation.id == cid).with_for_update())
    if (not enabled() or row.id != mid or row.provider_plan_id != pid
            or claim is None or not claim_matches(claim, row)):
        raise HTTPException(409, "Cancellation needs reconciliation.")
    if provider is not None and provider["status"] == "cancelled":
        validate(row, provider, plan)
        confirm(sub, claim, current)
    elif claim.state != "confirmed":
        claim.state = "uncertain"
    result = response(sub, claim)
    await session.commit()
    return result


def confirm(sub, claim, current):
    claim.state = "confirmed"
    if claim.confirmed_at is None:
        claim.confirmed_at = current
    sub.status, sub.cancel_at_period_end = "canceled", True
    sub.recovery_due_at, sub.grace_until = None, None


def receipt_identity(receipt):
    try:
        entity = decrypt_snapshot(receipt)["payload"]["subscription"]["entity"]
        if receipt.event_type != "subscription.cancelled" or entity.get("status") != "cancelled" or not identifier(entity.get("id"), "sub"):
            raise ValueError("Invalid cancellation identity")
        return entity["id"]
    except (KeyError, TypeError, ValueError):
        raise RejectReceipt("invalid_cancellation_receipt") from None


async def process_cancellation(sessions, receipt_id, client, *, now=None):
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
            sid = receipt_identity(receipt)
            settings = get_settings()
            if receipt.mode != "test" or receipt.account_id != settings.razorpay_webhook_account_id:
                raise RejectReceipt("cancellation_scope_mismatch")
            row = await session.scalar(select(RenewalMandate).where(RenewalMandate.provider_subscription_id == sid,
                RenewalMandate.mode == "test", RenewalMandate.account_id == receipt.account_id))
            if row is None:
                raise RetryReceipt("cancellation_binding_unavailable")
            uid = row.user_id
            await session.commit()
            # Reconciliation only: signed cancellation never authorizes a provider POST.
            sub, row = await source(session, uid, reconcile=True)
            pid, mid = row.provider_plan_id, row.id
            await session.commit()
            try:
                async with asyncio.timeout(110):
                    provider = await run_in_threadpool(client.subscription.fetch, sid)
                    plan = await run_in_threadpool(client.plan.fetch, pid)
            except Exception:
                raise RetryReceipt("cancellation_provider_unavailable") from None
            try:
                validate(row, provider, plan)
            except (ValueError, TypeError):
                raise RejectReceipt("cancellation_evidence_mismatch") from None
            if provider["status"] != "cancelled":
                raise RetryReceipt("cancellation_not_confirmed")
            sub, row = await source(session, uid, lock=True, reconcile=True)
            receipt = await session.scalar(select(PaymentWebhookEvent).where(PaymentWebhookEvent.id == receipt_id)
                .with_for_update().execution_options(populate_existing=True))
            if receipt is None or receipt.state != "pending":
                return "unchanged"
            if (not enabled() or row.id != mid or row.provider_plan_id != pid
                    or row.provider_subscription_id != sid or receipt_identity(receipt) != sid
                    or receipt.mode != "test" or receipt.account_id != row.account_id):
                raise RejectReceipt("cancellation_binding_changed")
            validate(row, provider, plan)
            claim = await session.scalar(select(PaymentCancellation).where(PaymentCancellation.mandate_id == mid).with_for_update())
            if claim is None:
                claim = new_claim(row, current, "uncertain")
                session.add(claim)
            if not claim_matches(claim, row):
                raise RejectReceipt("cancellation_claim_changed")
            confirm(sub, claim, current)
            processed(receipt, current)
            await session.commit()
            return "cancelled"
    except HTTPException:
        return await disposition(sessions, receipt_id, code="cancellation_lifecycle_changed", retry=False, now=current)
    except RetryReceipt as exc:
        return await disposition(sessions, receipt_id, code=str(exc), retry=True, now=current)
    except (RejectReceipt, ValueError, TypeError) as exc:
        return await disposition(sessions, receipt_id, code=str(exc) if isinstance(exc, RejectReceipt) else "cancellation_evidence_changed", retry=False, now=current)
