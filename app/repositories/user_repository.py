"""
User repository - handles all user-related database operations.
"""
from app.repositories.base import BaseRepository
from app.database import models


class UserRepository(BaseRepository):
    """Repository for User entity operations."""
    
    @classmethod
    def get_by_email(cls, email: str):
        """Get user by email address."""
        with cls.get_session() as db:
            user = db.query(models.User).filter(models.User.email == email).first()
            if not user:
                return None
            return {c.name: getattr(user, c.name) for c in user.__table__.columns}
    
    @classmethod
    def get_by_id(cls, user_id: str):
        """Get user by ID."""
        with cls.get_session() as db:
            user = db.query(models.User).filter(models.User.id == user_id).first()
            if not user:
                return None
            return {c.name: getattr(user, c.name) for c in user.__table__.columns}
    
    @classmethod
    def get_by_phone(cls, phone: str):
        """Get user by phone number."""
        with cls.get_session() as db:
            user = db.query(models.User).filter(models.User.phone == phone).first()
            if not user:
                return None
            return {c.name: getattr(user, c.name) for c in user.__table__.columns}
    
    @classmethod
    def create(cls, user_data: dict):
        """Create a new user."""
        with cls.get_session() as db:
            user = models.User(**user_data)
            db.add(user)
            db.commit()
            db.refresh(user)
            return {c.name: getattr(user, c.name) for c in user.__table__.columns}
    
    @classmethod
    def update(cls, user_id: str, update_data: dict):
        """Update an existing user."""
        with cls.get_session() as db:
            user = db.query(models.User).filter(models.User.id == user_id).first()
            if user:
                for key, value in update_data.items():
                    if hasattr(user, key):
                        setattr(user, key, value)
                db.commit()
                db.refresh(user)

                # TRIGGER SYNC: If user is a BARBER, sync to staff_profiles
                if (user.role == "BARBER" or getattr(user, "role") == "BARBER"):
                    # Use local import to avoid circular dependency
                    from app.repositories.shop_repository import StaffProfileRepository
                    
                    # Fields that need syncing
                    sync_fields = ["experience", "about", "portfolio", "profilePhoto"]
                    sync_data = {k: v for k, v in update_data.items() if k in sync_fields}
                    
                    if sync_data:
                        StaffProfileRepository.update(user_id, sync_data)

                return {c.name: getattr(user, c.name) for c in user.__table__.columns}
            return None


# Backward-compatible function exports
def get_user_by_email(email: str):
    """Get user by email. (Backward compatible)"""
    return UserRepository.get_by_email(email)


def get_user_by_id(user_id: str):
    """Get user by ID. (Backward compatible)"""
    return UserRepository.get_by_id(user_id)


def get_user_by_phone(phone: str):
    """Get user by phone. (Backward compatible)"""
    return UserRepository.get_by_phone(phone)


def add_user(user_data):
    """Create a new user. (Backward compatible)"""
    return UserRepository.create(user_data)


def update_user(user_id: str, update_data: dict):
    """Update a user. (Backward compatible)"""
    return UserRepository.update(user_id, update_data)
