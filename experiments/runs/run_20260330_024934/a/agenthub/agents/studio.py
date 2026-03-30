"""studio.py — AgentFactory that builds custom agents from configuration.

exports: build_custom_agent, AgentFactory, validate_agent_config
used_by: agents.py router → create_agent, runner.py → run_agent_stream
rules:   Must accept: model, system_prompt, tools list, memory_type
         Must validate tool compatibility with model
         Must set appropriate temperature defaults based on agent type
         Must enforce maximum context length based on model
agent:   AgentIntegrator | 2024-03-30 | implemented AgentFactory with config validation
         message: "implement memory summarization when context exceeds 80% of model limit"
"""

import json
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass, field
from enum import Enum

from agno import Agent
from agno.models import OpenAIChat
from agno.tools import Tool

from .base import AgentWrapper, AgentConfig
from .catalog import AgentSpec, get_agent_by_slug
from .memory import PersistentMemory


class MemoryType(str, Enum):
    """Types of memory supported by agents."""
    SQLITE = "sqlite"
    VECTOR = "vector"
    NONE = "none"


class ToolType(str, Enum):
    """Types of tools supported by agents."""
    WEB_SEARCH = "web_search"
    KNOWLEDGE_BASE = "knowledge_base"
    DATA_ANALYSIS = "data_analysis"
    CODE_ANALYSIS = "code_analysis"
    EMAIL_TOOLS = "email_tools"
    SUMMARIZATION = "summarization"
    VISUALIZATION = "visualization"
    SECURITY_SCAN = "security_scan"
    CONTENT_ANALYSIS = "content_analysis"
    TICKET_SYSTEM = "ticket_system"
    ESCALATION = "escalation"
    STATISTICS = "statistics"
    STYLE_CHECK = "style_check"
    GRAMMAR_CHECK = "grammar_check"
    TONE_ANALYSIS = "tone_analysis"
    CITATION_MANAGER = "citation_manager"


@dataclass
class StudioConfig:
    """Configuration for building a custom agent in the studio."""
    name: str
    model: str = "gpt-4"
    system_prompt: str = "You are a helpful AI assistant."
    temperature: float = 0.7
    max_tokens: int = 2000
    tools: List[ToolType] = field(default_factory=list)
    memory_type: MemoryType = MemoryType.SQLITE
    max_context_length: int = 8000
    price_per_run: float = 0.0
    category: str = "general"
    tags: List[str] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)
    
    def to_agent_config(self, agent_id: Optional[int] = None, user_id: Optional[int] = None) -> AgentConfig:
        """Convert StudioConfig to AgentConfig."""
        return AgentConfig(
            model=self.model,
            system_prompt=self.system_prompt,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            tools=self._create_tools(),
            memory_type=self.memory_type,
            max_context_length=self.max_context_length,
            price_per_run=self.price_per_run,
            agent_id=agent_id,
            user_id=user_id
        )
    
    def _create_tools(self) -> List[Tool]:
        """Create agno Tool objects from tool types."""
        # This is a placeholder - in practice, we would import actual tool implementations
        tools = []
        
        # Map tool types to actual tool instances
        tool_map = {
            ToolType.WEB_SEARCH: self._create_web_search_tool,
            ToolType.KNOWLEDGE_BASE: self._create_knowledge_base_tool,
            ToolType.DATA_ANALYSIS: self._create_data_analysis_tool,
            ToolType.CODE_ANALYSIS: self._create_code_analysis_tool,
            ToolType.EMAIL_TOOLS: self._create_email_tools,
            ToolType.SUMMARIZATION: self._create_summarization_tool,
            ToolType.VISUALIZATION: self._create_visualization_tool,
            ToolType.SECURITY_SCAN: self._create_security_scan_tool,
            ToolType.CONTENT_ANALYSIS: self._create_content_analysis_tool,
            ToolType.TICKET_SYSTEM: self._create_ticket_system_tool,
            ToolType.ESCALATION: self._create_escalation_tool,
            ToolType.STATISTICS: self._create_statistics_tool,
            ToolType.STYLE_CHECK: self._create_style_check_tool,
            ToolType.GRAMMAR_CHECK: self._create_grammar_check_tool,
            ToolType.TONE_ANALYSIS: self._create_tone_analysis_tool,
            ToolType.CITATION_MANAGER: self._create_citation_manager_tool,
        }
        
        for tool_type in self.tools:
            if tool_type in tool_map:
                tool = tool_map[tool_type]()
                if tool:
                    tools.append(tool)
        
        return tools
    
    # Placeholder tool creation methods
    def _create_web_search_tool(self) -> Optional[Tool]:
        """Create web search tool."""
        # In practice: return WebSearchTool(config=self.config.get("web_search", {}))
        return None
    
    def _create_knowledge_base_tool(self) -> Optional[Tool]:
        """Create knowledge base tool."""
        return None
    
    def _create_data_analysis_tool(self) -> Optional[Tool]:
        """Create data analysis tool."""
        return None
    
    def _create_code_analysis_tool(self) -> Optional[Tool]:
        """Create code analysis tool."""
        return None
    
    def _create_email_tools(self) -> Optional[Tool]:
        """Create email tools."""
        return None
    
    def _create_summarization_tool(self) -> Optional[Tool]:
        """Create summarization tool."""
        return None
    
    def _create_visualization_tool(self) -> Optional[Tool]:
        """Create visualization tool."""
        return None
    
    def _create_security_scan_tool(self) -> Optional[Tool]:
        """Create security scan tool."""
        return None
    
    def _create_content_analysis_tool(self) -> Optional[Tool]:
        """Create content analysis tool."""
        return None
    
    def _create_ticket_system_tool(self) -> Optional[Tool]:
        """Create ticket system tool."""
        return None
    
    def _create_escalation_tool(self) -> Optional[Tool]:
        """Create escalation tool."""
        return None
    
    def _create_statistics_tool(self) -> Optional[Tool]:
        """Create statistics tool."""
        return None
    
    def _create_style_check_tool(self) -> Optional[Tool]:
        """Create style check tool."""
        return None
    
    def _create_grammar_check_tool(self) -> Optional[Tool]:
        """Create grammar check tool."""
        return None
    
    def _create_tone_analysis_tool(self) -> Optional[Tool]:
        """Create tone analysis tool."""
        return None
    
    def _create_citation_manager_tool(self) -> Optional[Tool]:
        """Create citation manager tool."""
        return None


