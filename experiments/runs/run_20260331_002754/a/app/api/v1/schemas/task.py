"""app/api/v1/schemas/task.py — Pydantic schemas for task endpoints.

exports: TaskCreate, TaskUpdate, TaskResponse, TaskSchedule
used_by: app/api/v1/tasks.py → request/response validation
rules:   task input/output must be valid JSON; schedule must be valid cron expression
agent:   BackendEngineer | 2024-03-31 | created task schemas with validation
         message: "consider adding task dependency validation"
"""

import re
from typing import Optional, Dict, Any, List
from enum import Enum
from pydantic import BaseModel, Field, validator
from .base import BaseSchema, PaginatedResponse


class TaskType(str, Enum):
    """Task types."""
    AGENT_EXECUTION = "agent_execution"
    FILE_PROCESSING = "file_processing"
    WEBHOOK = "webhook"
    DATA_EXPORT = "data_export"
    BATCH_PROCESSING = "batch_processing"


class TaskStatus(str, Enum):
    """Task status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class TaskCreate(BaseSchema):
    """Schema for creating a task."""
    agent_id: Optional[int] = Field(None, description="Agent ID (for agent_execution tasks)")
    type: TaskType = Field(..., description="Task type")
    input_data: Dict[str, Any] = Field(default_factory=dict, description="Task input data")
    schedule: Optional["TaskSchedule"] = Field(None, description="Schedule for recurring tasks")
    
    @validator('agent_id')
    def validate_agent_id(cls, v, values):
        """Validate agent_id is required for agent_execution tasks."""
        if values.get('type') == TaskType.AGENT_EXECUTION and v is None:
            raise ValueError('agent_id is required for agent_execution tasks')
        return v


class TaskUpdate(BaseSchema):
    """Schema for updating a task."""
    input_data: Optional[Dict[str, Any]] = Field(None, description="Task input data")
    schedule: Optional["TaskSchedule"] = Field(None, description="Schedule for recurring tasks")
    status: Optional[TaskStatus] = Field(None, description="Task status")


class TaskSchedule(BaseSchema):
    """Schema for task scheduling."""
    cron_expression: Optional[str] = Field(None, description="Cron expression (e.g., '0 0 * * *')")
    interval_seconds: Optional[int] = Field(None, ge=60, description="Interval in seconds (min 60)")
    start_at: Optional[datetime] = Field(None, description="When to start scheduling")
    end_at: Optional[datetime] = Field(None, description="When to stop scheduling")
    timezone: str = Field(default="UTC", description="Timezone for scheduling")
    
    @validator('cron_expression')
    def validate_cron_expression(cls, v):
        """Validate cron expression."""
        if v is None:
            return v
        
        # Basic cron validation (5-6 fields)
        parts = v.strip().split()
        if len(parts) not in [5, 6]:
            raise ValueError('Cron expression must have 5 or 6 fields')
        
        return v
    
    @validator('interval_seconds')
    def validate_interval_seconds(cls, v):
        """Validate interval seconds."""
        if v is None:
            return v
        
        if v < 60:
            raise ValueError('Interval must be at least 60 seconds')
        
        return v


class TaskResponse(BaseSchema):
    """Schema for task response."""
    id: str = Field(..., description="Task ID (UUID)")
    organization_id: int = Field(..., description="Organization ID")
    agent_id: Optional[int] = Field(None, description="Agent ID")
    type: TaskType = Field(..., description="Task type")
    status: TaskStatus = Field(..., description="Task status")
    input_data: Dict[str, Any] = Field(..., description="Task input data")
    output_data: Dict[str, Any] = Field(..., description="Task output data")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    progress: int = Field(..., ge=0, le=100, description="Progress percentage")
    created_by: Optional[int] = Field(None, description="User who created this task")
    started_at: Optional[datetime] = Field(None, description="When task started")
    completed_at: Optional[datetime] = Field(None, description="When task completed")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate duration in seconds."""
        if not self.started_at:
            return None
        end = self.completed_at or datetime.now(self.started_at.tzinfo)
        return (end - self.started_at).total_seconds()


class TaskStats(BaseSchema):
    """Task statistics."""
    total_tasks: int = Field(..., description="Total tasks")
    pending_tasks: int = Field(..., description="Pending tasks")
    running_tasks: int = Field(..., description="Running tasks")
    completed_tasks: int = Field(..., description="Completed tasks")
    failed_tasks: int = Field(..., description="Failed tasks")
    avg_duration_seconds: Optional[float] = Field(None, description="Average duration in seconds")


class TaskListResponse(PaginatedResponse[TaskResponse]):
    """Paginated response for task list."""
    pass


# Import datetime after class definitions to avoid circular import
from datetime import datetime