import hmac
import hashlib
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import razorpay

from app.core.config import get_settings

router = APIRouter(prefix="/api/checkout", tags=["checkout"])

class CreateOrderRequest(BaseModel):
    amount: int  # in paise
    currency: str = "INR"
    receipt: str

class VerifyPaymentRequest(BaseModel):
    razorpay_payment_id: str
    razorpay_order_id: str
    razorpay_signature: str

def get_razorpay_client():
    settings = get_settings()
    if not settings.razorpay_key_id or not settings.razorpay_key_secret.get_secret_value():
        raise HTTPException(status_code=500, detail="Razorpay credentials not configured")
    return razorpay.Client(auth=(settings.razorpay_key_id, settings.razorpay_key_secret.get_secret_value()))

@router.post("/create-order")
async def create_order(req: CreateOrderRequest):
    if req.amount < 100:
        raise HTTPException(status_code=400, detail="Minimum amount is 100 paise")

    try:
        client = get_razorpay_client()
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
    except razorpay.errors.SignatureVerificationError:
        raise HTTPException(status_code=401, detail="Signature verification failed")
    except razorpay.errors.BadRequestError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        if "AuthenticationError" in type(e).__name__:
            raise HTTPException(status_code=401, detail="Razorpay auth failure")
        raise HTTPException(status_code=500, detail="Failed to create order")

@router.post("/verify-payment")
async def verify_payment(req: VerifyPaymentRequest):
    settings = get_settings()
    if not req.razorpay_payment_id or not req.razorpay_order_id or not req.razorpay_signature:
        raise HTTPException(status_code=400, detail="Missing fields")

    secret = settings.razorpay_key_secret.get_secret_value()
    
    # Algorithm: HMAC-SHA256(order_id + "|" + payment_id, KEY_SECRET)
    generated_signature = hmac.new(
        key=secret.encode('utf-8'),
        msg=f"{req.razorpay_order_id}|{req.razorpay_payment_id}".encode('utf-8'),
        digestmod=hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(generated_signature, req.razorpay_signature):
        raise HTTPException(status_code=400, detail="Signature mismatch")
        
    return {"status": "success", "message": "Payment verified successfully"}
