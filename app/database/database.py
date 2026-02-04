import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("database")

# 1. Database URL Selection Priority
# Priority 1: Environment Variable (Render/Production)
database_url = os.getenv("DATABASE_URL")

if database_url:
    logger.info("🚀 Database: Using PRODUCTION connection (DATABASE_URL)")
    # SQLAlchemy 2.0 requirements: convert postgres:// to postgresql://
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
else:
    # Priority 2: Fallback to Local Configs (Manual/Local)
    logger.info("🏠 Database: Using LOCAL connection (localhost)")
    database_url = f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_SERVER}/{settings.POSTGRES_DB}"

# 2. Engine Creation with Resilience Settings
engine = create_engine(
    database_url,
    pool_pre_ping=True,  # Critical for cloud DBs (Neon/Render) to drop stale connections
    pool_size=5,         # Conservative connection pool for starter/free tiers
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
