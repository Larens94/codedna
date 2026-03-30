"""Configuration settings for AgentHub application.

Supports multiple environments: development, testing, production.
"""

import os
from datetime import timedelta
from typing import List


class Config:
    """Base configuration."""
    
    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_recycle': 300,
        'pool_pre_ping': True,
    }
    
    # JWT
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'jwt-secret-key-change-in-production')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    JWT_TOKEN_LOCATION = ['headers']
    JWT_HEADER_NAME = 'Authorization'
    JWT_HEADER_TYPE = 'Bearer'
    
    # CORS
    CORS_ORIGINS: List[str] = ['http://localhost:3000', 'http://127.0.0.1:3000']
    
    # Bcrypt
    BCRYPT_LOG_ROUNDS = 12
    
    # Mail
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'True').lower() in ['true', '1', 't']
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', 'noreply@agenthub.com')
    
    # Celery
    CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
    CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
    CELERY_TASK_SERIALIZER = 'json'
    CELERY_RESULT_SERIALIZER = 'json'
    CELERY_ACCEPT_CONTENT = ['json']
    CELERY_TIMEZONE = 'UTC'
    
    # Stripe
    STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY', '')
    STRIPE_PUBLISHABLE_KEY = os.getenv('STRIPE_PUBLISHABLE_KEY', '')
    STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET', '')
    
    # Application
    APP_NAME = 'AgentHub'
    API_VERSION = 'v1'
    AGENT_TIMEOUT_SECONDS = 300  # 5 minutes
    MAX_AGENT_RUNS_PER_DAY = 100
    
    # Storage
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload
    
    # Logging
    LOG_LEVEL = 'INFO'
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Agent Framework
    AGNO_API_KEY = os.getenv('AGNO_API_KEY', '')
    AGNO_BASE_URL = os.getenv('AGNO_BASE_URL', 'https://api.agno.com')
    
    # Rate limiting
    RATELIMIT_DEFAULT = '100 per minute'
    RATELIMIT_STORAGE_URL = CELERY_BROKER_URL


class DevelopmentConfig(Config):
    """Development configuration."""
    
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///dev.db')
    CORS_ORIGINS = ['http://localhost:3000', 'http://127.0.0.1:3000', 'http://localhost:5000']
    
    # Agent Framework (mock for development)
    AGNO_API_KEY = os.getenv('AGNO_API_KEY', 'dev-agno-api-key')
    AGNO_BASE_URL = os.getenv('AGNO_BASE_URL', 'http://localhost:8000')
    
    # Logging
    LOG_LEVEL = 'DEBUG'


class TestingConfig(Config):
    """Testing configuration."""
    
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.getenv('TEST_DATABASE_URL', 'sqlite:///:memory:')
    JWT_SECRET_KEY = 'testing-jwt-secret-key'
    SECRET_KEY = 'testing-secret-key'
    BCRYPT_LOG_ROUNDS = 4  # Faster hashing for tests
    
    # Disable CSRF protection for testing
    WTF_CSRF_ENABLED = False
    
    # Mail
    MAIL_SUPPRESS_SEND = True
    
    # Stripe
    STRIPE_SECRET_KEY = 'sk_test_testing'
    
    # Agent Framework
    AGNO_API_KEY = 'test-agno-api-key'
    AGNO_BASE_URL = 'http://test.agno.com'


class ProductionConfig(Config):
    """Production configuration."""
    
    DEBUG = False
    TESTING = False
    
    # Security
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_HTTPONLY = True
    
    # CORS - set actual production domains
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '').split(',') if os.getenv('CORS_ORIGINS') else []
    
    # Database - use PostgreSQL in production
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    if not SQLALCHEMY_DATABASE_URI:
        raise ValueError('DATABASE_URL environment variable is required in production')
    
    # Stripe - must be set in production
    if not os.getenv('STRIPE_SECRET_KEY'):
        raise ValueError('STRIPE_SECRET_KEY environment variable is required in production')
    
    # Agent Framework - must be set in production
    if not os.getenv('AGNO_API_KEY'):
        raise ValueError('AGNO_API_KEY environment variable is required in production')
    
    # Logging
    LOG_LEVEL = 'WARNING'