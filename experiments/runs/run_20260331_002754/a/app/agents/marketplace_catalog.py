"""app/agents/marketplace_catalog.py — Marketplace catalog with AgentSpec dataclasses.

exports: AgentSpec, MarketplaceCatalog, AGENT_SPECS, get_marketplace_agents
used_by: app/api/v1/agents.py → marketplace endpoint, app/agents/agent_builder.py → build from spec
rules:   Each AgentSpec must have unique slug; include pricing tier; tools must be valid
agent:   AgentIntegrator | 2024-12-05 | implemented marketplace catalog with 6 agent types
         message: "add more specialized agents for vertical industries"
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum


class PricingTier(str, Enum):
    """Pricing tiers for marketplace agents."""
    FREE = "free"
    BASIC = "basic"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class MemoryType(str, Enum):
    """Memory types for agents."""
    NONE = "none"
    SESSION = "session"
    PERSISTENT = "persistent"


@dataclass
class AgentSpec:
    """Specification for a marketplace agent.
    
    Rules:
        Slug must be unique across marketplace
        Tools list must reference valid tool names
        Pricing tier determines credit cost per run
    """
    name: str
    slug: str
    description: str
    system_prompt: str
    model_provider: str = "openai"
    model_name: str = "gpt-4"
    temperature: float = 0.7
    max_tokens: int = 4000
    tools: List[str] = field(default_factory=list)
    memory_type: MemoryType = MemoryType.SESSION
    pricing_tier: PricingTier = PricingTier.BASIC
    tags: List[str] = field(default_factory=list)
    estimated_cost_per_run: float = 0.0
    config: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate agent spec."""
        if not self.slug.islower() or " " in self.slug:
            raise ValueError(f"Slug must be lowercase and contain no spaces: {self.slug}")
        
        if self.temperature < 0.0 or self.temperature > 2.0:
            raise ValueError(f"Temperature must be between 0.0 and 2.0: {self.temperature}")
        
        if self.max_tokens < 1 or self.max_tokens > 100000:
            raise ValueError(f"max_tokens must be between 1 and 100000: {self.max_tokens}")


# Marketplace agent specifications
AGENT_SPECS: Dict[str, AgentSpec] = {
    "seo-optimizer": AgentSpec(
        name="SEO Optimizer",
        slug="seo-optimizer",
        description="Optimizes content for search engines with keyword analysis and meta tag suggestions",
        system_prompt="""You are an expert SEO specialist. Analyze content for SEO optimization, 
suggest keyword placements, meta descriptions, title tags, and content structure improvements.
Focus on readability, keyword density, and technical SEO factors.""",
        model_provider="openai",
        model_name="gpt-4",
        temperature=0.3,
        max_tokens=3000,
        tools=["web_search", "calculator"],
        memory_type=MemoryType.SESSION,
        pricing_tier=PricingTier.PROFESSIONAL,
        tags=["seo", "content", "marketing", "optimization"],
        estimated_cost_per_run=0.05,
    ),
    
    "customer-support-bot": AgentSpec(
        name="Customer Support Bot",
        slug="customer-support-bot",
        description="Handles customer inquiries with empathy and efficiency",
        system_prompt="""You are a helpful customer support representative. 
Provide accurate, empathetic, and efficient support to customers.
If you don't know an answer, offer to escalate the issue.
Always maintain a professional and friendly tone.""",
        model_provider="openai",
        model_name="gpt-4",
        temperature=0.5,
        max_tokens=2000,
        tools=["web_search", "calculator", "api_call"],
        memory_type=MemoryType.PERSISTENT,
        pricing_tier=PricingTier.BASIC,
        tags=["support", "customer-service", "helpdesk"],
        estimated_cost_per_run=0.02,
    ),
    
    "data-analyst": AgentSpec(
        name="Data Analyst",
        slug="data-analyst",
        description="Analyzes datasets, generates insights, and creates visualizations",
        system_prompt="""You are a data analyst with expertise in statistical analysis, 
data visualization, and business intelligence. Analyze data, identify patterns,
provide insights, and suggest visualizations. Always verify data accuracy.""",
        model_provider="openai",
        model_name="gpt-4",
        temperature=0.2,
        max_tokens=6000,
        tools=["calculator", "code_execution", "file_read", "file_write"],
        memory_type=MemoryType.SESSION,
        pricing_tier=PricingTier.PROFESSIONAL,
        tags=["data", "analytics", "statistics", "visualization"],
        estimated_cost_per_run=0.08,
    ),
    
    "code-reviewer": AgentSpec(
        name="Code Reviewer",
        slug="code-reviewer",
        description="Reviews code for bugs, security issues, and best practices",
        system_prompt="""You are an expert software engineer conducting code reviews.
Check for bugs, security vulnerabilities, performance issues, and adherence to best practices.
Provide specific, actionable feedback with code examples when helpful.
Be constructive and professional in your feedback.""",
        model_provider="openai",
        model_name="gpt-4",
        temperature=0.1,
        max_tokens=4000,
        tools=["code_execution", "file_read"],
        memory_type=MemoryType.SESSION,
        pricing_tier=PricingTier.BASIC,
        tags=["code", "review", "security", "best-practices"],
        estimated_cost_per_run=0.03,
    ),
    
    "email-drafter": AgentSpec(
        name="Email Drafter",
        slug="email-drafter",
        description="Drafts professional emails tailored to context and audience",
        system_prompt="""You are a professional email writer. Draft clear, concise, 
and appropriate emails based on the context and audience.
Adjust tone for formal, informal, sales, or support emails as needed.
Include appropriate subject lines and calls to action.""",
        model_provider="openai",
        model_name="gpt-4",
        temperature=0.6,
        max_tokens=1500,
        tools=["web_search"],
        memory_type=MemoryType.NONE,
        pricing_tier=PricingTier.FREE,
        tags=["email", "communication", "productivity"],
        estimated_cost_per_run=0.01,
    ),
    
    "research-assistant": AgentSpec(
        name="Research Assistant",
        slug="research-assistant",
        description="Conducts research, summarizes information, and cites sources",
        system_prompt="""You are a research assistant with expertise in academic 
and market research. Gather information, synthesize findings, provide summaries,
and cite sources accurately. Maintain objectivity and highlight limitations.""",
        model_provider="openai",
        model_name="gpt-4",
        temperature=0.4,
        max_tokens=5000,
        tools=["web_search", "calculator", "file_read", "file_write"],
        memory_type=MemoryType.PERSISTENT,
        pricing_tier=PricingTier.PROFESSIONAL,
        tags=["research", "academic", "analysis", "summarization"],
        estimated_cost_per_run=0.06,
    ),
}


