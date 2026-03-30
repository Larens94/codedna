"""app/models/task.py — Async task/job model.

exports: Task
used_by: task service → background job management, worker → job processing
rules:   tasks support different types (agent_execution, file_processing, webhook); progress tracking required
agent:   Product Architect | 2024-03-30 | implemented task model with status tracking
         message: "consider adding priority field for task scheduling"
"""

import uuid
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum

from sqlalchemy import (
    Column,
    String,
    Text,
    DateTime,
    ForeignKey,
    JSON,
    Integer,
    Index,
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func

from app.models.base import Base, TimestampMixin


class TaskType(str, Enum):
    """Task types for different operations."""
    AGENT_EXECUTION = "agent_execution"
    FILE_PROCESSING = "file_processing"
    WEBHOOK = "webhook"
    DATA_EXPORT = "data_export"
    BATCH_PROCESSING = "batch_processing"


class TaskStatus(str, Enum):
    """Task status lifecycle."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class Task(Base, TimestampMixin):
    """Background task/job for async operations.
    
    Rules:
        Each task belongs to an organization
        Input and output data stored as JSON
        Progress tracked for long-running tasks
    """
    
    __tablename__ = "tasks"
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
        doc="Unique task identifier (UUID)",
    )
    
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        doc="Organization that owns this task",
    )
    
    agent_id = Column(
        Integer,
        ForeignKey("agents.id"),
        nullable=True,
        doc="Agent used for this task (if applicable)",
    )
    
    type = Column(
        SQLEnum(TaskType),
        nullable=False,
        doc="Task type",
    )
    
    status = Column(
        SQLEnum(TaskStatus),
        default=TaskStatus.PENDING,
        nullable=False,
        doc="Task status",
    )
    
    input_data = Column(
        JSON,
        default=dict,
        nullable=False,
        doc="Task input data",
    )
    
    output_data = Column(
        JSON,
        default=dict,
        nullable=False,
        doc="Task output data (result)",
    )
    
    error_message = Column(
        Text,
        nullable=True,
        doc="Error message if task failed",
    )
    
    progress = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Progress percentage (0-100)",
    )
    
    created_by = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
        doc="User who created this task",
    )
    
    started_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="When task started executing",
    )
    
    completed_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="When task completed",
    )
    
    # Relationships
    organization = relationship(
        "Organization",
        back_populates="tasks",
        lazy="selectin",
    )
    
    agent = relationship(
        "Agent",
        back_populates="tasks",
        lazy="selectin",
    )
    
    creator = relationship(
        "User",
        lazy="selectin",
    )
    
    usage_records = relationship(
        "UsageRecord",
        back_populates="task",
        cascade="all, delete-orphan",
        lazy="selectin",
        doc="Usage records for this task",
    )
    
    # Indexes
    __table_args__ = (
        Index("ix_tasks_org_id", organization_id),
        Index("ix_tasks_status", status),
        Index("ix_tasks_type", type),
        Index("ix_tasks_created_at", created_at),
        Index("ix_tasks_agent_id", agent_id),
    )
    
    @validates("progress")
    def validate_progress(self, key: str, progress: int) -> int:
        """Validate progress percentage.
        
        Args:
            key: Field name
            progress: Progress percentage
            
        Returns:
            int: Validated progress
            
        Raises:
            ValueError: If progress is out of range
        """
        if progress < 0 or progress > 100:
            raise ValueError("Progress must be between 0 and 100")
        return progress
    
    @property
    def duration_seconds(self) -> Optional[float]:
        """Get task duration in seconds.
        
        Returns:
            Optional[float]: Duration in seconds or None if not started
        """
        if not self.started_at:
            return None
        
        end_time = self.completed_at or datetime.now(self.started_at.tzinfo)
        return (end_time - self.started_at).total_seconds()
    
    @property
    def is_finished(self) -> bool:
        """Check if task is finished (completed, failed, or cancelled).
        
        Returns:
            bool: True if task is finished
        """
        return self.status in {
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
        }
    
    @property
    def can_retry(self) -> bool:
        """Check if task can be retried.
        
        Returns:
            bool: True if task failed and can be retried
        """
        return self.status == TaskStatus.FAILED
    
    def start(self) -> None:
        """Mark task as started."""
        self.status = TaskStatus.RUNNING
        self.started_at = func.now()
        self.progress = 0
    
    def update_progress(self, progress: int) -> None:
        """Update task progress.
        
        Args:
            progress: Progress percentage (0-100)
        """
        self.progress = progress
        if progress == 100:
            self.complete()
    
    def complete(self, output_data: Optional[Dict[str, Any]] = None) -> None:
        """Mark task as completed.
        
        Args:
            output_data: Optional output data
        """
        self.status = TaskStatus.COMPLETED
        self.progress = 100
        self.completed_at = func.now()
        if output_data is not None:
            self.output_data = output_data
    
    def fail(self, error_message: str) -> None:
        """Mark task as failed.
        
        Args:
            error_message: Error description
        """
        self.status = TaskStatus.FAILED
        self.error_message = error_message
        self.completed_at = func.now()
    
    def cancel(self) -> None:
        """Mark task as cancelled."""
        self.status = TaskStatus.CANCELLED
        self.completed_at = func.now()
    
    def __repr__(self) -> str:
        """String representation of task."""
        return f"<Task(id={self.id}, type={self.type}, status={self.status}, progress={self.progress}%)>"