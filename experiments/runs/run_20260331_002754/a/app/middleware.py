"""app/middleware.py — Custom FastAPI middleware.

exports: setup_middleware(app: FastAPI) -> None
used_by: app/main.py → create_app()
rules:   middleware order matters: CORS first, then security headers, then request processing
agent:   Product Architect | 2024-03-30 | implemented security and logging middleware
         message: "consider adding request ID tracking for distributed tracing"
"""

import time
import uuid
from typing import Callable, Optional

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
import logging

logger = logging.getLogger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Add request ID to every request for tracing.
    
    Rules:
        Generates UUID for each request if not provided in headers
        Adds X-Request-ID to response headers
        Logs request ID with all log messages for correlation
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Get request ID from headers or generate new one
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # Add request ID to request state
        request.state.request_id = request_id
        
        # Process request
        response = await call_next(request)
        
        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        
        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """Log request and response details.
    
    Rules:
        Logs method, path, status code, and response time
        Excludes health checks from detailed logging
        Includes request ID in logs
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip logging for health checks
        if request.url.path == "/health":
            return await call_next(request)
        
        # Start timer
        start_time = time.time()
        
        # Get request ID
        request_id = getattr(request.state, "request_id", "unknown")
        
        # Log request
        logger.info(
            f"Request started: {request.method} {request.url.path} "
            f"[ID: {request_id}] [Client: {request.client.host if request.client else 'unknown'}]"
        )
        
        # Process request
        response = await call_next(request)
        
        # Calculate response time
        response_time = time.time() - start_time
        
        # Log response
        logger.info(
            f"Request completed: {request.method} {request.url.path} "
            f"-> {response.status_code} [{response_time:.3f}s] "
            f"[ID: {request_id}]"
        )
        
        # Add response time header
        response.headers["X-Response-Time"] = f"{response_time:.3f}"
        
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses.
    
    Rules:
        Implements security best practices from OWASP
        Configurable via environment variables
        Different settings for development vs production
    """
    
    def __init__(self, app, environment: str = "development"):
        super().__init__(app)
        self.environment = environment
        
        # Security headers configuration
        self.headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
        }
        
        # Additional headers for production
        if environment == "production":
            self.headers.update({
                "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
                "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';",
                "Referrer-Policy": "strict-origin-when-cross-origin",
            })
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Add security headers
        for header, value in self.headers.items():
            response.headers[header] = value
        
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware using Redis.
    
    Rules:
        Uses Redis for distributed rate limiting
        Different limits for authenticated vs anonymous users
        Configurable via environment variables
    """
    
    def __init__(self, app, redis_client, config):
        super().__init__(app)
        self.redis = redis_client
        self.config = config
        
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for certain paths
        if request.url.path in ["/health", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)
        
        # Get rate limit key based on user or IP
        user_id = getattr(request.state, "user_id", None)
        if user_id:
            rate_limit_key = f"rate_limit:user:{user_id}"
            limit = self.config.RATE_LIMIT_PER_MINUTE * 2  # Higher limit for authenticated users
        else:
            client_ip = request.client.host if request.client else "unknown"
            rate_limit_key = f"rate_limit:ip:{client_ip}"
            limit = self.config.RATE_LIMIT_PER_MINUTE
        
        # Check rate limit
        allowed = await self.redis.rate_limit(
            key=rate_limit_key,
            limit=limit,
            window=60,  # 1 minute window
        )
        
        if not allowed:
            # Return 429 Too Many Requests
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Too many requests",
                    "retry_after": 60,
                },
                headers={"Retry-After": "60"},
            )
        
        return await call_next(request)


class DBConnectionMiddleware(BaseHTTPMiddleware):
    """Ensure database connection is available for each request.
    
    Rules:
        Checks database connection at start of request
        Attempts reconnection if connection is lost
        Logs connection issues but doesn't fail the request immediately
    """
    
    def __init__(self, app, db):
        super().__init__(app)
        self.db = db
        
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Check database connection
        if not self.db.is_connected():
            logger.warning("Database connection lost, attempting to reconnect...")
            try:
                await self.db.connect()
                logger.info("Database reconnected successfully")
            except Exception as e:
                logger.error(f"Failed to reconnect to database: {e}")
                # Continue anyway - some endpoints might work without DB
        
        return await call_next(request)


def setup_middleware(app: FastAPI) -> None:
    """Configure all middleware for the application.
    
    Args:
        app: FastAPI application instance
        
    Rules:
        Order matters - middleware are applied in reverse order of addition
        Add middleware in the order you want them to process requests
        Last added = first to process request, last to process response
    """
    config = app.state.config
    
    # 1. CORS middleware (must be first)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Response-Time"],
    )
    
    # 2. GZip middleware
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    # 3. Security headers middleware
    app.add_middleware(SecurityHeadersMiddleware, environment=config.ENVIRONMENT)
    
    # 4. Request ID middleware
    app.add_middleware(RequestIDMiddleware)
    
    # 5. Logging middleware
    app.add_middleware(LoggingMiddleware)
    
    # 6. Database connection middleware (if db is available)
    if hasattr(app.state, "db"):
        app.add_middleware(DBConnectionMiddleware, db=app.state.db)
    
    # 7. Rate limiting middleware (if redis is available)
    if hasattr(app.state, "redis"):
        app.add_middleware(RateLimitMiddleware, 
                          redis_client=app.state.redis,
                          config=config)
    
    logger.info("Middleware setup complete")