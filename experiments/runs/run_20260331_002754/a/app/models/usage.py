"""app/models/usage.py — Usage tracking for billing and analytics.

exports: UsageRecord
used_by: billing service → credit calculation, analytics service → reporting
rules:   every API call must create usage record; credits calculated based on metric value
agent:   Product Architect | 2024-03-30 | implemented usage tracking model
         message: "consider adding materialized view for daily usage aggregation"
"""

from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    JSON,
    Numeric,
    Index,
    Enum as SQLEnum,
)
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func

from app.models.base import Base, TimestampMixin


class UsageMetric(str, Enum):
    """Usage metrics for tracking and billing."""
    TOKEN_COUNT = "token_count"
    API_CALL = "api_call"
    EXECUTION_TIME = "execution_time"
    STORAGE_BYTES = "storage_bytes"
    AGENT_SESSION = "agent_session"


class UsageRecord(Base, TimestampMixin):
    """Record of resource usage for billing and analytics.
    
    Rules:
        Every API call that consumes resources creates a usage record
        Credits are calculated based on metric value and pricing
        Records are aggregated for billing periods
    """
    
    __tablename__ = "usage_records"
    
    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        doc="Unique usage record identifier",
    )
    
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        doc="Organization that incurred this usage",
    )
    
    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
        doc="User who caused this usage",
    )
    
    agent_id = Column(
        Integer,
        ForeignKey("agents.id"),
        nullable=True,
        doc="Agent used (if applicable)",
    )
    
    session_id = Column(
        # Using String for UUID to avoid dependency on UUID type
        String(36),
        nullable=True,
        doc="Agent session (if applicable)",
    )
    
    task_id = Column(
        String(36),
        nullable=True,
        doc="Task (if applicable)",
    )
    
    metric_name = Column(
        SQLEnum(UsageMetric),
        nullable=False,
        doc="Type of usage metric",
    )
    
    metric_value = Column(
        Numeric(12, 4),
        nullable=False,
        doc="Value of the metric",
    )
    
    credits_used = Column(
        Numeric(12, 4),
        default=0,
        nullable=False,
        doc="Credits used for this usage",
    )
    
    metadata = Column(
        JSON,
        default=dict,
        nullable=False,
        doc="Additional metadata (model, endpoint, etc.)",
    )
    
    recorded_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
        doc="When usage was recorded",
    )
    
    billed_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="When usage was billed (NULL if not yet billed)",
    )
    
    # Relationships
    organization = relationship(
        "Organization",
        back_populates="usage_records",
        lazy="selectin",
    )
    
    user = relationship(
        "User",
        lazy="selectin",
    )
    
    agent = relationship(
        "Agent",
        back_populates="usage_records",
        lazy="selectin",
    )
    
    session = relationship(
        "AgentSession",
        back_populates="usage_records",
        lazy="selectin",
        primaryjoin="UsageRecord.session_id == foreign(AgentSession.id)",
    )
    
    task = relationship(
        "Task",
        back_populates="usage_records",
        lazy="selectin",
        primaryjoin="UsageRecord.task_id == foreign(Task.id)",
    )
    
    # Indexes
    __table_args__ = (
        Index("ix_usage_org_id_recorded", organization_id, recorded_at),
        Index("ix_usage_metric_name", metric_name),
        Index("ix_usage_billed_at", billed_at),
        Index("ix_usage_agent_id", agent_id),
        Index("ix_usage_user_id", user_id),
    )
    
    @validates("metric_value")
    def validate_metric_value(self, key: str, value: float) -> float:
        """Validate metric value is non-negative.
        
        Args:
            key: Field name
            value: Metric value
            
        Returns:
            float: Validated value
            
        Raises:
            ValueError: If value is negative
        """
        if value < 0:
            raise ValueError("Metric value cannot be negative")
        return value
    
    @validates("credits_used")
    def validate_credits_used(self, key: str, credits: float) -> float:
        """Validate credits used is non-negative.
        
        Args:
            key: Field name
            credits: Credits used
            
        Returns:
            float: Validated credits
            
        Raises:
            ValueError: If credits is negative
        """
        if credits < 0:
            raise ValueError("Credits used cannot be negative")
        return credits
    
    @property
    def is_billed(self) -> bool:
        """Check if usage has been billed.
        
        Returns:
            bool: True if billed_at is not None
        """
        return self.billed_at is not None
    
    @property
    def cost_usd(self) -> float:
        """Calculate cost in USD based on credits.
        
        Returns:
            float: Cost in USD (assuming 1 credit = $0.01)
        """
        # TODO: Make pricing configurable per organization/plan
        return float(self.credits_used) * 0.01
    
    def mark_billed(self) -> None:
        """Mark usage record as billed."""
        self.billed_at = func.now()
    
    def __repr__(self) -> str:
        """String representation of usage record."""
        return f"<UsageRecord(id={self.id}, org={self.organization_id}, metric={self.metric_name}, value={self.metric_value})>"