"""Exactly-once paid invoice reconciliation; provider periods, not replay arithmetic."""
import asyncio
from datetime import datetime, timedelta, timezone
import uuid

from sqlalchemy import func, select, text
from starlette.concurrency import run_in_threadpool

from app.billing.activation import RejectReceipt, RetryReceipt, disposition, processed
from app.billing.offer_service import _stored_utc
from app.billing.renewal_mandates import enabled, identifier, validate_plan, validate_subscription, utc_required
from app.billing.webhook_inbox import decrypt_snapshot
from app.core.config import get_settings
from app.models.account_deletion import AccountDeletion
from app.models.payment_activation import PaymentActivation
from app.models.payment_renewal import RenewalCycle, RenewalMandate
from app.models.payment_webhook import PaymentWebhookEvent
from app.models.pricing_offer import CheckoutReservation
from app.models.subscription import Subscription
from app.models.user import User


class FutureCycle(RetryReceipt):
    def __init__(self, starts_at):
        super().__init__("cycle_not_started")
        self.starts_at = starts_at


def identity(row):
    try:
        snapshot = decrypt_snapshot(row)
        subscription = snapshot["payload"]["subscription"]["entity"]
        payment = snapshot["payload"]["payment"]["entity"]
        values = subscription["id"], payment["id"], payment["invoice_id"]
        if (row.event_type != "subscription.charged" or payment.get("status") != "captured"
                or not all(identifier(value, prefix) for value, prefix in zip(values, ("sub", "pay", "inv")))):
            raise ValueError("Invalid signed cycle identity")
        return values
    except (KeyError, TypeError, ValueError):
        raise RejectReceipt("invalid_renewal_receipt") from None


def validate_invoice(row, subscription, plan, invoice, payment, identities):
    sid, pid, iid = identities
    try:
        validate_plan(row, plan)
        if validate_subscription(row, subscription) != sid:
            raise ValueError("Wrong provider subscription")
        captured = payment.get("captured") if isinstance(payment, dict) else None
        # Official subscription examples use string "1"; never accept arbitrary truthiness.
        captured_ok = captured is True or (type(captured) is int and captured == 1) or (type(captured) is str and captured == "1")
        if (not isinstance(payment, dict) or payment.get("entity") != "payment" or payment.get("id") != pid
                or payment.get("invoice_id") != iid or not captured_ok or payment.get("status") != "captured"
                or type(payment.get("amount")) is not int or payment["amount"] != row.amount_minor
                or payment.get("currency") != row.currency or type(payment.get("amount_refunded")) is not int
                or payment["amount_refunded"] != 0 or payment.get("refund_status") is not None
                or not isinstance(invoice, dict) or invoice.get("entity") != "invoice" or invoice.get("id") != iid
                or invoice.get("subscription_id") != sid or invoice.get("payment_id") != pid
                or invoice.get("status") != "paid" or invoice.get("currency") != row.currency
                or type(invoice.get("amount")) is not int or invoice["amount"] != row.amount_minor
                or type(invoice.get("amount_paid")) is not int or invoice["amount_paid"] != row.amount_minor
                or type(invoice.get("amount_due")) is not int or invoice["amount_due"] != 0
                or type(invoice.get("billing_start")) is not int or type(invoice.get("billing_end")) is not int
                or type(subscription.get("paid_count")) is not int or not 1 <= subscription["paid_count"] <= row.total_count
                or subscription.get("status") not in ("active", "completed")
                or subscription.get("has_scheduled_changes") is not False
                or (subscription.get("status") == "completed" and subscription["paid_count"] != row.total_count)):
            raise ValueError("Unproven captured renewal invoice")
        start = datetime.fromtimestamp(invoice["billing_start"], timezone.utc)
        end = datetime.fromtimestamp(invoice["billing_end"], timezone.utc)
        duration = end - start
        minimum, maximum = (timedelta(days=27), timedelta(days=32)) if row.billing_interval == "monthly" else (timedelta(days=364), timedelta(days=367))
        if not minimum <= duration <= maximum or start < utc_required(row.starts_at):
            raise ValueError("Invalid finite cycle period")
        if payment.get("subscription_id") is not None and payment["subscription_id"] != sid:
            raise ValueError("Wrong payment subscription")
        return start, end
    except (ValueError, TypeError, KeyError, OverflowError, OSError):
        raise RejectReceipt("renewal_evidence_mismatch") from None


