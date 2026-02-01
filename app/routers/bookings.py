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
    get_staff_full_profile
)

# Request/Response Models
class CreateBookingRequest(BaseModel):
    shopId: str
    staffId: str
    customerId: str
    services: List[str]
    date: str
    timeSlot: str
    notes: Optional[str] = ""

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
        "notes": booking.notes or ""
    }
    
    try:
        new_booking = create_booking(booking_data)
        
        # --- TRIGGER NOTIFICATION FOR STAFF ---
        try:
            # 1. Get Customer Name
            customer = get_user_by_id(booking.customerId)
            customer_name = customer["name"] if customer else "A Customer"
            
            # 2. Get Staff's User ID (to send notification to)
            # Booking has `staffId` (profile ID), notification needs `userId`
            staff_profile = get_staff_full_profile(booking.staffId)
            
            if staff_profile and staff_profile.get("userId"):
                staff_user_id = staff_profile["userId"]
                
                # 3. Create Notification
                create_notification({
                    "userId": staff_user_id,
                    "title": "New Appointment Request",
                    "body": f"You have a new booking request from {customer_name} on {booking.date} at {booking.timeSlot}.",
                    "type": "APPOINTMENT",
                    "data": {"bookingId": new_booking["id"]}
                })
                print(f"[NOTIF] Sent appointment notification to staff user {staff_user_id}")
            else:
                print(f"[NOTIF] Could not find staff profile or userId for staffId: {booking.staffId}")

        except Exception as e:
            print(f"[NOTIF] Failed to send notification: {e}")
            import traceback
            with open("notification_error.log", "w") as f:
                f.write(traceback.format_exc())
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
    status: Optional[str] = Query(None)
):
    """Get bookings with optional filters"""
    return get_bookings(customer_id, staff_id, shop_id, status)

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
    """Update booking status (PENDING, ACCEPTED, CANCELLED, COMPLETED)"""
    
    valid_statuses = ["PENDING", "ACCEPTED", "CANCELLED", "COMPLETED", "NO_SHOW"]
    if new_status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        )
    
    updated = update_booking(booking_id, {"status": new_status})
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )
    
    # --- TRIGGER NOTIFICATION FOR CUSTOMER ---
    try:
        title = "Appointment Status Updated"
        body = f"Your appointment has been {new_status.lower()}."
        
        if new_status == "ACCEPTED":
            title = "Appointment Confirmed! ✅"
            body = f"Great news! Your appointment on {updated['date']} at {updated['timeSlot']} has been accepted."
        elif new_status == "CANCELLED":
            title = "Appointment Cancelled ❌"
            body = f"We're sorry, your appointment on {updated['date']} at {updated['timeSlot']} has been cancelled."
        elif new_status == "COMPLETED":
            title = "All Done! ✨"
            body = f"Your appointment on {updated['date']} is complete. We hope you enjoyed the service!"
        elif new_status == "NO_SHOW":
            title = "Appointment Missed ❓"
            body = f"It looks like you missed your appointment on {updated['date']}. Please contact us if you'd like to reschedule."
        
        create_notification({
            "userId": updated["customerId"],
            "title": title,
            "body": body,
            "type": "APPOINTMENT_STATUS",
            "data": {"bookingId": booking_id, "status": new_status}
        })
        print(f"[NOTIF] Sent status update notification to customer {updated['customerId']}")
    except Exception as e:
        print(f"[NOTIF] Failed to send status update notification: {e}")
    # ----------------------------------------
    
    return {
        "message": f"Booking status updated to {new_status}",
        "booking": updated
    }

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
    """Get available time slots for a specific date"""
    
    # Mock available slots
    all_slots = [
        "09:00 AM", "09:30 AM", "10:00 AM", "10:30 AM", "11:00 AM", "11:30 AM",
        "12:00 PM", "12:30 PM", "01:00 PM", "01:30 PM", "02:00 PM", "02:30 PM",
        "03:00 PM", "03:30 PM", "04:00 PM", "04:30 PM", "05:00 PM", "05:30 PM"
    ]
    
    # Get booked slots for this date
    booked_slots = [
        b["timeSlot"] for b in get_bookings(staff_id=staff_id, status="ACCEPTED") # Or PENDING/ACCEPTED
        if b["date"] == date
    ]
    
    # Return available slots
    available_slots = [slot for slot in all_slots if slot not in booked_slots]
    
    return {
        "date": date,
        "shopId": shop_id,
        "staffId": staff_id,
        "availableSlots": available_slots,
        "bookedSlots": booked_slots
    }
