"""models.py — SQLAlchemy models for AgentHub.

exports: Base, User, Agent, AgentRun, ScheduledTask, CreditAccount, Invoice, OrgMembership, AuditLog
used_by: session.py, seed.py, all API routers
rules:   all models must inherit from Base; use UUID for public IDs; timestamps in UTC
agent:   ProductArchitect | 2024-01-15 | created all core models with relationships
         message: "verify foreign key constraints and cascade behaviors are correct"
"""

import uuid
from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, ForeignKey, 
    Text, Float, JSON, Enum, BigInteger, UniqueConstraint, CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class User(Base):
    """User account with authentication and profile.
    
    Rules:   email must be unique; password hash required; status must be active/inactive
    message: claude-sonnet-4-6 | 2024-01-15 | consider adding email verification flow
    """
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(UUID(as_uuid=True), unique=True, default=uuid.uuid4, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255))
    avatar_url = Column(String(500))
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    agents = relationship("Agent", back_populates="owner", cascade="all, delete-orphan")
    agent_runs = relationship("AgentRun", back_populates="user", cascade="all, delete-orphan")
    credit_accounts = relationship("CreditAccount", back_populates="user", cascade="all, delete-orphan")
    org_memberships = relationship("OrgMembership", back_populates="user", cascade="all, delete-orphan", primaryjoin="User.id==OrgMembership.user_id", foreign_keys="[OrgMembership.user_id]")
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")


class Agent(Base):
    """Agent definition with configuration and pricing.
    
    Rules:   slug must be unique; price_per_run must be >= 0; owner_id required
    message: claude-sonnet-4-6 | 2024-01-15 | consider adding versioning for agent definitions
    """
    __tablename__ = "agents"
    
    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(UUID(as_uuid=True), unique=True, default=uuid.uuid4, index=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, index=True, nullable=False)
    description = Column(Text)
    system_prompt = Column(Text, nullable=False)
    model = Column(String(100), nullable=False)  # e.g., "claude-3-5-sonnet", "gpt-4"
    temperature = Column(Float, default=0.7)
    max_tokens = Column(Integer, default=2000)
    is_public = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    price_per_run = Column(Float, default=0.0, nullable=False)
    category = Column(String(100), default="general")
    tags = Column(JSON, default=list)  # List of strings
    config = Column(JSON, default=dict)  # Additional agent-specific configuration
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    owner = relationship("User", back_populates="agents")
    agent_runs = relationship("AgentRun", back_populates="agent", cascade="all, delete-orphan")
    scheduled_tasks = relationship("ScheduledTask", back_populates="agent", cascade="all, delete-orphan")
    
    __table_args__ = (
        CheckConstraint("price_per_run >= 0", name="price_non_negative"),
    )


