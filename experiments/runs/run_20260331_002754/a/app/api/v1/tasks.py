"""app/api/v1/tasks.py — Scheduled task management endpoints.

exports: router
used_by: app/api/v1/router.py -> tasks router
rules:   all task operations require authentication
agent:   claude-sonnet-4-6 | anthropic | 2026-03-31 | s_20260331_001 | created stub router to unblock startup
"""

from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import get_current_user, get_services
from app.services import ServiceContainer

router = APIRouter()


@router.get("/")
async def list_tasks(
    services: ServiceContainer = Depends(get_services),
    current_user: Any = Depends(get_current_user),
):
    """List scheduled tasks for current user."""
    try:
        return await services.tasks.list_tasks(user_id=current_user.id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_task(
    task_data: dict,
    services: ServiceContainer = Depends(get_services),
    current_user: Any = Depends(get_current_user),
):
    """Create a new scheduled task."""
    try:
        return await services.tasks.create_task(user_id=current_user.id, **task_data)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{task_id}")
async def get_task(
    task_id: int,
    services: ServiceContainer = Depends(get_services),
    current_user: Any = Depends(get_current_user),
):
    """Get a specific scheduled task."""
    try:
        return await services.tasks.get_task(task_id=task_id, user_id=current_user.id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: int,
    services: ServiceContainer = Depends(get_services),
    current_user: Any = Depends(get_current_user),
):
    """Delete a scheduled task."""
    try:
        await services.tasks.delete_task(task_id=task_id, user_id=current_user.id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
