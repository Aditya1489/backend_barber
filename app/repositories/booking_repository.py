"""
Booking repository - handles all booking-related database operations.
"""
from app.repositories.base import BaseRepository
from app.database import models
from datetime import datetime, timedelta
from sqlalchemy import func


class BookingRepository(BaseRepository):
    """Repository for Booking entity operations."""
    
    @classmethod
    def create(cls, booking_data: dict):
        """Create a new booking with duration calculation and UTC timestamps."""
        with cls.get_session() as db:
            # 1. Fetch actual services to calculate price and duration
            service_ids = booking_data.get("services", [])
            services = db.query(models.Service).filter(models.Service.id.in_(service_ids)).all()
            
            total_duration = sum(s.duration for s in services)
            total_amount = sum(s.price for s in services)
            
            # 2. Parse startTime and calculate endTime
            # Assumes format "YYYY-MM-DD HH:MM AM/PM" from frontend for now
            start_str = f"{booking_data['date']} {booking_data['timeSlot']}"
            try:
                start_dt = datetime.strptime(start_str, "%Y-%m-%d %I:%M %p")
                end_dt = start_dt + timedelta(minutes=total_duration)
            except ValueError:
                # Fallback for ISO format or other variations if they occur
                start_dt = datetime.fromisoformat(booking_data['date']) # Simpler fallback
                end_dt = start_dt + timedelta(minutes=total_duration)

            # 3. Update data with calculated values
            booking_data.update({
                "totalAmount": total_amount,
                "totalDuration": total_duration,
                "startTime": start_dt,
                "endTime": end_dt
            })

            # 4. Check for staff overlap
            if cls.check_staff_overlap(db, booking_data['staffId'], start_dt, end_dt):
                from fastapi import HTTPException
                raise HTTPException(status_code=400, detail="The selected barber is already booked for this time range.")

            booking = models.Booking(**booking_data)
            db.add(booking)
            db.commit()
            db.refresh(booking)
            return {c.name: getattr(booking, c.name) for c in booking.__table__.columns}

    @classmethod
    def check_staff_overlap(cls, db, staff_id: str, new_start: datetime, new_end: datetime, exclude_id: str = None):
        """
        Production-grade overlap check:
        new_start < existing_end AND new_end > existing_start
        """
        active_statuses = ["AWAITING_CUSTOMER_CONFIRMATION", "CONFIRMED", "IN_PROGRESS", "PENDING"]
        query = db.query(models.Booking).filter(
            models.Booking.staffId == staff_id,
            models.Booking.status.in_(active_statuses),
            models.Booking.startTime < new_end,
            models.Booking.endTime > new_start
        )
        if exclude_id:
            query = query.filter(models.Booking.id != exclude_id)
        
        return query.first() is not None
    
    @classmethod
    def check_customer_overlap(cls, customer_id: str, new_start: datetime, new_end: datetime):
        """Check if a customer has an overlapping active booking."""
        with cls.get_session() as db:
            active_statuses = ["AWAITING_CUSTOMER_CONFIRMATION", "CONFIRMED", "IN_PROGRESS", "PENDING"]
            overlap = db.query(models.Booking).filter(
                models.Booking.customerId == customer_id,
                models.Booking.status.in_(active_statuses),
                models.Booking.startTime < new_end,
                models.Booking.endTime > new_start
            ).first()
            return overlap is not None
    
    @classmethod
    def get_all(cls, customer_id=None, staff_id=None, shop_id=None, status=None, limit=None):
        """Get bookings with optional filters."""
        with cls.get_session() as db:
            # Use LEFT JOIN (outerjoin) to ensure bookings are returned even if user data is missing
            query = db.query(models.Booking, models.User).outerjoin(
                models.User, models.Booking.customerId == models.User.id
            )
            if customer_id:
                query = query.filter(models.Booking.customerId == customer_id)
            if staff_id:
                query = query.filter(models.Booking.staffId == staff_id)
            if shop_id:
                query = query.filter(models.Booking.shopId == shop_id)
            if status:
                query = query.filter(models.Booking.status == status)
            
            # Sort by date and time (newest first)
            query = query.order_by(models.Booking.date.desc(), models.Booking.timeSlot.desc())
            
            if limit:
                query = query.limit(limit)
            
            results = query.all()
            bookings_with_customers = []
            for booking, user in results:
                b_dict = {c.name: getattr(booking, c.name) for c in booking.__table__.columns}
                
                # Defensive handling for missing user data
                if user:
                    b_dict["customerName"] = user.name
                    
                    # Safely get profile photo from various profiles
                    photo = None
                    if user.customer_profile:
                        photo = user.customer_profile.profile_photo
                    elif user.owner_profile:
                        photo = user.owner_profile.profile_photo
                    elif user.staff_profile:
                        # staff_profile is a list/relationship
                        p = user.staff_profile[0] if isinstance(user.staff_profile, list) and user.staff_profile else user.staff_profile
                        if p: photo = getattr(p, 'imageUrl', None)
                    
                    b_dict["customerPhoto"] = photo
                else:
                    # Log missing user data for debugging
                    print(f"⚠️ [BOOKING] User not found for customerId: {booking.customerId}")
                    b_dict["customerName"] = "Unknown Customer"
                    b_dict["customerPhoto"] = None
                
                bookings_with_customers.append(b_dict)
            
            return bookings_with_customers
    
    @classmethod
    def get_by_id(cls, booking_id: str):
        """Get a specific booking by ID."""
        with cls.get_session() as db:
            booking = db.query(models.Booking).filter(models.Booking.id == booking_id).first()
            if not booking:
                return None
            return {c.name: getattr(booking, c.name) for c in booking.__table__.columns}
    
    @classmethod
    def update(cls, booking_id: str, update_data: dict):
        """Update a booking."""
        with cls.get_session() as db:
            booking = db.query(models.Booking).filter(models.Booking.id == booking_id).first()
            if booking:
                for key, value in update_data.items():
                    if hasattr(booking, key):
                        setattr(booking, key, value)
                db.commit()
                db.refresh(booking)
                return {c.name: getattr(booking, c.name) for c in booking.__table__.columns}
            return None


# Backward-compatible function exports
def create_booking(booking_data: dict):
    """Create a new booking. (Backward compatible)"""
    return BookingRepository.create(booking_data)


def get_bookings(customer_id=None, staff_id=None, shop_id=None, status=None, limit=None):
    """Get bookings with filters. (Backward compatible)"""
    return BookingRepository.get_all(customer_id, staff_id, shop_id, status, limit)


def get_booking_by_id(booking_id: str):
    """Get booking by ID. (Backward compatible)"""
    return BookingRepository.get_by_id(booking_id)


def update_booking(booking_id: str, update_data: dict):
    """Update a booking. (Backward compatible)"""
    return BookingRepository.update(booking_id, update_data)
