"""Agent run models for tracking agent executions."""

from datetime import datetime
from typing import Optional, Dict, Any
from decimal import Decimal
import enum
import json

from sqlalchemy import Column, Integer, String, Text, Enum, DateTime, ForeignKey, Numeric, Boolean, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app import db


class AgentRunStatus(enum.Enum):
    """Agent run status enumeration."""
    
    PENDING = 'pending'
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'
    TIMEOUT = 'timeout'
    CANCELLED = 'cancelled'


class AgentRun(db.Model):
    """Agent run model representing individual agent executions.
    
    Attributes:
        id: Primary key
        agent_id: Foreign key to agent
        agent_version_id: Foreign key to agent version used
        user_id: Foreign key to user who initiated run
        status: Run status
        input_data: Input data for agent (JSON)
        output_data: Output data from agent (JSON)
        error_message: Error message if run failed
        execution_time_ms: Execution time in milliseconds
        cost_usd: Cost in USD for this run
        started_at: When run started
        completed_at: When run completed
        created_at: Creation timestamp
        updated_at: Last update timestamp
        agent: Agent that was run
        agent_version: Specific version used
        user: User who initiated run
        logs: Run logs
    """
    
    __tablename__ = 'agent_runs'
    
    id = Column(Integer, primary_key=True)
    agent_id = Column(Integer, ForeignKey('agents.id', ondelete='CASCADE'), nullable=False)
    agent_version_id = Column(Integer, ForeignKey('agent_versions.id', ondelete='SET NULL'))
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    status = Column(Enum(AgentRunStatus), default=AgentRunStatus.PENDING, nullable=False)
    input_data = Column(Text)  # JSON input
    output_data = Column(Text)  # JSON output
    error_message = Column(Text)
    execution_time_ms = Column(Integer)
    cost_usd = Column(Numeric(10, 4), default=Decimal('0.0000'))
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    agent = relationship('Agent', back_populates='runs')
    agent_version = relationship('AgentVersion')
    user = relationship('User', back_populates='runs')
    logs = relationship('AgentRunLog', back_populates='run', cascade='all, delete-orphan')
    
    def start(self) -> None:
        """Mark run as started."""
        if self.status == AgentRunStatus.PENDING:
            self.status = AgentRunStatus.RUNNING
            self.started_at = datetime.utcnow()
    
    def complete(self, output_data: Optional[Dict[str, Any]] = None) -> None:
        """Mark run as completed.
        
        Args:
            output_data: Agent output data
        """
        self.status = AgentRunStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        
        if output_data:
            self.output_data = json.dumps(output_data)
        
        # Calculate execution time
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            self.execution_time_ms = int(delta.total_seconds() * 1000)
    
    def fail(self, error_message: str) -> None:
        """Mark run as failed.
        
        Args:
            error_message: Error description
        """
        self.status = AgentRunStatus.FAILED
        self.completed_at = datetime.utcnow()
        self.error_message = error_message
        
        # Calculate execution time
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            self.execution_time_ms = int(delta.total_seconds() * 1000)
    
    def cancel(self) -> None:
        """Mark run as cancelled."""
        self.status = AgentRunStatus.CANCELLED
        self.completed_at = datetime.utcnow()
    
    def timeout(self) -> None:
        """Mark run as timed out."""
        self.status = AgentRunStatus.TIMEOUT
        self.completed_at = datetime.utcnow()
        self.error_message = 'Execution timeout'
    
    def get_input(self) -> Dict[str, Any]:
        """Parse input data as JSON.
        
        Returns:
            Parsed input data dictionary
        """
        if self.input_data:
            return json.loads(self.input_data)
        return {}
    
    def get_output(self) -> Dict[str, Any]:
        """Parse output data as JSON.
        
        Returns:
            Parsed output data dictionary or empty dict if failed
        """
        if self.output_data and self.status == AgentRunStatus.COMPLETED:
            return json.loads(self.output_data)
        return {}
    
    def to_dict(self, include_details: bool = False) -> dict:
        """Convert agent run to dictionary representation.
        
        Args:
            include_details: Whether to include detailed information
            
        Returns:
            Dictionary representation of agent run
        """
        data = {
            'id': self.id,
            'agent_id': self.agent_id,
            'agent_version_id': self.agent_version_id,
            'user_id': self.user_id,
            'status': self.status.value if self.status else None,
            'error_message': self.error_message,
            'execution_time_ms': self.execution_time_ms,
            'cost_usd': float(self.cost_usd) if self.cost_usd else 0.0,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'agent': {
                'id': self.agent.id,
                'name': self.agent.name,
                'slug': self.agent.slug,
            } if self.agent else None,
            'user': {
                'id': self.user.id,
                'username': self.user.username,
            } if self.user else None,
        }
        
        if include_details:
            data.update({
                'input_data': self.get_input(),
                'output_data': self.get_output(),
                'logs': [log.to_dict() for log in self.logs],
            })
        
        return data
    
    def __repr__(self) -> str:
        return f'<AgentRun {self.id} ({self.status.value})>'


class AgentRunLog(db.Model):
    """Agent run log model for detailed execution logs.
    
    Attributes:
        id: Primary key
        run_id: Foreign key to agent run
        level: Log level (info, warning, error, debug)
        message: Log message
        timestamp: Log timestamp
        metadata: Additional log metadata (JSON)
        run: Parent agent run
    """
    
    __tablename__ = 'agent_run_logs'
    
    id = Column(Integer, primary_key=True)
    run_id = Column(Integer, ForeignKey('agent_runs.id', ondelete='CASCADE'), nullable=False)
    level = Column(String(20), nullable=False)  # info, warning, error, debug
    message = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    metadata = Column(Text)  # JSON metadata
    
    # Relationships
    run = relationship('AgentRun', back_populates='logs')
    
    def get_metadata(self) -> Dict[str, Any]:
        """Parse metadata as JSON.
        
        Returns:
            Parsed metadata dictionary
        """
        if self.metadata:
            return json.loads(self.metadata)
        return {}
    
    def to_dict(self) -> dict:
        """Convert log entry to dictionary representation.
        
        Returns:
            Dictionary representation of log entry
        """
        return {
            'id': self.id,
            'run_id': self.run_id,
            'level': self.level,
            'message': self.message,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'metadata': self.get_metadata(),
        }
    
    def __repr__(self) -> str:
        return f'<AgentRunLog {self.level}: {self.message[:50]}...>'