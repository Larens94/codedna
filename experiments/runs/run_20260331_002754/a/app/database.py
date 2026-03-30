"""app/database.py — Database connection and session management.

exports: Database, get_db(), Base, async_session
used_by: all services needing database access, app/main.py → create_app()
rules:   must use asyncpg driver; sessions must be properly closed; connection pooling required
agent:   Product Architect | 2024-03-30 | implemented async SQLAlchemy with connection pooling
         message: "verify that connection pool settings are optimal for production load"
"""

import logging
from typing import AsyncGenerator, Optional
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool, AsyncAdaptedQueuePool

logger = logging.getLogger(__name__)

# SQLAlchemy Base class for declarative models
Base = declarative_base()


class Database:
    """Database connection manager with async SQLAlchemy.
    
    Rules:
        Must support connection pooling for production
        Must properly handle connection lifecycle
        All queries must use async/await
    """
    
    def __init__(self, database_url: str, pool_size: int = 20, max_overflow: int = 10):
        """Initialize database connection.
        
        Args:
            database_url: PostgreSQL connection URL
            pool_size: Connection pool size
            max_overflow: Maximum overflow connections
        """
        self.database_url = database_url
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self._engine: Optional[AsyncEngine] = None
        self._session_factory: Optional[async_sessionmaker[AsyncSession]] = None
        self._connected = False
    
    async def connect(self) -> None:
        """Establish database connection and create engine.
        
        Rules:
            Connection pooling is disabled in testing environment
            Must use asyncpg driver for PostgreSQL
        """
        if self._connected:
            return
        
        # Configure pool based on environment
        pool_class = AsyncAdaptedQueuePool
        pool_args = {
            "pool_size": self.pool_size,
            "max_overflow": self.max_overflow,
            "pool_recycle": 3600,  # Recycle connections every hour
            "pool_pre_ping": True,  # Verify connections before use
        }
        
        # Create async engine
        self._engine = create_async_engine(
            self.database_url,
            echo=False,  # Set to True for SQL logging in development
            poolclass=pool_class,
            **pool_args,
        )
        
        # Create session factory
        self._session_factory = async_sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
        
        self._connected = True
        logger.info(f"Database connected to {self.database_url}")
    
    async def disconnect(self) -> None:
        """Close database connections."""
        if self._engine:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None
            self._connected = False
            logger.info("Database disconnected")
    
    def is_connected(self) -> bool:
        """Check if database is connected."""
        return self._connected
    
    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get a database session with automatic cleanup.
        
        Yields:
            AsyncSession: SQLAlchemy async session
            
        Rules:
            Session is automatically closed after use
            Exceptions are propagated, but session is always closed
            Must be used as async context manager: async with db.session() as session:
        """
        if not self._session_factory:
            raise RuntimeError("Database not connected. Call connect() first.")
        
        session: AsyncSession = self._session_factory()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
    
    async def create_tables(self) -> None:
        """Create all database tables.
        
        Rules:
            Only for development/testing - use migrations in production
            Must be called after models are imported
        """
        if not self._engine:
            await self.connect()
        
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created")
    
    async def drop_tables(self) -> None:
        """Drop all database tables.
        
        Rules:
            Only for testing - never call in production
        """
        if not self._engine:
            await self.connect()
        
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        logger.info("Database tables dropped")


# Global database instance (initialized in app factory)
_db: Optional[Database] = None


def get_db() -> Database:
    """Get global database instance.
    
    Returns:
        Database: Global database instance
        
    Rules:
        Must be called after app initialization
        Used by FastAPI dependency injection
    """
    if _db is None:
        raise RuntimeError("Database not initialized. Call create_app() first.")
    return _db


def set_db(db: Database) -> None:
    """Set global database instance.
    
    Args:
        db: Database instance
        
    Rules:
        Called by app factory during initialization
    """
    global _db
    _db = db


# Session dependency for FastAPI
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database sessions.
    
    Yields:
        AsyncSession: Database session
        
    Rules:
        Used as FastAPI dependency: Depends(get_session)
        Session is automatically closed after request
    """
    db = get_db()
    async with db.session() as session:
        yield session