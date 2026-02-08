import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("database")

def resolve_database_url():
    """
    AUTHORITATIVE DATABASE URL RESOLUTION
    ------------------------------------
    This function implements the strict priority logic required for 
    safe deployment across local and production (Render/Neon) environments.
    
    The SQLAlchemy engine MUST be created ONLY after this decision is made.
    """
    # 1. Check if we are on Render (Production)
    on_render = os.environ.get("RENDER") == "true"
    database_url = os.environ.get("DATABASE_URL")
    
    if on_render and database_url:
        # SQLAlchemy 1.4+ requires postgresql:// instead of postgres://
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        
        logger.info("🚀 Database: Using PRODUCTION connection (DATABASE_URL)")
        return database_url

    # 2. Fallback to specific local components (Local Mac development)
    logger.info("🏠 Database: Using LOCAL connection (localhost)")
    return f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_SERVER}/{settings.POSTGRES_DB}"

# DECISION: Resolve the URL before any engine or session initialization
DATABASE_URL = resolve_database_url()

# INITIALIZATION: Create engine and factory using the authoritative URL
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # Critical for cloud DBs (Neon/Render) to drop stale connections
    pool_size=5,         # Safe default for starter cloud DBs
    max_overflow=10,
    pool_timeout=30
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """Dependency for use in FastAPI routes"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
