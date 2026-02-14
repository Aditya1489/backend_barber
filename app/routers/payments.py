from fastapi import APIRouter, Header, Request, HTTPException, status
from app.services.payment_service import PaymentService
import json

router = APIRouter(prefix="/payments", tags=["payments"])

@router.post("/create-order")
async def create_payment_order(booking_id: str):
    """
    Create a Razorpay Order for a ₹1 confirmation fee.
    """
    print(f"💰 [PAYMENT] Received create-order request for booking_id: {booking_id}")
    order = await PaymentService.create_razorpay_order(booking_id)
    print(f"💰 [PAYMENT] Order creation result: {order}")
    if "error" in order:
        print(f"❌ [PAYMENT] Error creating order: {order['error']}")
        raise HTTPException(status_code=400, detail=order["error"])
    return order

@router.post("/webhook")
async def payment_webhook(
    request: Request,
    x_signature: str = Header(None)
):
    """
    Production-grade payment webhook handler.
    1. Reconstruct payload & verify signature
    2. Atomic booking confirmation
    """
    if not x_signature:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing signature")

    payload = await request.body()
    payload_str = payload.decode()

    # 1. VERIFY SIGNATURE
    if not PaymentService.verify_webhook_signature(payload_str, x_signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature")

    try:
        data = json.loads(payload_str)
        event_type = data.get("type")
        
        # 2. HANDLE PAYMENT SUCCESS
        if event_type == "payment.succeeded":
            booking_id = data.get("bookingId")
            payment_id = data.get("paymentId") # Provider's transaction ID
            
            if not booking_id:
                return {"status": "ignored", "reason": "No bookingId in payload"}

            result = await PaymentService.process_payment_success(booking_id, payment_id)
            
            if result["status"] == "error":
                raise HTTPException(status_code=400, detail=result["message"])
            
            return result
            
        return {"status": "ignored", "event": event_type}

    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    except Exception as e:
        print(f"[WEBHOOK_ERROR] {e}")
        raise HTTPException(status_code=500, detail="Internal processing error")
