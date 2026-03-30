"""scheduler.py — Scheduled task management schemas.

exports: ScheduledTaskCreate, ScheduledTaskUpdate, ScheduledTaskResponse, TaskRunResponse
used_by: scheduler.py router
rules:   must validate cron expressions; must enforce schedule constraints
agent:   BackendEngineer | 2024-01-15 | created scheduler schemas
         message: "implement cron expression validation and next run calculation"
"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, validator
import re
from croniter import croniter


class ScheduledTaskCreate(BaseModel):
    """Schema for creating a scheduled task."""
    
    name: str = Field(..., min_length=1, max_length=255, description="Task name")
    description: Optional[str] = Field(None, description="Task description")
    agent_id: int = Field(..., description="Agent ID to execute")
    cron_expression: Optional[str] = Field(None, description="Cron expression for scheduling")
    interval_seconds: Optional[int] = Field(None, ge=60, description="Interval in seconds (min 60)")
    input_data: Dict[str, Any] = Field(..., description="Input data for agent execution")
    is_active: bool = Field(True, description="Whether task is active")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Task metadata")
    
    @validator("cron_expression")
    def validate_cron_expression(cls, v, values):
        """Validate cron expression format."""
        if v is not None:
            try:
                # Test if cron expression is valid
                croniter(v, datetime.now())
            except Exception as e:
                raise ValueError(f"Invalid cron expression: {str(e)}")
        
        # Ensure either cron_expression or interval_seconds is provided
        if v is None and values.get("interval_seconds") is None:
            raise ValueError("Either cron_expression or interval_seconds must be provided")
        
        return v
    
    @validator("interval_seconds")
    def validate_interval_seconds(cls, v, values):
        """Validate interval seconds."""
        if v is not None and v < 60:
            raise ValueError("Interval must be at least 60 seconds")
        
        # Ensure either cron_expression or interval_seconds is provided
        if v is None and values.get("cron_expression") is None:
            raise ValueError("Either cron_expression or interval_seconds must be provided")
        
        return v


class ScheduledTaskUpdate(BaseModel):
    """Schema for updating a scheduled task."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Task name")
    description: Optional[str] = Field(None, description="Task description")
    cron_expression: Optional[str] = Field(None, description="Cron expression for scheduling")
    interval_seconds: Optional[int] = Field(None, ge=60, description="Interval in seconds")
    input_data: Optional[Dict[str, Any]] = Field(None, description="Input data for agent execution")
    is_active: Optional[bool] = Field(None, description="Whether task is active")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Task metadata")
    
    @validator("cron_expression")
    def validate_cron_expression(cls, v):
        """Validate cron expression format."""
        if v is not None:
            try:
                # Test if cron expression is valid
                croniter(v, datetime.now())
            except Exception as e:
                raise ValueError(f"Invalid cron expression: {str(e)}")
        return v
    
    @validator("interval_seconds")
    def validate_interval_seconds(cls, v):
        """Validate interval seconds."""
        if v is not None and v < 60:
            raise ValueError("Interval must be at least 60 seconds")
        return v


class ScheduledTaskResponse(BaseModel):
    """Schema for scheduled task response."""
    
    public_id: str = Field(..., description="Public task ID")
    name: str = Field(..., description="Task name")
    description: Optional[str] = Field(None, description="Task description")
    agent_id: int = Field(..., description="Agent ID to execute")
    cron_expression: Optional[str] = Field(None, description="Cron expression for scheduling")
    interval_seconds: Optional[int] = Field(None, description="Interval in seconds")
    input_data: Dict[str, Any] = Field(..., description="Input data for agent execution")
    is_active: bool = Field(..., description="Whether task is active")
    next_run_at: datetime = Field(..., description="Next scheduled run timestamp")
    last_run_at: Optional[datetime] = Field(None, description="Last run timestamp")
    last_run_status: Optional[str] = Field(None, description="Last run status")
    metadata: Dict[str, Any] = Field(..., description="Task metadata")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    
    class Config:
        from_attributes = True


class TaskRunResponse(BaseModel):
    """Schema for task run history response."""
    
    id: int = Field(..., description="Run ID")
    task_id: int = Field(..., description="Task ID")
    agent_run_id: Optional[int] = Field(None, description="Agent run ID")
    status: str = Field(..., description="Run status")
    scheduled_at: datetime = Field(..., description="Scheduled run timestamp")
    started_at: Optional[datetime] = Field(None, description="Actual start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    credits_used: float = Field(..., description="Credits used for this run")
    created_at: datetime = Field(..., description="Creation timestamp")
    
    class Config:
        from_attributes = True