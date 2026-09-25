import hmac
import hashlib
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

try:
    import razorpay  # type: ignore[import-untyped]
    RAZORPAY_AVAILABLE = True
except ImportError:
    razorpay = None  # type: ignore[assignment]
    RAZORPAY_AVAILABLE = False

router = APIRouter(prefix="/api/checkout", tags=["checkout"])

_ERR_500 = {500: {"description": "Internal server error / Razorpay credentials not configured"}}
_ERR_400 = {400: {"description": "Bad request"}}
_ERR_401 = {401: {"description": "Razorpay authentication failure"}}
_ERR_CHECKOUT = {400: {"description": "Bad request"}, 401: {"description": "Auth failure"}, 500: {"description": "Server error"}}


class CreateOrderRequest(BaseModel):
    amount: int  # in paise
    currency: str = "INR"
    receipt: str


class VerifyPaymentRequest(BaseModel):
    razorpay_payment_id: str
    razorpay_order_id: str
    razorpay_signature: str


def _get_keys() -> tuple[str, str]:
    """Read Razorpay keys directly from env — bypasses lru_cache so Docker
    env-var changes are always picked up without restarting the worker."""
    key_id = os.environ.get("RAZORPAY_KEY_ID", "")
    key_secret = os.environ.get("RAZORPAY_KEY_SECRET", "")
    if not key_id or not key_secret:
        raise HTTPException(
            status_code=500,
            detail=f"Razorpay credentials not configured (key_id present: {bool(key_id)})"
        )
    return key_id, key_secret


def _get_razorpay_client():  # type: ignore[return]
    if not RAZORPAY_AVAILABLE:
        raise HTTPException(
            status_code=500,
            detail="razorpay package not installed in this environment"
        )
    key_id, key_secret = _get_keys()
    return razorpay.Client(auth=(key_id, key_secret)), key_secret


@router.post("/create-order", responses=_ERR_CHECKOUT)
async def create_order(req: CreateOrderRequest):
    if req.amount < 100:
        raise HTTPException(status_code=400, detail="Minimum amount is 100 paise")

    try:
        client, _ = _get_razorpay_client()
        order_data = {
            "amount": req.amount,
            "currency": req.currency,
            "receipt": req.receipt
        }
        order = client.order.create(data=order_data)
        return {
            "order_id": order["id"],
            "amount": order["amount"],
            "currency": order["currency"]
        }
    except HTTPException:
        raise
    except Exception as e:
        error_name = type(e).__name__
        error_msg = str(e)
        if "Authentication" in error_name or "auth" in error_msg.lower() or "401" in error_msg:
            raise HTTPException(status_code=401, detail=f"Razorpay auth failure: {error_msg}")
        raise HTTPException(status_code=500, detail=f"Failed to create order: {error_name}: {error_msg}")


@router.post("/verify-payment", responses={**_ERR_400, **_ERR_401, **_ERR_500})
async def verify_payment(req: VerifyPaymentRequest):
    if not req.razorpay_payment_id or not req.razorpay_order_id or not req.razorpay_signature:
        raise HTTPException(status_code=400, detail="Missing fields")

    _, key_secret = _get_keys()

    # Algorithm: HMAC-SHA256(order_id + "|" + payment_id, KEY_SECRET)
    generated_signature = hmac.new(
        key=key_secret.encode('utf-8'),
        msg=f"{req.razorpay_order_id}|{req.razorpay_payment_id}".encode('utf-8'),
        digestmod=hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(generated_signature, req.razorpay_signature):
        raise HTTPException(status_code=400, detail="Signature mismatch")

    return {"status": "success", "message": "Payment verified successfully"}
