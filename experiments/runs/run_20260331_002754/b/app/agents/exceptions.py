"""Exceptions for the agent integration layer."""

from typing import Optional


class AgentError(Exception):
    """Base exception for agent-related errors."""
    
    def __init__(self, message: str, agent_id: Optional[str] = None):
        self.message = message
        self.agent_id = agent_id
        super().__init__(self.message)


class TokenLimitExceeded(AgentError):
    """Raised when token limit is exceeded."""
    
    def __init__(self, limit: int, actual: int, agent_id: Optional[str] = None):
        self.limit = limit
        self.actual = actual
        message = f"Token limit exceeded: {actual} > {limit}"
        super().__init__(message, agent_id)


class CreditExhausted(AgentError):
    """Raised when user credits are exhausted."""
    
    def __init__(self, available: float, required: float, user_id: Optional[int] = None):
        self.available = available
        self.required = required
        self.user_id = user_id
        message = f"Insufficient credits: {available} < {required}"
        super().__init__(message)


class AgentNotFound(AgentError):
    """Raised when agent is not found."""
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        message = f"Agent not found: {agent_id}"
        super().__init__(message, agent_id)


class ConfigurationError(AgentError):
    """Raised when agent configuration is invalid."""
    
    def __init__(self, message: str, field: Optional[str] = None):
        self.field = field
        super().__init__(message)


class MemoryError(AgentError):
    """Raised when memory operations fail."""
    
    pass


class ToolError(AgentError):
    """Raised when tool execution fails."""
    
    pass


class RateLimitExceeded(AgentError):
    """Raised when rate limit is exceeded."""
    
    def __init__(self, retry_after: Optional[int] = None):
        self.retry_after = retry_after
        message = "Rate limit exceeded"
        if retry_after:
            message += f", retry after {retry_after} seconds"
        super().__init__(message)


class ModelNotAvailable(AgentError):
    """Raised when requested model is not available."""
    
    def __init__(self, model: str):
        self.model = model
        message = f"Model not available: {model}"
        super().__init__(message)