"""Agent studio for building custom agents."""

import json
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Union
from enum import Enum

try:
    import agno
    from agno import Agent, Tool
    AGNO_AVAILABLE = True
except ImportError:
    AGNO_AVAILABLE = False
    agno = None
    Agent = None
    Tool = None

from app.agents.exceptions import ConfigurationError, AgentError
from app.agents.catalog import MemoryType, ToolSpec


logger = logging.getLogger(__name__)


class ModelProvider(str, Enum):
    """LLM model providers."""
    
    OPENAI = 'openai'
    ANTHROPIC = 'anthropic'
    GOOGLE = 'google'
    COHERE = 'cohere'
    HUGGINGFACE = 'huggingface'
    LOCAL = 'local'


@dataclass
class ModelConfig:
    """Configuration for LLM model."""
    
    provider: ModelProvider
    name: str  # e.g., 'gpt-4', 'claude-3-opus'
    api_key: Optional[str] = None
    base_url: Optional[str] = None  # For custom endpoints
    temperature: float = 0.7
    max_tokens: int = 2000
    timeout: int = 30


@dataclass
class ToolConfig:
    """Configuration for an agent tool."""
    
    name: str
    description: str
    config: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True


@dataclass
class AgentConfig:
    """Configuration for a custom agent.
    
    This dataclass captures all user-configurable aspects of an agent
    for the agent studio.
    """
    
    # Basic information
    name: str
    description: str = ''
    
    # Model configuration
    model_config: ModelConfig
    
    # System prompt
    system_prompt: str = 'You are a helpful AI assistant.'
    
    # Tools
    tools: List[ToolConfig] = field(default_factory=list)
    
    # Memory
    memory_type: MemoryType = MemoryType.NONE
    memory_config: Dict[str, Any] = field(default_factory=dict)
    
    # Execution limits
    max_tokens_per_run: Optional[int] = None
    credit_limit: Optional[float] = None
    
    # Advanced settings
    streaming_enabled: bool = True
    enable_history: bool = True
    enable_feedback: bool = False
    
    # Metadata
    tags: List[str] = field(default_factory=list)
    version: str = '1.0.0'
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary for storage.
        
        Returns:
            Dictionary representation
        """
        return {
            'name': self.name,
            'description': self.description,
            'model_config': {
                'provider': self.model_config.provider.value,
                'name': self.model_config.name,
                'temperature': self.model_config.temperature,
                'max_tokens': self.model_config.max_tokens,
                'timeout': self.model_config.timeout,
                # Note: api_key and base_url are not included for security
            },
            'system_prompt': self.system_prompt,
            'tools': [
                {
                    'name': tool.name,
                    'description': tool.description,
                    'config': tool.config,
                    'enabled': tool.enabled,
                }
                for tool in self.tools
            ],
            'memory_type': self.memory_type.value,
            'memory_config': self.memory_config,
            'max_tokens_per_run': self.max_tokens_per_run,
            'credit_limit': self.credit_limit,
            'streaming_enabled': self.streaming_enabled,
            'enable_history': self.enable_history,
            'enable_feedback': self.enable_feedback,
            'tags': self.tags,
            'version': self.version,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentConfig':
        """Create AgentConfig from dictionary.
        
        Args:
            data: Dictionary representation
            
        Returns:
            AgentConfig instance
            
        Raises:
            ConfigurationError: If data is invalid
        """
        try:
            # Extract model config
            model_config_data = data.get('model_config', {})
            model_config = ModelConfig(
                provider=ModelProvider(model_config_data.get('provider', 'openai')),
                name=model_config_data.get('name', 'gpt-3.5-turbo'),
                temperature=model_config_data.get('temperature', 0.7),
                max_tokens=model_config_data.get('max_tokens', 2000),
                timeout=model_config_data.get('timeout', 30),
            )
            
            # Extract tools
            tools = []
            for tool_data in data.get('tools', []):
                tools.append(ToolConfig(
                    name=tool_data['name'],
                    description=tool_data.get('description', ''),
                    config=tool_data.get('config', {}),
                    enabled=tool_data.get('enabled', True),
                ))
            
            # Create agent config
            return cls(
                name=data['name'],
                description=data.get('description', ''),
                model_config=model_config,
                system_prompt=data.get('system_prompt', 'You are a helpful AI assistant.'),
                tools=tools,
                memory_type=MemoryType(data.get('memory_type', 'none')),
                memory_config=data.get('memory_config', {}),
                max_tokens_per_run=data.get('max_tokens_per_run'),
                credit_limit=data.get('credit_limit'),
                streaming_enabled=data.get('streaming_enabled', True),
                enable_history=data.get('enable_history', True),
                enable_feedback=data.get('enable_feedback', False),
                tags=data.get('tags', []),
                version=data.get('version', '1.0.0'),
            )
        except (KeyError, ValueError) as e:
            raise ConfigurationError(f'Invalid agent configuration: {str(e)}')


def validate_agent_config(config: AgentConfig) -> List[str]:
    """Validate agent configuration.
    
    Args:
        config: Agent configuration to validate
        
    Returns:
        List of validation errors (empty if valid)
    """
    errors = []
    
    # Validate name
    if not config.name.strip():
        errors.append('Agent name cannot be empty')
    elif len(config.name) > 200:
        errors.append('Agent name cannot exceed 200 characters')
    
    # Validate model
    if not config.model_config.name.strip():
        errors.append('Model name cannot be empty')
    
    # Validate temperature
    if not 0 <= config.model_config.temperature <= 2:
        errors.append('Temperature must be between 0 and 2')
    
    # Validate max tokens
    if config.model_config.max_tokens < 1:
        errors.append('Max tokens must be at least 1')
    elif config.model_config.max_tokens > 100000:
        errors.append('Max tokens cannot exceed 100,000')
    
    # Validate system prompt
    if not config.system_prompt.strip():
        errors.append('System prompt cannot be empty')
    
    # Validate tool names
    tool_names = set()
    for tool in config.tools:
        if not tool.name.strip():
            errors.append(f'Tool {len(tool_names)} has empty name')
        elif tool.name in tool_names:
            errors.append(f'Duplicate tool name: {tool.name}')
        else:
            tool_names.add(tool.name)
    
    # Validate memory config
    if config.memory_type == MemoryType.SEMANTIC:
        if not config.memory_config.get('embedding_model'):
            errors.append('Embedding model required for semantic memory')
    
    # Validate token limit
    if config.max_tokens_per_run is not None:
        if config.max_tokens_per_run < 1:
            errors.append('Max tokens per run must be at least 1')
        elif config.max_tokens_per_run > 100000:
            errors.append('Max tokens per run cannot exceed 100,000')
    
    return errors


def build_custom_agent(config: AgentConfig, user_id: int) -> Any:
    """Build a custom agno.Agent from configuration.
    
    Args:
        config: Agent configuration
        user_id: ID of user creating the agent
        
    Returns:
        agno.Agent instance
        
    Raises:
        ConfigurationError: If configuration is invalid
        AgentError: If agent creation fails
    """
    if not AGNO_AVAILABLE:
        raise ImportError('Agno framework is not installed')
    
    # Validate configuration
    errors = validate_agent_config(config)
    if errors:
        raise ConfigurationError(f'Invalid agent configuration: {", ".join(errors)}')
    
    try:
        logger.info(f'Building custom agent "{config.name}" for user {user_id}')
        
        # Initialize agent with model configuration
        agent_kwargs = {
            'model': config.model_config.name,
            'system_prompt': config.system_prompt,
            'temperature': config.model_config.temperature,
            'max_tokens': config.model_config.max_tokens,
        }
        
        # Add API key if provided
        if config.model_config.api_key:
            agent_kwargs['api_key'] = config.model_config.api_key
        
        # Add base URL if provided
        if config.model_config.base_url:
            agent_kwargs['base_url'] = config.model_config.base_url
        
        # Create agent
        agent = Agent(**agent_kwargs)
        
        # Add tools (placeholder - actual tool registration depends on agno's API)
        # Assuming agno.Agent has an add_tool method
        for tool_config in config.tools:
            if tool_config.enabled:
                # Create tool instance
                # This is a placeholder - actual implementation depends on agno
                tool = Tool(
                    name=tool_config.name,
                    description=tool_config.description,
                    # Additional tool configuration would go here
                )
                agent.add_tool(tool)
        
        # Configure memory (placeholder)
        if config.memory_type != MemoryType.NONE:
            # Initialize memory based on type
            memory_config = config.memory_config.copy()
            memory_config['user_id'] = user_id
            
            # Assuming agno.Agent has memory configuration
            # agent.enable_memory(type=config.memory_type, config=memory_config)
            logger.info(f'Memory type {config.memory_type} configured for agent')
        
        # Set metadata
        agent.metadata = {
            'name': config.name,
            'description': config.description,
            'user_id': user_id,
            'version': config.version,
            'tags': config.tags,
        }
        
        logger.info(f'Successfully built agent "{config.name}"')
        return agent
        
    except Exception as e:
        logger.error(f'Failed to build agent: {str(e)}')
        raise AgentError(f'Failed to build agent: {str(e)}')


def create_agent_from_spec(spec: 'AgentSpec', user_id: int) -> Any:
    """Create an agent from a marketplace specification.
    
    Args:
        spec: Agent specification from catalog
        user_id: ID of user creating the agent
        
    Returns:
        agno.Agent instance
    """
    # Convert spec to AgentConfig
    model_config = ModelConfig(
        provider=ModelProvider.OPENAI,  # Assume OpenAI for marketplace agents
        name=spec.model,
        temperature=spec.temperature,
        max_tokens=spec.max_tokens,
    )
    
    agent_config = AgentConfig(
        name=spec.name,
        description=spec.description,
        model_config=model_config,
        system_prompt=spec.system_prompt,
        tools=[
            ToolConfig(
                name=tool.name,
                description=tool.description,
                config=tool.config,
                enabled=True,
            )
            for tool in spec.tools
        ],
        memory_type=spec.memory_type,
        tags=spec.tags,
        version=spec.version,
    )
    
    return build_custom_agent(agent_config, user_id)


def update_agent_config(existing_config: AgentConfig, updates: Dict[str, Any]) -> AgentConfig:
    """Update an existing agent configuration.
    
    Args:
        existing_config: Existing agent configuration
        updates: Dictionary of updates to apply
        
    Returns:
        Updated AgentConfig
        
    Raises:
        ConfigurationError: If updates are invalid
    """
    # Convert to dict, apply updates, then convert back
    config_dict = existing_config.to_dict()
    
    # Apply updates recursively
    def update_dict(target, source):
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                update_dict(target[key], value)
            else:
                target[key] = value
    
    update_dict(config_dict, updates)
    
    # Recreate from dict
    return AgentConfig.from_dict(config_dict)