class AgentFactory:
    """Factory for creating agents from various configurations."""
    
    @staticmethod
    def from_spec(spec: AgentSpec, agent_id: Optional[int] = None, user_id: Optional[int] = None) -> AgentWrapper:
        """Create an agent from an AgentSpec.
        
        Args:
            spec: Agent specification
            agent_id: Optional agent ID for tracking
            user_id: Optional user ID for credit checking
            
        Returns:
            Configured AgentWrapper
        """
        # Create studio config from spec
        studio_config = StudioConfig(
            name=spec.name,
            model=spec.model,
            system_prompt=spec.system_prompt,
            temperature=spec.temperature,
            max_tokens=spec.max_tokens,
            tools=[ToolType(tool) for tool in spec.required_tools],
            memory_type=MemoryType.SQLITE,
            max_context_length=8000,  # Default for GPT-4
            price_per_run=spec.price_per_run,
            category=spec.category.value,
            tags=spec.tags,
            config=spec.config
        )
        
        return build_custom_agent(studio_config, agent_id, user_id)
    
    @staticmethod
    def from_slug(slug: str, agent_id: Optional[int] = None, user_id: Optional[int] = None) -> Optional[AgentWrapper]:
        """Create an agent from a marketplace slug.
        
        Args:
            slug: Agent slug
            agent_id: Optional agent ID for tracking
            user_id: Optional user ID for credit checking
            
        Returns:
            Configured AgentWrapper or None if not found
        """
        spec = get_agent_by_slug(slug)
        if not spec:
            return None
        
        return AgentFactory.from_spec(spec, agent_id, user_id)
    
    @staticmethod
    def from_api_schema(agent_data: Dict[str, Any], agent_id: Optional[int] = None, user_id: Optional[int] = None) -> AgentWrapper:
        """Create an agent from API schema data.
        
        Args:
            agent_data: Agent data from API schema
            agent_id: Optional agent ID for tracking
            user_id: Optional user ID for credit checking
            
        Returns:
            Configured AgentWrapper
        """
        # Convert API schema to studio config
        studio_config = StudioConfig(
            name=agent_data.get("name", "Custom Agent"),
            model=agent_data.get("model", "gpt-4"),
            system_prompt=agent_data.get("system_prompt", "You are a helpful AI assistant."),
            temperature=agent_data.get("temperature", 0.7),
            max_tokens=agent_data.get("max_tokens", 2000),
            tools=[ToolType(tool) for tool in agent_data.get("tools", [])],
            memory_type=MemoryType(agent_data.get("memory_type", "sqlite")),
            max_context_length=agent_data.get("max_context_length", 8000),
            price_per_run=agent_data.get("price_per_run", 0.0),
            category=agent_data.get("category", "general"),
            tags=agent_data.get("tags", []),
            config=agent_data.get("config", {})
        )
        
        return build_custom_agent(studio_config, agent_id, user_id)


