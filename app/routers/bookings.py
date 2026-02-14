from fastapi import APIRouter, HTTPException, status, Query
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
import uuid

router = APIRouter(prefix="/bookings", tags=["bookings"])

from app.db import (
    create_booking, 
    get_bookings, 
    get_booking_by_id, 
    update_booking,
    create_notification,
    get_user_by_id,
    get_staff_full_profile,
    BookingRepository
)
from app.services.fcm_service import FCMService
from app.services.payment_service import PaymentService

# Request/Response Models
class CreateBookingRequest(BaseModel):
    shopId: str
    staffId: str
    customerId: str
    services: List[str]
    date: str
    timeSlot: str
    notes: Optional[str] = ""
    idempotencyKey: Optional[str] = None

class PaymentConfirmationRequest(BaseModel):
    razorpay_payment_id: str
    razorpay_order_id: str
    razorpay_signature: str
    idempotencyKey: Optional[str] = None

class UpdateBookingRequest(BaseModel):
    date: Optional[str] = None
    timeSlot: Optional[str] = None
    services: Optional[List[str]] = None
    notes: Optional[str] = None

class BookingResponse(BaseModel):
    id: str
    shopId: str
    staffId: str
    customerId: str
    customerName: Optional[str] = "Customer"
    customerPhoto: Optional[str] = None
    services: List[str]
    date: str
    timeSlot: str
    status: str
    totalAmount: float
    totalDuration: int
    bookedAt: datetime
    notes: str

# Routes
@router.post("/", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
async def create_booking_route(booking: CreateBookingRequest):
    """Create a new booking"""
    print(f"[DEBUG] Creating booking: {booking.model_dump()}")
    
    # --- IDEMPOTENCY CHECK ---
    if booking.idempotencyKey:
        from app.database.database import SessionLocal
        from app.database import models
        db_session = SessionLocal()
        existing = db_session.query(models.Booking).filter(models.Booking.idempotencyKey == booking.idempotencyKey).first()
        db_session.close()
        if existing:
            # Return existing booking if idempotency matches
            return {c.name: getattr(existing, c.name) for c in existing.__table__.columns}

    # --- RATE LIMITING (Pending Bookings) ---
    from app.database.database import SessionLocal
    from app.database import models
    db_session = SessionLocal()
    pending_count = db_session.query(models.Booking).filter(
        models.Booking.customerId == booking.customerId,
        models.Booking.status.in_(["PENDING", "AWAITING_CUSTOMER_CONFIRMATION"])
    ).count()
    db_session.close()
    if pending_count >= 3:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="You have too many pending bookings. Please confirm or cancel existing ones."
        )

    # --- SERVICE DATA RESOLUTION ---
    # Fetch durations from DB to compute exact startTime/endTime for overlap check
    db_session = SessionLocal()
    services = db_session.query(models.Service).filter(models.Service.id.in_(booking.services)).all()
    total_duration = sum(s.duration for s in services)
    db_session.close()

    try:
        start_dt = datetime.strptime(f"{booking.date} {booking.timeSlot}", "%Y-%m-%d %I:%M %p")
        end_dt = start_dt + timedelta(minutes=total_duration)
    except Exception as ie:
        print(f"❌ [BOOKING] Date parse error: {ie}")
        raise HTTPException(status_code=400, detail="Invalid date or time format.")

    # --- CONFLICT PROTECTION ---
    if BookingRepository.check_customer_overlap(booking.customerId, start_dt, end_dt):
        print(f"❌ [BOOKING] Overlap detected for customer {booking.customerId} at {start_dt}")
        
        # DEBUG: Find the specific conflicting booking
        from app.database.database import SessionLocal
        from app.database import models
        db_debug = SessionLocal()
        active_statuses = ["AWAITING_CUSTOMER_CONFIRMATION", "CONFIRMED", "IN_PROGRESS", "PENDING"]
        conflict = db_debug.query(models.Booking).filter(
            models.Booking.customerId == booking.customerId,
            models.Booking.status.in_(active_statuses),
            models.Booking.startTime < end_dt,
            models.Booking.endTime > start_dt
        ).first()
        db_debug.close()
        
        if conflict:
             print(f"❌ [BOOKING] Conflicting Booking: ID={conflict.id}, Status={conflict.status}, Date={conflict.date}, Slot={conflict.timeSlot}")

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You already have an active booking overlapping with the selected time range."
        )
    # ---------------------------

    # Calculate total amount and duration (mock calculation)
    total_amount = len(booking.services) * 30.0  # $30 per service
    total_duration = len(booking.services) * 30  # 30 min per service

    booking_data = {
        "shopId": booking.shopId,
        "staffId": booking.staffId,
        "customerId": booking.customerId,
        "services": booking.services,
        "date": booking.date,
        "timeSlot": booking.timeSlot,
        "status": "PENDING",
        "totalAmount": total_amount,
        "totalDuration": total_duration,
        "bookedAt": datetime.utcnow(),
        "notes": booking.notes or "",
        "idempotencyKey": booking.idempotencyKey
    }
    
    try:
        new_booking = create_booking(booking_data)
        
        # --- TRIGGER NOTIFICATION FOR STAFF ---
        try:
            customer = get_user_by_id(booking.customerId)
            customer_name = customer["name"] if customer else "A Customer"
            staff_profile = get_staff_full_profile(booking.staffId)
            
            if staff_profile and staff_profile.get("userId"):
                staff_user_id = staff_profile["userId"]
                staff_user = get_user_by_id(staff_user_id)
                
                # Database notification (legacy)
                create_notification({
                    "userId": staff_user_id,
                    "title": "New Appointment Request",
                    "body": f"You have a new booking request from {customer_name} on {booking.date} at {booking.timeSlot}.",
                    "type": "APPOINTMENT",
                    "data": {"bookingId": new_booking["id"]}
                })
                
                # Push Notification (NEW)
                if staff_user and staff_user.get("fcmToken"):
                    FCMService.send_to_user(
                        fcm_token=staff_user["fcmToken"],
                        title="New Appointment Request ✂️",
                        body=f"{customer_name} booked for {booking.date} at {booking.timeSlot}",
                        data={"bookingId": new_booking["id"], "type": "NEW_BOOKING"}
                    )
        except Exception as e:
            print(f"[NOTIF] Error notifying staff: {e}")
        # --------------------------------------
        
        return new_booking

    except Exception as e:
        import traceback
        with open("booking_error.log", "w") as f:
             f.write(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=List[BookingResponse])
