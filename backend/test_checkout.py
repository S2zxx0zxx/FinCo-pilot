import os
from fastapi.testclient import TestClient
from app.main import app

# Ensure env vars are set for testing
os.environ["RAZORPAY_KEY_ID"] = "rzp_test_Tf8nhZB0PfwLYu"
os.environ["RAZORPAY_KEY_SECRET"] = "h7A9CNmn87kI6XkMJ3E40stq"

client = TestClient(app)

def test_create_order():
    print("Testing /api/checkout/create-order ...")
    response = client.post(
        "/api/checkout/create-order",
        json={"amount": 50000, "currency": "INR", "receipt": "test_receipt_1"}
    )
    
    if response.status_code == 200:
        data = response.json()
        print("✅ Order Created successfully!")
        print("Order ID:", data["order_id"])
        print("Amount:", data["amount"])
        return data["order_id"]
    else:
        print("❌ Failed to create order:", response.json())
        return None

if __name__ == "__main__":
    test_create_order()
