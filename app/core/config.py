from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "BarberSync API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Database configuration (Defaults for local development)
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "aditya123"
    POSTGRES_DB: str = "barbersync"
    
    # Optional field, but database.py resolves authority via os.environ directly
    DATABASE_URL: Optional[str] = None
    
    # Security
    JWT_SECRET: str = "supersecretkey"
    GOOGLE_MAPS_API_KEY: str = ""

    # GCP & Production (Missing from previous version)
    GCP_PROJECT_ID: Optional[str] = None
    GCP_REGION: Optional[str] = None
    GCP_SERVICE_NAME: Optional[str] = None
    GCS_BUCKET_NAME: Optional[str] = None
    DB_INSTANCE_NAME: Optional[str] = None
    OTP_PROVIDER: str = "mock"
    ENVIRONMENT: str = "dev"
    PAYMENT_WEBHOOK_SECRET: Optional[str] = None
    RAZORPAY_KEY_ID: Optional[str] = None
    RAZORPAY_KEY_SECRET: Optional[str] = None

    class Config:
        case_sensitive = True
        env_file = ".env"
        extra = "ignore"

settings = Settings()
