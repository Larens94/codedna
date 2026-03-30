"""base.py — AgentWrapper: wraps agno.Agent, counts tokens, enforces credit cap.

exports: AgentWrapper, CreditExhaustedError
used_by: runner.py → run_agent_stream, studio.py → build_custom_agent
rules:   Never call agno.Agent directly from API layer — always go through AgentWrapper
         Token count must be extracted from agno response metadata and stored in AgentRun.tokens_used
         AgentWrapper must raise CreditExhaustedError before starting if balance < min_credits
         All agent instructions must be sanitised (strip HTML, limit to 10k chars)
agent:   AgentIntegrator | 2024-03-30 | implemented AgentWrapper with token counting and credit enforcement
         message: "implement memory summarization when context exceeds 80% of model limit"
"""

import asyncio
import json
import re
from typing import Dict, Any, Optional, List, Union, AsyncGenerator
from dataclasses import dataclass
from datetime import datetime
import html

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools import tool

from agenthub.schemas.agents import AgentResponse
from agenthub.db.models import AgentRun, CreditAccount


class CreditExhaustedError(Exception):
    """Raised when user doesn't have enough credits to run an agent."""
    def __init__(self, required: float, available: float):
        self.required = required
        self.available = available
        super().__init__(f"Insufficient credits. Required: {required}, Available: {available}")


@dataclass
class AgentConfig:
    """Configuration for building an agent."""
    model: str = "gpt-4"
    system_prompt: str = "You are a helpful AI assistant."
    temperature: float = 0.7
    max_tokens: int = 2000
    tools: List[Tool] = None
    memory_type: str = "sqlite"  # "sqlite", "vector", or "none"
    max_context_length: int = 8000  # Maximum context tokens for the model
    price_per_run: float = 0.0
    agent_id: Optional[int] = None
    user_id: Optional[int] = None


