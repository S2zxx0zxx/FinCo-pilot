"""Bounded collection failure reconciliation; never issue provider mutations."""
import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, text
from starlette.concurrency import run_in_threadpool

from app.billing.activation import RejectReceipt, RetryReceipt, disposition, processed
from app.billing.offer_service import _stored_utc
from app.billing.renewal_mandates import enabled as renewal_enabled, identifier, validate_plan, validate_subscription
from app.billing.webhook_inbox import decrypt_snapshot
from app.core.config import get_settings
from app.models.account_deletion import AccountDeletion
from app.models.payment_activation import PaymentActivation
from app.models.payment_recovery import PaymentRecovery
from app.models.payment_renewal import RenewalCycle, RenewalMandate
from app.models.payment_webhook import PaymentWebhookEvent
from app.models.pricing_offer import CheckoutReservation
from app.models.subscription import Subscription
from app.models.user import User


def enabled():
    return renewal_enabled() and get_settings().billing_recovery_enabled


def identity(receipt):
    try:
        entity = decrypt_snapshot(receipt)["payload"]["subscription"]["entity"]
        state = receipt.event_type.removeprefix("subscription.")
        if state not in ("pending", "halted") or entity.get("status") != state or not identifier(entity.get("id"), "sub"):
            raise ValueError()
        return entity["id"]
    except (KeyError, TypeError, ValueError):
        raise RejectReceipt("invalid_failure_receipt") from None


async def invoices_for(client, sid):
    """Bounded complete enumeration, independent of provider list ordering."""
    result = []
    seen = set()
    for skip in (0, 100):
        page = await run_in_threadpool(client.invoice.all, {"subscription_id": sid, "count": 100, "skip": skip})
        if (not isinstance(page, dict) or page.get("entity") != "collection"
                or type(page.get("count")) is not int or not isinstance(page.get("items"), list)
                or page["count"] != len(page["items"]) or page["count"] > 100):
            raise RetryReceipt("failure_invoice_inventory_unavailable")
        for item in page["items"]:
            if (not isinstance(item, dict) or item.get("entity") != "invoice" or not identifier(item.get("id"), "inv")
                    or item.get("subscription_id") != sid or item["id"] in seen):
                raise RejectReceipt("failure_invoice_inventory_mismatch")
            seen.add(item["id"])
            result.append(item)
        if page["count"] < 100:
            return result
    raise RetryReceipt("failure_invoice_inventory_incomplete")


def unpaid_invoice(row, invoices, expected):
    matches = [i for i in invoices if type(i.get("billing_start")) is int and i["billing_start"] == int(expected.timestamp())]
    if len(matches) != 1:
        raise RetryReceipt("failure_invoice_unavailable")
    i = matches[0]
    try:
        if (i.get("status") != "issued" or i.get("currency") != row.currency or i.get("payment_id") is not None
                or type(i.get("amount")) is not int or i["amount"] != row.amount_minor
                or type(i.get("amount_paid")) is not int or i["amount_paid"] != 0
                or type(i.get("amount_due")) is not int or i["amount_due"] != row.amount_minor
                or type(i.get("billing_end")) is not int):
            raise ValueError()
        end = datetime.fromtimestamp(i["billing_end"], timezone.utc)
        lo, hi = (27, 32) if row.billing_interval == "monthly" else (364, 367)
        if not timedelta(days=lo) <= end - expected <= timedelta(days=hi):
            raise ValueError()
        return i, end
    except (ValueError, TypeError, OverflowError, OSError):
        raise RejectReceipt("failure_invoice_evidence_mismatch") from None