def validate_agent_config(config: StudioConfig) -> List[str]:
    """Validate agent configuration.
    
    Args:
        config: Agent configuration
        
    Returns:
        List of validation errors (empty if valid)
    """
    errors = []
    
    # Validate model
    valid_models = ["gpt-4", "gpt-3.5-turbo", "claude-3-5-sonnet", "claude-3-opus", "claude-3-haiku"]
    if config.model not in valid_models:
        errors.append(f"Invalid model: {config.model}. Must be one of: {', '.join(valid_models)}")
    
    # Validate temperature
    if config.temperature < 0.0 or config.temperature > 2.0:
        errors.append(f"Temperature must be between 0.0 and 2.0, got {config.temperature}")
    
    # Validate max_tokens
    if config.max_tokens < 1 or config.max_tokens > 100000:
        errors.append(f"Max tokens must be between 1 and 100000, got {config.max_tokens}")
    
    # Validate max_context_length
    model_context_limits = {
        "gpt-4": 8192,
        "gpt-3.5-turbo": 4096,
        "claude-3-5-sonnet": 200000,
        "claude-3-opus": 200000,
        "claude-3-haiku": 200000,
    }
    
    max_allowed = model_context_limits.get(config.model, 8192)
    if config.max_context_length > max_allowed:
        errors.append(f"Max context length {config.max_context_length} exceeds model limit {max_allowed}")
    
    # Validate system prompt length
    if len(config.system_prompt) > 10000:
        errors.append(f"System prompt too long: {len(config.system_prompt)} characters (max 10000)")
    
    # Validate price
    if config.price_per_run < 0:
        errors.append(f"Price per run cannot be negative: {config.price_per_run}")
    
    # Validate memory type
    try:
        MemoryType(config.memory_type)
    except ValueError:
        errors.append(f"Invalid memory type: {config.memory_type}")
    
    # Validate tool types
    for tool in config.tools:
        try:
            ToolType(tool)
        except ValueError:
            errors.append(f"Invalid tool type: {tool}")
    
    return errors


def build_custom_agent(
    config: StudioConfig,
    agent_id: Optional[int] = None,
    user_id: Optional[int] = None,
    db_session = None
) -> AgentWrapper:
    """Build a custom agent from configuration.
    
    Args:
        config: Agent configuration
        agent_id: Optional agent ID for tracking
        user_id: Optional user ID for credit checking
        db_session: Optional database session
        
    Returns:
        Configured AgentWrapper
        
    Raises:
        ValueError: If configuration is invalid
    """
    # Validate configuration
    errors = validate_agent_config(config)
    if errors:
        raise ValueError(f"Invalid agent configuration: {', '.join(errors)}")
    
    # Convert to AgentConfig
    agent_config = config.to_agent_config(agent_id, user_id)
    
    # Create agent wrapper
    wrapper = AgentWrapper(agent_config, db_session)
    
    # Initialize memory if needed
    if config.memory_type != MemoryType.NONE:
        # In practice, we would attach memory to the agent
        # For now, we just create it for potential use
        memory = PersistentMemory(db_path="agents_memory.db")
        # TODO: Integrate memory with agent
    
    return wrapper


def create_agent_from_template(template_name: str, **kwargs) -> AgentWrapper:
    """Create an agent from a predefined template.
    
    Args:
        template_name: Name of the template
        **kwargs: Template-specific parameters
        
    Returns:
        Configured AgentWrapper
        
    Raises:
        ValueError: If template not found
    """
    templates = {
        "basic_chat": StudioConfig(
            name="Basic Chat Assistant",
            system_prompt="You are a helpful and friendly AI assistant.",
            temperature=0.7,
            max_tokens=1000,
            category="general"
        ),
        "technical_support": StudioConfig(
            name="Technical Support",
            system_prompt="You are a technical support specialist. Help users troubleshoot technical issues.",
            temperature=0.3,
            max_tokens=1500,
            tools=[ToolType.KNOWLEDGE_BASE, ToolType.TICKET_SYSTEM],
            category="support"
        ),
        "content_writer": StudioConfig(
            name="Content Writer",
            system_prompt="You are a professional content writer. Create engaging, well-structured content.",
            temperature=0.8,
            max_tokens=2000,
            tools=[ToolType.CONTENT_ANALYSIS, ToolType.GRAMMAR_CHECK],
            category="writing"
        ),
        "data_scientist": StudioConfig(
            name="Data Scientist",
            system_prompt="You are a data scientist. Analyze data and provide insights with statistical rigor.",
            temperature=0.2,
            max_tokens=2500,
            tools=[ToolType.DATA_ANALYSIS, ToolType.STATISTICS, ToolType.VISUALIZATION],
            category="data"
        ),
    }
    
    if template_name not in templates:
        raise ValueError(f"Template not found: {template_name}")
    
    config = templates[template_name]
    
    # Apply any customizations
    for key, value in kwargs.items():
        if hasattr(config, key):
            setattr(config, key, value)
    
    return build_custom_agent(config)