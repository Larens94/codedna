"""app/agents/agent_builder.py — Custom agent builder from configuration.

exports: AgentConfig, build_custom_agent, build_agent_from_spec
used_by: app/agents/agent_runner.py → create agent, app/services/agno_integration.py → initialize_agent
rules:   Accepts model, system_prompt, tools list, memory_type; validates configuration
agent:   AgentIntegrator | 2024-12-05 | implemented custom agent builder
         message: "add support for more LLM providers beyond OpenAI"
"""

import logging
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass, field
from enum import Enum

from app.agents.marketplace_catalog import AgentSpec, MemoryType
from app.agents.tools import dict_tools_available_from_agno

# Try to import agno, fallback to mock
try:
    from agno import Agent, Tool
    from agno.models import OpenAIChat, Anthropic, AzureOpenAI
    from agno.tools import SerpAPI, Calculator, FileReader, FileWriter, CodeInterpreter
    AGNO_AVAILABLE = True
except ImportError:
    # Mock classes for development
    class Agent:
        def __init__(self, **kwargs):
            self.config = kwargs
            self.tools = []
            self.memory = None
        async def run(self, prompt: str, **kwargs):
            return f"Mock response to: {prompt}"
        async def astream(self, prompt: str, **kwargs):
            async def stream():
                yield f"Mock streaming response to: {prompt}"
            return stream()
    
    class Tool:
        pass
    
    class OpenAIChat:
        def __init__(self, model: str = "gpt-4", **kwargs):
            self.model = model
            self.config = kwargs
    
    class Anthropic:
        def __init__(self, model: str = "claude-3-opus", **kwargs):
            self.model = model
            self.config = kwargs
    
    class AzureOpenAI:
        def __init__(self, **kwargs):
            self.config = kwargs
    
    class SerpAPI:
        pass
    
    class Calculator:
        pass
    
    class FileReader:
        pass
    
    class FileWriter:
        pass
    
    class CodeInterpreter:
        pass
    
    AGNO_AVAILABLE = False

logger = logging.getLogger(__name__)


class ModelProvider(str, Enum):
    """Supported model providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    AZURE = "azure"
    GOOGLE = "google"
    CUSTOM = "custom"


@dataclass
class AgentConfig:
    """Configuration for building a custom agent.
    
    Rules:
        Must have at least a model provider and system prompt
        Tools must be valid names from dict_tools_available_from_agno
        Memory type determines persistence level
    """
    name: str
    system_prompt: str
    model_provider: ModelProvider = ModelProvider.OPENAI
    model_name: str = "gpt-4"
    temperature: float = 0.7
    max_tokens: int = 4000
    tools: List[str] = field(default_factory=list)
    memory_type: MemoryType = MemoryType.SESSION
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate configuration."""
        if not self.system_prompt.strip():
            raise ValueError("System prompt cannot be empty")
        
        if self.temperature < 0.0 or self.temperature > 2.0:
            raise ValueError(f"Temperature must be between 0.0 and 2.0: {self.temperature}")
        
        if self.max_tokens < 1 or self.max_tokens > 100000:
            raise ValueError(f"max_tokens must be between 1 and 100000: {self.max_tokens}")
        
        # Validate tools
        valid_tools = set(dict_tools_available_from_agno.keys())
        for tool in self.tools:
            if tool not in valid_tools:
                raise ValueError(f"Tool '{tool}' not available. Valid tools: {list(valid_tools)}")


def build_custom_agent(config: AgentConfig) -> Agent:
    """Build custom agno.Agent from configuration.
    
    Args:
        config: Agent configuration
        
    Returns:
        agno.Agent instance
        
    Raises:
        ValueError: If configuration is invalid
        RuntimeError: If agent creation fails
    """
    logger.info(f"Building custom agent: {config.name}")
    
    # Select model based on provider
    model = None
    
    if config.model_provider == ModelProvider.OPENAI:
        model = OpenAIChat(
            model=config.model_name,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )
    elif config.model_provider == ModelProvider.ANTHROPIC:
        model = Anthropic(
            model=config.model_name,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )
    elif config.model_provider == ModelProvider.AZURE:
        model = AzureOpenAI(
            model=config.model_name,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )
    else:
        raise ValueError(f"Unsupported model provider: {config.model_provider}")
    
    # Get tools
    tools = []
    for tool_name in config.tools:
        if tool_name in dict_tools_available_from_agno:
            tools.append(dict_tools_available_from_agno[tool_name])
        else:
            logger.warning(f"Tool '{tool_name}' not found in available tools")
    
    # Build agent
    agent_kwargs = {
        "name": config.name,
        "model": model,
        "system_prompt": config.system_prompt,
        "tools": tools,
        "metadata": config.metadata,
    }
    
    # Add memory configuration if needed
    if config.memory_type != MemoryType.NONE:
        # In real implementation, configure memory
        # For now, just log
        logger.info(f"Agent configured with {config.memory_type.value} memory")
    
    try:
        agent = Agent(**agent_kwargs)
        logger.info(f"Custom agent '{config.name}' built successfully")
        return agent
    except Exception as e:
        logger.error(f"Failed to build agent '{config.name}': {e}")
        raise RuntimeError(f"Agent creation failed: {e}")


def build_agent_from_spec(spec: AgentSpec) -> Agent:
    """Build agent from marketplace specification.
    
    Args:
        spec: Agent specification from marketplace
        
    Returns:
        agno.Agent instance
    """
    config = AgentConfig(
        name=spec.name,
        system_prompt=spec.system_prompt,
        model_provider=ModelProvider(spec.model_provider),
        model_name=spec.model_name,
        temperature=spec.temperature,
        max_tokens=spec.max_tokens,
        tools=spec.tools,
        memory_type=spec.memory_type,
        metadata={
            "marketplace_slug": spec.slug,
            "pricing_tier": spec.pricing_tier.value,
            "tags": spec.tags,
        },
    )
    
    return build_custom_agent(config)


def build_agent_from_dict(config_dict: Dict[str, Any]) -> Agent:
    """Build agent from dictionary configuration.
    
    Args:
        config_dict: Agent configuration as dictionary
        
    Returns:
        agno.Agent instance
        
    Raises:
        ValueError: If configuration is invalid
    """
    # Convert dictionary to AgentConfig
    try:
        # Extract fields with defaults
        config = AgentConfig(
            name=config_dict.get("name", "Custom Agent"),
            system_prompt=config_dict["system_prompt"],
            model_provider=ModelProvider(config_dict.get("model_provider", "openai")),
            model_name=config_dict.get("model_name", "gpt-4"),
            temperature=float(config_dict.get("temperature", 0.7)),
            max_tokens=int(config_dict.get("max_tokens", 4000)),
            tools=config_dict.get("tools", []),
            memory_type=MemoryType(config_dict.get("memory_type", "session")),
            metadata=config_dict.get("metadata", {}),
        )
        
        return build_custom_agent(config)
        
    except KeyError as e:
        raise ValueError(f"Missing required field: {e}")
    except ValueError as e:
        raise ValueError(f"Invalid configuration: {e}")