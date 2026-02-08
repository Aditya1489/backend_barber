from sqlalchemy import Column, String, Float, Integer, JSON, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.database.database import Base
from datetime import datetime
import uuid

def generate_uuid():
    return str(uuid.uuid4())

class OwnerSettings(Base):
    """Configurable alert thresholds and preferences for owners"""
    __tablename__ = "owner_settings"
    
    ownerId = Column(String, ForeignKey("users.id"), primary_key=True)
    
    # Alert thresholds
    maxNoShowsPerBarber = Column(Integer, default=3)  # Per month
    noShowAction = Column(String, default="notify_owner")  # auto_disable, notify_owner
    maxCancellationsPerHour = Column(Integer, default=5)
    minUtilizationThreshold = Column(Float, default=0.6)  # 60%
    revenueDropThreshold = Column(Float, default=0.2)  # 20%
    
    # Notification preferences
    notificationSeverityLevel = Column(String, default="warning")  # info, warning, critical
    
    # Platform settings
    platformFeeRate = Column(Float, default=0.10)  # 10%
    
    createdAt = Column(DateTime, default=datetime.utcnow)
    updatedAt = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class StaffReliability(Base):
    """Calculated reliability metrics for staff members"""
    __tablename__ = "staff_reliability"
    
    staffId = Column(String, ForeignKey("staff_profiles.id"), primary_key=True)
    
    # Reliability metrics
    reliabilityScore = Column(Float, default=100.0)  # 0-100
    noShowCountMonth = Column(Integer, default=0)
    noShowCountAllTime = Column(Integer, default=0)
    completedCount = Column(Integer, default=0)
    cancelledCount = Column(Integer, default=0)
    
    # Performance metrics
    avgRating = Column(Float, default=0.0)
    totalEarnings = Column(Float, default=0.0)
    
    # Inactivity tracking
    inactivityEvents = Column(JSON, default=[])  # List of {date, reason, duration}
    lastAutoDisabled = Column(DateTime, nullable=True)
    
    # Calculation metadata
    lastCalculated = Column(DateTime, default=datetime.utcnow)
    calculationPeriod = Column(String, default="month")  # month, quarter, year
    
    createdAt = Column(DateTime, default=datetime.utcnow)
    updatedAt = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
