"""main.py — FastAPI app factory and entry point.

exports: create_app() -> FastAPI, lifespan_context()
used_by: uvicorn server, test suite
rules:   must register all routers before returning app; lifespan must manage db connections
agent:   ProductArchitect | 2024-01-15 | updated to include all routers, frontend, static files
         message: "verify that all routers are imported and registered correctly"
"""

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles

from agenthub.db.session import engine, SessionLocal
from agenthub.db.models import Base
from agenthub.api import agents, auth, billing, scheduler, tasks, teams, usage
from agenthub.frontend.routes import router_frontend
from agenthub.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager for FastAPI app.
    
    Rules:   must create all tables on startup; must dispose engine on shutdown
    message: claude-sonnet-4-6 | 2024-01-15 | verify table creation doesn't drop existing data
    """
    # Startup: create tables
    Base.metadata.create_all(bind=engine)
    yield
    # Shutdown: dispose engine
    engine.dispose()


def create_app() -> FastAPI:
    """Create and configure FastAPI application.
    
    Rules:   must include all routers; must set up CORS and trusted hosts
    message: claude-sonnet-4-6 | 2024-01-15 | ensure CORS origins are configurable via settings
    """
    app = FastAPI(
        title="AgentHub API",
        description="Multi-agent orchestration platform with marketplace",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
    )
    
    # Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.ALLOWED_HOSTS,
    )
    
    # Static files
    static_dir = Path(__file__).parent / "frontend" / "static"
    static_dir.mkdir(exist_ok=True, parents=True)
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    
    # API Router registration
    app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
    app.include_router(agents.router, prefix="/api/v1/agents", tags=["agents"])
    app.include_router(billing.router, prefix="/api/v1/billing", tags=["billing"])
    app.include_router(scheduler.router, prefix="/api/v1/scheduler", tags=["scheduler"])
    app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["tasks"])
    app.include_router(teams.router, prefix="/api/v1/teams", tags=["teams"])
    app.include_router(usage.router, prefix="/api/v1/usage", tags=["usage"])
    
    # Frontend Router registration
    app.include_router(router_frontend)
    
    # Health check endpoint
    @app.get("/health")
    async def health_check() -> dict:
        return {"status": "healthy", "service": "agenthub"}
    
    @app.get("/api/v1/health")
    async def api_health_check() -> dict:
        return {"status": "healthy", "api": "v1"}
    
    return app


# Global app instance
app = create_app()