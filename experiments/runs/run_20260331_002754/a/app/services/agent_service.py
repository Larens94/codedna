"""app/services/agent_service.py — AI agent management service.

exports: AgentService
used_by: app/services/container.py → ServiceContainer.agents, API agent endpoints
rules:   must validate agent configurations; enforce organization limits; manage API keys securely
         in-memory store _agents_store keyed by int id; marketplace pre-populated with IDs 1-6
         create_agent assigns IDs starting from 100 (incrementing _next_agent_id)
agent:   Product Architect | 2024-03-30 | created agent service skeleton
         message: "implement agent configuration validation against Agno framework schema"
         claude-sonnet-4-6 | anthropic | 2026-03-31 | s_20260331_002 | implemented in-memory store with marketplace agents; CRUD + session/run mocks
"""

import logging
import uuid
import secrets
from datetime import datetime
from types import SimpleNamespace
from typing import Optional, Dict, Any, List, AsyncGenerator

from app.exceptions import NotFoundError, ConflictError, ValidationError, AuthorizationError
from app.services.container import ServiceContainer

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# In-memory store (dev/demo — no Postgres)
# ---------------------------------------------------------------------------
_agents_store: Dict[int, dict] = {
    1: {
        "id": 1,
        "name": "SEO Optimizer Pro",
        "description": "Optimize your content for search engines automatically.",
        "category": "SEO",
        "pricing_tier": "pro",
        "monthly_price": 49,
        "rating": 4.8,
        "is_public": True,
        "is_active": True,
        "organization_id": 1,
        "created_at": "2024-01-01",
        "model_provider": "openai",
        "model_name": "gpt-4o",
        "slug": "seo-optimizer-pro",
        "system_prompt": "You are an SEO expert.",
        "config": {},
        "max_tokens_per_session": 4096,
        "temperature": 0.7,
        "creator_id": 1,
    },
    2: {
        "id": 2,
        "name": "Customer Support Agent",
        "description": "Handle customer inquiries with empathy and speed.",
        "category": "Support",
        "pricing_tier": "basic",
        "monthly_price": 29,
        "rating": 4.5,
        "is_public": True,
        "is_active": True,
        "organization_id": 1,
        "created_at": "2024-01-01",
        "model_provider": "openai",
        "model_name": "gpt-4o-mini",
        "slug": "customer-support-agent",
        "system_prompt": "You are a helpful customer support agent.",
        "config": {},
        "max_tokens_per_session": 2048,
        "temperature": 0.5,
        "creator_id": 1,
    },
    3: {
        "id": 3,
        "name": "Data Analyzer",
        "description": "Analyze datasets and surface actionable insights.",
        "category": "Data",
        "pricing_tier": "pro",
        "monthly_price": 79,
        "rating": 4.9,
        "is_public": True,
        "is_active": True,
        "organization_id": 1,
        "created_at": "2024-01-01",
        "model_provider": "openai",
        "model_name": "gpt-4o",
        "slug": "data-analyzer",
        "system_prompt": "You are a data analysis expert.",
        "config": {},
        "max_tokens_per_session": 8192,
        "temperature": 0.3,
        "creator_id": 1,
    },
    4: {
        "id": 4,
        "name": "Code Reviewer",
        "description": "Review pull requests and enforce coding standards.",
        "category": "Code",
        "pricing_tier": "enterprise",
        "monthly_price": 199,
        "rating": 4.7,
        "is_public": True,
        "is_active": True,
        "organization_id": 1,
        "created_at": "2024-01-01",
        "model_provider": "openai",
        "model_name": "gpt-4o",
        "slug": "code-reviewer",
        "system_prompt": "You are an expert code reviewer.",
        "config": {},
        "max_tokens_per_session": 8192,
        "temperature": 0.2,
        "creator_id": 1,
    },
    5: {
        "id": 5,
        "name": "Email Responder",
        "description": "Draft professional email replies in seconds.",
        "category": "Email",
        "pricing_tier": "free",
        "monthly_price": 0,
        "rating": 4.2,
        "is_public": True,
        "is_active": True,
        "organization_id": 1,
        "created_at": "2024-01-01",
        "model_provider": "openai",
        "model_name": "gpt-4o-mini",
        "slug": "email-responder",
        "system_prompt": "You are a professional email writer.",
        "config": {},
        "max_tokens_per_session": 2048,
        "temperature": 0.6,
        "creator_id": 1,
    },
    6: {
        "id": 6,
        "name": "Research Assistant",
        "description": "Deep research across the web and summarize findings.",
        "category": "Research",
        "pricing_tier": "basic",
        "monthly_price": 35,
        "rating": 4.6,
        "is_public": True,
        "is_active": True,
        "organization_id": 1,
        "created_at": "2024-01-01",
        "model_provider": "openai",
        "model_name": "gpt-4o",
        "slug": "research-assistant",
        "system_prompt": "You are a thorough research assistant.",
        "config": {},
        "max_tokens_per_session": 8192,
        "temperature": 0.4,
        "creator_id": 1,
    },
}

