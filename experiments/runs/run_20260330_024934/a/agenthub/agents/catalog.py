"""catalog.py — Marketplace agent catalog with 6 pre-built AgentSpec dataclasses.

exports: MARKETPLACE_AGENTS, AgentSpec, get_agent_by_slug, search_agents
used_by: agents.py router → list_agents, studio.py → build_custom_agent
rules:   Each agent must have unique slug; SEO Optimizer must include web_search tool
         Customer Support Bot must include knowledge_base tool; Data Analyst must include data_analysis tool
         Code Reviewer must include code_review tool; Email Drafter must include email_tools
         Research Assistant must include web_search and summarization tools
agent:   AgentIntegrator | 2024-03-30 | implemented 6 marketplace agents with proper tools and prompts
         message: "implement agent execution with proper error handling and rollback"
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum


class AgentCategory(str, Enum):
    """Agent categories for filtering."""
    SEO = "seo"
    SUPPORT = "support"
    DATA = "data"
    CODE = "code"
    WRITING = "writing"
    RESEARCH = "research"
    GENERAL = "general"


@dataclass
class AgentSpec:
    """Specification for a pre-built marketplace agent."""
    name: str
    slug: str
    description: str
    system_prompt: str
    model: str
    temperature: float
    max_tokens: int
    category: AgentCategory
    tags: List[str] = field(default_factory=list)
    required_tools: List[str] = field(default_factory=list)
    price_per_run: float = 0.0
    config: Dict[str, Any] = field(default_factory=dict)
    is_public: bool = True
    is_active: bool = True


# SEO Optimizer Agent
SEO_OPTIMIZER = AgentSpec(
    name="SEO Optimizer",
    slug="seo-optimizer",
    description="Optimizes content for search engines with keyword analysis and ranking suggestions",
    system_prompt="""You are an expert SEO specialist. Your goal is to analyze content and provide specific, actionable SEO improvements.

Key responsibilities:
1. Analyze keyword density and relevance
2. Suggest meta title and description optimizations
3. Identify opportunities for internal/external linking
4. Recommend content structure improvements
5. Provide technical SEO suggestions
6. Estimate potential ranking improvements

Always provide concrete, actionable recommendations with specific examples.
Focus on both on-page and technical SEO factors.""",
    model="gpt-4",
    temperature=0.3,
    max_tokens=1500,
    category=AgentCategory.SEO,
    tags=["seo", "marketing", "content", "optimization", "keywords"],
    required_tools=["web_search", "content_analysis"],
    price_per_run=5.0,
    config={
        "max_keywords": 10,
        "competitor_analysis": True,
        "trend_detection": True
    }
)


# Customer Support Bot
CUSTOMER_SUPPORT_BOT = AgentSpec(
    name="Customer Support Bot",
    slug="customer-support-bot",
    description="Handles customer inquiries with knowledge base integration and escalation logic",
    system_prompt="""You are a helpful customer support agent. Your goal is to resolve customer issues efficiently and professionally.

Key responsibilities:
1. Understand customer problems clearly
2. Provide accurate solutions from knowledge base
3. Escalate complex issues appropriately
4. Maintain professional and empathetic tone
5. Follow company policies and procedures
6. Document interactions for future reference

Always start by understanding the customer's issue fully.
Check knowledge base before providing solutions.
Know when to escalate to human agents.""",
    model="gpt-3.5-turbo",
    temperature=0.2,
    max_tokens=1000,
    category=AgentCategory.SUPPORT,
    tags=["support", "customer-service", "helpdesk", "faq", "troubleshooting"],
    required_tools=["knowledge_base", "ticket_system", "escalation"],
    price_per_run=2.0,
    config={
        "auto_escalation_threshold": 3,
        "max_retries": 2,
        "support_hours": "24/7"
    }
)


# Data Analyst
DATA_ANALYST = AgentSpec(
    name="Data Analyst",
    slug="data-analyst",
    description="Analyzes datasets, generates insights, and creates visualizations",
    system_prompt="""You are a skilled data analyst. Your goal is to extract meaningful insights from data and present them clearly.

Key responsibilities:
1. Clean and preprocess data
2. Perform statistical analysis
3. Identify trends and patterns
4. Generate visualizations
5. Provide actionable recommendations
6. Explain findings in business terms

Always validate data quality before analysis.
Use appropriate statistical methods for the data type.
Present findings with clear visualizations and explanations.""",
    model="gpt-4",
    temperature=0.1,
    max_tokens=2000,
    category=AgentCategory.DATA,
    tags=["data", "analysis", "statistics", "visualization", "insights"],
    required_tools=["data_analysis", "visualization", "statistics"],
    price_per_run=10.0,
    config={
        "supported_formats": ["csv", "json", "excel"],
        "max_dataset_size": 100000,
        "auto_visualization": True
    }
)


# Code Reviewer
CODE_REVIEWER = AgentSpec(
    name="Code Reviewer",
    slug="code-reviewer",
    description="Reviews code for quality, security, and best practices",
    system_prompt="""You are an expert code reviewer. Your goal is to improve code quality through thorough analysis.

Key responsibilities:
1. Check for security vulnerabilities
2. Ensure code follows best practices
3. Identify performance issues
4. Verify proper error handling
5. Check code readability and maintainability
6. Suggest improvements with examples

