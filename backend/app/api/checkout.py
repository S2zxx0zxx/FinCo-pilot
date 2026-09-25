"""Razorpay Standard Checkout endpoints with server-owned pricing offers.

Security / billing invariants:
- Checkout is disabled unless BILLING_CHECKOUT_ENABLED=true.
- Both mutations require an authenticated active FinCopilot user.
- The browser sends plan + interval only. Price/offer/scarcity are server-owned.
- A durable checkout reservation snapshots the exact offer before Razorpay order
  creation, so wave transitions cannot change the price mid-checkout.
- Provider success is verified with HMAC and fresh Razorpay order/payment reads.
- Only captured payments can finalize a reservation/founder claim.
- This module records purchase evidence but NEVER activates paid entitlements.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.billing.enums import BillingInterval, PlanId
from app.billing.offer_service import (
    attach_provider_order,
    cancel_reservation,
    mark_reservation_verified,
    reservation_for_verification,
    reserve_checkout_offer,
)
from app.billing.offers import ReservationStatus
from app.core.auth import current_active_user
from app.core.config import get_settings
from app.core.database import get_async_session
from app.models.pricing_offer import CheckoutReservation
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/checkout", tags=["checkout"])

_CHECKOUT_DISABLED: dict[int | str, dict[str, Any]] = {
    503: {"description": "Checkout feature is disabled or unavailable"},
}
_UNAUTH: dict[int | str, dict[str, Any]] = {
    401: {"description": "Authentication required"},
}
_BAD_REQUEST: dict[int | str, dict[str, Any]] = {
    400: {"description": "Bad or unsupported request"},
    409: {"description": "Checkout state conflict"},
}
_PROVIDER_ERROR: dict[int | str, dict[str, Any]] = {
    502: {"description": "Upstream payment provider error"},
}
_ALL_ERRORS: dict[int | str, dict[str, Any]] = {
    **_CHECKOUT_DISABLED,
    **_UNAUTH,
    **_BAD_REQUEST,
    **_PROVIDER_ERROR,
}


def _require_checkout_enabled() -> None:
    settings = get_settings()
    if not settings.billing_checkout_enabled:
        raise HTTPException(
            status_code=503,
            detail="Checkout is not enabled on this instance.",
        )


def _get_razorpay_client():
    try:
        import razorpay  # type: ignore[import-untyped]
    except ImportError as exc:
        logger.error("Razorpay package is not installed")
        raise HTTPException(
            status_code=503,
            detail="Payment provider package is not available.",
        ) from exc

    settings = get_settings()
    key_id = settings.razorpay_key_id.strip()
    key_secret = settings.razorpay_key_secret.get_secret_value().strip()
    if not key_id or not key_secret:
        logger.error(
            "Razorpay credentials are not configured (key_id=%s, key_secret=%s)",
            bool(key_id),
            bool(key_secret),
        )
        raise HTTPException(
            status_code=503,
            detail="Payment provider is not configured on this instance.",
        )

    return razorpay.Client(auth=(key_id, key_secret))


class CreateOrderRequest(BaseModel):
    plan: PlanId
    interval: BillingInterval = BillingInterval.MONTHLY


class CreateOrderResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    order_id: str
    amount: int
    currency: str
    plan: PlanId
    interval: BillingInterval
    reservation_id: str
    offer_code: str
    founder_wave: int | None = None
    founder_position: int | None = None
    renewal_amount_minor: int
    renewal_interval: BillingInterval
    service_period_days: int
    service_starts_at: str | None = None
    reservation_expires_at: str


class VerifyPaymentRequest(BaseModel):
    razorpay_payment_id: str
    razorpay_order_id: str
    razorpay_signature: str


class VerifyPaymentResponse(BaseModel):
    status: str
    message: str
    reservation_id: str
    offer_code: str
    founder_wave: int | None = None


class CancelReservationRequest(BaseModel):
    reservation_id: uuid.UUID


class CancelReservationResponse(BaseModel):
    status: str


def _order_response(
    reservation: CheckoutReservation, provider_order_id: str
) -> CreateOrderResponse:
    return CreateOrderResponse(
        order_id=provider_order_id,
        amount=reservation.amount_minor,
        currency=reservation.currency,
        plan=PlanId(reservation.plan),
        interval=BillingInterval(reservation.billing_interval),
        reservation_id=str(reservation.id),
        offer_code=reservation.offer_code,
        founder_wave=reservation.founder_wave,
        founder_position=reservation.founder_position,
        renewal_amount_minor=reservation.renewal_amount_minor,
        renewal_interval=BillingInterval(reservation.renewal_interval),
        service_period_days=reservation.service_period_days,
        service_starts_at=(
            reservation.service_starts_at.isoformat()
            if reservation.service_starts_at
            else None
        ),
        reservation_expires_at=reservation.expires_at.isoformat(),
    )


@router.post(
    "/create-order",
    response_model=CreateOrderResponse,
    responses=_ALL_ERRORS,
)
async def create_order(
    req: CreateOrderRequest,
    user: Annotated[User, Depends(current_active_user)],
    session: AsyncSession = Depends(get_async_session),
) -> CreateOrderResponse:
    """Create or reuse a server-priced Razorpay order.

    The DB reservation is committed before the provider network call so the
    campaign row lock is never held while waiting on Razorpay.
    """
    _require_checkout_enabled()

    settings = get_settings()
    try:
        reservation = await reserve_checkout_offer(
            session,
            user_id=user.id,
            plan=req.plan,
            interval=req.interval,
            reservation_ttl_seconds=settings.billing_offer_reservation_ttl_seconds,
        )
        await session.commit()
        await session.refresh(reservation)
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # Idempotent retry: one active reservation reuses the already-created
    # provider order instead of creating duplicate Razorpay orders.
    if reservation.provider_order_id:
        return _order_response(reservation, reservation.provider_order_id)

    client = _get_razorpay_client()
    receipt = f"fp-{reservation.id.hex[:20]}"
    notes = {
        "fincopilot_reservation_id": str(reservation.id),
        "fincopilot_user_id": str(user.id),
        "fincopilot_plan": reservation.plan,
        "fincopilot_interval": reservation.billing_interval,
        "fincopilot_offer_code": reservation.offer_code,
        "fincopilot_campaign_version": reservation.campaign_version,
    }
    if reservation.founder_wave is not None:
        notes["fincopilot_founder_wave"] = str(reservation.founder_wave)

    order_data = {
        "amount": reservation.amount_minor,
        "currency": reservation.currency,
        "receipt": receipt,
        "notes": notes,
    }

    try:
        order = client.order.create(data=order_data)
    except Exception as exc:
        logger.error(
            "Razorpay order creation failed (reservation=%s user=%s): %s",
            reservation.id,
            user.id,
            type(exc).__name__,
        )
        try:
            fresh = await session.get(
                CheckoutReservation, reservation.id, with_for_update=True
            )
            if fresh is not None:
                await cancel_reservation(
                    session,
                    reservation=fresh,
                    reason="provider_order_creation_failed",
                )
                await session.commit()
        except Exception:
            await session.rollback()
            logger.exception(
                "Failed to release checkout reservation after provider failure"
            )
        raise HTTPException(
            status_code=502,
            detail="Could not create payment order. Please try again later.",
        ) from exc

    if not isinstance(order, dict):
        raise HTTPException(
            status_code=502,
            detail="Payment provider returned an invalid order response.",
        )

    provider_order_id = str(order.get("id", ""))
    if not provider_order_id:
        raise HTTPException(
            status_code=502,
            detail="Payment provider did not return an order identifier.",
        )
    if order.get("amount") != reservation.amount_minor:
        raise HTTPException(
            status_code=502,
            detail="Payment provider returned an unexpected order amount.",
        )
    if order.get("currency") != reservation.currency:
        raise HTTPException(
            status_code=502,
            detail="Payment provider returned an unexpected order currency.",
        )

    try:
        fresh = await session.get(
            CheckoutReservation, reservation.id, with_for_update=True
        )
        if fresh is None:
            raise ValueError("Checkout reservation no longer exists")
        await attach_provider_order(
            session,
            reservation=fresh,
            provider_order_id=provider_order_id,
        )
        await session.commit()
        await session.refresh(fresh)
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return _order_response(fresh, provider_order_id)


@router.post(
    "/cancel-reservation",
    response_model=CancelReservationResponse,
    responses=_ALL_ERRORS,
)
async def cancel_checkout_reservation(
    req: CancelReservationRequest,
    user: Annotated[User, Depends(current_active_user)],
    session: AsyncSession = Depends(get_async_session),
) -> CancelReservationResponse:
    """Release an unverified checkout reservation (for modal dismiss/change)."""
    _require_checkout_enabled()
    reservation = (
        await session.execute(
            select(CheckoutReservation)
            .where(
                CheckoutReservation.id == req.reservation_id,
                CheckoutReservation.user_id == user.id,
            )
            .with_for_update()
        )
    ).scalar_one_or_none()
    if reservation is None:
        raise HTTPException(status_code=404, detail="Checkout reservation not found.")

    if reservation.status == ReservationStatus.VERIFIED.value:
        raise HTTPException(
            status_code=409,
            detail="A verified payment reservation cannot be cancelled.",
        )

    await cancel_reservation(
        session,
        reservation=reservation,
        reason="customer_cancelled_checkout",
    )
    await session.commit()
    return CancelReservationResponse(status="cancelled")


@router.post(
    "/verify-payment",
    response_model=VerifyPaymentResponse,
    responses=_ALL_ERRORS,
)
async def verify_payment(
    req: VerifyPaymentRequest,
    user: Annotated[User, Depends(current_active_user)],
    session: AsyncSession = Depends(get_async_session),
) -> VerifyPaymentResponse:
    """Verify signature + provider state + immutable offer reservation.

    A captured payment is recorded idempotently. Entitlements are deliberately
    untouched; signed webhook/subscription activation is a later roadmap item.
    """
    _require_checkout_enabled()

    if (
        not req.razorpay_payment_id
        or not req.razorpay_order_id
        or not req.razorpay_signature
    ):
        raise HTTPException(
            status_code=400, detail="Missing required payment fields."
        )

    settings = get_settings()
    key_secret = settings.razorpay_key_secret.get_secret_value().strip()
    if not key_secret:
        raise HTTPException(
            status_code=503,
            detail="Payment provider is not configured on this instance.",
        )

    body = f"{req.razorpay_order_id}|{req.razorpay_payment_id}"
    generated_signature = hmac.new(
        key=key_secret.encode("utf-8"),
        msg=body.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(generated_signature, req.razorpay_signature):
        logger.warning(
            "Razorpay signature mismatch (user=%s order=%s)",
            user.id,
            req.razorpay_order_id,
        )
        raise HTTPException(
            status_code=400,
            detail="Payment signature verification failed.",
        )

    client = _get_razorpay_client()
    try:
        rzp_order = client.order.fetch(req.razorpay_order_id)
        rzp_payment = client.payment.fetch(req.razorpay_payment_id)
    except Exception as exc:
        logger.error(
            "Razorpay verification fetch failed (user=%s order=%s payment=%s): %s",
            user.id,
            req.razorpay_order_id,
            req.razorpay_payment_id,
            type(exc).__name__,
        )
        raise HTTPException(
            status_code=502,
            detail="Could not verify payment with the payment provider.",
        ) from exc

    if not isinstance(rzp_order, dict) or not isinstance(rzp_payment, dict):
        raise HTTPException(
            status_code=502,
            detail="Payment provider returned an invalid verification response.",
        )

    reservation = await reservation_for_verification(
        session,
        user_id=user.id,
        provider_order_id=req.razorpay_order_id,
    )
    if reservation is None:
        raise HTTPException(
            status_code=400,
            detail="No matching FinCopilot checkout reservation was found.",
        )

    if str(rzp_order.get("id", "")) != req.razorpay_order_id:
        raise HTTPException(status_code=400, detail="Provider order mismatch.")
    if rzp_payment.get("order_id") != req.razorpay_order_id:
        raise HTTPException(
            status_code=400,
            detail="Payment does not belong to this order.",
        )

    notes_raw = rzp_order.get("notes")
    notes = notes_raw if isinstance(notes_raw, dict) else {}
    expected_notes = {
        "fincopilot_reservation_id": str(reservation.id),
        "fincopilot_user_id": str(user.id),
        "fincopilot_plan": reservation.plan,
        "fincopilot_interval": reservation.billing_interval,
        "fincopilot_offer_code": reservation.offer_code,
        "fincopilot_campaign_version": reservation.campaign_version,
    }
    for key, expected in expected_notes.items():
        if str(notes.get(key, "")) != expected:
            logger.warning(
                "Razorpay order note mismatch (%s) reservation=%s user=%s",
                key,
                reservation.id,
                user.id,
            )
            raise HTTPException(
                status_code=400,
                detail="Payment order metadata does not match the checkout reservation.",
            )

    if rzp_order.get("amount") != reservation.amount_minor:
        raise HTTPException(
            status_code=400,
            detail="Order amount does not match the reserved price.",
        )
    if rzp_payment.get("amount") != reservation.amount_minor:
        raise HTTPException(
            status_code=400,
            detail="Payment amount does not match the reserved price.",
        )
    if rzp_order.get("currency") != "INR" or rzp_payment.get("currency") != "INR":
        raise HTTPException(
            status_code=400,
            detail="Checkout currency does not match the INR billing contract.",
        )

    # Founder slots and paid-purchase evidence are only final after capture.
    if rzp_payment.get("status") != "captured":
        raise HTTPException(
            status_code=400,
            detail="Payment has not been captured.",
        )

    try:
        await mark_reservation_verified(
            session,
            reservation=reservation,
            provider_payment_id=req.razorpay_payment_id,
        )
        await session.commit()
        await session.refresh(reservation)
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    logger.info(
        "Razorpay captured payment verified "
        "(user=%s reservation=%s order=%s payment=%s offer=%s amount=%s)",
        user.id,
        reservation.id,
        req.razorpay_order_id,
        req.razorpay_payment_id,
        reservation.offer_code,
        reservation.amount_minor,
    )

    return VerifyPaymentResponse(
        status="verified",
        message=(
            "Payment captured and verified. Paid entitlement activation remains "
            "pending the signed subscription/webhook lifecycle."
        ),
        reservation_id=str(reservation.id),
        offer_code=reservation.offer_code,
        founder_wave=reservation.founder_wave,
    )
