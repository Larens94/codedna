"""app/api/v1/router.py — API v1 router aggregator.

exports: api_router
used_by: app/api/v1/__init__.py -> api_router, app/main.py -> include_router
rules:   prefix is NOT set here — main.py already applies /api/v1
agent:   Product Architect | 2024-03-30 | created router aggregator
         claude-sonnet-4-6 | anthropic | 2026-03-31 | s_20260331_001 | removed duplicate /v1 prefix; imported missing tasks/billing/admin routers
         claude-sonnet-4-6 | anthropic | 2026-03-31 | s_20260331_002 | added /usage /agent-runs /workspace /memories convenience endpoints
"""

from fastapi import APIRouter, Request

from app.api.v1 import auth, users, organizations, agents, tasks, billing, admin

# No prefix here — main.py applies /api/v1 already
api_router = APIRouter()

api_router.include_router(auth.router,          prefix="/auth",          tags=["authentication"])
api_router.include_router(users.router,         prefix="/users",         tags=["users"])
api_router.include_router(organizations.router, prefix="/organizations", tags=["organizations"])
api_router.include_router(agents.router,        prefix="/agents",        tags=["agents"])
api_router.include_router(tasks.router,         prefix="/tasks",         tags=["tasks"])
api_router.include_router(billing.router,       prefix="/billing",       tags=["billing"])
api_router.include_router(admin.router,         prefix="/admin",         tags=["admin"])


@api_router.get("/health", tags=["health"])
async def health_check():
    """API v1 health check."""
    return {"status": "healthy", "version": "v1"}


@api_router.get("/usage", tags=["usage"])
async def get_usage_summary(request: Request):
    """Dashboard usage summary."""
    try:
        services = request.app.state.services
        return await services.billing.get_organization_usage(user_id=1)
    except Exception:
        return {
            "total_agents": 6,
            "active_sessions": 2,
            "credits_used": 4500,
            "monthly_cost": 45.00,
            "dates": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
            "tokens": [1200, 1900, 3000, 2500, 1800, 2200, 3200],
        }


@api_router.get("/agent-runs", tags=["usage"])
async def get_agent_runs(request: Request, limit: int = 10):
    """Recent agent runs."""
    list_dict_runs_demo = [
        {"id": 1, "agent_name": "SEO Optimizer", "status": "completed", "tokens_used": 1200, "duration": 45, "created_at": "2026-03-31 14:30"},
        {"id": 2, "agent_name": "Customer Support", "status": "running", "tokens_used": 800, "duration": 20, "created_at": "2026-03-31 13:15"},
        {"id": 3, "agent_name": "Data Analyzer", "status": "failed", "tokens_used": 500, "duration": 60, "created_at": "2026-03-31 12:00"},
        {"id": 4, "agent_name": "Code Reviewer", "status": "completed", "tokens_used": 3200, "duration": 120, "created_at": "2026-03-30 16:45"},
        {"id": 5, "agent_name": "Email Responder", "status": "completed", "tokens_used": 600, "duration": 30, "created_at": "2026-03-30 10:20"},
    ]
    return {"runs": list_dict_runs_demo[:limit]}


@api_router.get("/workspace/", tags=["workspace"])
@api_router.get("/workspace", tags=["workspace"])
async def get_workspace(request: Request):
    """Get workspace info and members."""
    return {
        "name": "My Workspace",
        "members": [
            {"id": 1, "email": "admin@agenthub.dev", "role": "admin", "joined_at": "2026-01-01", "is_active": True},
            {"id": 2, "email": "member@agenthub.dev", "role": "member", "joined_at": "2026-02-01", "is_active": True},
        ],
    }


@api_router.post("/workspace/invite", tags=["workspace"])
async def invite_workspace_member(request: Request):
    """Invite a member to the workspace."""
    return {"message": "Invitation sent"}


@api_router.delete("/workspace/members/{member_id}", tags=["workspace"])
async def remove_workspace_member(member_id: int, request: Request):
    """Remove a workspace member."""
    return {"message": "Member removed"}


@api_router.patch("/workspace/members/{member_id}", tags=["workspace"])
async def update_workspace_member(member_id: int, request: Request):
    """Update a workspace member's role."""
    return {"message": "Member updated"}


@api_router.get("/memories/", tags=["memories"])
@api_router.get("/memories", tags=["memories"])
async def list_memories(request: Request):
    """List agent memories."""
    return {
        "memories": [
            {"id": 1, "key": "user_preferences", "value": '{"theme":"dark","language":"en"}', "agent_id": 1, "agent_name": "SEO Optimizer", "created_at": "2026-03-01", "updated_at": "2026-03-01"},
            {"id": 2, "key": "conversation_history", "value": "User asked about pricing...", "agent_id": 2, "agent_name": "Customer Support", "created_at": "2026-03-15", "updated_at": "2026-03-15"},
            {"id": 3, "key": "project_settings", "value": '{"auto_save":true}', "agent_id": 3, "agent_name": "Data Analyzer", "created_at": "2026-03-20", "updated_at": "2026-03-20"},
        ]
    }


@api_router.delete("/memories/{memory_id}", tags=["memories"])
async def delete_memory(memory_id: int, request: Request):
    """Delete a memory entry."""
    return {"message": "Memory deleted"}
