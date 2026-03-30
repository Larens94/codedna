"""Marketplace catalog with pre-built agent specifications."""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any


class AgentCategory(str, Enum):
    """Agent categories for marketplace."""
    
    PRODUCTIVITY = 'productivity'
    CREATIVE = 'creative'
    ANALYTICAL = 'analytical'
    CUSTOMER_SERVICE = 'customer_service'
    DEVELOPMENT = 'development'
    MARKETING = 'marketing'
    FINANCE = 'finance'
    EDUCATION = 'education'
    HEALTHCARE = 'healthcare'
    OTHER = 'other'


class MemoryType(str, Enum):
    """Types of memory available for agents."""
    
    NONE = 'none'
    KEY_VALUE = 'key_value'
    SEMANTIC = 'semantic'


@dataclass
class ToolSpec:
    """Specification for an agent tool."""
    
    name: str
    description: str
    config: Dict[str, Any] = field(default_factory=dict)
    required: bool = False


@dataclass
class AgentSpec:
    """Specification for a pre-built agent in the marketplace.
    
    This dataclass defines the configuration for agents that appear
    in the AgentHub marketplace. Each spec can be instantiated into
    a running agent.
    """
    
    # Basic information
    name: str
    slug: str
    description: str
    short_description: str
    
    # Agent configuration
    system_prompt: str
    model: str = 'gpt-4'
    temperature: float = 0.7
    max_tokens: int = 2000
    memory_type: MemoryType = MemoryType.NONE
    
    # Tools
    tools: List[ToolSpec] = field(default_factory=list)
    
    # Marketplace metadata
    category: AgentCategory = AgentCategory.PRODUCTIVITY
    price_per_run: float = 0.10  # USD
    is_featured: bool = False
    icon_emoji: str = '🤖'
    
    # Version and ownership
    version: str = '1.0.0'
    author: str = 'AgentHub Team'
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert spec to dictionary for API responses.
        
        Returns:
            Dictionary representation
        """
        return {
            'name': self.name,
            'slug': self.slug,
            'description': self.description,
            'short_description': self.short_description,
            'system_prompt': self.system_prompt,
            'model': self.model,
            'temperature': self.temperature,
            'max_tokens': self.max_tokens,
            'memory_type': self.memory_type.value,
            'tools': [
                {
                    'name': tool.name,
                    'description': tool.description,
                    'config': tool.config,
                    'required': tool.required,
                }
                for tool in self.tools
            ],
            'category': self.category.value,
            'price_per_run': self.price_per_run,
            'is_featured': self.is_featured,
            'icon_emoji': self.icon_emoji,
            'version': self.version,
            'author': self.author,
            'tags': self.tags,
        }


# Pre-built agent specifications
MARKETPLACE_CATALOG: List[AgentSpec] = []


def _initialize_catalog() -> None:
    """Initialize the marketplace catalog with pre-built agents."""
    global MARKETPLACE_CATALOG
    
    # 1. SEO Optimizer
    seo_optimizer = AgentSpec(
        name='SEO Optimizer',
        slug='seo-optimizer',
        description='Analyzes content and provides SEO optimization suggestions to improve search engine rankings.',
        short_description='Optimize your content for better search engine rankings',
        system_prompt="""You are an SEO expert. Analyze the given content and provide specific, actionable suggestions to improve its search engine optimization.

Consider:
1. Keyword optimization (density, placement, relevance)
2. Content structure (headings, paragraphs, readability)
3. Meta information (title tags, meta descriptions)
4. Technical SEO aspects (if mentioned)
5. Content quality and depth
6. Internal and external linking opportunities

Provide recommendations in order of priority with clear explanations of why each change matters. Include specific examples of how to implement the suggestions.""",
        model='gpt-4',
        temperature=0.3,
        max_tokens=1500,
        memory_type=MemoryType.NONE,
        tools=[],
        category=AgentCategory.MARKETING,
        price_per_run=0.15,
        is_featured=True,
        icon_emoji='🔍',
        tags=['seo', 'marketing', 'content', 'optimization'],
    )
    
    # 2. Customer Support Bot
    customer_support = AgentSpec(
        name='Customer Support Bot',
        slug='customer-support-bot',
        description='Handles customer inquiries, provides solutions, and escalates complex issues to human agents.',
        short_description='Automated customer support for common queries',
        system_prompt="""You are a friendly and helpful customer support agent. Your goal is to assist customers with their questions and issues in a professional, empathetic, and efficient manner.