async def process_renewal(session_maker, receipt_id: uuid.UUID, client, *, now=None):
    if not enabled():
        return "disabled"
    current = now or datetime.now(timezone.utc)
    settings = get_settings()
    key, account = settings.razorpay_key_id, settings.razorpay_webhook_account_id
    try:
        async with session_maker() as session:
            receipt = await session.get(PaymentWebhookEvent, receipt_id)
            if receipt is None or receipt.state != "pending":
                return "unchanged"
            due = _stored_utc(receipt.next_attempt_at)
            if due and due > current:
                return "not_due"
            ids = identity(receipt)
            row = await session.scalar(select(RenewalMandate).where(RenewalMandate.mode == "test",
                RenewalMandate.account_id == account, RenewalMandate.provider_subscription_id == ids[0]))
            if row is None:
                raise RetryReceipt("renewal_binding_unavailable")
            if receipt.mode != "test" or receipt.account_id != account or row.provider_key_id != key or row.state not in ("ready", "completed"):
                raise RejectReceipt("renewal_scope_mismatch")
            mandate_id, user_id, plan_id = row.id, row.user_id, row.provider_plan_id
            await session.commit()
        try:
            async with asyncio.timeout(110):
                subscription = await run_in_threadpool(client.subscription.fetch, ids[0])
                plan = await run_in_threadpool(client.plan.fetch, plan_id)
                invoice = await run_in_threadpool(client.invoice.fetch, ids[2])
                payment = await run_in_threadpool(client.payment.fetch, ids[1])
        except Exception:
            raise RetryReceipt("renewal_provider_unavailable") from None
        applied_at = current if now is not None else datetime.now(timezone.utc)
        async with session_maker() as session:
            if session.get_bind().dialect.name == "postgresql":
                await session.execute(text("SET LOCAL lock_timeout = '5s'"))
                await session.execute(text("SET LOCAL statement_timeout = '10s'"))
            user = await session.scalar(select(User).where(User.id == user_id).with_for_update())
            if user is None or not user.is_active:
                raise RejectReceipt("inactive_account")
            if await session.scalar(select(AccountDeletion.id).where(AccountDeletion.user_id == user_id,
                AccountDeletion.state != "cancelled").limit(1)):
                raise RejectReceipt("account_deletion_pending")
            row = await session.scalar(select(RenewalMandate).where(RenewalMandate.id == mandate_id).with_for_update().execution_options(populate_existing=True))
            receipt = await session.scalar(select(PaymentWebhookEvent).where(PaymentWebhookEvent.id == receipt_id).with_for_update().execution_options(populate_existing=True))
            if receipt is None or receipt.state != "pending":
                return "unchanged"
            if (row is None or row.user_id != user_id or row.provider_plan_id != plan_id
                    or row.provider_key_id != key or row.account_id != account or row.mode != "test"
                    or row.state not in ("ready", "completed") or receipt.mode != "test" or receipt.account_id != account
                    or not enabled() or settings.razorpay_key_id != key or settings.razorpay_webhook_account_id != account
                    or identity(receipt) != ids):
                raise RejectReceipt("renewal_binding_changed")
            start, end = validate_invoice(row, subscription, plan, invoice, payment, ids)
            existing = await session.scalar(select(RenewalCycle).where(RenewalCycle.mode == "test",
                RenewalCycle.account_id == account, RenewalCycle.invoice_id == ids[2]))
            if existing:
                if (existing.mandate_id != row.id or existing.user_id != user_id or existing.payment_id != ids[1]
                        or _stored_utc(existing.period_start) != start or _stored_utc(existing.period_end) != end):
                    raise RejectReceipt("renewal_invoice_already_bound")
                processed(receipt, applied_at)
                await session.commit()
                return "duplicate"
            if await session.scalar(select(PaymentActivation.id).where(PaymentActivation.mode == "test",
                PaymentActivation.account_id == account, PaymentActivation.payment_id == ids[1]).limit(1)):
                raise RejectReceipt("acquisition_payment_reused")
            sub = await session.scalar(select(Subscription).where(Subscription.id == row.subscription_id,
                Subscription.user_id == user_id).with_for_update().execution_options(populate_existing=True))
            if (sub is None or sub.provider != "razorpay" or sub.provider_subscription_id != ids[0]
                    or (sub.plan, sub.billing_interval) != (row.plan, row.billing_interval)
                    or sub.status not in ("active", "grace", "past_due") or sub.cancel_at_period_end):
                raise RejectReceipt("renewal_lifecycle_changed")
            last = await session.scalar(select(RenewalCycle).where(RenewalCycle.mandate_id == row.id)
                .order_by(RenewalCycle.period_end.desc()).limit(1))
            expected_start = _stored_utc(last.period_end if last else row.starts_at)
            if start > expected_start:
                raise RetryReceipt("renewal_predecessor_missing")
            if start != expected_start:
                raise RejectReceipt("renewal_period_overlap")
            count = await session.scalar(select(func.count()).select_from(RenewalCycle).where(RenewalCycle.mandate_id == row.id))
            if count >= row.total_count:
                raise RejectReceipt("renewal_cycles_exhausted")
            grant = await session.get(PaymentActivation, row.activation_id)
            quote = await session.get(CheckoutReservation, grant.reservation_id) if grant else None
            prior = await session.scalar(select(RenewalCycle).where(RenewalCycle.user_id == user_id)
                .order_by(RenewalCycle.period_end.desc()).limit(1))
            if (grant is None or grant.user_id != user_id or grant.mode != row.mode
                    or grant.account_id != row.account_id or grant.provider_key_id != row.provider_key_id
                    or (grant.plan, grant.billing_interval) != (row.plan, row.billing_interval)
                    or quote is None or quote.renewal_amount_minor != row.amount_minor
                    or quote.renewal_interval != row.billing_interval
                    or _stored_utc(sub.current_period_end) != _stored_utc(prior.period_end if prior else grant.period_end)):
                raise RejectReceipt("renewal_paid_term_changed")
            # Keep existing paid coverage intact; schedule a paid future cycle exactly at its start.
            if start > applied_at:
                raise FutureCycle(start)
            previous_end = _stored_utc(sub.current_period_end)
            if start > previous_end:
                sub.current_period_start = start
            from app.models.payment_recovery import PaymentRecovery
            recovery = await session.scalar(select(PaymentRecovery).where(
                PaymentRecovery.mandate_id == row.id, PaymentRecovery.period_start == start).with_for_update())
            if recovery is not None:
                if (recovery.user_id != user_id or recovery.mode != row.mode or recovery.account_id != account
                        or recovery.invoice_id != ids[2] or _stored_utc(recovery.period_end) != end
                        or recovery.resolved_at is not None):
                    raise RejectReceipt("recovery_invoice_changed")
                recovery.resolved_at = applied_at
            sub.status = "active"
            sub.recovery_due_at, sub.grace_until = None, None
            sub.current_period_end = end
            session.add(RenewalCycle(user_id=user_id, mandate_id=row.id, source_event_id=receipt_id,
                mode="test", account_id=account, provider_subscription_id=ids[0], invoice_id=ids[2], payment_id=ids[1],
                amount_minor=row.amount_minor, currency=row.currency, period_start=start, period_end=end, applied_at=applied_at))
            if count + 1 == row.total_count:
                row.state, row.active_user_id = "completed", None
            processed(receipt, applied_at)
            await session.commit()
            return "renewed"
    except FutureCycle as exc:
        return await disposition(session_maker, receipt_id, code=str(exc), retry=True, now=current, not_before=exc.starts_at)
    except RetryReceipt as exc:
        return await disposition(session_maker, receipt_id, code=str(exc), retry=True, now=current)
    except RejectReceipt as exc:
        return await disposition(session_maker, receipt_id, code=str(exc), retry=False, now=current)
