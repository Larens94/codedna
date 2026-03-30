"""app/dependencies.py — FastAPI dependencies for dependency injection.
"""app/dependencies.py — FastAPI dependencies for dependency injection.

exports: get_db_session(), get_redis(), get_services(), get_current_user()
used_by: all API endpoints → dependency injection
rules:   dependencies must be async where appropriate; proper error handling
agent:   Product Architect | 2024-03-30 | created FastAPI dependencies
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
    # This would typically get services from app state
    # For now, we'll create a simple implementation
    from fastapi import Request
    
    async def _get_services(request: Request) -> ServiceContainer:
        return request.app.state.services
    
    return await _get_services


async def get_current_user(
    services: ServiceContainer = Depends(get_services),
    token: str = Depends(oauth2_scheme),
) -> Any:
    """Get current authenticated user dependency.
    
    Args:
        services: Service container
        token: JWT access token
        
    Returns:
        User: Authenticated user
        
    Raises:
        HTTPException: If authentication fails
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
    """Get Redis client dependency.
    
    Returns:
        RedisClient: Redis client instance
    """
    return get_redis()


async def get_services(request: Request) -> ServiceContainer:
    """Get service container dependency.
    
    Args:
        request: FastAPI request object
        
    Returns:
        ServiceContainer: Service container with all business logic services
    """
    return request.app.state.services


async def get_current_user(
    services: ServiceContainer = Depends(get_services),
    token: str = Depends(oauth2_scheme),
) -> Any:
    """Get current authenticated user dependency.
    
    Args:
        services: Service container
        token: JWT access token
        
    Returns:
        User: Authenticated user
        
    Raises:
        HTTPException: If authentication fails
    """
    try:
        return await services.auth.get_current_user(token)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )