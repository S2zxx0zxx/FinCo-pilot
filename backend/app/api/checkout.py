"""
Razorpay Standard Checkout – backend endpoints.

Security invariants enforced here:
  - Checkout is fail-closed: disabled unless BILLING_CHECKOUT_ENABLED=true.
  - Both endpoints require an authenticated active user (current_active_user).
  - Amount is NEVER trusted from the browser; it is always read from the
    server-side canonical PRICE_CATALOG.
  - The Razorpay KEY_SECRET is read from Settings (SecretStr) and is never
    returned to the client or written to logs.
  - Payment verification uses constant-time hmac.compare_digest.
  - Raw Razorpay exception details are logged server-side but are NOT exposed
    to the client.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.billing.enums import BillingInterval, PlanId
from app.billing.pricing import PRICE_CATALOG
from app.core.auth import current_active_user
from app.core.config import get_settings
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/checkout", tags=["checkout"])

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CHECKOUT_DISABLED = {
    503: {"description": "Checkout feature is disabled on this instance"},
}
_UNAUTH = {401: {"description": "Authentication required"}}
_BAD_REQUEST = {400: {"description": "Bad or unsupported request"}}
_PROVIDER_ERROR = {502: {"description": "Upstream payment provider error"}}
_ALL_ERRORS = {**_CHECKOUT_DISABLED, **_UNAUTH, **_BAD_REQUEST, **_PROVIDER_ERROR}


def _require_checkout_enabled() -> None:
    """Fail-closed guard: raise 503 unless BILLING_CHECKOUT_ENABLED is true."""
    settings = get_settings()
    if not settings.billing_checkout_enabled:
        raise HTTPException(
            status_code=503,
            detail="Checkout is not enabled on this instance.",
        )


def _get_razorpay_client():
    """Return an authenticated razorpay.Client.

    Reads credentials from Settings (pydantic SecretStr) — never os.environ
    directly.  Raises HTTP 503 (configuration error) if credentials are absent.
    """
    try:
        import razorpay  # type: ignore[import-untyped]
    except ImportError as exc:
        logger.error("razorpay package is not installed: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="Payment provider package not available.",
        ) from exc

    settings = get_settings()
    key_id = settings.razorpay_key_id
    key_secret = settings.razorpay_key_secret.get_secret_value()

    if not key_id or not key_secret:
        logger.error(
            "Razorpay credentials are not configured "
            "(key_id present: %s, key_secret present: %s)",
            bool(key_id),
            bool(key_secret),
        )
        raise HTTPException(
            status_code=503,
            detail="Payment provider is not configured on this instance.",
        )

    return razorpay.Client(auth=(key_id, key_secret))


def _lookup_price(plan: PlanId, interval: BillingInterval) -> int:
    """Return the canonical amount_minor for this plan/interval.

    Raises HTTP 400 for unsupported combinations (Free, Max Annual, unknown).
    """
    if plan is PlanId.FREE:
        raise HTTPException(
            status_code=400,
            detail="Free plan does not require checkout.",
        )

    key = (plan, interval)
    price = PRICE_CATALOG.get(key)
    if price is None:
        raise HTTPException(
            status_code=400,
            detail=f"Plan '{plan}' / interval '{interval}' is not available for purchase.",
        )
    if price.amount_minor == 0:
        raise HTTPException(
            status_code=400,
            detail="Cannot create a checkout order for a zero-amount plan.",
        )
    if price.currency != "INR":
        # Future: other currencies.  For now INR only.
        raise HTTPException(
            status_code=400,
            detail="Only INR currency is supported at this time.",
        )
    return price.amount_minor


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class CreateOrderRequest(BaseModel):
    """What the browser is allowed to send — plan + interval only.

    The server derives amount, currency, and receipt internally so the browser
    can never influence the charged amount.
    """
    plan: PlanId
    interval: BillingInterval = BillingInterval.MONTHLY


class CreateOrderResponse(BaseModel):
    order_id: str
    amount: int          # minor units (paise), for display only
    currency: str        # always "INR"
    plan: str
    interval: str


class VerifyPaymentRequest(BaseModel):
    razorpay_payment_id: str
    razorpay_order_id: str
    razorpay_signature: str


class VerifyPaymentResponse(BaseModel):
    status: str          # "verified"
    message: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/create-order",
    response_model=CreateOrderResponse,
    responses=_ALL_ERRORS,
)
async def create_order(
    req: CreateOrderRequest,
    user: Annotated[User, Depends(current_active_user)],
) -> CreateOrderResponse:
    """Create a Razorpay order for the authenticated user.

    The browser supplies plan + interval only; amount is sourced from the
    server-side PRICE_CATALOG and cannot be manipulated by the client.
    """
    _require_checkout_enabled()

    amount_minor = _lookup_price(req.plan, req.interval)
    client = _get_razorpay_client()

    # Safe receipt: server-generated, no user data in the string.
    receipt = f"fp-{req.plan}-{req.interval}-{uuid.uuid4().hex[:12]}"

    order_data = {
        "amount": amount_minor,
        "currency": "INR",
        "receipt": receipt,
        "notes": {
            # Stored in Razorpay dashboard for auditing.
            # Never used server-side as a trust anchor — server always
            # re-validates from PRICE_CATALOG on verify-payment.
            "fincopilot_user_id": str(user.id),
            "fincopilot_plan": req.plan.value,
            "fincopilot_interval": req.interval.value,
        },
    }

    try:
        order = client.order.create(data=order_data)
    except Exception as exc:
        # Log the provider detail server-side; return a generic message to the
        # client to avoid leaking internal Razorpay error codes/details.
        exc_name = type(exc).__name__
        if "Authentication" in exc_name or "auth" in str(exc).lower():
            logger.error(
                "Razorpay authentication failure creating order "
                "(plan=%s interval=%s user=%s): %s",
                req.plan, req.interval, user.id, exc_name,
            )
            raise HTTPException(
                status_code=502,
                detail="Payment provider authentication error. "
                       "Please contact support.",
            ) from exc
        logger.error(
            "Razorpay order creation failed (plan=%s interval=%s user=%s): %s: %s",
            req.plan, req.interval, user.id, exc_name, exc,
        )
        raise HTTPException(
            status_code=502,
            detail="Could not create payment order. Please try again later.",
        ) from exc

    return CreateOrderResponse(
        order_id=order["id"],
        amount=order["amount"],
        currency=order["currency"],
        plan=req.plan.value,
        interval=req.interval.value,
    )


@router.post(
    "/verify-payment",
    response_model=VerifyPaymentResponse,
    responses=_ALL_ERRORS,
)
async def verify_payment(
    req: VerifyPaymentRequest,
    user: Annotated[User, Depends(current_active_user)],
) -> VerifyPaymentResponse:
    """Verify a completed Razorpay payment with full server-side validation.

    Steps (all must pass):
      1. Checkout feature-flag check.
      2. HMAC-SHA256 signature verification (constant-time).
      3. Fetch Razorpay order from provider API.
      4. Fetch Razorpay payment from provider API.
      5. Confirm payment.order_id matches submitted order_id.
      6. Confirm order notes.fincopilot_user_id == authenticated user.
      7. Confirm order notes plan/interval are valid FinCopilot values.
      8. Recompute expected amount from PRICE_CATALOG; confirm order/payment match.
      9. Confirm currency is INR.
     10. Confirm payment status is acceptable for the capture flow.
     11. Never activate entitlements here.
    """
    _require_checkout_enabled()

    if not req.razorpay_payment_id or not req.razorpay_order_id or not req.razorpay_signature:
        raise HTTPException(status_code=400, detail="Missing required payment fields.")

    settings = get_settings()
    key_secret = settings.razorpay_key_secret.get_secret_value()
    if not key_secret:
        logger.error("Razorpay key secret is not configured; cannot verify payment.")
        raise HTTPException(
            status_code=503,
            detail="Payment provider is not configured on this instance.",
        )

    # ── Step 2: HMAC-SHA256 signature (constant-time) ──────────────────────
    body = f"{req.razorpay_order_id}|{req.razorpay_payment_id}"
    generated_signature = hmac.new(
        key=key_secret.encode("utf-8"),
        msg=body.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(generated_signature, req.razorpay_signature):
        logger.warning(
            "Razorpay signature mismatch for user=%s order=%s",
            user.id, req.razorpay_order_id,
        )
        raise HTTPException(status_code=400, detail="Payment signature verification failed.")

    # ── Steps 3–10: Server-side deep validation via Razorpay API ───────────
    rzp_client = _get_razorpay_client()

    try:
        rzp_order = rzp_client.order.fetch(req.razorpay_order_id)
    except Exception as exc:
        logger.error(
            "Razorpay order fetch failed (order=%s user=%s): %s",
            req.razorpay_order_id, user.id, exc,
        )
        raise HTTPException(
            status_code=502,
            detail="Could not retrieve order from payment provider.",
        ) from exc

    try:
        rzp_payment = rzp_client.payment.fetch(req.razorpay_payment_id)
    except Exception as exc:
        logger.error(
            "Razorpay payment fetch failed (payment=%s user=%s): %s",
            req.razorpay_payment_id, user.id, exc,
        )
        raise HTTPException(
            status_code=502,
            detail="Could not retrieve payment from payment provider.",
        ) from exc

    # Step 5: payment must belong to this order
    if rzp_payment.get("order_id") != req.razorpay_order_id:
        logger.warning(
            "Payment order_id mismatch: payment.order_id=%s expected=%s user=%s",
            rzp_payment.get("order_id"), req.razorpay_order_id, user.id,
        )
        raise HTTPException(status_code=400, detail="Payment does not belong to this order.")

    # Step 6: order must belong to the authenticated user (via notes)
    notes = rzp_order.get("notes", {})
    order_user_id = notes.get("fincopilot_user_id", "")
    if order_user_id != str(user.id):
        logger.warning(
            "Order user mismatch: order.notes.user_id=%s authenticated=%s order=%s",
            order_user_id, user.id, req.razorpay_order_id,
        )
        raise HTTPException(status_code=400, detail="Order does not belong to this user.")

    # Step 7: notes must contain valid FinCopilot plan and interval
    try:
        order_plan = PlanId(notes.get("fincopilot_plan", ""))
        order_interval = BillingInterval(notes.get("fincopilot_interval", ""))
    except ValueError:
        logger.warning(
            "Invalid plan/interval in Razorpay order notes: plan=%s interval=%s order=%s",
            notes.get("fincopilot_plan"), notes.get("fincopilot_interval"),
            req.razorpay_order_id,
        )
        raise HTTPException(status_code=400, detail="Order contains invalid plan or interval.")

    # Step 8: recompute expected amount from PRICE_CATALOG (server-owned)
    expected_key = (order_plan, order_interval)
    expected_price = PRICE_CATALOG.get(expected_key)
    if expected_price is None or expected_price.amount_minor == 0:
        logger.warning(
            "Order notes reference an unpurchasable plan/interval: %s/%s order=%s",
            order_plan, order_interval, req.razorpay_order_id,
        )
        raise HTTPException(status_code=400, detail="Order plan/interval is not purchasable.")

    expected_amount = expected_price.amount_minor

    if rzp_order.get("amount") != expected_amount:
        logger.warning(
            "Order amount mismatch: order.amount=%s expected=%s order=%s user=%s",
            rzp_order.get("amount"), expected_amount, req.razorpay_order_id, user.id,
        )
        raise HTTPException(status_code=400, detail="Order amount does not match expected price.")

    if rzp_payment.get("amount") != expected_amount:
        logger.warning(
            "Payment amount mismatch: payment.amount=%s expected=%s payment=%s user=%s",
            rzp_payment.get("amount"), expected_amount, req.razorpay_payment_id, user.id,
        )
        raise HTTPException(status_code=400, detail="Payment amount does not match expected price.")

    # Step 9: currency must be INR
    if rzp_order.get("currency") != "INR":
        logger.warning(
            "Order currency mismatch: %s order=%s", rzp_order.get("currency"), req.razorpay_order_id,
        )
        raise HTTPException(status_code=400, detail="Order currency is not INR.")

    if rzp_payment.get("currency") != "INR":
        logger.warning(
            "Payment currency mismatch: %s payment=%s", rzp_payment.get("currency"), req.razorpay_payment_id,
        )
        raise HTTPException(status_code=400, detail="Payment currency is not INR.")

    # Step 10: payment status must be acceptable
    # Razorpay statuses: created, authorized, captured, refunded, failed
    # For manual-capture flow: "authorized" is acceptable.
    # For auto-capture flow: "captured" is required.
    # We accept both to handle either Razorpay dashboard capture setting.
    acceptable_statuses = {"authorized", "captured"}
    payment_status = rzp_payment.get("status", "")
    if payment_status not in acceptable_statuses:
        logger.warning(
            "Unacceptable payment status: %s payment=%s user=%s",
            payment_status, req.razorpay_payment_id, user.id,
        )
        raise HTTPException(
            status_code=400,
            detail=f"Payment status '{payment_status}' is not acceptable.",
        )

    logger.info(
        "Razorpay payment fully verified (user=%s order=%s payment=%s plan=%s interval=%s amount=%s). "
        "Entitlement activation pending webhook lifecycle.",
        user.id, req.razorpay_order_id, req.razorpay_payment_id,
        order_plan, order_interval, expected_amount,
    )

    # NOTE: Intentionally NO entitlement activation here.
    # Paid plan upgrades will be handled through the Razorpay webhook
    # lifecycle in a future milestone.
    return VerifyPaymentResponse(
        status="verified",
        message="Payment verified. Your subscription will be activated shortly.",
    )