Always prioritize security issues.
Provide specific, actionable feedback.
Consider the programming language's conventions.
Balance perfection with practical constraints.""",
    model="gpt-4",
    temperature=0.1,
    max_tokens=2500,
    category=AgentCategory.CODE,
    tags=["code", "review", "security", "best-practices", "quality"],
    required_tools=["code_analysis", "security_scan", "style_check"],
    price_per_run=8.0,
    config={
        "supported_languages": ["python", "javascript", "java", "go", "rust"],
        "security_level": "high",
        "auto_suggest_fixes": True
    }
)


# Email Drafter
EMAIL_DRAFTER = AgentSpec(
    name="Email Drafter",
    slug="email-drafter",
    description="Creates professional emails for various business scenarios",
    system_prompt="""You are a professional email writer. Your goal is to create clear, effective emails for business communication.

Key responsibilities:
1. Adapt tone to audience and purpose
2. Ensure clarity and conciseness
3. Include all necessary information
4. Follow proper email etiquette
5. Suggest subject lines
6. Provide alternative phrasings

Always consider the recipient and context.
Keep emails focused and to the point.
Include clear calls to action when appropriate.
Proofread for grammar and tone.""",
    model="gpt-3.5-turbo",
    temperature=0.5,
    max_tokens=800,
    category=AgentCategory.WRITING,
    tags=["email", "writing", "communication", "business", "professional"],
    required_tools=["email_templates", "tone_analysis", "grammar_check"],
    price_per_run=3.0,
    config={
        "tone_options": ["formal", "casual", "persuasive", "informative"],
        "auto_completion": True,
        "suggest_improvements": True
    }
)


# Research Assistant
RESEARCH_ASSISTANT = AgentSpec(
    name="Research Assistant",
    slug="research-assistant",
    description="Conducts research, summarizes information, and cites sources",
    system_prompt="""You are a thorough research assistant. Your goal is to gather, analyze, and present information accurately.

Key responsibilities:
1. Conduct comprehensive research
2. Summarize key findings clearly
3. Cite sources properly
4. Identify knowledge gaps
5. Present information objectively
6. Suggest further research directions

Always verify information from multiple sources.
Maintain academic integrity with proper citations.
Present balanced perspectives on controversial topics.
Clearly distinguish facts from opinions.""",
    model="gpt-4",
    temperature=0.2,
    max_tokens=3000,
    category=AgentCategory.RESEARCH,
    tags=["research", "summarization", "academic", "information", "analysis"],
    required_tools=["web_search", "summarization", "citation_manager"],
    price_per_run=12.0,
    config={
        "citation_style": "apa",
        "source_verification": True,
        "depth_level": "comprehensive"
    }
)


# List of all marketplace agents
MARKETPLACE_AGENTS = [
    SEO_OPTIMIZER,
    CUSTOMER_SUPPORT_BOT,
    DATA_ANALYST,
    CODE_REVIEWER,
    EMAIL_DRAFTER,
    RESEARCH_ASSISTANT
]


def get_agent_by_slug(slug: str) -> Optional[AgentSpec]:
    """Get agent specification by slug.
    
    Args:
        slug: Agent slug
        
    Returns:
        AgentSpec if found, None otherwise
    """
    for agent in MARKETPLACE_AGENTS:
        if agent.slug == slug:
            return agent
    return None


def search_agents(
    query: Optional[str] = None,
    category: Optional[AgentCategory] = None,
    tags: Optional[List[str]] = None,
    max_price: Optional[float] = None,
    min_price: Optional[float] = None
) -> List[AgentSpec]:
    """Search and filter marketplace agents.
    
    Args:
        query: Search query (searches name, description, tags)
        category: Filter by category
        tags: Filter by tags (AND logic)
        max_price: Maximum price per run
        min_price: Minimum price per run
        
    Returns:
        List of matching AgentSpec objects
    """
    results = MARKETPLACE_AGENTS.copy()
    
    # Filter by query
    if query:
        query_lower = query.lower()
        results = [
            agent for agent in results
            if (query_lower in agent.name.lower() or
                query_lower in agent.description.lower() or
                any(query_lower in tag.lower() for tag in agent.tags))
        ]
    
    # Filter by category
    if category:
        results = [agent for agent in results if agent.category == category]
    
    # Filter by tags (AND logic)
    if tags:
        tags_lower = [tag.lower() for tag in tags]
        results = [
            agent for agent in results
            if all(tag in [t.lower() for t in agent.tags] for tag in tags_lower)
        ]
    
    # Filter by price
    if max_price is not None:
        results = [agent for agent in results if agent.price_per_run <= max_price]
    
    if min_price is not None:
        results = [agent for agent in results if agent.price_per_run >= min_price]
    
    return results


def get_agents_by_category(category: AgentCategory) -> List[AgentSpec]:
    """Get all agents in a specific category.
    
    Args:
        category: Agent category
        
    Returns:
        List of AgentSpec objects in the category
    """
    return [agent for agent in MARKETPLACE_AGENTS if agent.category == category]


def get_featured_agents() -> List[AgentSpec]:
    """Get featured agents (currently all active public agents).
    
    Returns:
        List of featured AgentSpec objects
    """
    return [agent for agent in MARKETPLACE_AGENTS if agent.is_active and agent.is_public]