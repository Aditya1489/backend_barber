from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import uuid

router = APIRouter(prefix="/notifications", tags=["notifications"])

from app.db import (
    create_notification as db_create_notification,
    get_notifications,
    mark_notification_read
)

class NotificationRequest(BaseModel):
    userId: str # Target user
    senderId: str
    title: str
    body: str
    type: str # 'BOOKING', 'MESSAGE', 'ALARM'
    data: Optional[dict] = {}

class NotificationResponse(BaseModel):
    id: str
    userId: str
    title: str
    body: str
    isRead: bool
    createdAt: str

@router.post("/", response_model=NotificationResponse)
async def send_notification(notification: NotificationRequest):
    """Send a notification to a specific user"""
    return db_create_notification(notification.model_dump())

@router.get("/{user_id}", response_model=List[NotificationResponse])
async def get_user_notifications(user_id: str):
    """Get all notifications for a user"""
    return get_notifications(user_id)

@router.put("/{notif_id}/read")
async def mark_notification_as_read_route(notif_id: str):
    """Mark a notification as read"""
    if mark_notification_read(notif_id):
        return {"message": "Notification marked as read"}
    raise HTTPException(status_code=404, detail="Notification not found")
