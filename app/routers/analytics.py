from fastapi import APIRouter, HTTPException, status, Query
from pydantic import BaseModel
from typing import List, Optional, Dict
from app.db import get_bookings, get_all_hydrated_shops, get_user_by_id

router = APIRouter(prefix="/analytics", tags=["analytics"])

# Request/Response Models
class StaffPerformance(BaseModel):
    staffId: str
    staffName: str
    totalAppointments: int
    completedAppointments: int
    rejectedAppointments: int
    totalEarnings: float
    averageRating: float

class ShopAnalytics(BaseModel):
    totalAppointments: int
    pendingCount: int
    acceptedCount: int
    completedCount: int
    cancelledCount: int
    totalRevenue: float
    staffPerformance: List[StaffPerformance]

# Specific analytics routes
@router.get("/owner/{owner_id}", response_model=ShopAnalytics)
async def get_owner_analytics(
    owner_id: str,
    period: str = Query("daily", pattern="^(daily|weekly|monthly|yearly)$"),
    shop_id: Optional[str] = None
):
    """Get comprehensive analytics for an owner's shop(s)"""
    
    # 1. Find all shops owned by this user
    all_shops = get_all_hydrated_shops()
    owned_shops = [s for s in all_shops if s.get("ownerId") == owner_id]
    
    if not owned_shops:
        # Check if user is an owner
        user = get_user_by_id(owner_id)
        if not user or user.get("role") != "OWNER":
            raise HTTPException(status_code=404, detail="Owner not found or user is not an owner")
        
        return ShopAnalytics(
            totalAppointments=0, pendingCount=0, acceptedCount=0,
            completedCount=0, cancelledCount=0, totalRevenue=0.0,
            staffPerformance=[]
        )

    # 2. Filter bookings based on owned shops
    target_shop_ids = [shop_id] if shop_id else [s["id"] for s in owned_shops]
    
    # Get all bookings (we'll filter them)
    # Ideally we'd have a more targeted get_bookings helper
    all_bookings = []
    for sid in target_shop_ids:
        all_bookings.extend(get_bookings(shop_id=sid))
    
    # De-duplicate just in case
    bookings = {b["id"]: b for b in all_bookings}.values()
    
    completed = [b for b in bookings if b["status"] == "COMPLETED"]
    
    # 3. Staff Performance Calculation
    staff_stats = {}
    staff_ids = []
    for s in owned_shops:
        if not shop_id or s["id"] == shop_id:
            for staff in s.get("staff", []):
                staff_ids.append(staff["id"])
    
    for s_id in set(staff_ids):
        staff_user = get_user_by_id(s_id)
        staff_name = staff_user["name"] if staff_user else "Unknown Staff"
        
        s_bookings = [b for b in bookings if b["staffId"] == s_id]
        s_completed = [b for b in s_bookings if b["status"] == "COMPLETED"]
        s_rejected = [b for b in s_bookings if b["status"] == "CANCELLED"]
        
        staff_stats[s_id] = StaffPerformance(
            staffId=s_id,
            staffName=staff_name,
            totalAppointments=len(s_bookings),
            completedAppointments=len(s_completed),
            rejectedAppointments=len(s_rejected),
            totalEarnings=sum(b["totalAmount"] for b in s_completed),
            averageRating=4.8 # mock rating until we have actual ratings in staff
        )

    return ShopAnalytics(
        totalAppointments=len(bookings),
        pendingCount=len([b for b in bookings if b["status"] == "PENDING"]),
        acceptedCount=len([b for b in bookings if b["status"] == "ACCEPTED"]),
        completedCount=len(completed),
        cancelledCount=len([b for b in bookings if b["status"] == "CANCELLED"]),
        totalRevenue=sum(b["totalAmount"] for b in completed),
        staffPerformance=list(staff_stats.values())
    )

@router.get("/staff/{staff_id}/earnings")
async def get_staff_earnings(
    staff_id: str,
    period: str = Query("daily", pattern="^(daily|weekly|monthly|yearly)$")
):
    """Get earnings and performance metrics for a specific staff member"""
    
    staff_bookings = get_bookings(staff_id=staff_id)
    completed = [b for b in staff_bookings if b["status"] == "COMPLETED"]
    
    total_earned = sum(b["totalAmount"] for b in completed)
    tasks_done = len(completed)
    avg_per_task = total_earned / tasks_done if tasks_done > 0 else 0
    
    return {
        "staffId": staff_id,
        "period": period,
        "totalEarnings": total_earned,
        "tasksCompleted": tasks_done,
        "averagePerTask": avg_per_task,
        "recentTasks": completed[-5:]
    }