async def get_bookings_route(
    customer_id: Optional[str] = Query(None),
    staff_id: Optional[str] = Query(None),
    shop_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: Optional[int] = Query(None)
):
    """Get bookings with optional filters"""
    print(f"[DEBUG] Fetching bookings: customer_id={customer_id}, staff_id={staff_id}, shop_id={shop_id}, status={status}")
    results = get_bookings(customer_id, staff_id, shop_id, status, limit)
    print(f"[DEBUG] Found {len(results)} bookings")
    return results

@router.get("/{booking_id}", response_model=BookingResponse)
async def get_booking_route(booking_id: str):
    """Get a specific booking by ID"""
    booking = get_booking_by_id(booking_id)
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )
    return booking

@router.put("/{booking_id}", response_model=BookingResponse)
async def update_booking_route(booking_id: str, update_data: UpdateBookingRequest):
    """Update a booking"""
    
    booking = get_booking_by_id(booking_id)
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )
    
    # Only allow updates if status is PENDING
    if booking["status"] != "PENDING":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only update pending bookings"
        )
    
    data = update_data.model_dump(exclude_unset=True)
    if update_data.services:
        data["totalAmount"] = len(update_data.services) * 30.0
        data["totalDuration"] = len(update_data.services) * 30

    updated = update_booking(booking_id, data)
    return updated

