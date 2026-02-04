"""
Base repository with shared session management.
All repositories inherit from this to ensure consistent database access patterns.
"""
from contextlib import contextmanager
from app.database.database import SessionLocal


class BaseRepository:
    """Base class for all repositories with shared session management."""
    
    @staticmethod
    @contextmanager
    def get_session():
        """Context manager for database sessions. Ensures proper cleanup."""
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()
