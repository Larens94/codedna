"""FastAPI application factory and main entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.api.v1 import api_router


def create_fastapi_app() -> FastAPI:
    """Create and configure FastAPI application.
    
    Returns:
        FastAPI application instance
    """
    app = FastAPI(
        title=settings.APP_NAME,
        description="AgentHub - AI Agent Marketplace SaaS Platform",
        version="1.0.0",
        openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
    )
    
    # Configure CORS
    if settings.CORS_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.CORS_ORIGINS,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    # Security middleware
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"] if settings.DEBUG else ["agenthub.com", "api.agenthub.com"],
    )
    
    # Register API router
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)
    
    # Health check endpoint (outside API prefix)
    @app.get("/health")
    async def health_check():
        """Health check endpoint for load balancers."""
        return {"status": "healthy", "service": settings.APP_NAME}
    
    @app.get("/ready")
    async def readiness_check():
        """Readiness check for dependencies."""
        # TODO: Check database connectivity
        return {"status": "ready", "service": settings.APP_NAME}
    
    @app.get("/live")
    async def liveness_check():
        """Liveness check for container orchestrators."""
        return {"status": "alive", "service": settings.APP_NAME}
    
    # Exception handlers
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request, exc):
        """Handle HTTP exceptions with RFC 7807 format."""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "type": "about:blank",
                "title": exc.detail,
                "detail": exc.detail,
                "instance": request.url.path,
            },
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request, exc):
        """Handle validation errors with RFC 7807 format."""
        errors = []
        for error in exc.errors():
            errors.append({
                "field": ".".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"],
            })
        
        return JSONResponse(
            status_code=422,
            content={
                "type": "https://tools.ietf.org/html/rfc7807#section-3.1",
                "title": "Validation Error",
                "detail": "One or more fields failed validation",
                "instance": request.url.path,
                "errors": errors,
            },
        )
    
    @app.exception_handler(Exception)
    async def generic_exception_handler(request, exc):
        """Handle generic exceptions with RFC 7807 format."""
        # Log the exception here
        return JSONResponse(
            status_code=500,
            content={
                "type": "about:blank",
                "title": "Internal Server Error",
                "detail": "An unexpected error occurred. Please try again later.",
                "instance": request.url.path,
            },
        )
    
    return app


# Create app instance
app = create_fastapi_app()