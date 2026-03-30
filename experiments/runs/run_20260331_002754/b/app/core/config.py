"""FastAPI configuration settings using Pydantic Settings."""

import os
from typing import List, Optional
from datetime import timedelta
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # Application
    APP_NAME: str = "AgentHub"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    
    # Security
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    JWT_SECRET_KEY: str = "jwt-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60  # 1 hour
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    
    # Database
    DATABASE_URL: str = "sqlite:///app.db"
    DATABASE_POOL_RECYCLE: int = 300
    DATABASE_POOL_PRE_PING: bool = True
    
    # Redis
    REDIS_URL: Optional[str] = "redis://localhost:6379/0"
    
    # Stripe
    STRIPE_SECRET_KEY: Optional[str] = None
    STRIPE_PUBLISHABLE_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None
    
    # Agno Framework
    AGNO_API_KEY: Optional[str] = ""
    AGNO_BASE_URL: str = "https://api.agno.com"
    
    # Email
    MAIL_SERVER: str = "smtp.gmail.com"
    MAIL_PORT: int = 587
    MAIL_USE_TLS: bool = True
    MAIL_USERNAME: Optional[str] = None
    MAIL_PASSWORD: Optional[str] = None
    MAIL_DEFAULT_SENDER: str = "noreply@agenthub.com"
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 100
    
    # Agent Execution
    AGENT_TIMEOUT_SECONDS: int = 300
    MAX_AGENT_RUNS_PER_DAY: int = 100
    
    # Storage
    UPLOAD_FOLDER: str = "uploads"
    MAX_CONTENT_LENGTH: int = 16 * 1024 * 1024  # 16MB
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()