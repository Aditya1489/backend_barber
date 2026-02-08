from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, timedelta
from app.database.database import get_db
from app.database.models import AuditLog, User, Shop, Booking, Staff
from app.database.owner_models import OwnerSettings, StaffReliability
from pydantic import BaseModel

router = APIRouter(prefix="/api/owner", tags=["owner"])

# ==================== PYDANTIC MODELS ====================

class AuditLogResponse(BaseModel):
    id: str
    timestamp: datetime
    actorId: Optional[str]
    actorRole: Optional[str]
    actionType: str
    entityType: str
    entityId: str
    details: Optional[dict]
    reason: Optional[str]
    shopId: Optional[str]
    
    class Config:
        from_attributes = True

class OwnerSettingsResponse(BaseModel):
    ownerId: str
    maxNoShowsPerBarber: int
    noShowAction: str
    maxCancellationsPerHour: int
    minUtilizationThreshold: float
    revenueDropThreshold: float
    notificationSeverityLevel: str
    platformFeeRate: float
    
    class Config:
        from_attributes = True

class OwnerSettingsUpdate(BaseModel):
    maxNoShowsPerBarber: Optional[int] = None
    noShowAction: Optional[str] = None
    maxCancellationsPerHour: Optional[int] = None
    minUtilizationThreshold: Optional[float] = None
    revenueDropThreshold: Optional[float] = None
    notificationSeverityLevel: Optional[str] = None

class StaffReliabilityResponse(BaseModel):
    staffId: str
    reliabilityScore: float
    noShowCountMonth: int
    noShowCountAllTime: int
    completedCount: int
    cancelledCount: int
    avgRating: float
    totalEarnings: float
    inactivityEvents: List[dict]
    lastCalculated: datetime
    
    class Config:
        from_attributes = True

class ExceptionItem(BaseModel):
    severity: str  # critical, warning, info
    type: str  # barber_unavailable, risky_bookings, revenue_anomaly
    title: str
    description: str
    data: Optional[dict] = None
    actionRequired: bool = False

class ExceptionsResponse(BaseModel):
    shopId: str
    shopName: str
    health: str  # green, yellow, red
    exceptions: List[ExceptionItem]
    lastChecked: datetime

# ==================== HELPER FUNCTIONS ====================

def create_audit_log(
    db: Session,
    actor_id: Optional[str],
    actor_role: Optional[str],
    action_type: str,
    entity_type: str,
    entity_id: str,
    details: Optional[dict] = None,
    reason: Optional[str] = None,
    shop_id: Optional[str] = None
):
    """Helper function to create audit log entries"""
    audit_log = AuditLog(
        actorId=actor_id,
        actorRole=actor_role,
        actionType=action_type,
        entityType=entity_type,
        entityId=entity_id,
        details=details,
        reason=reason,
        shopId=shop_id
    )
    db.add(audit_log)
    db.commit()
    return audit_log

def calculate_staff_reliability(db: Session, staff_id: str) -> dict:
    """Calculate reliability metrics for a staff member"""
    # Get all bookings for this staff
    bookings = db.query(Booking).filter(Booking.staffId == staff_id).all()
    
    if not bookings:
        return {
            "reliabilityScore": 100.0,
            "noShowCountMonth": 0,
            "noShowCountAllTime": 0,
            "completedCount": 0,
            "cancelledCount": 0
        }
    
    # Calculate metrics
    total = len(bookings)
    completed = len([b for b in bookings if b.status == "COMPLETED"])
    no_shows = [b for b in bookings if b.status == "NO_SHOW"]
    cancelled = len([b for b in bookings if b.status in ["CANCELLED_BY_BARBER", "CANCELLED_BY_CUSTOMER"]])
    
    # No-shows in last month
    one_month_ago = datetime.utcnow() - timedelta(days=30)
    no_shows_month = len([b for b in no_shows if b.bookedAt >= one_month_ago])
    
    # Calculate reliability score (0-100)
    # Formula: (completed / total) * 100, penalize no-shows heavily
    if total > 0:
        base_score = (completed / total) * 100
        no_show_penalty = len(no_shows) * 5  # -5 points per no-show
        reliability_score = max(0, min(100, base_score - no_show_penalty))
    else:
        reliability_score = 100.0
    
    return {
        "reliabilityScore": round(reliability_score, 1),
        "noShowCountMonth": no_shows_month,
        "noShowCountAllTime": len(no_shows),
        "completedCount": completed,
        "cancelledCount": cancelled
    }

