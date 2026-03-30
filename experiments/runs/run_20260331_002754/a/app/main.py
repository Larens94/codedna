"""app/main.py — FastAPI application factory with dependency injection.

exports: create_app(config: Optional[Config] = None) -> FastAPI
used_by: main.py → application entry point, tests → test fixture
rules:   must initialize services in correct order: config → db → redis → services → routers
agent:   Product Architect | 2024-03-30 | implemented app factory with proper DI
         message: "check if we need lazy initialization for some heavy services like LLM clients"
"""

import logging
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.config import Config, get_config
from app.database import Database
from app.redis import RedisClient
from app.services import ServiceContainer
from app.api.v1 import api_router
from app.middleware import setup_middleware
from app.exceptions import setup_exception_handlers

logger = logging.getLogger(__name__)


def create_app(config: Optional[Config] = None) -> FastAPI:
    """Create and configure the FastAPI application.
    
    Args:
        config: Optional Config instance. If None, loads from environment.
        
    Returns:
        FastAPI application instance with all dependencies initialized.
    
    Rules:
        Order matters: config → logging → db → redis → services → routers → middleware
        All services must be registered in app.state for dependency injection
    """
    # 1. Load configuration
    if config is None:
        config = get_config()
    
    # 2. Setup logging
    logging.basicConfig(
        level=config.LOG_LEVEL,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger.info(f"Starting AgentHub application in {config.ENVIRONMENT} mode")
    
    # 3. Create FastAPI app
    app = FastAPI(
        title="AgentHub API",
        description="Multi-tenant SaaS platform for AI agents",
        version="1.0.0",
        docs_url="/docs" if config.ENVIRONMENT != "production" else None,
        redoc_url="/redoc" if config.ENVIRONMENT != "production" else None,
    )
    
    # 4. Store config in app state
    app.state.config = config
    
    # 5. Initialize core infrastructure
    logger.info("Initializing database connection...")
    db = Database(config.DATABASE_URL)
    app.state.db = db
    
    logger.info("Initializing Redis client...")
    redis_client = RedisClient(config.REDIS_URL)
    app.state.redis = redis_client
    
    # 6. Initialize service container
    logger.info("Initializing service container...")
    services = ServiceContainer(db=db, redis=redis_client, config=config)
    app.state.services = services
    
    # 7. Setup middleware
    logger.info("Setting up middleware...")
    setup_middleware(app)
    
    # 8. Setup exception handlers
    logger.info("Setting up exception handlers...")
    setup_exception_handlers(app)
    
    # 9. Include API routers
    logger.info("Registering API routes...")
    app.include_router(api_router, prefix="/api/v1")
    
    # 10. Add health check endpoint
    @app.get("/health")
    async def health_check():
        """Health check endpoint for load balancers and monitoring."""
        return {
            "status": "healthy",
            "environment": config.ENVIRONMENT,
            "database": "connected" if db.is_connected() else "disconnected",
            "redis": "connected" if redis_client.is_connected() else "disconnected",
        }
    
    # 11. Startup event - ensure connections
    @app.on_event("startup")
    async def startup_event():
        """Initialize connections on startup."""
        await db.connect()
        await redis_client.connect()
        logger.info("Application startup complete")
    
    # 12. Shutdown event - cleanup
    @app.on_event("shutdown")
    async def shutdown_event():
        """Cleanup connections on shutdown."""
        await redis_client.disconnect()
        await db.disconnect()
        logger.info("Application shutdown complete")
    
    logger.info(f"Application created successfully (debug={config.DEBUG})")
    return app


# For backward compatibility
app = create_app()