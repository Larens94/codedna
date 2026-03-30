"""app/models/agent.py — Agent, session, and message models.

exports: Agent, AgentSession, SessionMessage
used_by: agent service → CRUD, session service → conversation management
rules:   agent config must be valid JSON; sessions track token usage; messages preserve conversation history
agent:   Product Architect | 2024-03-30 | implemented agent models with conversation tracking
         message: "consider adding vector embeddings for message semantic search"
"""

import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

from sqlalchemy import (
    Boolean,
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    JSON,
    Index,
    UniqueConstraint,
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func

from app.models.base import Base, TimestampMixin


class ModelProvider(str, Enum):
    """Supported LLM model providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    AZURE = "azure"
    GOOGLE = "google"
    CUSTOM = "custom"


class MessageRole(str, Enum):
    """Message roles in conversation."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class Agent(Base, TimestampMixin):
    """AI agent configuration and metadata.
    
    Rules:
        Each agent belongs to an organization
        Config is validated JSON schema
        Slug must be unique within organization
    """
    
    __tablename__ = "agents"
    
    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        doc="Unique agent identifier",
    )
    
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        doc="Organization that owns this agent",
    )
    
    name = Column(
        String(255),
        nullable=False,
        doc="Agent name",
    )
    
    slug = Column(
        String(100),
        nullable=False,
        doc="URL-safe agent identifier (unique within org)",
    )
    
    description = Column(
        Text,
        nullable=True,
        doc="Agent description",
    )
    
    system_prompt = Column(
        Text,
        nullable=True,
        doc="System prompt for the agent",
    )
    
    config = Column(
        JSON,
        nullable=False,
        default=dict,
        doc="Agent configuration (model, parameters, tools, etc.)",
    )
    
    model_provider = Column(
        SQLEnum(ModelProvider),
        default=ModelProvider.OPENAI,
        nullable=False,
        doc="LLM provider",
    )
    
    model_name = Column(
        String(100),
        default="gpt-4",
        nullable=False,
        doc="Model name (e.g., gpt-4, claude-3-opus)",
    )
    
    max_tokens_per_session = Column(
        Integer,
        default=4000,
        nullable=False,
        doc="Maximum tokens per session",
    )
    
    temperature = Column(
        # Using String to avoid floating point issues, will convert to Decimal in service
        String(10),
        default="0.7",
        nullable=False,
        doc="Temperature parameter (0.0 to 2.0)",
    )
    
    is_public = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether agent is publicly accessible",
    )
    
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether agent is active",
    )
    
    created_by = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
        doc="User who created this agent",
    )
    
    # Relationships
    organization = relationship(
        "Organization",
        back_populates="agents",
        lazy="selectin",
    )
    
    created_by_user = relationship(
        "User",
        back_populates="created_agents",
        lazy="selectin",
        foreign_keys=[created_by],
    )
    
    sessions = relationship(
        "AgentSession",
        back_populates="agent",
        cascade="all, delete-orphan",
        lazy="selectin",
        doc="Sessions for this agent",
    )
    
    tasks = relationship(
        "Task",
        back_populates="agent",
        cascade="all, delete-orphan",
        lazy="selectin",
        doc="Tasks using this agent",
    )
    
    usage_records = relationship(
        "UsageRecord",
        back_populates="agent",
        cascade="all, delete-orphan",
        lazy="selectin",
        doc="Usage records for this agent",
    )
    
    # Constraints
    __table_args__ = (
        UniqueConstraint("organization_id", "slug", name="uq_org_agent_slug"),
        Index("ix_agents_org_id", organization_id),
        Index("ix_agents_is_active", is_active),
        Index("ix_agents_is_public", is_public),
    )
    
    @validates("slug")
    def validate_slug(self, key: str, slug: str) -> str:
        """Validate agent slug.
        
        Args:
            key: Field name
            slug: Slug to validate
            
        Returns:
            str: Validated slug
            
        Raises:
            ValueError: If slug format is invalid
        """
        import re
        
        if not slug:
            raise ValueError("Slug cannot be empty")
        
        slug = slug.strip().lower()
        
        if len(slug) < 3:
            raise ValueError("Slug must be at least 3 characters")
        if len(slug) > 100:
            raise ValueError("Slug must be at most 100 characters")
        if not re.match(r"^[a-z0-9-]+$", slug):
            raise ValueError("Slug can only contain lowercase letters, numbers, and hyphens")
        
        return slug
    
    @validates("temperature")
    def validate_temperature(self, key: str, temperature: str) -> str:
        """Validate temperature parameter.
        
        Args:
            key: Field name
            temperature: Temperature string to validate
            
        Returns:
            str: Validated temperature string
            
        Raises:
            ValueError: If temperature is out of range
        """
        try:
            temp_float = float(temperature)
        except ValueError:
            raise ValueError("Temperature must be a number")
        
        if temp_float < 0.0 or temp_float > 2.0:
            raise ValueError("Temperature must be between 0.0 and 2.0")
        
        return str(temp_float)
    
    @property
    def model_config(self) -> Dict[str, Any]:
        """Get model configuration.
        
        Returns:
            Dict with model provider and name
        """
        return {
            "provider": self.model_provider.value,
            "model": self.model_name,
            "temperature": float(self.temperature),
            "max_tokens": self.max_tokens_per_session,
        }
    
    def __repr__(self) -> str:
        """String representation of agent."""
        return f"<Agent(id={self.id}, name='{self.name}', org={self.organization_id})>"


