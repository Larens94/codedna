"""app/agents/__init__.py — AI agent integration layer.

exports: AgentWrapper, AgentSpec, MarketplaceCatalog, AgentConfig, build_custom_agent,
         dict_tools_available_from_agno, MemoryManager, memory_manager, AgentRunner, agent_runner,
         run_agent_stream, CreditExhaustedError
used_by: app/services/agno_integration.py -> agent execution, app/api/v1/agents.py -> marketplace
rules:   Never call agno.Agent directly from API layer -- always go through AgentWrapper
agent:   AgentIntegrator | 2024-12-05 | created agent integration layer foundation
         claude-sonnet-4-6 | anthropic | 2026-03-31 | s_20260331_001 | fixed __init__: removed invalid import of run_agent_stream/agent_runner from agent_runner module; created module-level agent_runner instance; fixed broken return annotation
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
from app.agents.agent_runner import AgentRunner, AgentRunRecord

from app.exceptions import CreditExhaustedError, AgentError, AgentTimeoutError

# Module-level singleton runner (no DB at import time — wired later by ServiceContainer)
agent_runner = AgentRunner()


async def run_agent_stream(agent, prompt: str, user_id: str, db=None):
    """Convenience wrapper: stream an agent run.

    Args:
        agent: AgentWrapper instance
        prompt: User prompt
        user_id: User ID for tracking
        db: Optional database connection

    Returns:
        AsyncGenerator yielding streaming chunks
    """
    return await agent_runner.run_agent_stream(
        agent_wrapper=agent,
        prompt=prompt,
        user_id=user_id,
        db=db,
    )


__all__ = [
    "AgentWrapper", "AgentRunStats",
    "AgentSpec", "MarketplaceCatalog", "catalog", "get_marketplace_agents",
    "PricingTier", "MemoryType",
    "AgentConfig", "build_custom_agent", "build_agent_from_spec",
    "build_agent_from_dict", "ModelProvider",
    "dict_tools_available_from_agno",
    "MemoryManager", "memory_manager", "MemoryEntry", "VectorMemory",
    "AgentRunner", "agent_runner", "AgentRunRecord", "run_agent_stream",
    "CreditExhaustedError", "AgentError", "AgentTimeoutError",
]
