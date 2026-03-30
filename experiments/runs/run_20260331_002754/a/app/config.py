"""app/config.py — Application configuration with environment variables.

exports: Config, get_config()
used_by: app/main.py → create_app(), all services needing configuration
rules:   must validate all required env vars on startup; use pydantic for validation
agent:   Product Architect | 2024-03-30 | implemented config with pydantic validation
         message: "consider adding config caching to avoid repeated validation"
"""

import os
from typing import Optional, List
from functools import lru_cache

from pydantic import Field, PostgresDsn, RedisDsn, validator
from pydantic_settings import BaseSettings


class Config(BaseSettings):
    """Application configuration loaded from environment variables."""
    
    # Environment
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    DEBUG: bool = Field(default=False, env="DEBUG")
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Server
    HOST: str = Field(default="0.0.0.0", env="HOST")
    PORT: int = Field(default=8000, env="PORT")
    WORKERS: int = Field(default=1, env="WORKERS")
    
    # API
    API_V1_PREFIX: str = Field(default="/api/v1", env="API_V1_PREFIX")
    JWT_SECRET_KEY: str = Field(env="JWT_SECRET_KEY")
    JWT_ALGORITHM: str = Field(default="HS256", env="JWT_ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=15, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, env="REFRESH_TOKEN_EXPIRE_DAYS")
    CORS_ORIGINS: List[str] = Field(default=["http://localhost:3000"], env="CORS_ORIGINS")
    
    # Database
    DATABASE_URL: PostgresDsn = Field(env="DATABASE_URL")
    DATABASE_POOL_SIZE: int = Field(default=20, env="DATABASE_POOL_SIZE")
    DATABASE_MAX_OVERFLOW: int = Field(default=10, env="DATABASE_MAX_OVERFLOW")
    
    # Redis
    REDIS_URL: RedisDsn = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    REDIS_SESSION_TTL: int = Field(default=3600, env="REDIS_SESSION_TTL")  # 1 hour
    
    # Storage
    STORAGE_TYPE: str = Field(default="local", env="STORAGE_TYPE")  # local, s3, minio
    AWS_ACCESS_KEY_ID: Optional[str] = Field(default=None, env="AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: Optional[str] = Field(default=None, env="AWS_SECRET_ACCESS_KEY")
    AWS_S3_BUCKET: Optional[str] = Field(default=None, env="AWS_S3_BUCKET")
    AWS_REGION: Optional[str] = Field(default="us-east-1", env="AWS_REGION")
    
    # Agent Runtime
    AGENT_TIMEOUT_SECONDS: int = Field(default=300, env="AGENT_TIMEOUT_SECONDS")
    AGENT_MAX_TOKENS: int = Field(default=4000, env="AGENT_MAX_TOKENS")
    OPENAI_API_KEY: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    ANTHROPIC_API_KEY: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")
    
    # Billing
    STRIPE_SECRET_KEY: Optional[str] = Field(default=None, env="STRIPE_SECRET_KEY")
    STRIPE_WEBHOOK_SECRET: Optional[str] = Field(default=None, env="STRIPE_WEBHOOK_SECRET")
    FREE_TIER_CREDITS: int = Field(default=1000, env="FREE_TIER_CREDITS")
    
    # Security
    PASSWORD_HASH_ALGORITHM: str = Field(default="argon2", env="PASSWORD_HASH_ALGORITHM")
    RATE_LIMIT_PER_MINUTE: int = Field(default=60, env="RATE_LIMIT_PER_MINUTE")
    
    # External Services
    SENTRY_DSN: Optional[str] = Field(default=None, env="SENTRY_DSN")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
    
    @validator("ENVIRONMENT")
    def validate_environment(cls, v):
        """Validate environment is one of allowed values."""
        allowed = {"development", "testing", "staging", "production"}
        if v not in allowed:
            raise ValueError(f"ENVIRONMENT must be one of {allowed}")
        return v
    
    @validator("CORS_ORIGINS", pre=True)
    def parse_cors_origins(cls, v):
        """Parse CORS origins from comma-separated string."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @validator("DATABASE_URL", pre=True)
    def validate_database_url(cls, v):
        """Ensure DATABASE_URL is set in production."""
        if v is None and os.getenv("ENVIRONMENT") == "production":
            raise ValueError("DATABASE_URL must be set in production")
        return v
    
    @validator("JWT_SECRET_KEY")
    def validate_jwt_secret_key(cls, v):
        """Ensure JWT secret key is set and strong enough."""
        if not v:
            raise ValueError("JWT_SECRET_KEY must be set")
        if len(v) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters")
        return v


@lru_cache()
def get_config() -> Config:
    """Get cached configuration instance.
    
    Returns:
        Config: Application configuration
        
    Rules:
        Uses LRU cache to avoid repeated validation of environment variables
    """
    return Config()


# For backward compatibility
config = get_config()