# ==================== ENDPOINTS ====================

@router.get("/audit-trail/{owner_id}", response_model=List[AuditLogResponse])
async def get_audit_trail(
    owner_id: str,
    db: Session = Depends(get_db),
    shop_id: Optional[str] = Query(None),
    action_type: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    limit: int = Query(50, le=200)
):
    """
    Get audit trail for an owner with optional filters.
    Returns immutable history of all critical actions.
    """
    # Verify owner exists
    owner = db.query(User).filter(User.id == owner_id, User.role == "OWNER").first()
    if not owner:
        raise HTTPException(status_code=404, detail="Owner not found")
    
    # Build query
    query = db.query(AuditLog)
    
    # Filter by shop if provided
    if shop_id:
        query = query.filter(AuditLog.shopId == shop_id)
    else:
        # Get all shops owned by this owner
        shop_ids = [s.id for s in db.query(Shop).filter(Shop.ownerId == owner_id).all()]
        if shop_ids:
            query = query.filter(AuditLog.shopId.in_(shop_ids))
    
    # Filter by action type
    if action_type:
        query = query.filter(AuditLog.actionType == action_type)
    
    # Filter by date range
    if start_date:
        start_dt = datetime.fromisoformat(start_date)
        query = query.filter(AuditLog.timestamp >= start_dt)
    
    if end_date:
        end_dt = datetime.fromisoformat(end_date)
        query = query.filter(AuditLog.timestamp <= end_dt)
    
    # Order by most recent first
    query = query.order_by(AuditLog.timestamp.desc())
    
    # Limit results
    logs = query.limit(limit).all()
    
    return logs

