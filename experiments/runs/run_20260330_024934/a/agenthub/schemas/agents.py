"""agents.py — Agent management schemas for request/response validation.

exports: AgentCreate, AgentUpdate, AgentResponse, AgentRunCreate, AgentRunResponse
used_by: agents.py router
rules:   must validate system_prompt length; must enforce pricing constraints
agent:   BackendEngineer | 2024-01-15 | created agent schemas
         message: "implement agent execution with proper error handling and rollback"
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, validator
import re


class AgentCreate(BaseModel):
    """Schema for creating a new agent."""
    
    name: str = Field(..., min_length=1, max_length=255, description="Agent name")
    slug: str = Field(..., min_length=1, max_length=100, description="URL-friendly slug")
    description: Optional[str] = Field(None, description="Agent description")
    system_prompt: str = Field(..., min_length=10, max_length=10000, description="System prompt")
    model: str = Field(..., description="AI model to use (e.g., claude-3-5-sonnet, gpt-4)")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="Temperature parameter")
    max_tokens: int = Field(2000, ge=1, le=100000, description="Maximum tokens per response")
    is_public: bool = Field(False, description="Whether agent is publicly visible")
    price_per_run: float = Field(0.0, ge=0.0, description="Price per run in credits")
    category: str = Field("general", description="Agent category")
    tags: List[str] = Field(default_factory=list, description="Agent tags")
    config: Dict[str, Any] = Field(default_factory=dict, description="Additional configuration")
    
    @validator("slug")
    def validate_slug(cls, v):
        """Validate slug format."""
        if not re.match(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", v):
            raise ValueError("Slug must contain only lowercase letters, numbers, and hyphens")
        return v
    
    @validator("model")
    def validate_model(cls, v):
        """Validate model name."""
        allowed_models = ["claude-3-5-sonnet", "gpt-4", "gpt-3.5-turbo", "claude-3-opus", "claude-3-haiku"]
        if v not in allowed_models:
            raise ValueError(f"Model must be one of: {', '.join(allowed_models)}")
        return v


class AgentUpdate(BaseModel):
    """Schema for updating an existing agent."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Agent name")
    description: Optional[str] = Field(None, description="Agent description")
    system_prompt: Optional[str] = Field(None, min_length=10, max_length=10000, description="System prompt")
    model: Optional[str] = Field(None, description="AI model to use")
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0, description="Temperature parameter")
    max_tokens: Optional[int] = Field(None, ge=1, le=100000, description="Maximum tokens per response")
    is_public: Optional[bool] = Field(None, description="Whether agent is publicly visible")
    is_active: Optional[bool] = Field(None, description="Whether agent is active")
    price_per_run: Optional[float] = Field(None, ge=0.0, description="Price per run in credits")
    category: Optional[str] = Field(None, description="Agent category")
    tags: Optional[List[str]] = Field(None, description="Agent tags")
    config: Optional[Dict[str, Any]] = Field(None, description="Additional configuration")
    
    @validator("model")
    def validate_model(cls, v):
        """Validate model name."""
        if v is not None:
            allowed_models = ["claude-3-5-sonnet", "gpt-4", "gpt-3.5-turbo", "claude-3-opus", "claude-3-haiku"]
            if v not in allowed_models:
                raise ValueError(f"Model must be one of: {', '.join(allowed_models)}")
        return v


class AgentResponse(BaseModel):
    """Schema for agent response."""
    
    public_id: str = Field(..., description="Public agent ID")
    name: str = Field(..., description="Agent name")
    slug: str = Field(..., description="URL-friendly slug")
    description: Optional[str] = Field(None, description="Agent description")
    system_prompt: str = Field(..., description="System prompt")
    model: str = Field(..., description="AI model to use")
    temperature: float = Field(..., description="Temperature parameter")
    max_tokens: int = Field(..., description="Maximum tokens per response")
    is_public: bool = Field(..., description="Whether agent is publicly visible")
    is_active: bool = Field(..., description="Whether agent is active")
    price_per_run: float = Field(..., description="Price per run in credits")
    category: str = Field(..., description="Agent category")
    tags: List[str] = Field(..., description="Agent tags")
    config: Dict[str, Any] = Field(..., description="Additional configuration")
    owner_id: int = Field(..., description="Owner user ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    
    class Config:
        from_attributes = True


class AgentRunCreate(BaseModel):
    """Schema for creating an agent run."""
    
    input_data: Dict[str, Any] = Field(..., description="Input data for the agent")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Run metadata")


class AgentRunResponse(BaseModel):
    """Schema for agent run response."""
    
    public_id: str = Field(..., description="Public run ID")
    agent_id: int = Field(..., description="Agent ID")
    user_id: int = Field(..., description="User ID")
    input_data: Dict[str, Any] = Field(..., description="Input data for the agent")
    output_data: Optional[Dict[str, Any]] = Field(None, description="Output data from agent")
    status: str = Field(..., description="Run status")
    credits_used: float = Field(..., description="Credits used for this run")
    started_at: Optional[datetime] = Field(None, description="Run start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Run completion timestamp")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    metadata: Dict[str, Any] = Field(..., description="Run metadata")
    created_at: datetime = Field(..., description="Creation timestamp")
    
    class Config:
        from_attributes = True