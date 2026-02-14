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
    Priority:
    1. GCP Cloud SQL (Unix Socket) - via DB_INSTANCE_NAME
    2. Render/Generic Cloud (TCP/IP) - via DATABASE_URL
    3. Component-based (TCP/IP) - via individual variables
    """
    # Debug info (Sanitized)
    logger.info(f"🔍 DB Resolution: DB_INSTANCE_NAME={os.environ.get('DB_INSTANCE_NAME')}")
    
    # 1. GCP Cloud SQL (Unix Socket)
    instance_connection = os.environ.get("DB_INSTANCE_NAME")
    if instance_connection:
        db_user = os.environ.get("POSTGRES_USER", "postgres")
        db_pass = os.environ.get("POSTGRES_PASSWORD", "")
        db_name = os.environ.get("POSTGRES_DB", "barbersync")
        logger.info(f"🚀 Database: Using GCP PRODUCTION connection (Unix Socket: {instance_connection})")
        return f"postgresql://{db_user}:{db_pass}@/{db_name}?host=/cloudsql/{instance_connection}"

    # 2. Render/Neon (Direct URL)
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        logger.info("🚀 Database: Using RENDER/CLOUD PRODUCTION connection (DATABASE_URL)")
        return database_url

    # 3. Fallback to components
    server = os.environ.get("POSTGRES_SERVER", "localhost")
    user = os.environ.get("POSTGRES_USER", "postgres")
    password = os.environ.get("POSTGRES_PASSWORD", "aditya123")
    db = os.environ.get("POSTGRES_DB", "barbersync")
    
    logger.info(f"🏠 Database: Using COMPONENT connection ({server}:{user})")
    return f"postgresql://{user}:{password}@{server}/{db}"

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
