"""session.py — Database engine and session management.

exports: engine, SessionLocal, get_db()
used_by: main.py, all API routers, seed.py
rules:   engine must use connection pooling; sessions must be closed after use
agent:   ProductArchitect | 2024-01-15 | created SQLAlchemy engine with connection pooling
         message: "verify connection pool settings are appropriate for production"
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

from agenthub.config import settings

# Create engine with connection pooling
engine = create_engine(
    settings.DATABASE_URL,
    poolclass=QueuePool,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_recycle=settings.DB_POOL_RECYCLE,
    pool_pre_ping=True,  # Verify connections before using
    echo=settings.DB_ECHO,  # Log SQL queries in debug mode
)

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,  # Keep objects in session after commit
)


def get_db() -> Session:
    """Dependency for FastAPI to get database session.
    
    Rules:   must yield session; must close session even on exceptions
    message: claude-sonnet-4-6 | 2024-01-15 | consider adding session metrics and monitoring
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()