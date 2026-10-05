"""Durable first-purchase activation. Provider I/O never holds SQL locks."""
import asyncio
from datetime import datetime, timedelta, timezone
import re
import uuid

from sqlalchemy import true, or_, select, text
from starlette.concurrency import run_in_threadpool

from app.billing.checkout_orders import validate_order
from app.billing.offer_service import _stored_utc, mark_reservation_verified
from app.billing.webhook_inbox import decrypt_snapshot
from app.core.config import get_settings
from app.models.payment_activation import PaymentActivation
from app.models.payment_webhook import PaymentWebhookEvent
from app.models.pricing_offer import CheckoutReservation
from app.models.subscription import Subscription
from app.models.user import User
from app.models.account_deletion import AccountDeletion


class RetryReceipt(Exception):
    """Sanitized local disposition only; never include provider errors."""


class RejectReceipt(Exception):
    """Terminal unsafe/unsupported purchase requires operator review."""


def activation_enabled() -> bool:
    settings = get_settings()
    return bool(settings.billing_activation_enabled and settings.razorpay_webhook_enabled
                and not settings.is_production and settings.razorpay_webhook_mode == "test"
                and settings.razorpay_key_id.startswith("rzp_test_")
                and settings.razorpay_key_secret.get_secret_value()
                and settings.razorpay_webhook_account_id)


def payment_identity(row: PaymentWebhookEvent) -> tuple[str, str]:
    if row.event_type not in ("payment.captured", "order.paid"):
        raise RejectReceipt("unsupported_event")
    try:
        snapshot = decrypt_snapshot(row)
        payment = snapshot["payload"]["payment"]["entity"]
        payment_id, order_id = payment["id"], payment["order_id"]
        if row.event_type == "order.paid" and snapshot["payload"]["order"]["entity"]["id"] != order_id:
            raise ValueError("Invalid signed order identity")
        if (not isinstance(payment_id, str) or not re.fullmatch(r"pay_[A-Za-z0-9]{1,80}", payment_id)
                or not isinstance(order_id, str) or not re.fullmatch(r"order_[A-Za-z0-9]{1,80}", order_id)
                or payment.get("captured") is not True or payment.get("status") != "captured"):
            raise ValueError("Invalid signed identity")
        return payment_id, order_id
    except (ValueError, KeyError, TypeError):
        raise RejectReceipt("invalid_receipt") from None


def validate_capture(order: dict, payment: dict, row: CheckoutReservation,
                     payment_id: str) -> None:
    try:
        validate_order(order, row)
    except ValueError:
        raise RejectReceipt("order_mismatch") from None
    if (not isinstance(payment, dict) or payment.get("entity") != "payment"
            or payment.get("id") != payment_id or payment.get("order_id") != row.provider_order_id
            or payment.get("captured") is not True or payment.get("status") != "captured"
            or type(payment.get("amount")) is not int or payment["amount"] != row.amount_minor
            or payment.get("currency") != "INR" or row.currency != "INR"
            or type(payment.get("amount_refunded")) is not int or payment["amount_refunded"] != 0
            or payment.get("refund_status") is not None
            or order.get("status") != "paid" or type(order.get("amount_paid")) is not int
            or order["amount_paid"] != row.amount_minor or type(order.get("amount_due")) is not int
            or order["amount_due"] != 0):
        raise RejectReceipt("capture_mismatch")


async def fetch_capture(client, order_id: str, payment_id: str) -> tuple[dict, dict]:
    try:
        async with asyncio.timeout(55):
            order = await run_in_threadpool(client.order.fetch, order_id)
            payment = await run_in_threadpool(client.payment.fetch, payment_id)
        return order, payment
    except Exception:
        raise RetryReceipt("provider_unavailable") from None


def processed(row: PaymentWebhookEvent, now: datetime) -> None:
    row.state, row.processing_error, row.next_attempt_at = "processed", None, None
    row.processing_attempts += 1
    row.processed_at = now


async def disposition(session_maker, identity: uuid.UUID, *, code: str, retry: bool,
                      now: datetime, not_before: datetime | None = None) -> str:
    async with session_maker() as session:
        row = await session.scalar(select(PaymentWebhookEvent).where(PaymentWebhookEvent.id == identity)
                                   .with_for_update().execution_options(populate_existing=True))
        if row is None or row.state != "pending":
            return "unchanged"
        row.processing_attempts += 1
        row.processing_error = code
        row.state = "pending" if retry else "quarantined"
        row.next_attempt_at = (not_before or now + timedelta(seconds=min(3600, 30 * 2**min(row.processing_attempts, 7)))) if retry else None
        await session.commit()
        return "retry" if retry else "quarantined"


