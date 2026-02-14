from sqlalchemy import Column, String, Float, Integer, JSON, DateTime, ForeignKey, Boolean, UniqueConstraint, Index, func
from sqlalchemy.dialects.postgresql import TSTZRANGE
from sqlalchemy.orm import relationship
from app.database.database import Base
from datetime import datetime
import uuid

def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String, unique=True, index=True, nullable=False) # Enforce Unique
    # password removed
    fcmToken = Column(String, nullable=True)
    createdAt = Column(DateTime, default=datetime.utcnow)
    
    # Legal Consent & Digital Signature
    agreed_to_privacy = Column(Boolean, default=False)
    agreed_to_terms = Column(Boolean, default=False)
    legal_consent_name = Column(String, nullable=True)
    legal_consent_place = Column(String, nullable=True)
    legal_consent_timestamp = Column(DateTime, nullable=True)
    
    # Relationships
    roles = relationship("UserRole", back_populates="user", cascade="all, delete-orphan")
    customer_profile = relationship("CustomerProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    owner_profile = relationship("OwnerProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    staff_profile = relationship("Staff", back_populates="user") # Changed to list (uselist=True by default)
    # Renaming to staff_profiles would be better naming but breaks existing code access significantly.
    # Leaving name `staff_profile` but it will now return a LIST.
    # Existing code `user.staff_profile.some_field` WILL BREAK.
    # I must fix existing code in repositories.
    
    # Valid for Owners
    shops_owned = relationship("Shop", back_populates="owner")


class Role(Base):
    __tablename__ = "roles"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, unique=True, nullable=False) # customer, barber, owner, admin


class UserRole(Base):
    __tablename__ = "user_roles"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role_id = Column(String, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)
    shop_id = Column(String, ForeignKey("shops.id", ondelete="CASCADE"), nullable=True)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('user_id', 'role_id', 'shop_id', name='uq_user_role_shop'),
    )

    user = relationship("User", back_populates="roles")
    role = relationship("Role")
    # shop relationship optional if needed


class StaffInvite(Base):
    __tablename__ = "staff_invites"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    phone = Column(String, index=True, nullable=False)
    shop_id = Column(String, ForeignKey("shops.id", ondelete="CASCADE"), nullable=False)
    role = Column(String, default="BARBER", nullable=False)
    status = Column(String, default="PENDING", nullable=False) # PENDING, ACCEPTED, DECLINED, EXPIRED
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)

    shop = relationship("Shop") 


class CustomerProfile(Base):
    __tablename__ = "customer_profiles"
    
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    profile_photo = Column(String, nullable=True)
    preferences = Column(JSON, default={})
    loyalty_points = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="customer_profile")


class OwnerProfile(Base):
    __tablename__ = "owner_profiles"
    
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    profile_photo = Column(String, nullable=True)
    permissions = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="owner_profile")

# Legacy Shop Models (Updated for new Auth)

class Shop(Base):
    __tablename__ = "shops"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    address = Column(String, nullable=False)
    description = Column(String, nullable=True)
    rating = Column(Float, default=0.0)
    reviewsCount = Column(Integer, default=0)
    coordinates = Column(JSON, default={}) 
    ownerId = Column(String, ForeignKey("users.id")) # Owner's User ID
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    hours = Column(JSON, default={})
    amenities = Column(JSON, default=[])
    
    # Relationships
    owner = relationship("User", back_populates="shops_owned")
    staff = relationship("Staff", back_populates="shop")
    services = relationship("Service", back_populates="shop")
    photo_rows = relationship("ShopPhoto", back_populates="shop", cascade="all, delete-orphan")

