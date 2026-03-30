"""config.py — Application configuration and settings.

exports: settings, Settings
used_by: main.py, session.py, all API routers
rules:   must load from environment variables with sensible defaults
agent:   ProductArchitect | 2024-01-15 | created pydantic settings with environment loading
         message: "verify all required environment variables are documented"
"""

import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import validator


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    # Application
    APP_NAME: str = "AgentHub"
    DEBUG: bool = False
    SECRET_KEY: str = "your-secret-key-here-change-in-production"
    API_V1_STR: str = "/api/v1"

    # Database — str to support both PostgreSQL and SQLite (dev/test)
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost/agenthub"
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_RECYCLE: int = 3600  # 1 hour
    DB_ECHO: bool = False
    
    # Security
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ALGORITHM: str = "HS256"
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    ALLOWED_HOSTS: List[str] = ["localhost", "127.0.0.1"]
    
    # Billing
    STRIPE_SECRET_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None
    CREDIT_EXCHANGE_RATE: float = 1.0  # 1 USD = 1 credit
    
    # Agent Execution
    AGENT_EXECUTION_TIMEOUT: int = 300  # 5 minutes
    MAX_CONCURRENT_AGENTS: int = 10
    
    # Scheduler
    SCHEDULER_INTERVAL: int = 60  # Check every 60 seconds
    MAX_RETRY_ATTEMPTS: int = 3
    
    @validator("CORS_ORIGINS", pre=True)
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @validator("ALLOWED_HOSTS", pre=True)
    def parse_allowed_hosts(cls, v):
        if isinstance(v, str):
            return [host.strip() for host in v.split(",")]
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = 'allow'


# Global settings instance
settings = Settings()