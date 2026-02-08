"""
Booking repository - handles all booking-related database operations.
"""
from app.repositories.base import BaseRepository
from app.database import models


class BookingRepository(BaseRepository):
    """Repository for Booking entity operations."""
    
    @classmethod
    def create(cls, booking_data: dict):
        """Create a new booking."""
        with cls.get_session() as db:
            booking = models.Booking(**booking_data)
            db.add(booking)
            db.commit()
            db.refresh(booking)
            return {c.name: getattr(booking, c.name) for c in booking.__table__.columns}
    
    @classmethod
    def check_customer_overlap(cls, customer_id: str, date: str, time_slot: str):
        """Check if a customer has an overlapping active booking."""
        with cls.get_session() as db:
            active_statuses = ["AWAITING_CUSTOMER_CONFIRMATION", "CONFIRMED", "IN_PROGRESS", "PENDING"]
            overlap = db.query(models.Booking).filter(
                models.Booking.customerId == customer_id,
                models.Booking.date == date,
                models.Booking.timeSlot == time_slot,
                models.Booking.status.in_(active_statuses)
            ).first()
            return overlap is not None
    
    @classmethod
    def get_all(cls, customer_id=None, staff_id=None, shop_id=None, status=None, limit=None):
        """Get bookings with optional filters."""
        with cls.get_session() as db:
            query = db.query(models.Booking, models.User).join(
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
                b_dict["customerName"] = user.name
                b_dict["customerPhoto"] = user.profilePhoto
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