_next_agent_id: int = 100


class AgentService:
    """AI agent management service.

    Rules:
        Agent configurations must be validated against Agno schema
        API keys must be hashed before storage (like passwords)
        Agent execution must respect organization limits and credits
        All agent operations must be scoped to organization
        In-memory store only — no Postgres in this demo environment
    """

    def __init__(self, container: ServiceContainer):
        self.container = container
        logger.info("AgentService initialized")

    # ------------------------------------------------------------------
    # Core CRUD
    # ------------------------------------------------------------------

    async def list_agents(
        self,
        user_id: Any = None,
        organization_id: Optional[int] = None,
        page: int = 1,
        per_page: int = 20,
        search: Optional[str] = None,
        model_provider: Optional[str] = None,
        is_public: Optional[bool] = None,
        is_active: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """List agents with optional filters.

        Rules:
            Returns items list and total count for pagination
            Filters are applied in-memory on _agents_store
        """
        list_dict_agents_all = list(_agents_store.values())

        # Apply filters
        if organization_id is not None:
            list_dict_agents_all = [a for a in list_dict_agents_all if a.get("organization_id") == organization_id]
        if search is not None:
            str_search_lower = search.lower()
            list_dict_agents_all = [
                a for a in list_dict_agents_all
                if str_search_lower in a.get("name", "").lower()
                or str_search_lower in a.get("description", "").lower()
            ]
        if model_provider is not None:
            str_provider = model_provider.value if hasattr(model_provider, "value") else str(model_provider)
            list_dict_agents_all = [a for a in list_dict_agents_all if a.get("model_provider") == str_provider]
        if is_public is not None:
            list_dict_agents_all = [a for a in list_dict_agents_all if a.get("is_public") == is_public]
        if is_active is not None:
            list_dict_agents_all = [a for a in list_dict_agents_all if a.get("is_active") == is_active]

        int_total = len(list_dict_agents_all)
        int_offset = (page - 1) * per_page
        list_dict_agents_page = list_dict_agents_all[int_offset: int_offset + per_page]

        return {"items": list_dict_agents_page, "total": int_total}

    async def create_agent(
        self,
        organization_id: int,
        creator_id: Any,
        name: str,
        slug: str = "",
        description: str = "",
        system_prompt: str = "",
        config: Optional[Dict[str, Any]] = None,
        model_provider: Any = "openai",
        model_name: str = "gpt-4o",
        max_tokens_per_session: int = 4096,
        temperature: float = 0.7,
        is_public: bool = False,
    ) -> SimpleNamespace:
        """Create a new agent in the in-memory store.

        Rules:
            IDs start at 100 and increment via module-level _next_agent_id
            Returns SimpleNamespace (not dict) to support attribute access
        """
        global _next_agent_id
        str_provider = model_provider.value if hasattr(model_provider, "value") else str(model_provider)
        int_new_id = _next_agent_id
        _next_agent_id += 1

        dict_agent_new = {
            "id": int_new_id,
            "name": name,
            "slug": slug or name.lower().replace(" ", "-"),
            "description": description,
            "system_prompt": system_prompt,
            "config": config or {},
            "model_provider": str_provider,
            "model_name": model_name,
            "max_tokens_per_session": max_tokens_per_session,
            "temperature": temperature,
            "is_public": is_public,
            "is_active": True,
            "organization_id": organization_id,
            "creator_id": creator_id,
            "created_at": datetime.utcnow().isoformat(),
            "category": "Custom",
            "pricing_tier": "free",
            "monthly_price": 0,
            "rating": 0.0,
        }
        _agents_store[int_new_id] = dict_agent_new

        return SimpleNamespace(**dict_agent_new)

    async def get_agent(self, agent_id: int) -> SimpleNamespace:
        """Get agent by integer ID.

        Raises:
            NotFoundError: if agent_id not in _agents_store
        """
        dict_agent = _agents_store.get(agent_id)
        if dict_agent is None:
            raise NotFoundError(f"Agent {agent_id} not found")
        return SimpleNamespace(**dict_agent)

    async def update_agent(
        self,
        agent_id: int,
        updates: Dict[str, Any],
        updated_by: Any = None,
    ) -> SimpleNamespace:
        """Update agent fields in-memory."""
        dict_agent = _agents_store.get(agent_id)
        if dict_agent is None:
            raise NotFoundError(f"Agent {agent_id} not found")
        dict_agent.update(updates)
        return SimpleNamespace(**dict_agent)

    async def delete_agent(self, agent_id: int, deleted_by: Any = None) -> None:
        """Soft-delete agent (marks is_active=False)."""
        dict_agent = _agents_store.get(agent_id)
        if dict_agent is None:
            raise NotFoundError(f"Agent {agent_id} not found")
        dict_agent["is_active"] = False

    # ------------------------------------------------------------------
    # Session / run mocks (return demo data without raising)
    # ------------------------------------------------------------------

    async def run_agent(
        self,
        agent_id: Any = None,
        organization_id: Any = None,
        user_id: Any = None,
        prompt: str = "",
        session_id: Any = None,
        parameters: Any = None,
        stream: bool = False,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Run agent — returns demo response."""
        return {
            "response": "Demo response",
            "session_id": "demo",
            "message_id": "1",
            "token_count": 100,
            "credits_used": 1,
        }

    async def list_agent_sessions(
        self,
        agent_id: Any = None,
        user_id: Any = None,
        page: int = 1,
        per_page: int = 20,
        is_active: Optional[bool] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """List agent sessions — returns empty demo list."""
        return {"items": [], "total": 0}

    async def create_agent_session(
        self,
        agent_id: Any = None,
        organization_id: Any = None,
        user_id: Any = None,
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> SimpleNamespace:
        """Create agent session — returns demo SimpleNamespace."""
        return SimpleNamespace(
            id="demo-session",
            agent_id=agent_id,
            user_id=user_id,
            is_active=True,
            title=title or "Demo",
            metadata=metadata or {},
        )

    async def get_agent_session(
        self,
        session_id: Any = None,
        user_id: Any = None,
        **kwargs: Any,
    ) -> SimpleNamespace:
        """Get agent session — returns demo SimpleNamespace."""
        return SimpleNamespace(
            id=session_id,
            user_id=user_id,
            organization_id=1,
            is_active=True,
        )

    async def end_agent_session(self, session_id: Any = None, **kwargs: Any) -> None:
        """End agent session — no-op in demo."""
        return None

    async def list_session_messages(
        self,
        session_id: Any = None,
        page: int = 1,
        per_page: int = 20,
        role: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """List session messages — returns empty demo list."""
        return {"items": [], "total": 0}

    async def create_session_message(
        self,
        session_id: Any = None,
        role: str = "user",
        content: str = "",
        tool_calls: Any = None,
        tool_call_id: Any = None,
        metadata: Any = None,
        **kwargs: Any,
    ) -> SimpleNamespace:
        """Create session message — returns demo SimpleNamespace."""
        return SimpleNamespace(
            id="msg-1",
            role=role,
            content=content,
            timestamp=datetime.utcnow(),
        )

    async def run_agent_stream(
        self,
        agent_id: Any = None,
        organization_id: Any = None,
        user_id: Any = None,
        prompt: str = "",
        session_id: Any = None,
        parameters: Any = None,
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        """Run agent streaming — yields a single demo SSE chunk."""
        async def _gen():
            yield "data: {\"chunk\": \"Demo streaming response\"}\n\n"
        return _gen()

    # ------------------------------------------------------------------
    # Methods that remain unimplemented (original skeleton stubs)
    # ------------------------------------------------------------------

    async def regenerate_api_key(self, organization_id: Any, agent_id: Any, regenerated_by: Any) -> str:
        raise NotImplementedError("regenerate_api_key not yet implemented")

    async def validate_agent_config(self, config: Dict[str, Any]) -> List[str]:
        raise NotImplementedError("validate_agent_config not yet implemented")

    async def execute_agent(self, organization_id: Any, agent_id: Any, input_data: Any, **kwargs: Any) -> Dict[str, Any]:
        raise NotImplementedError("execute_agent not yet implemented")

    async def update_agent_last_used(self, agent_id: Any) -> None:
        raise NotImplementedError("update_agent_last_used not yet implemented")

    async def get_agent_usage(self, organization_id: Any, agent_id: Any, period: Any = None) -> Dict[str, Any]:
        raise NotImplementedError("get_agent_usage not yet implemented")
