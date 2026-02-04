"""
Database access layer - Backward compatibility facade.

This file now re-exports all functions from the repository layer.
The actual implementations are in app/repositories/*.

New code should import directly from repositories:
    from app.repositories import UserRepository, BookingRepository

Legacy code can continue to use:
    from app.db import get_user_by_email, create_booking
"""
import uuid
from datetime import datetime

# Re-export all repository functions for backward compatibility
from app.repositories import (
    # User operations
    get_user_by_email,
    get_user_by_id,
    get_user_by_phone,
    add_user,
    update_user,
    # Booking operations
    create_booking,
    get_bookings,
    get_booking_by_id,
    update_booking,
    # Shop operations
    get_hydrated_shop,
    get_all_hydrated_shops,
    create_shop,
    update_shop,
    delete_shop,
    add_shop_photo,
    # Service operations
    add_service,
    update_service,
    delete_service,
    # Staff operations
    get_staff_full_profile,
    update_staff_profile,
    # Review operations
    create_review,
    get_reviews,
    update_review,
    delete_review,
    # Notification operations
    create_notification,
    get_notifications,
    mark_notification_read,
)

# Keep the session helper for any code that still needs direct DB access
from app.database.database import SessionLocal

def get_db_session():
    """Get a database session. Remember to close it when done."""
    return SessionLocal()

# Legacy comment for clarity
# All original functions have been refactored to app/repositories/
# This file is kept for backward compatibility only.