@router.post("/audit-log")
async def create_audit_log_entry(
    actor_id: Optional[str],
    actor_role: str,
    action_type: str,
    entity_type: str,
    entity_id: str,
    details: Optional[dict] = None,
    reason: Optional[str] = None,
    shop_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Create a new audit log entry"""
    log = create_audit_log(
        db=db,
        actor_id=actor_id,
        actor_role=actor_role,
        action_type=action_type,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details,
        reason=reason,
        shop_id=shop_id
    )
    return {"id": log.id, "created": True}

@router.get("/settings/{owner_id}", response_model=OwnerSettingsResponse)
async def get_owner_settings(owner_id: str, db: Session = Depends(get_db)):
    """Get owner settings, create default if not exists"""
    settings = db.query(OwnerSettings).filter(OwnerSettings.ownerId == owner_id).first()
    
    if not settings:
        # Create default settings
        settings = OwnerSettings(ownerId=owner_id)
        db.add(settings)
        db.commit()
        db.refresh(settings)
    
    return settings

@router.put("/settings/{owner_id}", response_model=OwnerSettingsResponse)
async def update_owner_settings(
    owner_id: str,
    updates: OwnerSettingsUpdate,
    db: Session = Depends(get_db)
):
    """Update owner settings"""
    settings = db.query(OwnerSettings).filter(OwnerSettings.ownerId == owner_id).first()
    
    if not settings:
        settings = OwnerSettings(ownerId=owner_id)
        db.add(settings)
    
    # Update fields
    for field, value in updates.dict(exclude_unset=True).items():
        setattr(settings, field, value)
    
    settings.updatedAt = datetime.utcnow()
    db.commit()
    db.refresh(settings)
    
    # Create audit log
    create_audit_log(
        db=db,
        actor_id=owner_id,
        actor_role="OWNER",
        action_type="settings_update",
        entity_type="owner_settings",
        entity_id=owner_id,
        details=updates.dict(exclude_unset=True)
    )
    
    return settings

@router.get("/staff/{staff_id}/reliability", response_model=StaffReliabilityResponse)
async def get_staff_reliability(staff_id: str, db: Session = Depends(get_db)):
    """Get or calculate staff reliability metrics"""
    # Check if cached metrics exist
    reliability = db.query(StaffReliability).filter(StaffReliability.staffId == staff_id).first()
    
    # Recalculate if older than 1 hour or doesn't exist
    should_recalculate = (
        not reliability or 
        (datetime.utcnow() - reliability.lastCalculated).total_seconds() > 3600
    )
    
    if should_recalculate:
        metrics = calculate_staff_reliability(db, staff_id)
        
        if reliability:
            # Update existing
            for key, value in metrics.items():
                setattr(reliability, key, value)
            reliability.lastCalculated = datetime.utcnow()
        else:
            # Create new
            reliability = StaffReliability(
                staffId=staff_id,
                **metrics,
                lastCalculated=datetime.utcnow()
            )
            db.add(reliability)
        
        db.commit()
        db.refresh(reliability)
    
    return reliability

@router.get("/exceptions/{owner_id}", response_model=List[ExceptionsResponse])
async def get_owner_exceptions(owner_id: str, db: Session = Depends(get_db)):
    """
    Get exception-based dashboard data.
    Returns ONLY items that need owner attention.
    """
    # Get all shops for this owner
    shops = db.query(Shop).filter(Shop.ownerId == owner_id).all()
    
    if not shops:
        return []
    
    # Get owner settings for thresholds
    settings = db.query(OwnerSettings).filter(OwnerSettings.ownerId == owner_id).first()
    if not settings:
        settings = OwnerSettings(ownerId=owner_id)
    
    results = []
    
    for shop in shops:
        exceptions = []
        
        # Check 1: Unexpectedly unavailable barbers
        staff_members = db.query(Staff).filter(
            Staff.shopId == shop.id,
            Staff.isAvailable == False
        ).all()
        
        if staff_members:
            exceptions.append(ExceptionItem(
                severity="warning",
                type="barber_unavailable",
                title=f"{len(staff_members)} Barber(s) Unavailable",
                description=f"{', '.join([s.name for s in staff_members])} marked as unavailable",
                data={"staffIds": [s.id for s in staff_members]},
                actionRequired=True
            ))
        
        # Check 2: Risky bookings (pending > 2 hours)
        two_hours_ago = datetime.utcnow() - timedelta(hours=2)
        risky_bookings = db.query(Booking).filter(
            Booking.shopId == shop.id,
            Booking.status == "PENDING",
            Booking.bookedAt < two_hours_ago
        ).all()
        
        if risky_bookings:
            exceptions.append(ExceptionItem(
                severity="warning",
                type="risky_bookings",
                title=f"{len(risky_bookings)} Pending Requests > 2hrs",
                description="These bookings need immediate attention",
                data={"count": len(risky_bookings)},
                actionRequired=True
            ))
        
        # Check 3: Staff with high no-show count
        for staff in db.query(Staff).filter(Staff.shopId == shop.id).all():
            reliability = db.query(StaffReliability).filter(
                StaffReliability.staffId == staff.id
            ).first()
            
            if reliability and reliability.noShowCountMonth >= settings.maxNoShowsPerBarber:
                exceptions.append(ExceptionItem(
                    severity="critical",
                    type="staff_reliability",
                    title=f"{staff.name} - High No-Show Rate",
                    description=f"{reliability.noShowCountMonth} no-shows this month (threshold: {settings.maxNoShowsPerBarber})",
                    data={"staffId": staff.id, "noShowCount": reliability.noShowCountMonth},
                    actionRequired=True
                ))
        
        # Determine overall health
        if any(e.severity == "critical" for e in exceptions):
            health = "red"
        elif exceptions:
            health = "yellow"
        else:
            health = "green"
        
        results.append(ExceptionsResponse(
            shopId=shop.id,
            shopName=shop.name,
            health=health,
            exceptions=exceptions,
            lastChecked=datetime.utcnow()
        ))
    
    return results