Guidelines:
1. Always be polite and patient
2. Listen carefully to the customer's concern
3. Provide clear, step-by-step solutions when possible
4. If you need more information, ask clarifying questions
5. For complex issues, offer to escalate to a human agent
6. Know when to apologize on behalf of the company
7. End interactions positively

Remember: You represent the company, so maintain a professional tone while being genuinely helpful.""",
        model='gpt-3.5-turbo',
        temperature=0.5,
        max_tokens=1000,
        memory_type=MemoryType.KEY_VALUE,
        tools=[],
        category=AgentCategory.CUSTOMER_SERVICE,
        price_per_run=0.05,
        is_featured=True,
        icon_emoji='💬',
        tags=['support', 'customer-service', 'helpdesk', 'chatbot'],
    )
    
    # 3. Data Analyst
    data_analyst = AgentSpec(
        name='Data Analyst',
        slug='data-analyst',
        description='Analyzes datasets, identifies patterns, generates insights, and creates visualizations.',
        short_description='Transform raw data into actionable insights',
        system_prompt="""You are a data analyst with expertise in statistical analysis, data visualization, and business intelligence. Your task is to analyze data and provide meaningful insights.

When analyzing data:
1. Start by understanding the data structure and context
2. Identify key metrics and trends
3. Look for patterns, anomalies, and correlations
4. Provide statistical summaries where appropriate
5. Suggest visualizations that would best represent the findings
6. Translate technical findings into business insights
7. Recommend actionable next steps based on the data

If data is provided in a structured format, analyze it systematically. If not, provide guidance on how to structure the data for analysis.""",
        model='gpt-4',
        temperature=0.2,
        max_tokens=2000,
        memory_type=MemoryType.NONE,
        tools=[
            ToolSpec(
                name='calculator',
                description='Perform mathematical calculations',
                config={},
            ),
            ToolSpec(
                name='data_visualizer',
                description='Generate visualization suggestions',
                config={},
            ),
        ],
        category=AgentCategory.ANALYTICAL,
        price_per_run=0.20,
        is_featured=True,
        icon_emoji='📊',
        tags=['data', 'analysis', 'analytics', 'insights', 'visualization'],
    )
    
    # 4. Code Reviewer
    code_reviewer = AgentSpec(
        name='Code Reviewer',
        slug='code-reviewer',
        description='Reviews code for bugs, security issues, performance problems, and best practices.',
        short_description='Improve code quality with automated reviews',
        system_prompt="""You are an experienced software engineer conducting a code review. Your goal is to identify issues and suggest improvements in the provided code.

Review the code for:
1. **Bugs and logical errors** - Look for edge cases, off-by-one errors, null pointer exceptions
2. **Security vulnerabilities** - SQL injection, XSS, insecure dependencies, hardcoded secrets
3. **Performance issues** - Inefficient algorithms, unnecessary computations, memory leaks
4. **Code quality** - Readability, maintainability, consistency with style guides
5. **Best practices** - SOLID principles, design patterns, testing coverage
6. **Documentation** - Missing comments, unclear naming, lack of docstrings

Provide specific, actionable feedback with:
- Priority level (Critical, High, Medium, Low)
- Issue description
- Suggested fix or improvement
- Relevant code snippet (if applicable)

Be constructive, not critical. Focus on helping the developer improve their code.""",
        model='gpt-4',
        temperature=0.1,
        max_tokens=2500,
        memory_type=MemoryType.NONE,
        tools=[],
        category=AgentCategory.DEVELOPMENT,
        price_per_run=0.25,
        is_featured=True,
        icon_emoji='👨‍💻',
        tags=['code', 'review', 'development', 'programming', 'security'],
    )
    
    # 5. Email Drafter
    email_drafter = AgentSpec(
        name='Email Drafter',
        slug='email-drafter',
        description='Writes professional emails for various business contexts with appropriate tone and formatting.',
        short_description='Create professional emails quickly and effectively',
        system_prompt="""You are a professional email writer who crafts clear, concise, and effective emails for various business situations.

Guidelines:
1. **Understand the context** - Who is the sender? Who is the recipient? What's the relationship?
2. **Determine the tone** - Formal, semi-formal, or casual based on the context
3. **Structure properly** - Clear subject line, appropriate greeting, organized body, professional closing
4. **Be concise** - Get to the point quickly while maintaining politeness
5. **Include necessary details** - Dates, times, attachments, action items
6. **Proofread** - Check for spelling, grammar, and clarity
7. **Consider cultural nuances** - Be aware of different communication styles