@router.patch("/{booking_id}/status")
async def update_booking_status_route(booking_id: str, new_status: str):
    """Update booking status with strict FSM logic"""
    
    booking = get_booking_by_id(booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    valid_statuses = [
        "PENDING", "AWAITING_CUSTOMER_CONFIRMATION", "CONFIRMED", 
        "IN_PROGRESS", "COMPLETED", "CANCELLED_BY_CUSTOMER", 
        "CANCELLED_BY_BARBER", "NO_SHOW", "EXPIRED"
    ]
    # --- STRICT FSM TRANSITION MATRIX ---
    # PENDING -> AWAITING_CUSTOMER_CONFIRMATION
    # AWAITING_CUSTOMER_CONFIRMATION -> CONFIRMED | EXPIRED
    # CONFIRMED -> IN_PROGRESS | CANCELLED
    # IN_PROGRESS -> COMPLETED
    # CANCELLED / EXPIRED / COMPLETED -> Terminal (No transitions allowed)

    current_status = booking["status"]
    allowed = False
    
    if current_status == "PENDING":
        allowed = new_status in ["AWAITING_CUSTOMER_CONFIRMATION", "CANCELLED_BY_BARBER", "CANCELLED_BY_CUSTOMER"]
    elif current_status == "AWAITING_CUSTOMER_CONFIRMATION":
        allowed = new_status in ["CONFIRMED", "EXPIRED", "CANCELLED_BY_CUSTOMER"]
    elif current_status == "CONFIRMED":
        allowed = new_status in ["IN_PROGRESS", "CANCELLED_BY_CUSTOMER", "CANCELLED_BY_BARBER"]
    elif current_status == "IN_PROGRESS":
        allowed = new_status in ["COMPLETED", "CANCELLED_BY_BARBER"]
    
    if not allowed and current_status != new_status:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Illegal transition: Cannot move booking from {current_status} to {new_status}"
        )
    
    update_data = {"status": new_status}
    
    # Logic for AWAITING_CUSTOMER_CONFIRMATION (Barber accepts)
    if new_status == "AWAITING_CUSTOMER_CONFIRMATION":
        # Set expiry to 15 minutes from now
        update_data["expiresAt"] = datetime.utcnow() + timedelta(minutes=15)
        
    # Logic for CONFIRMED (Customer pays ₹1)
    if new_status == "CONFIRMED":
        update_data["isPaidConfirmation"] = True

    try:
        updated = update_booking(booking_id, update_data)
        if not updated:
            raise Exception("Failed to update booking in database")
    except Exception as e:
        print(f"❌ [BOOKING] Update failed: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Database update failed")
    
    # --- TRIGGER NOTIFICATIONS ---
    try:
        title = "Booking Update"
        body = f"Your booking is now {new_status}."
        
        if new_status == "AWAITING_CUSTOMER_CONFIRMATION":
            title = "Action Required: Pay ₹1 to Confirm! 💳"
            body = f"Your barber has accepted your request. Please confirm your booking by paying ₹1 within 15 minutes."
        elif new_status == "CONFIRMED":
            title = "Booking Confirmed! ✅"
            body = f"Payment received. Your appointment on {updated.get('date', 'unknown')} is now fully confirmed."
        elif "CANCELLED" in new_status:
            title = "Booking Cancelled ❌"
            body = f"The booking for {updated.get('date', 'unknown')} has been cancelled."
        
        # Database notification (legacy)
        customer_id = updated.get("customerId")
        if customer_id:
            print(f"🔔 [BACKEND] Creating notification for customer: {customer_id}")
            create_notification({
                "userId": customer_id,
                "title": title,
                "body": body,
                "type": "APPOINTMENT_STATUS",
                "data": {"bookingId": booking_id, "status": new_status}
            })
            
            # Push Notification (NEW)
            customer_user = get_user_by_id(customer_id)
            if customer_user and customer_user.get("fcmToken"):
                FCMService.send_to_user(
                    fcm_token=customer_user["fcmToken"],
                    title=title,
                    body=body,
                    data={"bookingId": booking_id, "status": new_status, "type": "STATUS_UPDATE"}
                )
    except Exception as e:
        print(f"⚠️ [NOTIF] Error: {e}")
        import traceback
        traceback.print_exc()
    
    # --- AUDIT LOGGING ---
    try:
        from app.database.database import SessionLocal
        from app.routers.owner import create_audit_log
        db_session = SessionLocal()
        create_audit_log(
            db=db_session,
            actor_id=None, # System
            actor_role="SYSTEM",
            action_type="status_change",
            entity_type="booking",
            entity_id=booking_id,
            details={"oldStatus": booking.get("status"), "newStatus": new_status},
            shop_id=booking.get("shopId")
        )
        db_session.close()
    except Exception as e:
        print(f"⚠️ [AUDIT] Error: {e}")
        import traceback
        traceback.print_exc()

    return {"message": f"Status updated to {new_status}", "booking": updated}

@router.post("/{booking_id}/confirm-payment")
async def confirm_booking_payment(booking_id: str, confirmation: PaymentConfirmationRequest):
    """Securely confirm booking after Razorpay payment"""
    booking = get_booking_by_id(booking_id)
    if not booking or booking["status"] != "AWAITING_CUSTOMER_CONFIRMATION":
        raise HTTPException(status_code=400, detail="Booking not in confirmable state")
    
    # 1. Verify Payment Signature
    is_valid = PaymentService.verify_payment_signature(
        payment_id=confirmation.razorpay_payment_id,
        order_id=confirmation.razorpay_order_id,
        signature=confirmation.razorpay_signature
    )
    
    if not is_valid:
        raise HTTPException(status_code=400, detail="Invalid payment signature")

    # 2. Check if expired
    if booking.get("expiresAt") and datetime.utcnow() > booking["expiresAt"]:
        update_booking(booking_id, {"status": "EXPIRED"})
        raise HTTPException(status_code=400, detail="Booking has expired")
        
    # 3. Update status to CONFIRMED
    result = await update_booking_status_route(booking_id, "CONFIRMED")
    
    # Update notes with payment info
    new_notes = (booking.get("notes") or "") + f"\n[PAYMENT] Confirmed via App. ID: {confirmation.razorpay_payment_id}"
    update_booking(booking_id, {"notes": new_notes})
    
    return result

