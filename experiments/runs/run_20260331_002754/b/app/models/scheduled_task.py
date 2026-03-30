"""Scheduled task models for recurring agent executions."""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Interval, JSON, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
import croniter

from app import db


class TaskStatus(enum.Enum):
    """Task status enumeration."""
    
    ACTIVE = 'active'
    PAUSED = 'paused'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'


class TaskRecurrence(enum.Enum):
    """Task recurrence pattern."""
    
    ONCE = 'once'
    HOURLY = 'hourly'
    DAILY = 'daily'
    WEEKLY = 'weekly'
    MONTHLY = 'monthly'
    CRON = 'cron'


class ScheduledTask(db.Model):
    """Scheduled task model for recurring agent executions.
    
    Attributes:
        id: Primary key
        user_id: Foreign key to user
        organization_id: Foreign key to organization
        agent_id: Foreign key to agent
        name: Task name
        description: Task description
        status: Task status
        recurrence: Recurrence pattern
        cron_expression: Cron expression (if recurrence is CRON)
        interval_seconds: Interval in seconds (for hourly/daily/etc)
        next_run_at: When to run next
        last_run_at: When last run occurred
        last_run_status: Status of last run
        last_run_result: Result of last run (JSON)
        max_retries: Maximum number of retries on failure
        retry_count: Current retry count
        timeout_seconds: Task timeout in seconds
        parameters: Agent run parameters (JSON)
        metadata: Additional metadata (JSON)
        created_at: Creation timestamp
        updated_at: Last update timestamp
        user: Associated user
        organization: Associated organization
        agent: Associated agent
        task_runs: Associated task runs
    """
    
    __tablename__ = 'scheduled_tasks'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    organization_id = Column(Integer, ForeignKey('organizations.id', ondelete='CASCADE'))
    agent_id = Column(Integer, ForeignKey('agents.id', ondelete='CASCADE'), nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    status = Column(Enum(TaskStatus), default=TaskStatus.ACTIVE, nullable=False)
    recurrence = Column(Enum(TaskRecurrence), default=TaskRecurrence.ONCE, nullable=False)
    cron_expression = Column(String(100))  # e.g., "0 9 * * *" for daily at 9 AM
    interval_seconds = Column(Integer)  # For hourly/daily/weekly/monthly
    next_run_at = Column(DateTime, nullable=False)
    last_run_at = Column(DateTime)
    last_run_status = Column(String(50))
    last_run_result = Column(JSON)
    max_retries = Column(Integer, default=3)
    retry_count = Column(Integer, default=0)
    timeout_seconds = Column(Integer, default=300)  # 5 minutes default
    parameters = Column(JSON)  # Agent run parameters
    metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Indexes for efficient querying
    __table_args__ = (
        db.Index('ix_scheduled_tasks_status_next_run', 'status', 'next_run_at'),
        db.Index('ix_scheduled_tasks_user_id', 'user_id'),
        db.Index('ix_scheduled_tasks_organization_id', 'organization_id'),
        db.Index('ix_scheduled_tasks_agent_id', 'agent_id'),
    )
    
    # Relationships
    user = relationship('User')
    organization = relationship('Organization')
    agent = relationship('Agent')
    task_runs = relationship('TaskRun', back_populates='scheduled_task', cascade='all, delete-orphan')
    
    def get_parameters_dict(self) -> Dict[str, Any]:
        """Get parameters as dictionary.
        
        Returns:
            Parameters dictionary
        """
        return self.parameters or {}
    
    def get_metadata_dict(self) -> Dict[str, Any]:
        """Get metadata as dictionary.
        
        Returns:
            Metadata dictionary
        """
        return self.metadata or {}
    
    def calculate_next_run(self) -> Optional[datetime]:
        """Calculate next run time based on recurrence pattern.
        
        Returns:
            Next run datetime or None if not recurring
        """
        if self.status != TaskStatus.ACTIVE:
            return None
        
        now = datetime.utcnow()
        
        if self.recurrence == TaskRecurrence.ONCE:
            return None
        
        if self.recurrence == TaskRecurrence.CRON and self.cron_expression:
            try:
                cron = croniter.croniter(self.cron_expression, now)
                return cron.get_next(datetime)
            except Exception:
                return None
        
        if self.interval_seconds:
            # Start from last run or now if never run
            base_time = self.last_run_at or now
            return base_time + timedelta(seconds=self.interval_seconds)
        
        return None
    
    def should_run_now(self) -> bool:
        """Check if task should run now.
        
        Returns:
            True if task should run, False otherwise
        """
        if self.status != TaskStatus.ACTIVE:
            return False
        
        if not self.next_run_at:
            return False
        
        now = datetime.utcnow()
        return now >= self.next_run_at
    
    def mark_as_running(self) -> None:
        """Mark task as currently running."""
        self.last_run_at = datetime.utcnow()
        self.next_run_at = self.calculate_next_run()
    
    def update_run_result(self, status: str, result: Dict[str, Any]) -> None:
        """Update task with run result.
        
        Args:
            status: Run status ('success', 'failed', etc.)
            result: Run result dictionary
        """
        self.last_run_status = status
        self.last_run_result = result
        
        if status == 'success':
            self.retry_count = 0
        else:
            self.retry_count += 1
            if self.retry_count >= self.max_retries:
                self.status = TaskStatus.FAILED
        
        db.session.commit()
    
    def to_dict(self, include_runs: bool = False) -> Dict[str, Any]:
        """Convert scheduled task to dictionary representation.
        
        Args:
            include_runs: Whether to include task runs
            
        Returns:
            Dictionary representation of scheduled task
        """
        data = {
            'id': self.id,
            'user_id': self.user_id,
            'organization_id': self.organization_id,
            'agent_id': self.agent_id,
            'name': self.name,
            'description': self.description,
            'status': self.status.value if self.status else None,
            'recurrence': self.recurrence.value if self.recurrence else None,
            'cron_expression': self.cron_expression,
            'interval_seconds': self.interval_seconds,
            'next_run_at': self.next_run_at.isoformat() if self.next_run_at else None,
            'last_run_at': self.last_run_at.isoformat() if self.last_run_at else None,
            'last_run_status': self.last_run_status,
            'max_retries': self.max_retries,
            'retry_count': self.retry_count,
            'timeout_seconds': self.timeout_seconds,
            'parameters': self.get_parameters_dict(),
            'metadata': self.get_metadata_dict(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'should_run_now': self.should_run_now(),
        }
        
        if include_runs:
            data['task_runs'] = [task_run.to_dict() for task_run in self.task_runs[:10]]  # Limit to 10
        
        return data
    
    def __repr__(self) -> str:
        return f'<ScheduledTask {self.name} (ID: {self.id}, Next: {self.next_run_at})>'


class TaskRun(db.Model):
    """Task run model for tracking individual scheduled task executions.
    
    Attributes:
        id: Primary key
        scheduled_task_id: Foreign key to scheduled task
        agent_run_id: Foreign key to agent run
        started_at: When run started
        completed_at: When run completed
        status: Run status
        result: Run result (JSON)
        error_message: Error message if failed
        logs: Execution logs
        created_at: Creation timestamp
        scheduled_task: Associated scheduled task
        agent_run: Associated agent run
    """
    
    __tablename__ = 'task_runs'
    
    id = Column(Integer, primary_key=True)
    scheduled_task_id = Column(Integer, ForeignKey('scheduled_tasks.id', ondelete='CASCADE'), nullable=False)
    agent_run_id = Column(Integer, ForeignKey('agent_runs.id', ondelete='SET NULL'))
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    status = Column(String(50), default='pending')  # pending, running, success, failed, cancelled
    result = Column(JSON)
    error_message = Column(Text)
    logs = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        db.Index('ix_task_runs_scheduled_task_id', 'scheduled_task_id'),
        db.Index('ix_task_runs_status', 'status'),
        db.Index('ix_task_runs_started_at', 'started_at'),
    )
    
    # Relationships
    scheduled_task = relationship('ScheduledTask', back_populates='task_runs')
    agent_run = relationship('AgentRun')
    
    def get_result_dict(self) -> Dict[str, Any]:
        """Get result as dictionary.
        
        Returns:
            Result dictionary
        """
        return self.result or {}
    
    def mark_completed(self, status: str, result: Optional[Dict[str, Any]] = None, error: Optional[str] = None) -> None:
        """Mark task run as completed.
        
        Args:
            status: Completion status
            result: Run result
            error: Error message if failed
        """
        self.completed_at = datetime.utcnow()
        self.status = status
        self.result = result
        self.error_message = error
        
        db.session.commit()
    
    def duration_seconds(self) -> Optional[float]:
        """Calculate run duration in seconds.
        
        Returns:
            Duration in seconds or None if not completed
        """
        if not self.started_at or not self.completed_at:
            return None
        
        return (self.completed_at - self.started_at).total_seconds()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert task run to dictionary representation.
        
        Returns:
            Dictionary representation of task run
        """
        return {
            'id': self.id,
            'scheduled_task_id': self.scheduled_task_id,
            'agent_run_id': self.agent_run_id,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'status': self.status,
            'result': self.get_result_dict(),
            'error_message': self.error_message,
            'logs': self.logs,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'duration_seconds': self.duration_seconds(),
        }
    
    def __repr__(self) -> str:
        return f'<TaskRun {self.id} for Task {self.scheduled_task_id} ({self.status})>'