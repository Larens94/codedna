"""app/middleware/__init__.py — FastAPI middleware for security, logging, etc.

exports: setup_middleware(app: FastAPI) -> None
used_by: app/main.py → create_app() → middleware setup
rules:   middleware order matters; security headers first, logging last
agent:   Product Architect | 2024-03-30 | created middleware setup function
         message: "verify CORS configuration allows frontend origins"
"""

import time
import logging
from typing import Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging HTTP requests and responses."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Log request and response details.
        
        Rules:
            Logs method, path, status code, and response time
            Excludes health check endpoints from detailed logging
        """
        # Skip logging for health checks
        if request.url.path in ["/health", "/metrics"]:
            return await call_next(request)
        
        start_time = time.time()
        
        # Log request
        logger.info(
            f"Request: {request.method} {request.url.path} "
            f"Client: {request.client.host if request.client else 'unknown'}"
        )
        
        # Process request
        response = await call_next(request)
        
        # Calculate response time
        process_time = time.time() - start_time
        
        # Log response
        logger.info(
            f"Response: {request.method} {request.url.path} "
            f"Status: {response.status_code} "
            f"Duration: {process_time:.3f}s"
        )
        
        # Add header with response time
        response.headers["X-Process-Time"] = str(process_time)
        
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware for adding security headers."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add security headers to response.
        
        Rules:
            Implements security best practices
            Headers help prevent common web vulnerabilities
        """
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        
        # CSP header (adjust based on your needs)
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "form-action 'self'; "
            "base-uri 'self'"
        )
        response.headers["Content-Security-Policy"] = csp
        
        return response


def setup_middleware(app: FastAPI) -> None:
    """Setup all middleware for the application.
    
    Args:
        app: FastAPI application instance
        
    Rules:
        Order is important - execute in this order:
        1. TrustedHostMiddleware
        2. CORSMiddleware
        3. GZipMiddleware
        4. SecurityHeadersMiddleware
        5. LoggingMiddleware
    """
    # Get config from app state
    config = app.state.config
    
    # 1. Trusted hosts (only in production)
    if config.ENVIRONMENT == "production":
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=["*"],  # Configure allowed hosts in production
        )
    
    # 2. CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Process-Time"],
    )
    
    # 3. GZip compression
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    # 4. Security headers
    app.add_middleware(SecurityHeadersMiddleware)
    
    # 5. Logging
    app.add_middleware(LoggingMiddleware)
    
    logger.info("Middleware setup complete")