"""app/dependencies.py — FastAPI dependencies for dependency injection.

exports: get_db_session(), get_redis_client(), get_services(), get_current_user()
used_by: all API endpoints -> dependency injection
rules:   dependencies must be async where appropriate; proper error handling
agent:   Product Architect | 2024-03-30 | created FastAPI dependencies
         claude-sonnet-4-6 | anthropic | 2026-03-31 | s_20260331_001 | fixed syntax errors (em-dash, orphaned block, duplicate function)
         message: "verify that database sessions are properly closed after request"
"""

import logging
from typing import AsyncGenerator, Any

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.redis import get_redis
from app.services import ServiceContainer

logger = logging.getLogger(__name__)

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session dependency.

    Yields:
        AsyncSession: Database session

    Rules:
        Session is automatically closed after request
        Used as FastAPI dependency: Depends(get_db_session)
    """
    async for session in get_session():
        yield session


async def get_redis_client():
    """Get Redis client dependency."""
    return get_redis()


async def get_services(request: Request) -> ServiceContainer:
    """Get service container dependency."""
    return request.app.state.services


async def get_current_user(
    services: ServiceContainer = Depends(get_services),
    token: str = Depends(oauth2_scheme),
) -> Any:
    """Get current authenticated user dependency.

    Raises:
        HTTPException 401: If token is missing or invalid.
    """
    try:
        return await services.auth.get_current_user(token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
