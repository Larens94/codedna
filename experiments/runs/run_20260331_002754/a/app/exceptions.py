"""app/exceptions.py — Custom exceptions and exception handlers.

exports: setup_exception_handlers(app: FastAPI) -> None, AgentHubError, ValidationError, NotFoundError, AuthError, PermissionError, CreditExhaustedError, AgentError, AgentTimeoutError, ServiceUnavailableError
used_by: app/main.py → create_app() → exception handlers, all services → raise custom exceptions
rules:   all exceptions must be properly serialized to JSON; include error codes for client handling
agent:   Product Architect | 2024-03-30 | created exception hierarchy and handlers
         message: "verify that all exceptions include proper HTTP status codes"
"""

import logging
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ErrorResponse(BaseModel):
    """Standard error response format.
    
    Rules:
        All API errors return this format
        Code is machine-readable error identifier
        Detail is human-readable message
    """
    code: str
    detail: str
    message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class AgentHubError(Exception):
    """Base exception for all AgentHub errors.
    
    Rules:
        All custom exceptions inherit from this
        Includes HTTP status code and error code
    """
    
    def __init__(
        self,
        detail: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        code: str = "internal_error",
        message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.detail = detail
        self.status_code = status_code
        self.code = code
        self.message = message or detail
        self.metadata = metadata
        super().__init__(detail)


class ValidationError(AgentHubError):
    """Validation error for invalid requests."""
    
    def __init__(
        self,
        detail: str,
        message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="validation_error",
            message=message,
            metadata=metadata,
        )


class NotFoundError(AgentHubError):
    """Resource not found error."""
    
    def __init__(
        self,
        resource: str,
        identifier: Any,
        message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        detail = f"{resource} with identifier '{identifier}' not found"
        super().__init__(
            detail=detail,
            status_code=status.HTTP_404_NOT_FOUND,
            code="not_found",
            message=message or detail,
            metadata=metadata,
        )


class AuthError(AgentHubError):
    """Authentication error."""
    
    def __init__(
        self,
        detail: str = "Authentication required",
        message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="authentication_error",
            message=message or detail,
            metadata=metadata,
        )


class PermissionError(AgentHubError):
    """Permission denied error."""
    
    def __init__(
        self,
        detail: str = "Permission denied",
        message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_403_FORBIDDEN,
            code="permission_error",
            message=message or detail,
            metadata=metadata,
        )


class RateLimitError(AgentHubError):
    """Rate limit exceeded error."""
    
    def __init__(
        self,
        detail: str = "Rate limit exceeded",
        message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            code="rate_limit_exceeded",
            message=message or detail,
            metadata=metadata,
        )


class ServiceError(AgentHubError):
    """External service error."""
    
    def __init__(
        self,
        service: str,
        detail: str,
        message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        detail = f"{service} error: {detail}"
        super().__init__(
            detail=detail,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="service_error",
            message=message or detail,
            metadata=metadata,
        )


class CreditExhaustedError(AgentHubError):
    """Credit exhausted error (HTTP 402 Payment Required)."""
    
    def __init__(
        self,
        detail: str = "Insufficient credits",
        message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            code="credit_exhausted",
            message=message or detail,
            metadata=metadata,
        )


class AgentError(AgentHubError):
    """Agent execution error."""
    
    def __init__(
        self,
        detail: str,
        message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="agent_error",
            message=message,
            metadata=metadata,
        )


class AgentTimeoutError(AgentHubError):
    """Agent execution timeout error."""
    
    def __init__(
        self,
        detail: str = "Agent execution timeout",
        message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            code="agent_timeout",
            message=message or detail,
            metadata=metadata,
        )


class ServiceUnavailableError(AgentHubError):
    """Service unavailable error."""
    
    def __init__(
        self,
        detail: str = "Service temporarily unavailable",
        message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="service_unavailable",
            message=message or detail,
            metadata=metadata,
        )


async def agenthub_exception_handler(
    request: Request,
    exc: AgentHubError,
) -> JSONResponse:
    """Handle AgentHubError exceptions.
    
    Rules:
        Returns standardized error response format
        Logs error details for debugging
    """
    logger.error(
        f"AgentHubError: {exc.code} - {exc.detail}",
        extra={
            "status_code": exc.status_code,
            "path": request.url.path,
            "method": request.method,
            "metadata": exc.metadata,
        },
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            code=exc.code,
            detail=exc.detail,
            message=exc.message,
            metadata=exc.metadata,
        ).dict(exclude_none=True),
    )


async def http_exception_handler(
    request: Request,
    exc: HTTPException,
) -> JSONResponse:
    """Handle FastAPI HTTPException.
    
    Rules:
        Converts HTTPException to standardized format
    """
    logger.warning(
        f"HTTPException: {exc.status_code} - {exc.detail}",
        extra={
            "path": request.url.path,
            "method": request.method,
        },
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            code="http_error",
            detail=str(exc.detail),
            message=str(exc.detail),
        ).dict(exclude_none=True),
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Handle request validation errors.
    
    Rules:
        Extracts validation error details
        Returns formatted validation errors
    """
    errors = []
    for error in exc.errors():
        errors.append({
            "loc": error["loc"],
            "msg": error["msg"],
            "type": error["type"],
        })
    
    logger.warning(
        f"Validation error: {errors}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "errors": errors,
        },
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(
            code="validation_error",
            detail="Request validation failed",
            message="Please check your request data",
            metadata={"errors": errors},
        ).dict(exclude_none=True),
    )


async def generic_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Handle all other exceptions.
    
    Rules:
        Catches unexpected exceptions
        Returns generic error to avoid leaking details
        Logs full exception for debugging
    """
    logger.exception(
        f"Unhandled exception: {exc}",
        extra={
            "path": request.url.path,
            "method": request.method,
        },
    )
    
    # In production, don't expose internal error details
    if hasattr(request.app.state, "config"):
        config = request.app.state.config
        if config.ENVIRONMENT == "production":
            detail = "Internal server error"
        else:
            detail = str(exc)
    else:
        detail = "Internal server error"
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            code="internal_error",
            detail=detail,
            message="An unexpected error occurred",
        ).dict(exclude_none=True),
    )


def setup_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers.
    
    Args:
        app: FastAPI application instance
    """
    # Register custom exception handlers
    app.add_exception_handler(AgentHubError, agenthub_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
    
    logger.info("Exception handlers setup complete")


# ── Aliases for services that use alternate names ─────────────────────────────
AuthenticationError = AuthError
AuthorizationError  = PermissionError
InvalidTokenError   = AuthError


class ConflictError(AgentHubError):
    """Raised when a resource already exists or conflicts with existing state."""
    def __init__(self, detail: str = "Conflict", **kwargs):
        super().__init__(detail=detail, status_code=409, code="CONFLICT", **kwargs)