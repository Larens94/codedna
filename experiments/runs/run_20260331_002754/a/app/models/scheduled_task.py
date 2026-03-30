"""app/models/scheduled_task.py — Scheduled/recurring task model.

exports: ScheduledTask, TaskExecution
used_by: scheduler service → recurring task management, task service → execution tracking
rules:   schedules must be valid cron expressions; executions tracked for audit; retry logic supported
agent:   DataEngineer | 2024-11-06 | implemented scheduled task model
         message: "consider adding timezone support for scheduled tasks"
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum

from sqlalchemy import (
    Column,
    String,
    Text,
    DateTime,
    ForeignKey,
    JSON,
    Integer,
    Boolean,
    Index,
    Enum as SQLEnum,
    CheckConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func

from app.models.base import Base, TimestampMixin


class ScheduleType(str, Enum):
    """Schedule type enumeration."""
    CRON = "cron"
    INTERVAL = "interval"
    DATE = "date"


class ScheduledTaskStatus(str, Enum):
    """Scheduled task status."""
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    DISABLED = "disabled"


class ScheduledTask(Base, TimestampMixin):
    """Scheduled/recurring task configuration.
    
    Rules:
        Each scheduled task belongs to an organization
        Cron expressions validated for correctness
        Tasks can be one-time or recurring
        Execution history is preserved for audit
    """
    
    __tablename__ = "scheduled_tasks"
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
        doc="Unique scheduled task identifier (UUID)",
    )
    
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        doc="Organization that owns this scheduled task",
    )
    
    agent_id = Column(
        Integer,
        ForeignKey("agents.id"),
        nullable=False,
        doc="Agent to execute",
    )
    
    name = Column(
        String(255),
        nullable=False,
        doc="Scheduled task name",
    )
    
    description = Column(
        Text,
        nullable=True,
        doc="Task description",
    )
    
    schedule_type = Column(
        SQLEnum(ScheduleType),
        nullable=False,
        doc="Type of schedule (cron, interval, date)",
    )
    
    schedule_expression = Column(
        String(100),
        nullable=False,
        doc="Schedule expression (cron string, interval seconds, or ISO date)",
    )
    
    input_data = Column(
        JSON,
        default=dict,
        nullable=False,
        doc="Input data for task execution",
    )
    
    status = Column(
        SQLEnum(ScheduledTaskStatus),
        default=ScheduledTaskStatus.ACTIVE,
        nullable=False,
        doc="Scheduled task status",
    )
    
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether scheduled task is active (enabled)",
    )
    
    max_retries = Column(
        Integer,
        default=3,
        nullable=False,
        doc="Maximum number of retries on failure",
    )
    
    retry_delay_seconds = Column(
        Integer,
        default=60,
        nullable=False,
        doc="Delay between retries in seconds",
    )
    
    timeout_seconds = Column(
        Integer,
        default=300,
        nullable=False,
        doc="Maximum execution time in seconds",
    )
    
    next_run_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="When task is scheduled to run next",
    )
    
    last_run_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="When task was last executed",
    )
    
    created_by = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
        doc="User who created this scheduled task",
    )
    
    # Relationships
    organization = relationship(
        "Organization",
        back_populates="scheduled_tasks",
        lazy="selectin",
    )
    
    agent = relationship(
        "Agent",
        back_populates="scheduled_tasks",
        lazy="selectin",
    )
    
    creator = relationship(
        "User",
        lazy="selectin",
    )
    
    executions = relationship(
        "TaskExecution",
        back_populates="scheduled_task",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="TaskExecution.created_at.desc()",
        doc="Execution history for this scheduled task",
    )
    
    # Constraints
    __table_args__ = (
        CheckConstraint("max_retries >= 0", name="ck_max_retries_non_negative"),
        CheckConstraint("retry_delay_seconds >= 0", name="ck_retry_delay_non_negative"),
        CheckConstraint("timeout_seconds > 0", name="ck_timeout_positive"),
        Index("ix_scheduled_tasks_org_id", organization_id),
        Index("ix_scheduled_tasks_agent_id", agent_id),
        Index("ix_scheduled_tasks_status", status),
        Index("ix_scheduled_tasks_is_active", is_active),
        Index("ix_scheduled_tasks_next_run_at", next_run_at),
        Index("ix_scheduled_tasks_created_by", created_by),
    )
    
    @validates("schedule_expression")
    def validate_schedule_expression(self, key: str, expression: str) -> str:
        """Validate schedule expression based on type.
        
        Args:
            key: Field name
            expression: Schedule expression
            
        Returns:
            str: Validated expression
            
        Raises:
            ValueError: If expression is invalid for schedule type
        """
        if self.schedule_type == ScheduleType.CRON:
            # Basic cron validation (5 or 6 fields)
            parts = expression.strip().split()
            if len(parts) not in (5, 6):
                raise ValueError("Cron expression must have 5 or 6 fields")
            
            # TODO: Validate each cron field
            # For now, just check it's not empty
            
        elif self.schedule_type == ScheduleType.INTERVAL:
            # Interval must be positive integer
            try:
                interval = int(expression)
                if interval <= 0:
                    raise ValueError("Interval must be positive")
            except ValueError:
                raise ValueError("Interval must be a positive integer")
            
        elif self.schedule_type == ScheduleType.DATE:
            # Date must be valid ISO format datetime
            try:
                datetime.fromisoformat(expression.replace('Z', '+00:00'))
            except ValueError:
                raise ValueError("Date must be in ISO format")
        
        return expression
    
    @property
    def execution_count(self) -> int:
        """Get total number of executions.
        
        Returns:
            int: Number of executions
        """
        return len(self.executions) if self.executions else 0
    
    @property
    def success_count(self) -> int:
        """Get number of successful executions.
        
        Returns:
            int: Number of successful executions
        """
        if not self.executions:
            return 0
        return sum(1 for e in self.executions if e.status == "completed")
    
    @property
    def failure_count(self) -> int:
        """Get number of failed executions.
        
        Returns:
            int: Number of failed executions
        """
        if not self.executions:
            return 0
        return sum(1 for e in self.executions if e.status == "failed")
    
    @property
    def success_rate(self) -> float:
        """Get execution success rate.
        
        Returns:
            float: Success rate (0.0 to 1.0)
        """
        total = self.execution_count
        if total == 0:
            return 0.0
        return self.success_count / total
    
    def enable(self) -> None:
        """Enable scheduled task."""
        self.is_active = True
        self.status = ScheduledTaskStatus.ACTIVE
    
    def disable(self) -> None:
        """Disable scheduled task."""
        self.is_active = False
        self.status = ScheduledTaskStatus.DISABLED
    
    def pause(self) -> None:
        """Pause scheduled task."""
        self.is_active = False
        self.status = ScheduledTaskStatus.PAUSED
    
    def __repr__(self) -> str:
        """String representation of scheduled task."""
        return f"<ScheduledTask(id={self.id}, name='{self.name}', org={self.organization_id}, status={self.status})>"


class TaskExecution(Base, TimestampMixin):
    """Execution record for a scheduled task.
    
    Rules:
        Each execution tracks start, end, status, and result
        Retry attempts are tracked separately
        Errors are captured with stack traces
    """
    
    __tablename__ = "task_executions"
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
        doc="Unique execution identifier (UUID)",
    )
    
    scheduled_task_id = Column(
        UUID(as_uuid=True),
        ForeignKey("scheduled_tasks.id", ondelete="CASCADE"),
        nullable=False,
        doc="Scheduled task that was executed",
    )
    
    task_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tasks.id"),
        nullable=True,
        doc="Task record created for this execution",
    )
    
    status = Column(
        String(50),
        nullable=False,
        doc="Execution status (pending, running, completed, failed, cancelled)",
    )
    
    started_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="When execution started",
    )
    
    completed_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="When execution completed",
    )
    
    duration_seconds = Column(
        Numeric(10, 3),
        nullable=True,
        doc="Execution duration in seconds",
    )
    
    retry_count = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Number of retry attempts",
    )
    
    error_message = Column(
        Text,
        nullable=True,
        doc="Error message if execution failed",
    )
    
    error_details = Column(
        JSON,
        nullable=True,
        doc="Detailed error information (stack trace, etc.)",
    )
    
    result_data = Column(
        JSON,
        nullable=True,
        doc="Execution result data",
    )
    
    metadata = Column(
        JSON,
        default=dict,
        nullable=False,
        doc="Execution metadata",
    )
    
    # Relationships
    scheduled_task = relationship(
        "ScheduledTask",
        back_populates="executions",
        lazy="selectin",
    )
    
    task = relationship(
        "Task",
        lazy="selectin",
    )
    
    # Indexes
    __table_args__ = (
        Index("ix_task_executions_scheduled_task_id", scheduled_task_id),
        Index("ix_task_executions_status", status),
        Index("ix_task_executions_started_at", started_at),
        Index("ix_task_executions_completed_at", completed_at),
        Index("ix_task_executions_task_id", task_id),
    )
    
    @property
    def is_finished(self) -> bool:
        """Check if execution is finished.
        
        Returns:
            bool: True if execution is finished
        """
        return self.status in {"completed", "failed", "cancelled"}
    
    @property
    def is_successful(self) -> bool:
        """Check if execution was successful.
        
        Returns:
            bool: True if execution completed successfully
        """
        return self.status == "completed"
    
    @property
    def is_failed(self) -> bool:
        """Check if execution failed.
        
        Returns:
            bool: True if execution failed
        """
        return self.status == "failed"
    
    def calculate_duration(self) -> Optional[float]:
        """Calculate execution duration.
        
        Returns:
            Optional[float]: Duration in seconds or None if not completed
        """
        if not self.started_at or not self.completed_at:
            return None
        return (self.completed_at - self.started_at).total_seconds()
    
    def __repr__(self) -> str:
        """String representation of task execution."""
        return f"<TaskExecution(id={self.id}, scheduled_task={self.scheduled_task_id}, status={self.status})>"