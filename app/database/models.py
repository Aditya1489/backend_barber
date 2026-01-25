from sqlalchemy import Column, String, Float, Integer, JSON, DateTime, ForeignKey, Boolean
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
    phone = Column(String, index=True, nullable=False)
    password = Column(String, nullable=False)
    role = Column(String, nullable=False) # CUSTOMER, OWNER, BARBER
    profilePhoto = Column(String, nullable=True)
    permissions = Column(JSON, default={})
    createdAt = Column(DateTime, default=datetime.utcnow)
    
    # Barber/Staff specific fields
    experience = Column(Integer, nullable=True)
    about = Column(String, nullable=True)
    portfolio = Column(JSON, nullable=True) # List of image URLs
    
    # Relationships
    shops_owned = relationship("Shop", back_populates="owner")
    staff_profile = relationship("Staff", back_populates="user", uselist=False)

class Shop(Base):
    __tablename__ = "shops"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    address = Column(String, nullable=False)
    description = Column(String, nullable=True)
    rating = Column(Float, default=0.0)
    reviewsCount = Column(Integer, default=0)
    photos = Column(JSON, default=[])
    coordinates = Column(JSON, default={}) # {"lat": 0.0, "lng": 0.0}
    ownerId = Column(String, ForeignKey("users.id"))
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    hours = Column(JSON, default={})
    amenities = Column(JSON, default=[])
    
    # Relationships
    owner = relationship("User", back_populates="shops_owned")
    staff = relationship("Staff", back_populates="shop")
    services = relationship("Service", back_populates="shop")

class Staff(Base):
    __tablename__ = "staff_profiles"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    userId = Column(String, ForeignKey("users.id"), unique=True)
    shopId = Column(String, ForeignKey("shops.id"), nullable=True)
    name = Column(String, nullable=False)
    role = Column(String, default="Barber")
    experience = Column(Integer, default=0)
    rating = Column(Float, default=0.0)
    reviewsCount = Column(Integer, default=0)
    imageUrl = Column(String, nullable=True)
    description = Column(String, nullable=True)
    workPhotos = Column(JSON, default=[])
    
    # Relationships
    user = relationship("User", back_populates="staff_profile")
    shop = relationship("Shop", back_populates="staff")

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
    services = Column(JSON, default=[]) # List of service IDs or objects
    date = Column(String, nullable=False) # Store as string for now to match old logic or DateTime
    timeSlot = Column(String, nullable=False)
    status = Column(String, default="PENDING") # PENDING, CONFIRMED, CANCELLED, COMPLETED
    totalAmount = Column(Float, nullable=False)
    totalDuration = Column(Integer, nullable=True) # In minutes
    bookedAt = Column(DateTime, default=datetime.utcnow)
    notes = Column(String, nullable=True)

class Review(Base):
    __tablename__ = "reviews"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    shopId = Column(String, ForeignKey("shops.id"))
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
    type = Column(String, nullable=False) # APPOINTMENT, PROMO, SYSTEM
    data = Column(JSON, default={})
    isRead = Column(Boolean, default=False)
    createdAt = Column(DateTime, default=datetime.utcnow)
