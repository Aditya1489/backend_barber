"""
Notification repository - handles all notification-related database operations.
"""
import uuid
from app.repositories.base import BaseRepository
from app.database.database import SessionLocal
from app.database import models


class NotificationRepository(BaseRepository):
    """Repository for Notification entity operations."""
    
    @classmethod
    def create(cls, data: dict):
        """Create a new notification."""
        db = SessionLocal()
        try:
            new_notif = models.Notification(
                id=str(uuid.uuid4()),
                userId=data["userId"],
                title=data["title"],
                body=data["body"],
                type=data["type"],
                data=data.get("data", {}),
                isRead=False
            )
            db.add(new_notif)
            db.commit()
            db.refresh(new_notif)
            return {
                "id": new_notif.id,
                "userId": new_notif.userId,
                "title": new_notif.title,
                "body": new_notif.body,
                "isRead": new_notif.isRead,
                "createdAt": new_notif.createdAt.isoformat() + "Z"
            }
        finally:
            db.close()
    
    @classmethod
    def get_by_user(cls, user_id: str):
        """Get all notifications for a user."""
        db = SessionLocal()
        try:
            notifs = db.query(models.Notification).filter(
                models.Notification.userId == user_id
            ).order_by(models.Notification.createdAt.desc()).all()
            return [{
                "id": n.id,
                "userId": n.userId,
                "title": n.title,
                "body": n.body,
                "type": n.type,
                "data": n.data,
                "isRead": n.isRead,
                "createdAt": n.createdAt.isoformat() + "Z"
            } for n in notifs]
        finally:
            db.close()
    
    @classmethod
    def mark_read(cls, notif_id: str):
        """Mark a notification as read."""
        db = SessionLocal()
        try:
            notif = db.query(models.Notification).filter(
                models.Notification.id == notif_id
            ).first()
            if notif:
                notif.isRead = True
                db.commit()
                return True
            return False
        finally:
            db.close()


# Backward-compatible function exports
def create_notification(data: dict):
    """Create a notification. (Backward compatible)"""
    return NotificationRepository.create(data)


def get_notifications(user_id: str):
    """Get notifications for a user. (Backward compatible)"""
    return NotificationRepository.get_by_user(user_id)


def mark_notification_read(notif_id: str):
    """Mark notification as read. (Backward compatible)"""
    return NotificationRepository.mark_read(notif_id)
