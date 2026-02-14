import razorpay
import hmac
import hashlib
import os
from datetime import datetime
from app.core.config import settings
from app.database.database import SessionLocal
from app.database import models
from app.repositories import BookingRepository
from app.repositories.notification_repository import NotificationRepository
from app.services.fcm_service import FCMService

class PaymentService:
    @staticmethod
    async def create_razorpay_order(booking_id: str):
        """Create a Razorpay order for ₹1."""
        try:
            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            
            # Amount is in paise (100 paise = ₹1)
            # Receipt length must be <= 40 chars
            short_receipt_id = f"rcpt_{booking_id[:30]}"
            data = {
                "amount": 100, 
                "currency": "INR",
                "receipt": short_receipt_id,
                "notes": {
                    "bookingId": booking_id
                }
            }
            order = client.order.create(data=data)
            return {
                "id": order["id"],
                "amount": order["amount"],
                "currency": order["currency"],
                "key": settings.RAZORPAY_KEY_ID
            }
        except Exception as e:
            print(f"[RAZORPAY_ORDER_ERROR] {e}")
            return {"error": str(e)}

    @staticmethod
    def verify_webhook_signature(payload: str, signature: str) -> bool:
        """Verify the signature from Razorpay."""
        try:
            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            # Verify signature using SDK
            client.utility.verify_webhook_signature(
                payload, 
                signature, 
                settings.PAYMENT_WEBHOOK_SECRET or "super_secret_dev_key"
            )
            return True
        except Exception as e:
            print(f"[RAZORPAY_SIG_ERROR] {e}")
            return False

    @staticmethod
    async def process_payment_success(booking_id: str, payment_id: str):
        """
        Atomic payment processing:
        1. Check idempotency (has this payment been handled?)
        2. Verify booking state (still confirmable?)
        3. Confirm booking & log action
        """
        db = SessionLocal()
        try:
            booking = db.query(models.Booking).filter(models.Booking.id == booking_id).first()
            if not booking:
                return {"status": "error", "message": "Booking not found"}

            # 1. Idempotency Check
            if booking.status == "CONFIRMED":
                return {"status": "success", "message": "Already confirmed"}

            # 2. Prevent "Ghost Bookings" (Payment success after expiry)
            if booking.status == "EXPIRED":
                # Implementation Note: In production, trigger an automatic refund here
                return {"status": "expired", "message": "Payment received after booking expired. Manual refund required."}

            if booking.status != "AWAITING_CUSTOMER_CONFIRMATION":
                return {"status": "error", "message": f"Illegal state: {booking.status}"}

            # 3. Confirm Booking Transactionally
            booking.status = "CONFIRMED"
            booking.isPaidConfirmation = True
            
            # Log the payment detail
            if not booking.notes:
                booking.notes = ""
            booking.notes += f"\\n[PAYMENT] Confirmed via webhook. ID: {payment_id} at {datetime.utcnow()}"

            db.commit()
            
            # --- Trigger Async Notifications (Outside transaction) ---
            try:
                # Fetch User models for FCM tokens
                customer_user = db.query(models.User).filter(models.User.id == booking.customerId).first()
                
                # Notify Customer
                if customer_user:
                    notification_data = {
                        "userId": booking.customerId,
                        "title": "Payment Successful! ✅",
                        "body": f"Your appointment for {booking.date} is confirmed.",
                        "type": "BOOKING_CONFIRMED",
                        "data": {"bookingId": booking.id, "status": "CONFIRMED"}
                    }
                    
                    # 1. Persist Notification (CRITICAL for polling)
                    NotificationRepository.create(notification_data)
                    print(f"✅ [PAYMENT] Persisted notification for customer {booking.customerId}")

                    # 2. Send FCM
                    if customer_user.fcmToken:
                        FCMService.send_to_user(
                            fcm_token=customer_user.fcmToken,
                            title=notification_data["title"],
                            body=notification_data["body"],
                            data=notification_data["data"]
                        )
                
                # Notify Barber
                staff = db.query(models.Staff).filter(models.Staff.id == booking.staffId).first()
                if staff:
                    staff_user = db.query(models.User).filter(models.User.id == staff.userId).first()
                    
                    if staff_user and staff_user.id:
                        staff_notif_data = {
                            "userId": staff_user.id,
                            "title": "New Confirmed Booking! ✂️",
                            "body": f"Payment received for {booking.timeSlot} on {booking.date}.",
                            "type": "NEW_CONFIRMED",
                            "data": {"bookingId": booking.id}
                        }
                        
                         # 1. Persist Notification
                        NotificationRepository.create(staff_notif_data)

                        # 2. Send FCM
                        if staff_user.fcmToken:
                            FCMService.send_to_user(
                                fcm_token=staff_user.fcmToken,
                                title=staff_notif_data["title"],
                                body=staff_notif_data["body"],
                                data=staff_notif_data["data"]
                            )
            except Exception as e:
                print(f"[PAYMENT_NOTIF] Error: {e}")

            return {"status": "success", "message": "Booking confirmed"}
        except Exception as e:
            db.rollback()
            return {"status": "error", "message": str(e)}
        finally:
            db.close()

    @staticmethod
    def verify_payment_signature(payment_id: str, order_id: str, signature: str) -> bool:
        """Verify the signature from the client (Razorpay Checkout)."""
        try:
            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            params_dict = {
                'razorpay_order_id': order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': signature
            }
            client.utility.verify_payment_signature(params_dict)
            return True
        except Exception as e:
            print(f"[RAZORPAY_PAY_SIG_ERROR] {e}")
            return False
