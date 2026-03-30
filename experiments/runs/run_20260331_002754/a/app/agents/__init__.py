"""app/agents/__init__.py — AI agent integration layer.

exports: AgentWrapper, AgentSpec, MarketplaceCatalog, AgentConfig, build_custom_agent, 
         dict_tools_available_from_agno, MemoryManager, memory_manager, AgentRunner, agent_runner,
         run_agent_stream, CreditExhaustedError
used_by: app/services/agno_integration.py → agent execution, app/api/v1/agents.py → marketplace
rules:   Never call agno.Agent directly from API layer — always go through AgentWrapper
agent:   AgentIntegrator | 2024-12-05 | created agent integration layer foundation
         message: "implement token counting and credit cap enforcement"
"""

from app.agents.agent_wrapper import AgentWrapper, AgentRunStats
from app.agents.marketplace_catalog import (
    AgentSpec, 
    MarketplaceCatalog, 
    catalog, 
    get_marketplace_agents,
    PricingTier,
    MemoryType,
)
from app.agents.agent_builder import (
    AgentConfig, 
    build_custom_agent, 
    build_agent_from_spec,
    build_agent_from_dict,
    ModelProvider,
)
from app.agents.tools import dict_tools_available_from_agno
from app.agents.memory_manager import MemoryManager, memory_manager, MemoryEntry, VectorMemory
from app.agents.agent_runner import (
    AgentRunner, 
    agent_runner, 
    AgentRunRecord,
    run_agent_stream,
)

from app.exceptions import CreditExhaustedError, AgentError, AgentTimeoutError

# Convenience function for streaming
async def run_agent_stream(agent, prompt, user_id, db) -> AgentRunner.run_agent_stream:
    """Run agent with streaming response.
    
    Args:
        agent: AgentWrapper instance
        prompt: User prompt
        user_id: User ID for tracking
        db: Database connection
        
    Returns:
        AsyncGenerator yielding streaming chunks
    """
    return agent_runner.run_agent_stream(
        agent_wrapper=agent,
        prompt=prompt,
        user_id=user_id,
        db=db,
    )

__all__ = [
    # Core wrapper
    "AgentWrapper",
    "AgentRunStats",
    
    # Marketplace
    "AgentSpec",
    "MarketplaceCatalog",
    "catalog",
    "get_marketplace_agents",
    "PricingTier",
    "MemoryType",
    
    # Agent builder
    "AgentConfig",
    "build_custom_agent",
    "build_agent_from_spec",
    "build_agent_from_dict",
    "ModelProvider",
    
    # Tools
    "dict_tools_available_from_agno",
    
    # Memory
    "MemoryManager",
    "memory_manager",
    "MemoryEntry",
    "VectorMemory",
    
    # Agent runner
    "AgentRunner",
    "agent_runner",
    "AgentRunRecord",
    "run_agent_stream",
    
    # Exceptions
    "CreditExhaustedError",
    "AgentError",
    "AgentTimeoutError",
]