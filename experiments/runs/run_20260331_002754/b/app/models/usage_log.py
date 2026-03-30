"""Usage logging for token tracking and cost calculation."""

from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float, Numeric, JSON, BigInteger
from sqlalchemy.orm import relationship
from decimal import Decimal
import enum

from app import db


class UsageType(enum.Enum):
    """Usage type enumeration."""
    
    AGENT_RUN = 'agent_run'
    API_CALL = 'api_call'
    MEMORY_STORAGE = 'memory_storage'
    AGENT_TRAINING = 'agent_training'
    FILE_STORAGE = 'file_storage'


class ProviderType(enum.Enum):
    """AI provider type enumeration."""
    
    OPENAI = 'openai'
    ANTHROPIC = 'anthropic'
    GOOGLE = 'google'
    AZURE = 'azure'
    AGNO = 'agno'
    CUSTOM = 'custom'


class UsageLog(db.Model):
    """Usage log model for tracking token usage and costs.
    
    Attributes:
        id: Primary key
        user_id: Foreign key to user
        organization_id: Foreign key to organization
        agent_id: Foreign key to agent
        agent_run_id: Foreign key to agent run
        usage_type: Type of usage
        provider: AI provider
        model: Model used
        prompt_tokens: Number of prompt tokens
        completion_tokens: Number of completion tokens
        total_tokens: Total tokens (prompt + completion)
        input_cost_usd: Cost for input tokens in USD
        output_cost_usd: Cost for output tokens in USD
        total_cost_usd: Total cost in USD
        credits_used: Credits deducted for this usage
        metadata: Additional metadata (JSON)
        logged_at: When usage was logged
        created_at: Creation timestamp
        user: Associated user
        organization: Associated organization
        agent: Associated agent
        agent_run: Associated agent run
    """
    
    __tablename__ = 'usage_logs'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'))
    organization_id = Column(Integer, ForeignKey('organizations.id', ondelete='CASCADE'))
    agent_id = Column(Integer, ForeignKey('agents.id', ondelete='CASCADE'))
    agent_run_id = Column(Integer, ForeignKey('agent_runs.id', ondelete='CASCADE'))
    usage_type = Column(Enum(UsageType), nullable=False)
    provider = Column(Enum(ProviderType))
    model = Column(String(100))
    prompt_tokens = Column(BigInteger, default=0)
    completion_tokens = Column(BigInteger, default=0)
    total_tokens = Column(BigInteger, default=0)
    input_cost_usd = Column(Numeric(12, 8), default=Decimal('0.00000000'))  # Small costs per token
    output_cost_usd = Column(Numeric(12, 8), default=Decimal('0.00000000'))
    total_cost_usd = Column(Numeric(10, 4), default=Decimal('0.0000'))
    credits_used = Column(Integer, default=0)  # Credits = cost_usd * 100 (1 credit = $0.01)
    metadata = Column(JSON)
    logged_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Indexes for efficient querying
    __table_args__ = (
        db.Index('ix_usage_logs_user_id_logged_at', 'user_id', 'logged_at'),
        db.Index('ix_usage_logs_organization_id_logged_at', 'organization_id', 'logged_at'),
        db.Index('ix_usage_logs_agent_id_logged_at', 'agent_id', 'logged_at'),
        db.Index('ix_usage_logs_agent_run_id', 'agent_run_id'),
        db.Index('ix_usage_logs_usage_type', 'usage_type'),
    )
    
    # Relationships
    user = relationship('User')
    organization = relationship('Organization')
    agent = relationship('Agent')
    agent_run = relationship('AgentRun')
    
    def calculate_costs(self, input_price_per_1k: float, output_price_per_1k: float) -> None:
        """Calculate costs based on token counts and pricing.
        
        Args:
            input_price_per_1k: Price per 1K input tokens in USD
            output_price_per_1k: Price per 1K output tokens in USD
        """
        # Calculate input cost
        self.input_cost_usd = Decimal(str((self.prompt_tokens / 1000) * input_price_per_1k))
        
        # Calculate output cost
        self.output_cost_usd = Decimal(str((self.completion_tokens / 1000) * output_price_per_1k))
        
        # Calculate total cost
        self.total_cost_usd = self.input_cost_usd + self.output_cost_usd
        
        # Calculate credits used (1 credit = $0.01)
        self.credits_used = int(self.total_cost_usd * 100)
    
    def get_metadata_dict(self) -> Dict[str, Any]:
        """Get metadata as dictionary.
        
        Returns:
            Metadata dictionary
        """
        return self.metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert usage log to dictionary representation.
        
        Returns:
            Dictionary representation of usage log
        """
        return {
            'id': self.id,
            'user_id': self.user_id,
            'organization_id': self.organization_id,
            'agent_id': self.agent_id,
            'agent_run_id': self.agent_run_id,
            'usage_type': self.usage_type.value if self.usage_type else None,
            'provider': self.provider.value if self.provider else None,
            'model': self.model,
            'prompt_tokens': self.prompt_tokens,
            'completion_tokens': self.completion_tokens,
            'total_tokens': self.total_tokens,
            'input_cost_usd': float(self.input_cost_usd) if self.input_cost_usd else 0.0,
            'output_cost_usd': float(self.output_cost_usd) if self.output_cost_usd else 0.0,
            'total_cost_usd': float(self.total_cost_usd) if self.total_cost_usd else 0.0,
            'credits_used': self.credits_used,
            'metadata': self.get_metadata_dict(),
            'logged_at': self.logged_at.isoformat() if self.logged_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
    
    def __repr__(self) -> str:
        return f'<UsageLog {self.id}: {self.usage_type.value} ({self.total_tokens} tokens)>'


class PricingRate(db.Model):
    """Pricing rate model for AI provider costs.
    
    Attributes:
        id: Primary key
        provider: AI provider
        model: Model name
        input_price_per_1k_usd: Price per 1K input tokens in USD
        output_price_per_1k_usd: Price per 1K output tokens in USD
        is_active: Whether this rate is active
        effective_from: When this rate becomes effective
        effective_to: When this rate expires
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """
    
    __tablename__ = 'pricing_rates'
    
    id = Column(Integer, primary_key=True)
    provider = Column(Enum(ProviderType), nullable=False)
    model = Column(String(100), nullable=False)
    input_price_per_1k_usd = Column(Numeric(10, 6), nullable=False)  # e.g., 0.001500 for $0.0015 per 1K
    output_price_per_1k_usd = Column(Numeric(10, 6), nullable=False)
    is_active = Column(Boolean, default=True)
    effective_from = Column(DateTime, default=datetime.utcnow)
    effective_to = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        db.Index('ix_pricing_rates_provider_model', 'provider', 'model'),
        db.UniqueConstraint('provider', 'model', 'effective_from', name='uq_provider_model_effective_from'),
    )
    
    def get_current_rate(cls, provider: ProviderType, model: str) -> Optional['PricingRate']:
        """Get current active pricing rate for provider and model.
        
        Args:
            provider: AI provider
            model: Model name
            
        Returns:
            PricingRate instance or None if not found
        """
        now = datetime.utcnow()
        return cls.query.filter(
            cls.provider == provider,
            cls.model == model,
            cls.is_active == True,
            cls.effective_from <= now,
            (cls.effective_to == None) | (cls.effective_to > now)
        ).first()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert pricing rate to dictionary representation.
        
        Returns:
            Dictionary representation of pricing rate
        """
        return {
            'id': self.id,
            'provider': self.provider.value if self.provider else None,
            'model': self.model,
            'input_price_per_1k_usd': float(self.input_price_per_1k_usd) if self.input_price_per_1k_usd else 0.0,
            'output_price_per_1k_usd': float(self.output_price_per_1k_usd) if self.output_price_per_1k_usd else 0.0,
            'is_active': self.is_active,
            'effective_from': self.effective_from.isoformat() if self.effective_from else None,
            'effective_to': self.effective_to.isoformat() if self.effective_to else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def __repr__(self) -> str:
        return f'<PricingRate {self.provider.value}/{self.model}: ${self.input_price_per_1k_usd}/1K in, ${self.output_price_per_1k_usd}/1K out>'