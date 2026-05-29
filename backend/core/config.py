import os
from pydantic import BaseModel
from dotenv import load_dotenv
from typing import List

# Load environment variables from root or backend .env
load_dotenv()

class Settings(BaseModel):
    # App config
    APP_ENV: str = os.getenv("APP_ENV", "development")
    APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT: int = int(os.getenv("APP_PORT", "8000"))
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev_secret_key")
    JWT_SECRET: str = os.getenv("JWT_SECRET", "dev_jwt_secret")
    CORS_ORIGINS: List[str] = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")]
    
    # Paths
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "uploads")
    EXPORT_DIR: str = os.getenv("EXPORT_DIR", "exports")
    CACHE_DIR: str = os.getenv("CACHE_DIR", "cache")
    
    # Limits
    MAX_UPLOAD_MB: int = int(os.getenv("MAX_UPLOAD_MB", "500"))
    WS_HEARTBEAT_INTERVAL: int = int(os.getenv("WS_HEARTBEAT_INTERVAL", "30"))
    
    # Advanced
    ENABLE_GPU: bool = os.getenv("ENABLE_GPU", "false").lower() == "true"
    ENABLE_BACKGROUND_WORKERS: bool = os.getenv("ENABLE_BACKGROUND_WORKERS", "true").lower() == "true"

settings = Settings()
