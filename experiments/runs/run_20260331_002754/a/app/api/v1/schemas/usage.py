"""app/api/v1/schemas/usage.py — Pydantic schemas for usage endpoints.

exports: UsageRecordResponse, UsageStatsResponse, UsageQueryParams
used_by: app/api/v1/usage.py → request/response validation
rules:   metric values must be non-negative; time ranges must be valid
agent:   BackendEngineer | 2024-03-31 | created usage schemas with validation
         message: "consider adding usage alerts for high consumption"
"""

from datetime import datetime, date
from typing import Optional, Dict, Any, List
from enum import Enum
from pydantic import BaseModel, Field, validator
from .base import BaseSchema, PaginatedResponse


class UsageMetric(str, Enum):
    """Usage metrics."""
    TOKEN_COUNT = "token_count"
    API_CALL = "api_call"
    EXECUTION_TIME = "execution_time"
    STORAGE_BYTES = "storage_bytes"
    AGENT_SESSION = "agent_session"


class UsageRecordResponse(BaseSchema):
    """Schema for usage record response."""
    id: int = Field(..., description="Usage record ID")
    organization_id: int = Field(..., description="Organization ID")
    user_id: Optional[int] = Field(None, description="User ID")
    agent_id: Optional[int] = Field(None, description="Agent ID")
    session_id: Optional[str] = Field(None, description="Session ID")
    task_id: Optional[str] = Field(None, description="Task ID")
    metric_name: UsageMetric = Field(..., description="Type of usage metric")
    metric_value: float = Field(..., ge=0, description="Value of the metric")
    credits_used: float = Field(..., ge=0, description="Credits used")
    metadata: Dict[str, Any] = Field(..., description="Additional metadata")
    recorded_at: datetime = Field(..., description="When usage was recorded")
    billed_at: Optional[datetime] = Field(None, description="When usage was billed")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class UsageQueryParams(BaseSchema):
    """Schema for usage query parameters."""
    start_date: Optional[date] = Field(None, description="Start date for usage query")
    end_date: Optional[date] = Field(None, description="End date for usage query")
    metric_name: Optional[UsageMetric] = Field(None, description="Filter by metric type")
    agent_id: Optional[int] = Field(None, description="Filter by agent")
    user_id: Optional[int] = Field(None, description="Filter by user")
    group_by: Optional[str] = Field(None, description="Group by field (day, week, month, agent, user)")
    limit: Optional[int] = Field(default=100, ge=1, le=1000, description="Maximum records to return")
    
    @validator('end_date')
    def validate_date_range(cls, v, values):
        """Validate date range."""
        start_date = values.get('start_date')
        if start_date and v:
            if v < start_date:
                raise ValueError('end_date must be after start_date')
            # Limit to 1 year max for performance
            if (v - start_date).days > 365:
                raise ValueError('Date range cannot exceed 1 year')
        return v
    
    @validator('group_by')
    def validate_group_by(cls, v):
        """Validate group by field."""
        if v is None:
            return v
        
        valid_groups = {'day', 'week', 'month', 'agent', 'user'}
        if v not in valid_groups:
            raise ValueError(f'group_by must be one of {valid_groups}')
        return v


class UsageStatsResponse(BaseSchema):
    """Schema for usage statistics response."""
    total_credits_used: float = Field(..., ge=0, description="Total credits used in period")
    total_token_count: float = Field(..., ge=0, description="Total tokens used in period")
    total_api_calls: int = Field(..., ge=0, description="Total API calls in period")
    total_execution_time: float = Field(..., ge=0, description="Total execution time in seconds")
    avg_daily_credits: float = Field(..., ge=0, description="Average daily credits used")
    peak_usage_day: Optional[date] = Field(None, description="Day with highest usage")
    peak_usage_value: float = Field(..., ge=0, description="Peak usage value")
    usage_by_metric: Dict[str, float] = Field(..., description="Usage broken down by metric")
    usage_by_agent: Dict[str, float] = Field(..., description="Usage broken down by agent")
    usage_by_user: Dict[str, float] = Field(..., description="Usage broken down by user")


class UsageExportRequest(BaseSchema):
    """Schema for usage export request."""
    start_date: date = Field(..., description="Start date for export")
    end_date: date = Field(..., description="End date for export")
    format: str = Field(default="csv", description="Export format (csv, json)")
    include_metadata: bool = Field(default=False, description="Include metadata in export")
    
    @validator('end_date')
    def validate_date_range(cls, v, values):
        """Validate date range."""
        start_date = values.get('start_date')
        if start_date and v:
            if v < start_date:
                raise ValueError('end_date must be after start_date')
            if (v - start_date).days > 365:
                raise ValueError('Date range cannot exceed 1 year')
        return v
    
    @validator('format')
    def validate_format(cls, v):
        """Validate export format."""
        valid_formats = {'csv', 'json'}
        if v not in valid_formats:
            raise ValueError(f'format must be one of {valid_formats}')
        return v


class UsageAlertCreate(BaseSchema):
    """Schema for creating usage alert."""
    threshold_credits: float = Field(..., gt=0, description="Credit threshold for alert")
    threshold_percentage: Optional[float] = Field(None, ge=0, le=100, description="Percentage of monthly limit")
    notification_email: Optional[str] = Field(None, description="Email for notifications (defaults to billing email)")
    enabled: bool = Field(default=True, description="Whether alert is enabled")
    
    @validator('threshold_percentage')
    def validate_threshold(cls, v, values):
        """Validate at least one threshold is set."""
        if v is None and values.get('threshold_credits') is None:
            raise ValueError('Either threshold_credits or threshold_percentage must be set')
        return v


class UsageAlertResponse(BaseSchema):
    """Schema for usage alert response."""
    id: int = Field(..., description="Alert ID")
    organization_id: int = Field(..., description="Organization ID")
    threshold_credits: float = Field(..., description="Credit threshold")
    threshold_percentage: Optional[float] = Field(None, description="Percentage threshold")
    notification_email: str = Field(..., description="Notification email")
    enabled: bool = Field(..., description="Whether alert is enabled")
    triggered_at: Optional[datetime] = Field(None, description="When alert was last triggered")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class UsageListResponse(PaginatedResponse[UsageRecordResponse]):
    """Paginated response for usage list."""
    pass