class AgentRun(Base):
    """Execution record of an agent run.
    
    Rules:   must track credits used; status must be one of pending/running/completed/failed
    message: claude-sonnet-4-6 | 2024-01-15 | add retry logic and failure reasons
    """
    __tablename__ = "agent_runs"
    
    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(UUID(as_uuid=True), unique=True, default=uuid.uuid4, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    agent_id = Column(Integer, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    input_data = Column(JSON, nullable=False)
    output_data = Column(JSON)
    status = Column(
        Enum("pending", "running", "completed", "failed", name="run_status"),
        default="pending",
        nullable=False
    )
    credits_used = Column(Float, default=0.0)
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    error_message = Column(Text)
    metadata_ = Column('metadata', JSON, default=dict)  # Additional run metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="agent_runs")
    agent = relationship("Agent", back_populates="agent_runs")
    
    __table_args__ = (
        CheckConstraint("credits_used >= 0", name="credits_non_negative"),
    )


class ScheduledTask(Base):
    """Recurring or scheduled agent executions.
    
    Rules:   cron_expression or interval_seconds required; must have next_run_at
    message: claude-sonnet-4-6 | 2024-01-15 | implement timezone support for cron schedules
    """
    __tablename__ = "scheduled_tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(UUID(as_uuid=True), unique=True, default=uuid.uuid4, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    agent_id = Column(Integer, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    cron_expression = Column(String(100))  # e.g., "0 9 * * *"
    interval_seconds = Column(Integer)  # For interval-based scheduling
    input_data = Column(JSON, nullable=False)
    is_active = Column(Boolean, default=True)
    next_run_at = Column(DateTime(timezone=True), nullable=False)
    last_run_at = Column(DateTime(timezone=True))
    last_run_status = Column(
        Enum("pending", "running", "completed", "failed", name="task_status")
    )
    metadata_ = Column('metadata', JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User")
    agent = relationship("Agent", back_populates="scheduled_tasks")
    
    __table_args__ = (
        CheckConstraint(
            "cron_expression IS NOT NULL OR interval_seconds IS NOT NULL",
            name="schedule_required"
        ),
        CheckConstraint(
            "interval_seconds IS NULL OR interval_seconds > 0",
            name="positive_interval"
        ),
    )


class CreditAccount(Base):
    """User credit balance and transactions.
    
    Rules:   balance must be >= 0; must track all transactions
    message: claude-sonnet-4-6 | 2024-01-15 | implement credit expiration and renewal
    """
    __tablename__ = "credit_accounts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    balance = Column(Float, default=0.0, nullable=False)
    currency = Column(String(3), default="USD", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="credit_accounts")
    invoices = relationship("Invoice", back_populates="credit_account", cascade="all, delete-orphan")
    
    __table_args__ = (
        CheckConstraint("balance >= 0", name="non_negative_balance"),
    )


class Invoice(Base):
    """Billing invoice for credit purchases.
    
    Rules:   amount must be > 0; status must be draft/paid/failed/refunded
    message: claude-sonnet-4-6 | 2024-01-15 | integrate with Stripe/PayPal webhooks
    """
    __tablename__ = "invoices"
    
    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(UUID(as_uuid=True), unique=True, default=uuid.uuid4, index=True)
    credit_account_id = Column(Integer, ForeignKey("credit_accounts.id", ondelete="CASCADE"), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(3), default="USD", nullable=False)
    status = Column(
        Enum("draft", "pending", "paid", "failed", "refunded", name="invoice_status"),
        default="draft",
        nullable=False
    )
    payment_method = Column(String(100))
    payment_id = Column(String(255))  # External payment system ID
    credits_added = Column(Float, nullable=False)
    metadata_ = Column('metadata', JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    paid_at = Column(DateTime(timezone=True))
    
    # Relationships
    credit_account = relationship("CreditAccount", back_populates="invoices")
    
    __table_args__ = (
        CheckConstraint("amount > 0", name="positive_amount"),
        CheckConstraint("credits_added > 0", name="positive_credits"),
    )


class OrgMembership(Base):
    """Organization membership for team collaboration.
    
    Rules:   user can have multiple orgs; role must be member/admin/owner
    message: claude-sonnet-4-6 | 2024-01-15 | implement org-level credit pools and billing
    """
    __tablename__ = "org_memberships"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    org_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role = Column(
        Enum("member", "admin", "owner", name="org_role"),
        default="member",
        nullable=False
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="org_memberships", foreign_keys=[user_id])
    org = relationship("User", foreign_keys=[org_id])
    
    __table_args__ = (
        UniqueConstraint("user_id", "org_id", name="unique_org_membership"),
    )


class AuditLog(Base):
    """System audit trail for security and compliance.
    
    Rules:   must log all significant actions; include user context
    message: claude-sonnet-4-6 | 2024-01-15 | implement log rotation and retention policies
    """
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(100), nullable=False)  # e.g., "login", "agent_run", "credit_purchase"
    resource_type = Column(String(50))  # e.g., "agent", "user", "invoice"
    resource_id = Column(String(100))  # Could be integer or UUID string
    details = Column(JSON, default=dict)
    ip_address = Column(String(45))  # Supports IPv6
    user_agent = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="audit_logs")