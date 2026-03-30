"""app/api/v1/admin.py — Admin-only endpoints.

exports: router
used_by: app/api/v1/router.py -> admin router
rules:   all endpoints require superuser role; never expose raw DB objects
agent:   claude-sonnet-4-6 | anthropic | 2026-03-31 | s_20260331_001 | created stub router to unblock startup
"""

from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import get_current_user, get_services
from app.services import ServiceContainer

router = APIRouter()


@router.get("/users")
async def list_all_users(
    services: ServiceContainer = Depends(get_services),
    current_user: Any = Depends(get_current_user),
):
    """List all users (admin only)."""
    if not getattr(current_user, "is_superuser", False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    try:
        return await services.users.list_all_users()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/stats")
async def platform_stats(
    services: ServiceContainer = Depends(get_services),
    current_user: Any = Depends(get_current_user),
):
    """Get platform-wide statistics (admin only)."""
    if not getattr(current_user, "is_superuser", False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    return {"status": "ok", "message": "stats endpoint — implementation pending"}
