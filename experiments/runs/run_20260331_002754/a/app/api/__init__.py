"""app/api/__init__.py — API layer package.

exports: api_router
used_by: app/main.py → create_app()
rules:   all API endpoints must be versioned; dependencies must be injected via FastAPI Depends
agent:   Product Architect | 2024-03-30 | created API package structure
         message: "ensure all routers include proper error handling and response models"
"""

from .v1.router import api_router

__all__ = ["api_router"]