"""AI Agent integration layer for AgentHub.

This module provides the core agent integration layer for AgentHub,
including agent wrapping, marketplace catalog, agent studio, memory
management, and agent execution.
"""

from .agent_wrapper import AgentWrapper, TokenCounter
from .catalog import AgentSpec, get_marketplace_catalog, get_agent_spec_by_slug
from .studio import AgentConfig, build_custom_agent, validate_agent_config
from .memory import PersistentMemory, MemoryType, MemoryStore
from .runner import run_agent, run_agent_stream, AgentRunner
from .exceptions import AgentError, TokenLimitExceeded, CreditExhausted

__all__ = [
    'AgentWrapper',
    'TokenCounter',
    'AgentSpec',
    'get_marketplace_catalog',
    'get_agent_spec_by_slug',
    'AgentConfig',
    'build_custom_agent',
    'validate_agent_config',
    'PersistentMemory',
    'MemoryType',
    'MemoryStore',
    'run_agent',
    'run_agent_stream',
    'AgentRunner',
    'AgentError',
    'TokenLimitExceeded',
    'CreditExhausted',
]