async def process_receipt(session_maker, identity: uuid.UUID, client, *, now: datetime | None = None) -> str:
    if not activation_enabled():
        return "disabled"
    current = now or datetime.now(timezone.utc)
    settings = get_settings()
    key_id, account = settings.razorpay_key_id, settings.razorpay_webhook_account_id
    try:
        # Finish the read transaction BEFORE making any external request.
        async with session_maker() as session:
            receipt = await session.get(PaymentWebhookEvent, identity)
            if receipt is None or receipt.state != "pending":
                return "unchanged"
            due = _stored_utc(receipt.next_attempt_at)
            if due and due > current:
                return "not_due"
            if receipt.mode != "test" or receipt.account_id != account:
                raise RejectReceipt("provider_scope_mismatch")
            if receipt.event_type == "subscription.charged":
                await session.commit()
                from app.billing.renewal_cycles import process_renewal
                return await process_renewal(session_maker, identity, client, now=now)
            payment_id, order_id = payment_identity(receipt)
            reservation = await session.scalar(select(CheckoutReservation).where(
                CheckoutReservation.provider_order_id == order_id))
            if reservation is None:
                raise RetryReceipt("reservation_unavailable")
            reservation_id, user_id = reservation.id, reservation.user_id
            if reservation.provider_key_id != key_id or reservation.provider_order_state != "ready":
                raise RejectReceipt("checkout_key_mismatch")
            await session.commit()

        order, payment = await fetch_capture(client, order_id, payment_id)
        # External reads may take time: entitlement term anchoring uses the time
        # after reconciliation, not when the worker started waiting for provider.
        applied_at = current if now is not None else datetime.now(timezone.utc)
        async with session_maker() as session:
            if session.get_bind().dialect.name == "postgresql":
                await session.execute(text("SET LOCAL lock_timeout = '5s'"))
                await session.execute(text("SET LOCAL statement_timeout = '10s'"))
            # User fence first: account deletion cannot commit underneath a grant.
            user = await session.scalar(select(User).where(User.id == user_id).with_for_update()
                                        .execution_options(populate_existing=True))
            if user is None or not user.is_active:
                raise RejectReceipt("inactive_account")
            deletion = await session.scalar(select(AccountDeletion.id).where(
                AccountDeletion.user_id == user_id, AccountDeletion.state != "cancelled").limit(1))
            if deletion:
                raise RejectReceipt("account_deletion_pending")
            row = await session.scalar(select(CheckoutReservation).where(CheckoutReservation.id == reservation_id)
                                      .with_for_update().execution_options(populate_existing=True))
            receipt = await session.scalar(select(PaymentWebhookEvent).where(PaymentWebhookEvent.id == identity)
                                          .with_for_update().execution_options(populate_existing=True))
            if receipt is None or receipt.state != "pending":
                return "unchanged"
            if (row is None or row.user_id != user_id or row.provider_key_id != key_id
                    or row.provider != "razorpay" or row.provider_order_state != "ready"
                    or not activation_enabled() or settings.razorpay_key_id != key_id
                    or receipt.account_id != account or settings.razorpay_webhook_account_id != account
                    or receipt.mode != "test" or payment_identity(receipt) != (payment_id, order_id)):
                raise RejectReceipt("checkout_changed")
            validate_capture(order, payment, row, payment_id)
            existing = await session.scalar(select(PaymentActivation).where(
                PaymentActivation.provider == "razorpay", PaymentActivation.mode == "test",
                PaymentActivation.account_id == account, PaymentActivation.payment_id == payment_id))
            if existing:
                if existing.reservation_id != row.id or existing.user_id != user_id:
                    raise RejectReceipt("payment_already_bound")
                processed(receipt, applied_at)
                await session.commit()
                return "duplicate"
            subscription = await session.scalar(select(Subscription).where(Subscription.user_id == user_id)
                                               .with_for_update().execution_options(populate_existing=True))
            prior = await session.scalar(select(PaymentActivation.id).where(PaymentActivation.user_id == user_id).limit(1))
            if prior or (subscription and (subscription.plan != "free" or subscription.status != "free")):
                raise RejectReceipt("lifecycle_review_required")
            if (row.plan, row.billing_interval) not in (("pro", "monthly"), ("pro", "annual"), ("max", "monthly")):
                raise RejectReceipt("invalid_reserved_plan")
            try:
                await mark_reservation_verified(session, reservation=row, provider_payment_id=payment_id, now=applied_at)
            except ValueError:
                raise RejectReceipt("reservation_conflict") from None
            start = _stored_utc(row.service_starts_at)
            if start is None or not 1 <= row.service_period_days <= 366:
                raise RejectReceipt("invalid_service_period")
            end = start + timedelta(days=row.service_period_days)
            if subscription is None:
                subscription = Subscription(user_id=user_id)
                session.add(subscription)
            subscription.plan, subscription.status = row.plan, "active"
            subscription.billing_interval = row.billing_interval
            subscription.current_period_start, subscription.current_period_end = start, end
            subscription.provider, subscription.cancel_at_period_end = "razorpay", False
            session.add(PaymentActivation(provider="razorpay", mode="test", account_id=account,
                provider_key_id=key_id, payment_id=payment_id, order_id=order_id, reservation_id=row.id,
                user_id=user_id, source_event_id=identity, plan=row.plan, billing_interval=row.billing_interval,
                amount_minor=row.amount_minor, currency=row.currency, period_start=start, period_end=end,
                applied_at=applied_at))
            processed(receipt, applied_at)
            await session.commit()
            return "activated"
    except RejectReceipt as exc:
        return await disposition(session_maker, identity, code=str(exc), retry=False, now=current)
    except RetryReceipt as exc:
        return await disposition(session_maker, identity, code=str(exc), retry=True, now=current)


async def scan_receipts(session_maker, client, *, now: datetime | None = None) -> dict[str, int]:
    if not activation_enabled():
        return {"disabled": 1}
    current = now or datetime.now(timezone.utc)
    async with session_maker() as session:
        identities = list((await session.scalars(select(PaymentWebhookEvent.id).where(
            PaymentWebhookEvent.state == "pending",
            (true() if get_settings().billing_renewal_enabled else PaymentWebhookEvent.event_type != "subscription.charged"),
            or_(PaymentWebhookEvent.next_attempt_at.is_(None),
                PaymentWebhookEvent.next_attempt_at <= current)).order_by(PaymentWebhookEvent.received_at).limit(5))).all())
    counts = {}
    for identity in identities:
        try:
            result = await process_receipt(session_maker, identity, client, now=now)
        except Exception:
            # Failed/ambiguous DB commit is not called processed; next scan retries
            # durable state. Never log SQL params or provider/crypto error objects.
            result = "database_retry"
        counts[result] = counts.get(result, 0) + 1
    return counts
