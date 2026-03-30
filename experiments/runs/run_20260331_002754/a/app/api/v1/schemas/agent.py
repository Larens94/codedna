"""app/api/v1/schemas/agent.py — Pydantic schemas for agent endpoints.

exports: AgentCreate, AgentUpdate, AgentResponse, AgentSessionCreate, AgentSessionResponse, SessionMessageCreate, SessionMessageResponse
used_by: app/api/v1/agents.py → request/response validation
rules:   agent config must be valid JSON; temperature between 0 and 2
agent:   BackendEngineer | 2024-03-31 | created agent schemas with validation
         message: "consider adding tool definitions validation"
"""

import re
from typing import Optional, Dict, Any, List
from enum import Enum
from pydantic import BaseModel, Field, validator, ConfigDict
from .base import BaseSchema, PaginatedResponse


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


class AgentCreate(BaseSchema):
    """Schema for creating an agent."""
    name: str = Field(..., min_length=1, max_length=255, description="Agent name")
    slug: str = Field(..., min_length=3, max_length=100, description="URL-safe identifier (unique within org)")
    description: Optional[str] = Field(None, description="Agent description")
    system_prompt: Optional[str] = Field(None, description="System prompt for the agent")
    config: Dict[str, Any] = Field(default_factory=dict, description="Agent configuration (model, parameters, tools, etc.)")
    model_provider: ModelProvider = Field(default=ModelProvider.OPENAI, description="LLM provider")
    model_name: str = Field(default="gpt-4", description="Model name (e.g., gpt-4, claude-3-opus)")
    max_tokens_per_session: int = Field(default=4000, ge=1, le=1000000, description="Maximum tokens per session")
    temperature: str = Field(default="0.7", description="Temperature parameter (0.0 to 2.0)")
    is_public: bool = Field(default=False, description="Whether agent is publicly accessible")
    
    @validator('slug')
    def validate_slug(cls, v):
        """Validate slug format."""
        if not re.match(r'^[a-z0-9-]+$', v):
            raise ValueError('Slug can only contain lowercase letters, numbers, and hyphens')
        return v.lower()
    
    @validator('temperature')
    def validate_temperature(cls, v):
        """Validate temperature parameter."""
        try:
            temp_float = float(v)
        except ValueError:
            raise ValueError('Temperature must be a number')
        
        if temp_float < 0.0 or temp_float > 2.0:
            raise ValueError('Temperature must be between 0.0 and 2.0')
        
        return str(temp_float)


class AgentUpdate(BaseSchema):
    """Schema for updating an agent."""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Agent name")
    description: Optional[str] = Field(None, description="Agent description")
    system_prompt: Optional[str] = Field(None, description="System prompt")
    config: Optional[Dict[str, Any]] = Field(None, description="Agent configuration")
    model_provider: Optional[ModelProvider] = Field(None, description="LLM provider")
    model_name: Optional[str] = Field(None, description="Model name")
    max_tokens_per_session: Optional[int] = Field(None, ge=1, le=1000000, description="Maximum tokens per session")
    temperature: Optional[str] = Field(None, description="Temperature parameter")
    is_public: Optional[bool] = Field(None, description="Whether agent is publicly accessible")
    is_active: Optional[bool] = Field(None, description="Whether agent is active")
    
    @validator('temperature')
    def validate_temperature(cls, v):
        """Validate temperature parameter."""
        if v is None:
            return v
        
        try:
            temp_float = float(v)
        except ValueError:
            raise ValueError('Temperature must be a number')
        
        if temp_float < 0.0 or temp_float > 2.0:
            raise ValueError('Temperature must be between 0.0 and 2.0')
        
        return str(temp_float)


class AgentResponse(BaseSchema):
    """Schema for agent response."""
    id: int = Field(..., description="Agent ID")
    organization_id: int = Field(..., description="Organization ID")
    name: str = Field(..., description="Agent name")
    slug: str = Field(..., description="URL-safe identifier")
    description: Optional[str] = Field(None, description="Agent description")
    system_prompt: Optional[str] = Field(None, description="System prompt")
    config: Dict[str, Any] = Field(..., description="Agent configuration")
    model_provider: ModelProvider = Field(..., description="LLM provider")
    model_name: str = Field(..., description="Model name")
    max_tokens_per_session: int = Field(..., description="Maximum tokens per session")
    temperature: str = Field(..., description="Temperature parameter")
    is_public: bool = Field(..., description="Whether agent is publicly accessible")
    is_active: bool = Field(..., description="Whether agent is active")
    created_by: Optional[int] = Field(None, description="User who created this agent")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class AgentRunRequest(BaseSchema):
    """Schema for running an agent."""
    prompt: str = Field(..., min_length=1, description="User prompt")
    session_id: Optional[str] = Field(None, description="Existing session ID (optional)")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Additional parameters")
    stream: bool = Field(default=False, description="Whether to stream response")


class AgentRunResponse(BaseSchema):
    """Schema for agent run response (non-streaming)."""
    response: str = Field(..., description="Agent response")
    session_id: str = Field(..., description="Session ID")
    message_id: int = Field(..., description="Message ID")
    token_count: int = Field(..., description="Tokens used")
    credits_used: float = Field(..., description="Credits used")


class AgentSessionCreate(BaseSchema):
    """Schema for creating an agent session."""
    title: Optional[str] = Field(None, max_length=255, description="Session title")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Session metadata")


class AgentSessionResponse(BaseSchema):
    """Schema for agent session response."""
    id: str = Field(..., description="Session ID (UUID)")
    agent_id: int = Field(..., description="Agent ID")
    user_id: Optional[int] = Field(None, description="User ID")
    organization_id: int = Field(..., description="Organization ID")
    title: Optional[str] = Field(None, description="Session title")
    metadata: Dict[str, Any] = Field(..., description="Session metadata")
    token_count: int = Field(..., description="Total tokens used")
    is_active: bool = Field(..., description="Whether session is active")
    ended_at: Optional[datetime] = Field(None, description="When session ended")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    message_count: int = Field(..., description="Number of messages in session")


class SessionMessageCreate(BaseSchema):
    """Schema for creating a session message."""
    role: MessageRole = Field(..., description="Message role")
    content: str = Field(..., min_length=1, description="Message content")
    tool_calls: Optional[List[Dict[str, Any]]] = Field(None, description="Tool calls (for assistant role)")
    tool_call_id: Optional[str] = Field(None, description="Tool call ID (for tool role)")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Message metadata")


class SessionMessageResponse(BaseSchema):
    """Schema for session message response."""
    id: int = Field(..., description="Message ID")
    session_id: str = Field(..., description="Session ID")
    role: MessageRole = Field(..., description="Message role")
    content: str = Field(..., description="Message content")
    tool_calls: Optional[List[Dict[str, Any]]] = Field(None, description="Tool calls")
    tool_call_id: Optional[str] = Field(None, description="Tool call ID")
    token_count: Optional[int] = Field(None, description="Tokens used")
    metadata: Dict[str, Any] = Field(..., description="Message metadata")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class AgentListResponse(PaginatedResponse[AgentResponse]):
    """Paginated response for agent list."""
    pass


class AgentSessionListResponse(PaginatedResponse[AgentSessionResponse]):
    """Paginated response for agent session list."""
    pass


class SessionMessageListResponse(PaginatedResponse[SessionMessageResponse]):
    """Paginated response for session message list."""
    pass


# Import datetime after class definitions to avoid circular import
from datetime import datetime