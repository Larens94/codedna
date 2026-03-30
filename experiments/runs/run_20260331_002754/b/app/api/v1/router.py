"""API router for version 1 endpoints."""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    agents,
    marketplace,
    studio,
    tasks,
    usage,
    workspace,
    billing,
    memory,
)

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(agents.router, prefix="/agents", tags=["agents"])
api_router.include_router(marketplace.router, prefix="/marketplace", tags=["marketplace"])
api_router.include_router(studio.router, prefix="/studio", tags=["studio"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
api_router.include_router(usage.router, prefix="/usage", tags=["usage"])
api_router.include_router(workspace.router, prefix="/workspace", tags=["workspace"])
api_router.include_router(billing.router, prefix="/billing", tags=["billing"])
api_router.include_router(memory.router, prefix="/memory", tags=["memory"])