async def process_failure(session_maker, receipt_id, client, *, now: datetime | None = None):
    if not enabled():
        return "disabled"
    current = now or datetime.now(timezone.utc)
    settings = get_settings()
    account, key = settings.razorpay_webhook_account_id, settings.razorpay_key_id
    try:
        async with session_maker() as session:
            receipt = await session.get(PaymentWebhookEvent, receipt_id)
            if receipt is None or receipt.state != "pending":
                return "unchanged"
            due = _stored_utc(receipt.next_attempt_at)
            if due and due > current:
                return "not_due"
            sid = identity(receipt)
            row = await session.scalar(select(RenewalMandate).where(RenewalMandate.mode == "test",
                RenewalMandate.account_id == account, RenewalMandate.provider_subscription_id == sid))
            if row is None:
                raise RetryReceipt("failure_binding_unavailable")
            if receipt.mode != "test" or receipt.account_id != account or row.provider_key_id != key or row.state != "ready":
                raise RejectReceipt("failure_scope_mismatch")
            mid, uid, pid = row.id, row.user_id, row.provider_plan_id
            await session.commit()
        try:
            async with asyncio.timeout(110):
                provider = await run_in_threadpool(client.subscription.fetch, sid)
                plan = await run_in_threadpool(client.plan.fetch, pid)
                invoices = await invoices_for(client, sid)
        except (RetryReceipt, RejectReceipt):
            raise
        except Exception:
            raise RetryReceipt("failure_provider_unavailable") from None
        applied = current if now is not None else datetime.now(timezone.utc)
        async with session_maker() as session:
            if session.get_bind().dialect.name == "postgresql":
                await session.execute(text("SET LOCAL lock_timeout = '5s'"))
                await session.execute(text("SET LOCAL statement_timeout = '10s'"))
            user = await session.scalar(select(User).where(User.id == uid).with_for_update())
            if user is None or not user.is_active:
                raise RejectReceipt("inactive_account")
            if await session.scalar(select(AccountDeletion.id).where(AccountDeletion.user_id == uid,
                AccountDeletion.state != "cancelled").limit(1)):
                raise RejectReceipt("account_deletion_pending")
            row = await session.scalar(select(RenewalMandate).where(RenewalMandate.id == mid).with_for_update().execution_options(populate_existing=True))
            receipt = await session.scalar(select(PaymentWebhookEvent).where(PaymentWebhookEvent.id == receipt_id).with_for_update().execution_options(populate_existing=True))
            if receipt is None or receipt.state != "pending":
                return "unchanged"
            fresh = get_settings()
            if (row is None or row.user_id != uid or row.provider_plan_id != pid or row.provider_subscription_id != sid
                    or row.mode != "test" or row.account_id != account or row.provider_key_id != key or row.state != "ready"
                    or receipt.mode != "test" or receipt.account_id != account or identity(receipt) != sid
                    or not enabled() or fresh.razorpay_key_id != key or fresh.razorpay_webhook_account_id != account):
                raise RejectReceipt("failure_binding_changed")
            try:
                validate_plan(row, plan)
                validate_subscription(row, provider, statuses={"pending", "halted", "active", "completed"})
                if provider.get("has_scheduled_changes") is not False:
                    raise ValueError()
            except (ValueError, TypeError, KeyError):
                raise RejectReceipt("failure_subscription_evidence_mismatch") from None
            sub = await session.scalar(select(Subscription).where(Subscription.id == row.subscription_id,
                Subscription.user_id == uid).with_for_update().execution_options(populate_existing=True))
            if (sub is None or sub.provider != "razorpay" or sub.provider_subscription_id != sid
                    or sub.status not in ("active", "grace", "past_due") or sub.cancel_at_period_end
                    or (sub.plan, sub.billing_interval) != (row.plan, row.billing_interval)):
                raise RejectReceipt("failure_lifecycle_changed")
            count = await session.scalar(select(func.count()).select_from(RenewalCycle).where(RenewalCycle.mandate_id == mid))
            # An old signed failure may arrive after its exact period was already paid.
            # Only retained captured-cycle evidence permits acknowledging it without regression.
            signed_start = decrypt_snapshot(receipt)["payload"]["subscription"]["entity"].get("current_start")
            if provider["status"] in ("active", "completed") and provider["paid_count"] == count and type(signed_start) is int:
                try:
                    signed_period = datetime.fromtimestamp(signed_start, timezone.utc)
                except (ValueError, OverflowError, OSError):
                    raise RejectReceipt("failure_signed_period_invalid") from None
                covered = await session.scalar(select(RenewalCycle).where(RenewalCycle.mandate_id == mid,
                    RenewalCycle.user_id == uid, RenewalCycle.mode == "test", RenewalCycle.account_id == account,
                    RenewalCycle.period_start == signed_period).limit(1))
                if covered is not None:
                    processed(receipt, applied)
                    await session.commit()
                    return "failure_superseded"
            # A fresh active state is not evidence of paid access. Retry until captured-cycle reconciliation.
            if provider["paid_count"] > count or provider["status"] in ("active", "completed"):
                raise RetryReceipt("failure_paid_reconciliation_required")
            if provider["paid_count"] != count or count >= row.total_count:
                raise RejectReceipt("failure_cycle_count_mismatch")
            last = await session.scalar(select(RenewalCycle).where(RenewalCycle.mandate_id == mid).order_by(RenewalCycle.period_end.desc()).limit(1))
            expected = _stored_utc(last.period_end if last else row.starts_at)
            if expected is None:
                raise RejectReceipt("failure_paid_term_missing")
            grant = await session.get(PaymentActivation, row.activation_id)
            quote = await session.get(CheckoutReservation, grant.reservation_id) if grant else None
            prior = await session.scalar(select(RenewalCycle).where(RenewalCycle.user_id == uid).order_by(RenewalCycle.period_end.desc()).limit(1))
            if (grant is None or grant.user_id != uid or grant.mode != row.mode or grant.account_id != account
                    or grant.provider_key_id != key or (grant.plan, grant.billing_interval) != (row.plan, row.billing_interval)
                    or quote is None or quote.renewal_amount_minor != row.amount_minor or quote.renewal_interval != row.billing_interval
                    or _stored_utc(sub.current_period_end) != expected
                    or expected != _stored_utc(prior.period_end if prior else grant.period_end)):
                raise RejectReceipt("failure_paid_term_changed")
            invoice, end = unpaid_invoice(row, invoices, expected)
            if expected > applied:
                raise RetryReceipt("failure_period_not_started")
            case = await session.scalar(select(PaymentRecovery).where(PaymentRecovery.mandate_id == mid,
                PaymentRecovery.period_start == expected).with_for_update())
            if case is None:
                hours = fresh.billing_recovery_grace_hours
                if type(hours) is not int or not 0 <= hours <= 72:
                    raise RejectReceipt("failure_grace_policy_invalid")
                case = PaymentRecovery(user_id=uid, mandate_id=mid, source_event_id=receipt_id, mode="test",
                    account_id=account, invoice_id=invoice["id"], provider_state=provider["status"], period_start=expected,
                    period_end=end, grace_until=expected + timedelta(hours=hours), observed_at=applied)
                session.add(case)
            elif (case.user_id != uid or case.mode != "test" or case.account_id != account or case.invoice_id != invoice["id"]
                    or _stored_utc(case.period_end) != end or case.resolved_at is not None):
                raise RejectReceipt("failure_case_changed")
            elif provider["status"] == "halted":
                case.provider_state = "halted"
            deadline = _stored_utc(case.grace_until)
            if deadline is None or not expected <= deadline <= expected + timedelta(hours=72):
                raise RejectReceipt("failure_case_deadline_invalid")
            sub.recovery_due_at, sub.grace_until = expected, deadline
            sub.status = "grace" if deadline > applied else "past_due"
            processed(receipt, applied)
            await session.commit()
            return "recovery_recorded"
    except RetryReceipt as exc:
        return await disposition(session_maker, receipt_id, code=str(exc), retry=True, now=current)
    except RejectReceipt as exc:
        return await disposition(session_maker, receipt_id, code=str(exc), retry=False, now=current)
