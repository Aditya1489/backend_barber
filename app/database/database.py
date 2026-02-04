import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Configure logging to ensure visibility in Render/Local logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("database")

def resolve_database_url():
    """
    AUTHORITATIVE DATABASE URL RESOLUTION
    ------------------------------------
    This function implements the strict priority logic required for 
    safe deployment across local and production (Render/Neon) environments.
    
    Reasoning:
    Engine creation must happen only after the correct URL is resolved.
    Direct environment check bypasses potential issues with Pydantic 
    reading from local .env files that shouldn't exist in production.
    """
    # 1. Check direct environment variable first (Authoritative for Render/Neon)
    database_url = os.environ.get("DATABASE_URL")
    
    if database_url:
        # SQLAlchemy 1.4+ requires postgresql:// (Render often provides postgres://)
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        
        logger.info("🚀 Database: Using PRODUCTION connection (DATABASE_URL)")
        return database_url

    # 2. Fallback to specific local components from settings class
    logger.info("🏠 Database: Using LOCAL connection (localhost)")
    return f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_SERVER}/{settings.POSTGRES_DB}"

# DECISION: Resolve the URL before any engine or session initialization
DATABASE_URL = resolve_database_url()

# INITIALIZATION: Create engine and factory using the authoritative URL
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # Ensures stale connections (neon cold starts) are handled
    pool_size=5,         # Safe defaults for cloud database connections
    max_overflow=10,
    pool_timeout=30
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """FastAPI dependency for database sessions"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
