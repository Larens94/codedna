"""__init__.py — Agno agent wrappers and marketplace catalog.

exports: AgentWrapper, AgentFactory, PersistentMemory, run_agent_stream
used_by: api/agents.py → agent execution, cli.py → agent studio
rules:   All agent operations must go through AgentWrapper
         Marketplace agents must be loaded from catalog.py
         Memory operations must use PersistentMemory
agent:   AgentIntegrator | 2024-03-30 | implemented complete agent framework
         message: "implement agent execution with proper error handling and rollback"
"""

from .base import AgentWrapper, AgentConfig, CreditExhaustedError
from .catalog import (
    MARKETPLACE_AGENTS, AgentSpec, get_agent_by_slug, 
    search_agents, get_agents_by_category, get_featured_agents
)
from .studio import (
    AgentFactory, StudioConfig, build_custom_agent, 
    validate_agent_config, create_agent_from_template
)
from .memory import PersistentMemory, MemoryEntry, MemoryType, summarize_context
from .runner import AgentRunner, run_agent_stream, execute_agent_sync

__all__ = [
    # Base
    "AgentWrapper",
    "AgentConfig",
    "CreditExhaustedError",
    
    # Catalog
    "MARKETPLACE_AGENTS",
    "AgentSpec",
    "get_agent_by_slug",
    "search_agents",
    "get_agents_by_category",
    "get_featured_agents",
    
    # Studio
    "AgentFactory",
    "StudioConfig",
    "build_custom_agent",
    "validate_agent_config",
    "create_agent_from_template",
    
    # Memory
    "PersistentMemory",
    "MemoryEntry",
    "MemoryType",
    "summarize_context",
    
    # Runner
    "AgentRunner",
    "run_agent_stream",
    "execute_agent_sync",
]