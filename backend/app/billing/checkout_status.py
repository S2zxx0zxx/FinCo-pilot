"""Fresh owned checkout observations. Never collect, release, or grant from a GET."""
import asyncio
import re
from datetime import datetime, timezone
from sqlalchemy import select
from starlette.concurrency import run_in_threadpool
from app.billing.activation import RejectReceipt, RetryReceipt, activation_enabled, processed
from app.billing.checkout_orders import validate_order
from app.billing.offer_service import _stored_utc
from app.billing.webhook_inbox import decrypt_snapshot
from app.core.config import get_settings
from app.models.payment_activation import PaymentActivation
from app.models.payment_webhook import PaymentWebhookEvent
from app.models.pricing_offer import CheckoutReservation
from app.models.user import User


def validate_inventory(row, order, collection):
    if row.provider != "razorpay" or row.currency != "INR" or not row.provider_receipt:
        raise ValueError("Unsupported checkout binding")
    validate_order(order, row)
    if (not isinstance(collection, dict) or collection.get("entity") != "collection"
            or not isinstance(collection.get("items"), list)
            or type(collection.get("count")) is not int
            or collection["count"] != len(collection["items"]) or collection["count"] > 100
            or type(order.get("attempts")) is not int or order["attempts"] != collection["count"]):
        raise ValueError("Incomplete checkout inventory")
    items = collection["items"]
    ids = set()
    for item in items:
        if (not isinstance(item, dict) or item.get("entity") != "payment"
                or not isinstance(item.get("id"), str) or not re.fullmatch(r"pay_[A-Za-z0-9]{1,80}", item["id"])
                or item["id"] in ids or item.get("order_id") != row.provider_order_id
                or item.get("invoice_id") is not None
                or type(item.get("amount")) is not int or item["amount"] != row.amount_minor
                or item.get("currency") != row.currency
                or item.get("status") not in {"created", "authorized", "failed", "captured", "refunded"}
                or type(item.get("captured")) is not bool
                or item["captured"] != (item["status"] in {"captured", "refunded"})
                or type(item.get("amount_refunded")) is not int
                or not 0 <= item["amount_refunded"] <= row.amount_minor
                or item.get("refund_status") != (None if item["amount_refunded"] == 0 else "full" if item["amount_refunded"] == row.amount_minor else "partial")
                or (not item["captured"] and item["amount_refunded"] != 0)
                or (item["status"] == "refunded" and item["amount_refunded"] != row.amount_minor)):
            raise ValueError("Invalid checkout payment")
        ids.add(item["id"])
    captures = [item for item in items if item["captured"]]
    if len(captures) > 1:
        raise ValueError("Multiple captured payments")
    paid = row.amount_minor if captures else 0
    if (type(order.get("amount_paid")) is not int or order["amount_paid"] != paid
            or type(order.get("amount_due")) is not int or order["amount_due"] != row.amount_minor - paid
            or order.get("status") != ("paid" if captures else "attempted" if items else "created")):
        raise ValueError("Inconsistent checkout totals")
    if captures:
        if row.provider_payment_id and captures[0]["id"] != row.provider_payment_id:
            raise ValueError("Captured payment binding changed")
        return ("refund_review" if captures[0]["amount_refunded"] else "captured"), ids
    states = {item["status"] for item in items}
    return next((state for state in ("authorized", "created", "failed") if state in states), "ready"), ids


async def fetch_status(row, client):
    try:
        async with asyncio.timeout(55):
            order = await run_in_threadpool(client.order.fetch, row.provider_order_id)
            collection = await run_in_threadpool(client.order.payments, row.provider_order_id)
        return validate_inventory(row, order, collection)
    except Exception:
        raise RetryReceipt("checkout_provider_unresolved") from None