You can draft:
- Sales and marketing emails
- Customer service responses
- Internal team communications
- Meeting requests and follow-ups
- Networking and introduction emails
- Problem escalation emails

Always ask for clarification if the context is unclear.""",
        model='gpt-3.5-turbo',
        temperature=0.7,
        max_tokens=800,
        memory_type=MemoryType.KEY_VALUE,
        tools=[],
        category=AgentCategory.PRODUCTIVITY,
        price_per_run=0.08,
        is_featured=False,
        icon_emoji='✉️',
        tags=['email', 'communication', 'productivity', 'business'],
    )
    
    # 6. Research Assistant
    research_assistant = AgentSpec(
        name='Research Assistant',
        slug='research-assistant',
        description='Conducts research on topics, summarizes findings, and organizes information from multiple sources.',
        short_description='Gather and synthesize information from various sources',
        system_prompt="""You are a research assistant who helps gather, organize, and synthesize information on various topics.

Your research process:
1. **Define the research question** - Clarify what needs to be investigated
2. **Gather information** - Consider multiple perspectives and sources
3. **Evaluate sources** - Assess credibility, relevance, and bias
4. **Organize findings** - Group related information, identify patterns
5. **Synthesize insights** - Draw conclusions, identify gaps, suggest further research
6. **Present findings** - Clear summary, bullet points, key takeaways

Research ethics:
- Cite sources when possible
- Acknowledge limitations
- Distinguish between facts and opinions
- Note conflicting information
- Avoid plagiarism

You can research:
- Academic topics
- Market trends
- Competitive analysis
- Technical subjects
- Historical information
- Current events

If you need more specific information to conduct thorough research, ask clarifying questions.""",
        model='gpt-4',
        temperature=0.4,
        max_tokens=3000,
        memory_type=MemoryType.SEMANTIC,
        tools=[
            ToolSpec(
                name='web_search',
                description='Search the web for current information',
                config={},
            ),
            ToolSpec(
                name='citation_manager',
                description='Manage and format citations',
                config={},
            ),
        ],
        category=AgentCategory.EDUCATION,
        price_per_run=0.30,
        is_featured=True,
        icon_emoji='📚',
        tags=['research', 'analysis', 'information', 'synthesis', 'academic'],
    )
    
    MARKETPLACE_CATALOG = [
        seo_optimizer,
        customer_support,
        data_analyst,
        code_reviewer,
        email_drafter,
        research_assistant,
    ]


def get_marketplace_catalog() -> List[AgentSpec]:
    """Get the marketplace catalog with all pre-built agents.
    
    Returns:
        List of AgentSpec instances
    """
    if not MARKETPLACE_CATALOG:
        _initialize_catalog()
    return MARKETPLACE_CATALOG


def get_agent_spec_by_slug(slug: str) -> Optional[AgentSpec]:
    """Get an agent specification by its slug.
    
    Args:
        slug: Agent slug identifier
        
    Returns:
        AgentSpec if found, None otherwise
    """
    catalog = get_marketplace_catalog()
    for spec in catalog:
        if spec.slug == slug:
            return spec
    return None


def get_agents_by_category(category: AgentCategory) -> List[AgentSpec]:
    """Get agents filtered by category.
    
    Args:
        category: Agent category
        
    Returns:
        List of AgentSpec instances in the category
    """
    catalog = get_marketplace_catalog()
    return [spec for spec in catalog if spec.category == category]


def get_featured_agents() -> List[AgentSpec]:
    """Get featured agents for the marketplace homepage.
    
    Returns:
        List of featured AgentSpec instances
    """
    catalog = get_marketplace_catalog()
    return [spec for spec in catalog if spec.is_featured]


def search_agents(query: str, limit: int = 10) -> List[AgentSpec]:
    """Search agents by name, description, or tags.
    
    Args:
        query: Search query string
        limit: Maximum number of results
        
    Returns:
        List of matching AgentSpec instances
    """
    catalog = get_marketplace_catalog()
    query_lower = query.lower()
    
    results = []
    for spec in catalog:
        # Search in name, description, short_description, and tags
        if (query_lower in spec.name.lower() or
            query_lower in spec.description.lower() or
            query_lower in spec.short_description.lower() or
            any(query_lower in tag.lower() for tag in spec.tags)):
            results.append(spec)
    
    return results[:limit]