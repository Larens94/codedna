"""app/api/v1/__init__.py — API version 1 package.

exports: api_router
used_by: app/main.py -> include_router
rules:   all endpoints must include response models; must handle authentication via dependencies
agent:   Product Architect | 2024-03-30 | created API v1 structure
         claude-sonnet-4-6 | anthropic | 2026-03-31 | s_20260331_001 | added api_router re-export (was missing)
         message: "add API version header to all responses for future compatibility"
"""

from app.api.v1.router import api_router

__all__ = ["api_router"]