class AgentSession(Base, TimestampMixin):
    """Agent conversation session.
    
    Rules:
        Each session tracks a conversation with an agent
        Token usage is accumulated for billing
        Sessions can be active or ended
    """
    
    __tablename__ = "agent_sessions"
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
        doc="Unique session identifier (UUID)",
    )
    
    agent_id = Column(
        Integer,
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        doc="Agent for this session",
    )
    
    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
        doc="User who started this session",
    )
    
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        doc="Organization that owns this session",
    )
    
    title = Column(
        String(255),
        nullable=True,
        doc="Session title (auto-generated from first message)",
    )
    
    metadata = Column(
        JSON,
        default=dict,
        nullable=False,
        doc="Session metadata (browser, IP, etc.)",
    )
    
    token_count = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Total tokens used in this session",
    )
    
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether session is active",
    )
    
    ended_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="When session was ended",
    )
    
    # Relationships
    agent = relationship(
        "Agent",
        back_populates="sessions",
        lazy="selectin",
    )
    
    user = relationship(
        "User",
        lazy="selectin",
    )
    
    organization = relationship(
        "Organization",
        back_populates="sessions",
        lazy="selectin",
    )
    
    messages = relationship(
        "SessionMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="SessionMessage.created_at",
        doc="Messages in this session",
    )
    
    usage_records = relationship(
        "UsageRecord",
        back_populates="session",
        cascade="all, delete-orphan",
        lazy="selectin",
        doc="Usage records for this session",
    )
    
    # Indexes
    __table_args__ = (
        Index("ix_sessions_agent_id", agent_id),
        Index("ix_sessions_user_id", user_id),
        Index("ix_sessions_org_id", organization_id),
        Index("ix_sessions_is_active", is_active),
        Index("ix_sessions_created_at", created_at),
    )
    
    @property
    def message_count(self) -> int:
        """Get number of messages in session.
        
        Returns:
            int: Number of messages
        """
        return len(self.messages) if self.messages else 0
    
    def end_session(self) -> None:
        """Mark session as ended."""
        self.is_active = False
        self.ended_at = func.now()
    
    def __repr__(self) -> str:
        """String representation of session."""
        return f"<AgentSession(id={self.id}, agent={self.agent_id}, active={self.is_active})>"


class SessionMessage(Base, TimestampMixin):
    """Message in an agent session.
    
    Rules:
        Each message belongs to a session
        Tool calls and responses are stored as JSON
        Token count is recorded for billing
    """
    
    __tablename__ = "session_messages"
    
    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        doc="Unique message identifier",
    )
    
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agent_sessions.id", ondelete="CASCADE"),
        nullable=False,
        doc="Session this message belongs to",
    )
    
    role = Column(
        SQLEnum(MessageRole),
        nullable=False,
        doc="Message role (user, assistant, system, tool)",
    )
    
    content = Column(
        Text,
        nullable=False,
        doc="Message content",
    )
    
    tool_calls = Column(
        JSON,
        nullable=True,
        doc="Tool calls made by the assistant (JSON array)",
    )
    
    tool_call_id = Column(
        String(100),
        nullable=True,
        doc="Tool call ID for tool response messages",
    )
    
    token_count = Column(
        Integer,
        nullable=True,
        doc="Tokens used by this message",
    )
    
    metadata = Column(
        JSON,
        default=dict,
        nullable=False,
        doc="Message metadata (latency, model, etc.)",
    )
    
    # Relationships
    session = relationship(
        "AgentSession",
        back_populates="messages",
        lazy="selectin",
    )
    
    # Indexes
    __table_args__ = (
        Index("ix_messages_session_id", session_id),
        Index("ix_messages_role", role),
        Index("ix_messages_created_at", created_at),
    )
    
    def __repr__(self) -> str:
        """String representation of message."""
        content_preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"<SessionMessage(id={self.id}, role={self.role}, content='{content_preview}')>"