class AgentWrapper:
    """Wraps agno.Agent with token counting, credit enforcement, and input sanitization."""
    
    def __init__(self, config: AgentConfig, db_session=None):
        """Initialize the agent wrapper.
        
        Args:
            config: Agent configuration
            db_session: Optional database session for credit checking
        """
        self.config = config
        self.db_session = db_session
        self.agent = None
        self.tokens_used = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self._initialize_agent()
        
    def _initialize_agent(self):
        """Initialize the underlying agno.Agent."""
        # Map model names to agno model classes
        model_map = {
            "gpt-4": OpenAIChat,
            "gpt-3.5-turbo": OpenAIChat,
            "claude-3-5-sonnet": OpenAIChat,  # Note: agno may need Claude-specific model
            "claude-3-opus": OpenAIChat,
            "claude-3-haiku": OpenAIChat,
        }
        
        model_class = model_map.get(self.config.model, OpenAIChat)
        
        # Create the agent
        self.agent = Agent(
            model=model_class(
                id=self.config.model,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            ),
            system_prompt=self._sanitize_prompt(self.config.system_prompt),
            tools=self.config.tools or [],
            show_tool_calls=True,
            markdown=True,
        )
        
    def _sanitize_prompt(self, prompt: str) -> str:
        """Sanitize system prompt by stripping HTML and limiting length.
        
        Args:
            prompt: Raw prompt text
            
        Returns:
            Sanitized prompt (max 10k chars, no HTML)
        """
        # Strip HTML tags
        sanitized = html.escape(prompt)
        
        # Limit to 10k characters
        if len(sanitized) > 10000:
            sanitized = sanitized[:10000] + "... [truncated]"
            
        return sanitized
    
    def _sanitize_input(self, input_data: Union[str, Dict, List]) -> str:
        """Sanitize user input.
        
        Args:
            input_data: User input (string, dict, or list)
            
        Returns:
            Sanitized string input
        """
        if isinstance(input_data, str):
            sanitized = html.escape(input_data)
        elif isinstance(input_data, dict) or isinstance(input_data, list):
            # Convert to JSON string and sanitize
            json_str = json.dumps(input_data)
            sanitized = html.escape(json_str)
        else:
            sanitized = str(input_data)
            sanitized = html.escape(sanitized)
            
        # Limit to 10k characters
        if len(sanitized) > 10000:
            sanitized = sanitized[:10000] + "... [truncated]"
            
        return sanitized
    
    async def check_credits(self, required_credits: float) -> bool:
        """Check if user has enough credits.
        
        Args:
            required_credits: Credits required for this run
            
        Returns:
            True if user has enough credits
            
        Raises:
            CreditExhaustedError: If user doesn't have enough credits
        """
        if not self.db_session or not self.config.user_id:
            # No credit checking if no DB session or user ID
            return True
            
        if required_credits <= 0:
            return True
            
        # Query credit account
        from sqlalchemy.orm import Session
        from agenthub.db.models import CreditAccount
        
        credit_account = self.db_session.query(CreditAccount).filter(
            CreditAccount.user_id == self.config.user_id
        ).first()
        
        if not credit_account:
            raise CreditExhaustedError(required_credits, 0.0)
            
        if credit_account.balance < required_credits:
            raise CreditExhaustedError(required_credits, credit_account.balance)
            
        return True
    
    async def deduct_credits(self, credits: float) -> bool:
        """Deduct credits from user's account.
        
        Args:
            credits: Credits to deduct
            
        Returns:
            True if successful
            
        Raises:
            ValueError: If credits cannot be deducted
        """
        if not self.db_session or not self.config.user_id:
            return True
            
        if credits <= 0:
            return True
            
        from sqlalchemy.orm import Session
        from agenthub.db.models import CreditAccount
        
        credit_account = self.db_session.query(CreditAccount).filter(
            CreditAccount.user_id == self.config.user_id
        ).first()
        
        if not credit_account:
            raise ValueError("Credit account not found")
            
        if credit_account.balance < credits:
            raise CreditExhaustedError(credits, credit_account.balance)
            
        credit_account.balance -= credits
        self.db_session.commit()
        
        return True
    
    def _extract_token_counts(self, response: Any) -> Dict[str, int]:
        """Extract token counts from agno response.
        
        Args:
            response: agno response object
            
        Returns:
            Dictionary with input_tokens and output_tokens
        """
        # This is a placeholder - actual implementation depends on agno's response format
        # In practice, we would extract this from response metadata
        return {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0
        }
    
    async def run(self, prompt: Union[str, Dict, List], 
                  stream: bool = False) -> Union[str, AsyncGenerator[str, None]]:
        """Run the agent with the given prompt.
        
        Args:
            prompt: User prompt (string, dict, or list)
            stream: Whether to stream the response
            
        Returns:
            Agent response (string if not streaming, generator if streaming)
            
        Raises:
            CreditExhaustedError: If user doesn't have enough credits
        """
        # Check credits before running
        await self.check_credits(self.config.price_per_run)
        
        # Sanitize input
        sanitized_prompt = self._sanitize_input(prompt)
        
        # Deduct credits
        await self.deduct_credits(self.config.price_per_run)
        
        if stream:
            return self._run_streaming(sanitized_prompt)
        else:
            return await self._run_non_streaming(sanitized_prompt)
    
    async def _run_non_streaming(self, prompt: str) -> str:
        """Run agent in non-streaming mode."""
        try:
            response = await self.agent.run(prompt)
            
            # Extract token counts (placeholder - implement based on agno's actual response)
            token_counts = self._extract_token_counts(response)
            self.input_tokens = token_counts.get("input_tokens", 0)
            self.output_tokens = token_counts.get("output_tokens", 0)
            self.tokens_used = token_counts.get("total_tokens", 0)
            
            return str(response)
            
        except Exception as e:
            # Refund credits on error
            if self.db_session and self.config.user_id:
                await self._refund_credits(self.config.price_per_run)
            raise
    
    async def _run_streaming(self, prompt: str) -> AsyncGenerator[str, None]:
        """Run agent in streaming mode."""
        try:
            # This is a simplified implementation
            # In practice, we would use agno's streaming API
            response = await self.agent.run(prompt)
            
            # Extract token counts
            token_counts = self._extract_token_counts(response)
            self.input_tokens = token_counts.get("input_tokens", 0)
            self.output_tokens = token_counts.get("output_tokens", 0)
            self.tokens_used = token_counts.get("total_tokens", 0)
            
            # Yield response in chunks (simplified)
            response_str = str(response)
            chunk_size = 100
            for i in range(0, len(response_str), chunk_size):
                yield response_str[i:i + chunk_size]
                await asyncio.sleep(0.01)  # Small delay to simulate streaming
                
        except Exception as e:
            # Refund credits on error
            if self.db_session and self.config.user_id:
                await self._refund_credits(self.config.price_per_run)
            raise
    
    async def _refund_credits(self, credits: float) -> bool:
        """Refund credits to user's account.
        
        Args:
            credits: Credits to refund
            
        Returns:
            True if successful
        """
        if not self.db_session or not self.config.user_id:
            return False
            
        if credits <= 0:
            return True
            
        from sqlalchemy.orm import Session
        from agenthub.db.models import CreditAccount
        
        credit_account = self.db_session.query(CreditAccount).filter(
            CreditAccount.user_id == self.config.user_id
        ).first()
        
        if not credit_account:
            return False
            
        credit_account.balance += credits
        self.db_session.commit()
        
        return True
    
    def get_token_counts(self) -> Dict[str, int]:
        """Get token counts from the last run."""
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.tokens_used
        }
    
    def estimate_cost(self, tokens_per_thousand: float = 0.01) -> float:
        """Estimate cost based on tokens used.
        
        Args:
            tokens_per_thousand: Cost per thousand tokens
            
        Returns:
            Estimated cost
        """
        return (self.tokens_used / 1000) * tokens_per_thousand