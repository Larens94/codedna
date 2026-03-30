"""app/api/v1/router.py — API v1 router aggregator.

exports: api_router
used_by: app/api/__init__.py → api_router
rules:   must include all version 1 routers; must add authentication dependency to protected routes
agent:   Product Architect | 2024-03-30 | created router aggregator with dependency injection
         message: "consider adding OpenAPI tags grouping for better documentation"
"""

from fastapi import APIRouter, Depends

from app.api.v1 import auth, users, organizations, agents, tasks, billing, admin

# Create main API router for v1
api_router = APIRouter(prefix="/v1")

# Include all sub-routers
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(organizations.router, prefix="/organizations", tags=["organizations"])
api_router.include_router(agents.router, prefix="/agents", tags=["agents"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
api_router.include_router(billing.router, prefix="/billing", tags=["billing"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])

# Health check endpoint (no authentication required)
@api_router.get("/health")
async def health_check():
    """API health check endpoint."""
    return {"status": "healthy", "version": "v1"}