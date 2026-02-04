"""
Repository package - provides organized database access layer.

All functions are re-exported here for backward compatibility with existing code.
New code should import directly from specific repositories for cleaner architecture.
"""

# User operations
from app.repositories.user_repository import (
    UserRepository,
    get_user_by_email,
    get_user_by_id,
    get_user_by_phone,
    add_user,
    update_user,
)

# Booking operations
from app.repositories.booking_repository import (
    BookingRepository,
    create_booking,
    get_bookings,
    get_booking_by_id,
    update_booking,
)

# Shop, Service, and Staff operations
from app.repositories.shop_repository import (
    ShopRepository,
    ServiceRepository,
    StaffProfileRepository,
    get_hydrated_shop,
    get_all_hydrated_shops,
    create_shop,
    update_shop,
    delete_shop,
    add_shop_photo,
    add_service,
    update_service,
    delete_service,
    get_staff_full_profile,
    update_staff_profile,
)

# Review operations
from app.repositories.review_repository import (
    ReviewRepository,
    create_review,
    get_reviews,
    update_review,
    delete_review,
)

# Notification operations
from app.repositories.notification_repository import (
    NotificationRepository,
    create_notification,
    get_notifications,
    mark_notification_read,
)

# Export all for backward compatibility
__all__ = [
    # Repositories
    "UserRepository",
    "BookingRepository",
    "ShopRepository",
    "ServiceRepository",
    "StaffProfileRepository",
    "ReviewRepository",
    "NotificationRepository",
    # User functions
    "get_user_by_email",
    "get_user_by_id",
    "get_user_by_phone",
    "add_user",
    "update_user",
    # Booking functions
    "create_booking",
    "get_bookings",
    "get_booking_by_id",
    "update_booking",
    # Shop functions
    "get_hydrated_shop",
    "get_all_hydrated_shops",
    "create_shop",
    "update_shop",
    "delete_shop",
    "add_shop_photo",
    # Service functions
    "add_service",
    "update_service",
    "delete_service",
    # Staff functions
    "get_staff_full_profile",
    "update_staff_profile",
    # Review functions
    "create_review",
    "get_reviews",
    "update_review",
    "delete_review",
    # Notification functions
    "create_notification",
    "get_notifications",
    "mark_notification_read",
]