class MarketplaceCatalog:
    """Marketplace catalog manager."""
    
    def __init__(self):
        self.agents = AGENT_SPECS
    
    def list_agents(
        self,
        category: Optional[str] = None,
        tier: Optional[PricingTier] = None,
        search: Optional[str] = None,
    ) -> List[AgentSpec]:
        """List marketplace agents with optional filtering.
        
        Args:
            category: Filter by tag/category
            tier: Filter by pricing tier
            search: Search in name, description, or tags
            
        Returns:
            List of agent specs matching criteria
        """
        filtered = list(self.agents.values())
        
        if category:
            filtered = [a for a in filtered if category in a.tags]
        
        if tier:
            filtered = [a for a in filtered if a.pricing_tier == tier]
        
        if search:
            search_lower = search.lower()
            filtered = [
                a for a in filtered
                if (search_lower in a.name.lower() or
                    search_lower in a.description.lower() or
                    any(search_lower in tag.lower() for tag in a.tags))
            ]
        
        return filtered
    
    def get_agent(self, slug: str) -> Optional[AgentSpec]:
        """Get agent spec by slug.
        
        Args:
            slug: Agent slug
            
        Returns:
            AgentSpec or None if not found
        """
        return self.agents.get(slug)
    
    def add_agent(self, spec: AgentSpec) -> None:
        """Add custom agent to marketplace.
        
        Args:
            spec: Agent specification
            
        Raises:
            ValueError: If slug already exists
        """
        if spec.slug in self.agents:
            raise ValueError(f"Agent with slug '{spec.slug}' already exists")
        
        self.agents[spec.slug] = spec
    
    def remove_agent(self, slug: str) -> bool:
        """Remove agent from marketplace.
        
        Args:
            slug: Agent slug
            
        Returns:
            True if removed, False if not found
        """
        if slug in self.agents:
            del self.agents[slug]
            return True
        return False


# Global catalog instance
catalog = MarketplaceCatalog()


def get_marketplace_agents(
    category: Optional[str] = None,
    tier: Optional[str] = None,
    search: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Get marketplace agents as dictionaries for API responses.
    
    Args:
        category: Filter by category/tag
        tier: Filter by pricing tier
        search: Search term
        
    Returns:
        List of agent dictionaries
    """
    tier_enum = PricingTier(tier) if tier else None
    agents = catalog.list_agents(category, tier_enum, search)
    
    return [
        {
            "name": agent.name,
            "slug": agent.slug,
            "description": agent.description,
            "system_prompt": agent.system_prompt[:500] + "..." if len(agent.system_prompt) > 500 else agent.system_prompt,
            "model_provider": agent.model_provider,
            "model_name": agent.model_name,
            "temperature": agent.temperature,
            "max_tokens": agent.max_tokens,
            "tools": agent.tools,
            "memory_type": agent.memory_type.value,
            "pricing_tier": agent.pricing_tier.value,
            "tags": agent.tags,
            "estimated_cost_per_run": agent.estimated_cost_per_run,
        }
        for agent in agents
    ]