class Staff(Base):
    __tablename__ = "staff_profiles"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    userId = Column(String, ForeignKey("users.id"), unique=False) # Changed unique to False
    shopId = Column(String, ForeignKey("shops.id"), nullable=True)
    name = Column(String, nullable=False)
    role = Column(String, default="Barber") # Job title, not App Role
    experience = Column(Integer, default=0)
    rating = Column(Float, default=0.0)
    reviewsCount = Column(Integer, default=0)
    imageUrl = Column(String, nullable=True) # Profile photo for barber role
    description = Column(String, nullable=True)
    skills = Column(String, nullable=True)
    workingDays = Column(JSON, default=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"])
    workingHours = Column(JSON, default={})
    bufferTime = Column(Integer, default=0)
    isAvailable = Column(Boolean, default=True)
    
    # Relationships
    user = relationship("User", back_populates="staff_profile")
    shop = relationship("Shop", back_populates="staff")
    work_photo_rows = relationship("StaffWorkPhoto", back_populates="staff", cascade="all, delete-orphan")
    service_objs = relationship("Service", secondary="staff_services_link")

class Service(Base):
    __tablename__ = "services"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    shopId = Column(String, ForeignKey("shops.id"))
    name = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    duration = Column(Integer, nullable=False) # In minutes
    imageUrl = Column(String, nullable=True)
    
    # Relationships
    shop = relationship("Shop", back_populates="services")

class Booking(Base) :
    __tablename__ = "bookings"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    customerId = Column(String, ForeignKey("users.id"))
    shopId = Column(String, ForeignKey("shops.id"))
    staffId = Column(String, ForeignKey("staff_profiles.id"))
    services = Column(JSON, default=[]) 
    date = Column(String, nullable=False) 
    timeSlot = Column(String, nullable=False) # Deprecated: Use startTime/endTime
    startTime = Column(DateTime(timezone=True), nullable=True, index=True)
    endTime = Column(DateTime(timezone=True), nullable=True, index=True)
    status = Column(String, default="PENDING", index=True) 
    isPaidConfirmation = Column(Boolean, default=False)
    expiresAt = Column(DateTime, nullable=True)
    totalAmount = Column(Float, nullable=False)
    totalDuration = Column(Integer, nullable=True) 
    bookedAt = Column(DateTime, default=datetime.utcnow)
    notes = Column(String, nullable=True)
    idempotencyKey = Column(String, nullable=True, unique=True)
    reminded24h = Column(Boolean, default=False)
    reminded2h = Column(Boolean, default=False)
    reminded15m = Column(Boolean, default=False)

    __table_args__ = (
        Index('ix_bookings_staff_range_status', 'staffId', 'startTime', 'endTime', 'status'),
    )

class Review(Base):
    __tablename__ = "reviews"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    shopId = Column(String, ForeignKey("shops.id"))
    staffId = Column(String, ForeignKey("staff_profiles.id"), nullable=True)
    customerId = Column(String, ForeignKey("users.id"))
    customerName = Column(String, nullable=False)
    rating = Column(Float, nullable=False)
    comment = Column(String, nullable=True)
    photos = Column(JSON, default=[])
    helpful = Column(Integer, default=0)
    createdAt = Column(DateTime, default=datetime.utcnow)

class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    userId = Column(String, ForeignKey("users.id"))
    title = Column(String, nullable=False)
    body = Column(String, nullable=False)
    type = Column(String, nullable=False) 
    data = Column(JSON, default={})
    isRead = Column(Boolean, default=False)
    createdAt = Column(DateTime, default=datetime.utcnow)

class AuditLog(Base):
    """Immutable audit trail for owner supervision"""
    __tablename__ = "audit_logs"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    actorId = Column(String, nullable=True)  # Who performed the action (userId or 'SYSTEM')
    actorRole = Column(String, nullable=True)  # OWNER, BARBER, CUSTOMER, SYSTEM
    actionType = Column(String, nullable=False)  # booking_override, price_change, staff_disable, etc.
    entityType = Column(String, nullable=False)  # booking, service, staff, shop
    entityId = Column(String, nullable=False)
    details = Column(JSON, nullable=True)  # Additional context (old/new values, etc.)
    reason = Column(String, nullable=True)  # User-provided reason for the action
    shopId = Column(String, ForeignKey("shops.id"), nullable=True)  # For filtering by shop
    createdAt = Column(DateTime, default=datetime.utcnow)


class ShopPhoto(Base):
    __tablename__ = "shop_photos"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    shopId = Column(String, ForeignKey("shops.id"))
    url = Column(String, nullable=False)
    order = Column(Integer, default=0)
    
    shop = relationship("Shop", back_populates="photo_rows")

class StaffWorkPhoto(Base):
    __tablename__ = "staff_work_photos"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    staffId = Column(String, ForeignKey("staff_profiles.id"))
    url = Column(String, nullable=False)
    
    staff = relationship("Staff", back_populates="work_photo_rows")

class StaffService(Base):
    __tablename__ = "staff_services_link"
    
    staffId = Column(String, ForeignKey("staff_profiles.id"), primary_key=True)
    serviceId = Column(String, ForeignKey("services.id"), primary_key=True)
