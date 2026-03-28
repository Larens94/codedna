#!/usr/bin/env python3
"""
main.py — API Gateway for distributed trading system with Circuit Breaker and Rate Limiting.

exports: create_app() -> FastAPI, CircuitBreaker, RateLimiter
used_by: [cascade] → all services depend on API Gateway
rules:   Must implement Circuit Breaker pattern, Rate Limiting (1000 req/min), Correlation ID tracking
agent:   deepseek-chat | 2026-03-29 | Created API Gateway with Circuit Breaker and Rate Limiting patterns
"""

import time
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import httpx

# ============================================================================
# CIRCUIT BREAKER PATTERN
# ============================================================================

class CircuitBreaker:
    """Circuit Breaker pattern for downstream service failure protection."""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 30):
        """Initialize circuit breaker.
        
        Rules:
          - Closed state: Normal operation, requests pass through
          - Open state: Circuit open, requests fail fast
          - Half-open state: Testing if service recovered
          - Must track failures and successes
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self.failure_count = 0
        self.last_failure_time = None
        self.last_success_time = None
    
    def record_failure(self):
        """Record a failure and update circuit state."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            print(f"⚠️ Circuit breaker OPENED after {self.failure_count} failures")
    
    def record_success(self):
        """Record a success and update circuit state."""
        self.failure_count = 0
        self.last_success_time = time.time()
        
        if self.state == "HALF_OPEN":
            self.state = "CLOSED"
            print("✅ Circuit breaker CLOSED after successful test")
    
    def can_execute(self) -> bool:
        """Check if request can be executed based on circuit state."""
        if self.state == "CLOSED":
            return True
        
        if self.state == "OPEN":
            # Check if recovery timeout has passed
            if self.last_failure_time and (time.time() - self.last_failure_time) > self.recovery_timeout:
                self.state = "HALF_OPEN"
                print("🔄 Circuit breaker HALF-OPEN for testing")
                return True
            return False
        
        if self.state == "HALF_OPEN":
            return True
        
        return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get circuit breaker status."""
        return {
            "state": self.state,
            "failure_count": self.failure_count,
            "failure_threshold": self.failure_threshold,
            "last_failure_time": self.last_failure_time,
            "last_success_time": self.last_success_time,
            "recovery_timeout": self.recovery_timeout
        }

# ============================================================================
# RATE LIMITER PATTERN
# ============================================================================

class RateLimiter:
    """Rate Limiter pattern (1000 requests per minute)."""
    
    def __init__(self, requests_per_minute: int = 1000):
        """Initialize rate limiter.
        
        Rules:
          - Track requests per client IP
          - Limit to 1000 requests per minute
          - Use sliding window algorithm
          - Return 429 Too Many Requests when limit exceeded
        """
        self.requests_per_minute = requests_per_minute
        self.requests: Dict[str, List[float]] = {}
    
    def is_allowed(self, client_ip: str) -> bool:
        """Check if request from client IP is allowed."""
        now = time.time()
        minute_ago = now - 60
        
        # Clean old requests
        if client_ip in self.requests:
            self.requests[client_ip] = [req_time for req_time in self.requests[client_ip] if req_time > minute_ago]
        else:
            self.requests[client_ip] = []
        
        # Check if limit exceeded
        if len(self.requests[client_ip]) >= self.requests_per_minute:
            return False
        
        # Add current request
        self.requests[client_ip].append(now)
        return True
    
    def get_client_stats(self, client_ip: str) -> Dict[str, Any]:
        """Get rate limiting stats for a client."""
        if client_ip not in self.requests:
            return {"requests_last_minute": 0, "limit": self.requests_per_minute}
        
        now = time.time()
        minute_ago = now - 60
        recent_requests = [req_time for req_time in self.requests[client_ip] if req_time > minute_ago]
        
        return {
            "requests_last_minute": len(recent_requests),
            "limit": self.requests_per_minute,
            "remaining": max(0, self.requests_per_minute - len(recent_requests))
        }

# ============================================================================
# MODELS
# ============================================================================

class HealthResponse(BaseModel):
    """Health check response model."""
    status: str = Field(..., description="Service status")
    timestamp: datetime = Field(default_factory=datetime.now)
    services: Dict[str, str] = Field(default_factory=dict)
    circuit_breakers: Dict[str, Dict[str, Any]] = Field(default_factory=dict)

class OrderRequest(BaseModel):
    """Order request model."""
    user_id: int = Field(..., description="User ID")
    items: List[Dict[str, Any]] = Field(..., description="Order items")
    correlation_id: Optional[str] = Field(None, description="Correlation ID for tracing")

class InventoryRequest(BaseModel):
    """Inventory request model."""
    product_id: int = Field(..., description="Product ID")
    quantity: int = Field(..., description="Quantity to check/reserve")
    correlation_id: Optional[str] = Field(None, description="Correlation ID for tracing")

# ============================================================================
# API GATEWAY APPLICATION
# ============================================================================

class APIGateway:
    """API Gateway for distributed trading system."""
    
    def __init__(self):
        """Initialize API Gateway.
        
        Rules:
          - Must route requests to appropriate services
          - Must track correlation IDs for distributed tracing
          - Must implement health check endpoint
          - Must handle service failures gracefully
        """
        self.order_service_circuit = CircuitBreaker(failure_threshold=3, recovery_timeout=15)
        self.inventory_service_circuit = CircuitBreaker(failure_threshold=3, recovery_timeout=15)
        self.rate_limiter = RateLimiter(requests_per_minute=1000)
        
        # Service URLs (in production would be configurable)
        self.order_service_url = "http://localhost:8001"
        self.inventory_service_url = "http://localhost:8002"
        
        self.http_client = httpx.AsyncClient(timeout=10.0)
    
    async def route_to_order_service(self, request: OrderRequest, correlation_id: str) -> Dict[str, Any]:
        """Route request to Order Service with Circuit Breaker protection."""
        
        # Check circuit breaker
        if not self.order_service_circuit.can_execute():
            raise HTTPException(
                status_code=503,
                detail="Order Service unavailable (circuit breaker open)"
            )
        
        try:
            # Make request to Order Service
            response = await self.http_client.post(
                f"{self.order_service_url}/orders",
                json={
                    "user_id": request.user_id,
                    "items": request.items,
                    "correlation_id": correlation_id
                },
                headers={"X-Correlation-ID": correlation_id}
            )
            response.raise_for_status()
            
            # Record success
            self.order_service_circuit.record_success()
            return response.json()
            
        except Exception as e:
            # Record failure
            self.order_service_circuit.record_failure()
            raise HTTPException(
                status_code=502,
                detail=f"Order Service error: {str(e)}"
            )
    
    async def route_to_inventory_service(self, request: InventoryRequest, correlation_id: str) -> Dict[str, Any]:
        """Route request to Inventory Service with Circuit Breaker protection."""
        
        # Check circuit breaker
        if not self.inventory_service_circuit.can_execute():
            raise HTTPException(
                status_code=503,
                detail="Inventory Service unavailable (circuit breaker open)"
            )
        
        try:
            # Make request to Inventory Service
            response = await self.http_client.get(
                f"{self.inventory_service_url}/inventory/{request.product_id}/check",
                params={"quantity": request.quantity},
                headers={"X-Correlation-ID": correlation_id}
            )
            response.raise_for_status()
            
            # Record success
            self.inventory_service_circuit.record_success()
            return response.json()
            
        except Exception as e:
            # Record failure
            self.inventory_service_circuit.record_failure()
            raise HTTPException(
                status_code=502,
                detail=f"Inventory Service error: {str(e)}"
            )
    
    async def health_check(self) -> HealthResponse:
        """Perform health check of all services."""
        services_status = {}
        circuit_status = {}
        
        # Check Order Service
        try:
            response = await self.http_client.get(f"{self.order_service_url}/health", timeout=5.0)
            services_status["order_service"] = "healthy" if response.status_code == 200 else "unhealthy"
        except:
            services_status["order_service"] = "unreachable"
        
        # Check Inventory Service
        try:
            response = await self.http_client.get(f"{self.inventory_service_url}/health", timeout=5.0)
            services_status["inventory_service"] = "healthy" if response.status_code == 200 else "unhealthy"
        except:
            services_status["inventory_service"] = "unreachable"
        
        # Get circuit breaker status
        circuit_status["order_service"] = self.order_service_circuit.get_status()
        circuit_status["inventory_service"] = self.inventory_service_circuit.get_status()
        
        # Determine overall status
        overall_status = "healthy"
        if any(status != "healthy" for status in services_status.values()):
            overall_status = "degraded"
        if all(status == "unreachable" for status in services_status.values()):
            overall_status = "unhealthy"
        
        return HealthResponse(
            status=overall_status,
            services=services_status,
            circuit_breakers=circuit_status
        )
    
    async def close(self):
        """Cleanup resources."""
        await self.http_client.aclose()

# ============================================================================
# FASTAPI APPLICATION
# ============================================================================

def create_app() -> FastAPI:
    """Create and configure FastAPI application.
    
    exports: create_app() -> FastAPI
    """
    app = FastAPI(
        title="Trading System API Gateway",
        description="API Gateway with Circuit Breaker and Rate Limiting patterns",
        version="1.0.0"
    )
    
    # Create API Gateway instance
    api_gateway = APIGateway()
    
    # Dependency to get client IP
    def get_client_ip(request: Request) -> str:
        """Extract client IP from request."""
        return request.client.host if request.client else "unknown"
    
    # Dependency to get or generate correlation ID
    def get_correlation_id(request: Request) -> str:
        """Get or generate correlation ID for distributed tracing."""
        correlation_id = request.headers.get("X-Correlation-ID")
        if not correlation_id:
            correlation_id = str(uuid.uuid4())
        return correlation_id
    
    # Middleware for rate limiting
    @app.middleware("http")
    async def rate_limit_middleware(request: Request, call_next):
        """Middleware for rate limiting."""
        client_ip = get_client_ip(request)
        
        if not api_gateway.rate_limiter.is_allowed(client_ip):
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded",
                    "limit": 1000,
                    "period": "minute"
                }
            )
        
        response = await call_next(request)
        return response
    
    # Middleware for correlation ID
    @app.middleware("http")
    async def correlation_id_middleware(request: Request, call_next):
        """Middleware to add correlation ID to response."""
        correlation_id = get_correlation_id(request)
        
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response
    
    # Health check endpoint
    @app.get("/health", response_model=HealthResponse)
    async def health():
        """Health check endpoint."""
        return await api_gateway.health_check()
    
    # Order endpoints
    @app.post("/orders")
    async def create_order(
        order: OrderRequest,
        correlation_id: str = Depends(get_correlation_id)
    ):
        """Create a new order."""
        return await api_gateway.route_to_order_service(order, correlation_id)
    
    # Inventory endpoints
    @app.get("/inventory/{product_id}/check")
    async def check_inventory(
        product_id: int,
        quantity: int,
        correlation_id: str = Depends(get_correlation_id)
    ):
        """Check inventory availability."""
        request = InventoryRequest(product_id=product_id, quantity=quantity)
        return await api_gateway.route_to_inventory_service(request, correlation_id)
    
    # Rate limiting stats endpoint
    @app.get("/rate-limit/stats")
    async def get_rate_limit_stats(client_ip: str = Depends(get_client_ip)):
        """Get rate limiting statistics for client."""
        return api_gateway.rate_limiter.get_client_stats(client_ip)
    
    # Circuit breaker status endpoint
    @app.get("/circuit-breakers/status")
    async def get_circuit_breaker_status():
        """Get circuit breaker status."""
        return {
            "order_service": api_gateway.order_service_circuit.get_status(),
            "inventory_service": api_gateway.inventory_service_circuit.get_status()
        }
    
    # Cleanup on shutdown
    @app.on_event("shutdown")
    async def shutdown_event():
        await api_gateway.close()
    
    return app

# Create app instance
app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)