async def owned_status(session, uid, client, *, credential_stamp=None):
    from app.core.auth import get_jwt_strategy
    row = await session.scalar(select(CheckoutReservation).where(CheckoutReservation.user_id == uid,
        CheckoutReservation.status.in_(("reserved", "verified")), CheckoutReservation.provider_order_state != "unstarted")
        .order_by(CheckoutReservation.created_at.desc()).limit(1))
    if row is None:
        await session.commit()
        return {"available": True, "checkout": None}
    identity, key = row.id, get_settings().razorpay_key_id.strip()
    binding = (row.provider_order_id, row.provider_receipt, row.amount_minor, row.currency)
    state = "unresolved"
    observed_ids = set()
    await session.commit()
    if row.provider_key_id == key and row.provider_order_state == "ready" and row.provider_order_id:
        try:
            state, observed_ids = await fetch_status(row, client)
        except RetryReceipt:
            pass
    actor = await session.get(User, uid, populate_existing=True)
    if (actor is None or not actor.is_active
            or (credential_stamp is not None and get_jwt_strategy().stamp(actor) != credential_stamp)):
        from fastapi import HTTPException
        raise HTTPException(403, "Current account authorization is required.")
    fresh = await session.get(CheckoutReservation, identity, populate_existing=True)
    if (fresh is None or fresh.user_id != uid or (fresh.provider_order_id, fresh.provider_receipt, fresh.amount_minor, fresh.currency) != binding
            or fresh.provider_key_id != key or get_settings().razorpay_key_id.strip() != key
            or not get_settings().billing_checkout_enabled or get_settings().is_production):
        state = "unresolved"
    expiry = _stored_utc(fresh.expires_at) if fresh else None
    if state == "ready" and expiry and expiry <= datetime.now(timezone.utc):
        state = "expired"
    grant = await session.scalar(select(PaymentActivation).where(PaymentActivation.reservation_id == identity))
    if (grant is not None or (fresh is not None and fresh.status == "verified")) and (
            state not in {"captured", "refund_review"}
            or (grant is not None and grant.payment_id not in observed_ids)
            or (fresh is not None and fresh.provider_payment_id not in observed_ids)):
        state = "unresolved"
    await session.commit()
    return {"available": True, "checkout": {"reservation_id": str(identity), "state": state,
        "activation_confirmed": grant is not None, "test_mode": True}}


async def process_signal(sessions, identity, client, *, now=None):
    current = now or datetime.now(timezone.utc)
    settings = get_settings()
    account, key = settings.razorpay_webhook_account_id, settings.razorpay_key_id
    try:
        async with sessions() as session:
            receipt = await session.get(PaymentWebhookEvent, identity)
            if receipt is None or receipt.state != "pending":
                return "unchanged"
            due = _stored_utc(receipt.next_attempt_at)
            if due and due > current:
                return "not_due"
            if receipt.event_type not in {"payment.failed", "payment.authorized"}:
                raise RejectReceipt("unsupported_checkout_signal")
            snapshot = decrypt_snapshot(receipt)
            payment = snapshot["payload"]["payment"]["entity"]
            if receipt.mode != "test" or receipt.account_id != account:
                raise RejectReceipt("checkout_signal_scope")
            row = await session.scalar(select(CheckoutReservation).where(CheckoutReservation.provider_order_id == payment.get("order_id")))
            if row is None:
                raise RetryReceipt("checkout_signal_binding_unavailable")
            if row.provider_key_id != key or row.provider_order_state != "ready":
                raise RejectReceipt("checkout_signal_binding_changed")
            row_id, order_id, payment_id = row.id, row.provider_order_id, payment.get("id")
            binding = (row.user_id, row.provider_receipt, row.amount_minor, row.currency)
            await session.commit()
        _, ids = await fetch_status(row, client)
        if payment_id not in ids:
            raise RetryReceipt("checkout_signal_payment_not_visible")
        async with sessions() as session:
            fresh = await session.get(CheckoutReservation, row_id, populate_existing=True)
            receipt = await session.scalar(select(PaymentWebhookEvent).where(PaymentWebhookEvent.id == identity).with_for_update())
            if receipt is None or receipt.state != "pending":
                return "unchanged"
            if (fresh is None or fresh.provider_order_id != order_id or fresh.provider_key_id != key
                    or fresh.provider_order_state != "ready"
                    or (fresh.user_id, fresh.provider_receipt, fresh.amount_minor, fresh.currency) != binding
                    or not activation_enabled() or settings.razorpay_key_id != key
                    or settings.razorpay_webhook_account_id != account):
                raise RejectReceipt("checkout_signal_binding_changed")
            processed(receipt, current)
            await session.commit()
        return "checkout_signal_reconciled"  # Non-granting, including a late capture.
    except (KeyError, TypeError, ValueError):
        raise RejectReceipt("invalid_checkout_signal") from None
