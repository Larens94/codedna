"""app/api/v1/schemas/admin.py — Pydantic schemas for admin endpoints.

exports: AdminUserUpdate, AdminOrganizationUpdate, SystemStatsResponse
used_by: app/api/v1/admin.py → request/response validation
rules:   admin endpoints require superuser role; sensitive operations must be audited
agent:   BackendEngineer | 2024-03-31 | created admin schemas with validation
         message: "consider adding audit log export functionality"
"""

from datetime import datetime, date
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, validator
from .base import BaseSchema, PaginatedResponse


class AdminUserUpdate(BaseSchema):
    """Schema for admin user updates."""
    email: Optional[str] = Field(None, description="User email")
    first_name: Optional[str] = Field(None, description="First name")
    last_name: Optional[str] = Field(None, description="Last name")
    username: Optional[str] = Field(None, description="Username")
    is_active: Optional[bool] = Field(None, description="Whether user is active")
    is_superuser: Optional[bool] = Field(None, description="Whether user is superuser")
    email_verified: Optional[bool] = Field(None, description="Whether email is verified")
    password: Optional[str] = Field(None, description="New password (will be hashed)")


class AdminOrganizationUpdate(BaseSchema):
    """Schema for admin organization updates."""
    name: Optional[str] = Field(None, description="Organization name")
    slug: Optional[str] = Field(None, description="Organization slug")
    description: Optional[str] = Field(None, description="Organization description")
    billing_email: Optional[str] = Field(None, description="Billing email")
    plan_tier: Optional[str] = Field(None, description="Plan tier")
    monthly_credit_limit: Optional[int] = Field(None, description="Monthly credit limit")
    is_active: Optional[bool] = Field(None, description="Whether organization is active")
    stripe_customer_id: Optional[str] = Field(None, description="Stripe customer ID")
    stripe_subscription_id: Optional[str] = Field(None, description="Stripe subscription ID")


class SystemStatsResponse(BaseSchema):
    """Schema for system statistics response."""
    total_users: int = Field(..., description="Total users")
    active_users: int = Field(..., description="Active users (last 30 days)")
    total_organizations: int = Field(..., description="Total organizations")
    active_organizations: int = Field(..., description="Active organizations")
    total_agents: int = Field(..., description="Total agents")
    public_agents: int = Field(..., description="Public agents")
    total_tasks: int = Field(..., description="Total tasks")
    pending_tasks: int = Field(..., description="Pending tasks")
    total_usage_credits: float = Field(..., description="Total credits used")
    total_revenue: float = Field(..., description="Total revenue")
    daily_active_users: List[Dict[str, Any]] = Field(..., description="Daily active users for last 30 days")
    monthly_growth: Dict[str, float] = Field(..., description="Monthly growth percentages")


class AuditLogQueryParams(BaseSchema):
    """Schema for audit log query parameters."""
    start_date: Optional[datetime] = Field(None, description="Start date/time")
    end_date: Optional[datetime] = Field(None, description="End date/time")
    user_id: Optional[int] = Field(None, description="Filter by user ID")
    organization_id: Optional[int] = Field(None, description="Filter by organization ID")
    action_type: Optional[str] = Field(None, description="Filter by action type")
    resource_type: Optional[str] = Field(None, description="Filter by resource type")
    resource_id: Optional[str] = Field(None, description="Filter by resource ID")
    page: int = Field(default=1, ge=1, description="Page number")
    per_page: int = Field(default=50, ge=1, le=200, description="Items per page")
    
    @validator('end_date')
    def validate_date_range(cls, v, values):
        """Validate date range."""
        start_date = values.get('start_date')
        if start_date and v:
            if v < start_date:
                raise ValueError('end_date must be after start_date')
        return v


class AuditLogEntryResponse(BaseSchema):
    """Schema for audit log entry response."""
    id: int = Field(..., description="Audit log entry ID")
    timestamp: datetime = Field(..., description="When the action occurred")
    user_id: Optional[int] = Field(None, description="User who performed the action")
    user_email: Optional[str] = Field(None, description="User email")
    organization_id: Optional[int] = Field(None, description="Organization ID")
    organization_name: Optional[str] = Field(None, description="Organization name")
    action_type: str = Field(..., description="Type of action (create, update, delete, etc.)")
    resource_type: str = Field(..., description="Type of resource (user, organization, agent, etc.)")
    resource_id: str = Field(..., description="Resource ID")
    resource_name: Optional[str] = Field(None, description="Resource name")
    changes: Dict[str, Any] = Field(..., description="Changes made (old/new values)")
    ip_address: Optional[str] = Field(None, description="IP address")
    user_agent: Optional[str] = Field(None, description="User agent string")
    request_id: Optional[str] = Field(None, description="Request ID for tracing")


class AdminBillingAdjustment(BaseSchema):
    """Schema for billing adjustments by admin."""
    organization_id: int = Field(..., description="Organization ID")
    amount: float = Field(..., description="Adjustment amount (positive adds credits, negative deducts)")
    currency: str = Field(default="USD", description="Currency")
    reason: str = Field(..., min_length=1, max_length=500, description="Reason for adjustment")
    reference_id: Optional[str] = Field(None, description="External reference ID")
    
    @validator('currency')
    def validate_currency(cls, v):
        """Validate currency code."""
        if len(v) != 3 or not v.isalpha():
            raise ValueError('Currency code must be 3 letters (ISO 4217)')
        return v.upper()


class AdminBillingAdjustmentResponse(AdminBillingAdjustment):
    """Schema for billing adjustment response."""
    id: int = Field(..., description="Adjustment ID")
    created_by: int = Field(..., description="Admin user ID who created adjustment")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class AdminJobCreate(BaseSchema):
    """Schema for creating admin jobs."""
    job_type: str = Field(..., description="Job type (data_cleanup, report_generation, etc.)")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Job parameters")
    priority: str = Field(default="normal", description="Job priority (low, normal, high, critical)")
    schedule_at: Optional[datetime] = Field(None, description="When to run the job (default: immediately)")
    
    @validator('priority')
    def validate_priority(cls, v):
        """Validate priority."""
        valid_priorities = {'low', 'normal', 'high', 'critical'}
        if v not in valid_priorities:
            raise ValueError(f'priority must be one of {valid_priorities}')
        return v


class AdminJobResponse(BaseSchema):
    """Schema for admin job response."""
    id: str = Field(..., description="Job ID")
    job_type: str = Field(..., description="Job type")
    status: str = Field(..., description="Job status")
    parameters: Dict[str, Any] = Field(..., description="Job parameters")
    priority: str = Field(..., description="Job priority")
    created_by: int = Field(..., description="Admin user ID who created job")
    created_at: datetime = Field(..., description="Creation timestamp")
    started_at: Optional[datetime] = Field(None, description="When job started")
    completed_at: Optional[datetime] = Field(None, description="When job completed")
    result: Optional[Dict[str, Any]] = Field(None, description="Job result")
    error_message: Optional[str] = Field(None, description="Error message if failed")


class AuditLogListResponse(PaginatedResponse[AuditLogEntryResponse]):
    """Paginated response for audit log list."""
    pass