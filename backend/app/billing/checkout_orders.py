"""Single durable dispatch. Unknown outcomes reconcile; never repeat POST.
Provider calls run outside SQL locks and outside the async event loop.
"""
from __future__ import annotations
import re
from datetime import timedelta
from typing import Any
from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool
from app.billing.offer_service import _stored_utc, attach_provider_order, utcnow
from app.models.pricing_offer import CheckoutReservation


def order_notes(row: CheckoutReservation) -> dict[str, str]:
    notes = {"fincopilot_reservation_id": str(row.id), "fincopilot_user_id": str(row.user_id), "fincopilot_plan": row.plan, "fincopilot_interval": row.billing_interval, "fincopilot_offer_code": row.offer_code, "fincopilot_campaign_version": row.campaign_version}
    if row.founder_wave is not None:
        notes["fincopilot_founder_wave"] = str(row.founder_wave)
    return notes


def validate_order(order: Any, row: CheckoutReservation) -> str:
    if not isinstance(order, dict):
        raise ValueError("Invalid provider order")
    identifier = order.get("id")
    if not isinstance(identifier, str) or not re.fullmatch(r"order_[A-Za-z0-9]{1,80}", identifier):
        raise ValueError("Invalid provider identifier")
    if type(order.get("amount")) is not int or order["amount"] != row.amount_minor:
        raise ValueError("Provider amount mismatch")
    if order.get("entity") != "order" or order.get("currency") != row.currency or order.get("receipt") != row.provider_receipt:
        raise ValueError("Provider entity/currency/receipt mismatch")
    notes = order.get("notes")
    if not isinstance(notes, dict) or any(notes.get(k) != v for k, v in order_notes(row).items()):
        raise ValueError("Provider reservation metadata mismatch")
    if row.provider_order_id and row.provider_order_id != identifier:
        raise ValueError("Provider identity mismatch")
    return identifier


def require_unattempted(order: dict, row: CheckoutReservation) -> None:
    if (order.get("status") != "created" or type(order.get("attempts")) is not int or order["attempts"] != 0 or type(order.get("amount_paid")) is not int or order["amount_paid"] != 0 or type(order.get("amount_due")) is not int or order["amount_due"] != row.amount_minor):
        raise HTTPException(409, "This order has a payment attempt; reconciliation is required. No new order was created.")


async def ensure_provider_order(session: AsyncSession, row: CheckoutReservation, client: Any, *, key_id: str) -> CheckoutReservation:
    row_id = row.id
    if row.provider_key_id and row.provider_key_id != key_id:
        raise HTTPException(409, "Payment key changed; reconcile the original checkout before retrying.")
    claimed = await session.execute(update(CheckoutReservation).where(CheckoutReservation.id == row_id, CheckoutReservation.status == "reserved", CheckoutReservation.provider_order_id.is_(None), CheckoutReservation.provider_order_state == "unstarted").values(provider_order_state="creating", provider_started_at=utcnow(), provider_key_id=key_id, provider_receipt="fp-" + row_id.hex).returning(CheckoutReservation.id))
    dispatch = claimed.scalar_one_or_none() is not None
    await session.commit()
    await session.refresh(row)
    if row.provider_key_id and row.provider_key_id != key_id:
        raise HTTPException(409, "Payment key changed during order creation.")
    if row.status != "reserved":
        raise HTTPException(409, "Checkout reservation is no longer active.")
    if not dispatch and row.provider_order_state == "creating":
        started = _stored_utc(row.provider_started_at)
        if started and started > utcnow() - timedelta(seconds=60):
            raise HTTPException(409, "Order creation is in progress. Retry this same checkout shortly.", headers={"Retry-After": "5"})
    try:
        if dispatch:
            order = await run_in_threadpool(client.order.create, data={"amount": row.amount_minor, "currency": row.currency, "receipt": row.provider_receipt, "notes": order_notes(row), "partial_payment": False})
        elif row.provider_order_id:
            order = await run_in_threadpool(client.order.fetch, row.provider_order_id)
        else:
            collection = await run_in_threadpool(client.order.all, {"receipt": row.provider_receipt, "count": 100, "skip": 0})
            if not isinstance(collection, dict) or collection.get("entity") != "collection" or not isinstance(collection.get("items"), list):
                raise ValueError("Invalid receipt inventory")
            items = collection["items"]
            if len(items) >= 100 or type(collection.get("count")) is not int or collection["count"] != len(items):
                raise ValueError("Incomplete receipt inventory")
            matches = [item for item in items if isinstance(item, dict) and item.get("receipt") == row.provider_receipt]
            if len(matches) != 1:
                raise ValueError("Unresolved or duplicate receipt")
            order = matches[0]
        identifier = validate_order(order, row)
    except Exception as exc:
        await session.rollback()
        await session.execute(update(CheckoutReservation).where(CheckoutReservation.id == row_id, CheckoutReservation.provider_order_id.is_(None), CheckoutReservation.provider_order_state.in_(("creating", "uncertain"))).values(provider_order_state="uncertain"))
        await session.commit()
        raise HTTPException(502, "Order outcome is unresolved. Retry the same checkout for reconciliation; do not start another payment.") from exc
    fresh = (await session.execute(select(CheckoutReservation).where(CheckoutReservation.id == row_id).with_for_update().execution_options(populate_existing=True))).scalar_one()
    if fresh.provider_key_id and fresh.provider_key_id != key_id:
        await session.rollback()
        raise HTTPException(409, "Checkout provider identity changed.")
    try:
        await attach_provider_order(session, reservation=fresh, provider_order_id=identifier)
        fresh.provider_key_id = key_id
        await session.commit()
        await session.refresh(fresh)
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(409, "Checkout state changed; reconciliation required.") from exc
    require_unattempted(order, fresh)
    expiry = _stored_utc(fresh.expires_at)
    if expiry and expiry <= utcnow():
        raise HTTPException(409, "Checkout window expired. Provider order retained for reconciliation; no new payment started.")
    return fresh