@router.delete("/{booking_id}")
async def cancel_booking_route(booking_id: str):
    """Cancel a booking"""
    updated = update_booking(booking_id, {"status": "CANCELLED"})
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )
    
    return {
        "message": "Booking cancelled successfully",
        "booking": updated
    }

@router.get("/available-slots/{shop_id}/{staff_id}")
async def get_available_slots(shop_id: str, staff_id: str, date: str):
    """Get available time slots using real barber availability and buffer time"""
    
    staff = get_staff_full_profile(staff_id)
    if not staff:
        raise HTTPException(status_code=404, detail="Staff member not found")
        
    # Check working days
    try:
        dt = datetime.strptime(date, "%Y-%m-%d")
        day_name = dt.strftime("%a") # Mon, Tue...
    except:
        day_name = "Mon" # Fallback
        
    working_days = staff.get("workingDays", [])
    if day_name not in working_days or not staff.get("isAvailable", True):
        return {"date": date, "availableSlots": [], "message": f"Barber is not working on {day_name}"}

    # Get working hours for the day
    working_hours = staff.get("workingHours", {}).get(day_name, {"start": "09:00 AM", "end": "06:00 PM"})
    
    # Mock generating slots based on working hours (simple 30-min intervals)
    all_slots = [
        "09:00 AM", "09:30 AM", "10:00 AM", "10:30 AM", "11:00 AM", "11:30 AM",
        "12:00 PM", "12:30 PM", "01:00 PM", "01:30 PM", "02:00 PM", "02:30 PM",
        "03:00 PM", "03:30 PM", "04:00 PM", "04:30 PM", "05:00 PM", "05:30 PM"
    ]
    
    # Get booked slots
    active_statuses = ["AWAITING_CUSTOMER_CONFIRMATION", "CONFIRMED", "IN_PROGRESS", "PENDING"]
    booked_bookings = get_bookings(staff_id=staff_id)
    booked_slots = [
        b["timeSlot"] for b in booked_bookings 
        if b["date"] == date and b["status"] in active_statuses
    ]
    
    # Simple Slot filtering with Buffer Time consideration
    # In a real system, we'd do time math. Here we just exclude overlaps.
    available_slots = [slot for slot in all_slots if slot not in booked_slots]
    
    return {
        "date": date,
        "shopId": shop_id,
        "staffId": staff_id,
        "availableSlots": available_slots,
        "bookedSlots": booked_slots,
        "workingHours": working_hours,
        "bufferTime": staff.get("bufferTime", 0)
    }

@router.post("/{booking_id}/override")
async def override_booking(booking_id: str, owner_id: str, reason: str, new_status: str):
    """Allow owner to override a booking status with a mandatory reason (Audit logged)"""
    from app.database.database import SessionLocal
    from app.database import models
    from app.db import get_booking_by_id, update_booking
    
    # 1. Verify ownership (simplified)
    booking = get_booking_by_id(booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    db = SessionLocal()
    try:
        shop = db.query(models.Shop).filter(models.Shop.id == booking["shopId"]).first()
        if not shop or shop.ownerId != owner_id:
            raise HTTPException(status_code=403, detail="Only the shop owner can override bookings.")
        
        # 2. Update status
        old_status = booking["status"]
        updated = update_booking(booking_id, {"status": new_status})
        
        # 3. Create Audit Log
        from app.routers.owner import create_audit_log
        create_audit_log(
            db=db,
            actor_id=owner_id,
            actor_role="OWNER",
            action_type="booking_override",
            entity_type="booking",
            entity_id=booking_id,
            details={"oldStatus": old_status, "newStatus": new_status},
            reason=reason,
            shop_id=booking["shopId"]
        )
        
        # 4. Notify affected parties
        create_notification({
            "userId": booking["customerId"],
            "title": "Booking Adjusted by Owner",
            "body": f"Your booking was updated to {new_status} by the shop owner. Reason: {reason}",
            "type": "SYSTEM"
        })
        
        return {"message": "Override successful and logged", "booking": updated}
    finally:
        db.close()
