"""Agent wrapper for Agno agents with token counting and credit cap enforcement."""

import json
import logging
import time
from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, List, Optional, Union, Generator, AsyncGenerator
from datetime import datetime

try:
    import agno
    AGNO_AVAILABLE = True
except ImportError:
    AGNO_AVAILABLE = False
    agno = None

try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False
    tiktoken = None

from app.agents.exceptions import (
    AgentError, TokenLimitExceeded, CreditExhausted, 
    ConfigurationError, ToolError, RateLimitExceeded
)

logger = logging.getLogger(__name__)


@dataclass
class TokenUsage:
    """Token usage statistics."""
    
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    
    def add_prompt_tokens(self, tokens: int) -> None:
        """Add prompt tokens."""
        self.prompt_tokens += tokens
        self.total_tokens += tokens
    
    def add_completion_tokens(self, tokens: int) -> None:
        """Add completion tokens."""
        self.completion_tokens += tokens
        self.total_tokens += tokens
    
    def to_dict(self) -> Dict[str, int]:
        """Convert to dictionary."""
        return {
            'prompt_tokens': self.prompt_tokens,
            'completion_tokens': self.completion_tokens,
            'total_tokens': self.total_tokens,
        }
    
    def reset(self) -> None:
        """Reset token counts."""
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.total_tokens = 0


class TokenCounter:
    """Token counter for various LLM models."""
    
    # Average characters per token approximation
    AVG_CHARS_PER_TOKEN = 4
    
    # Model to encoding mapping for tiktoken
    MODEL_ENCODINGS = {
        'gpt-4': 'cl100k_base',
        'gpt-4-': 'cl100k_base',
        'gpt-3.5-turbo': 'cl100k_base',
        'gpt-3.5-turbo-': 'cl100k_base',
        'text-embedding-ada-002': 'cl100k_base',
        'text-davinci-003': 'p50k_base',
        'text-davinci-002': 'p50k_base',
        'code-davinci-002': 'p50k_base',
    }
    
    def __init__(self, model: str = 'gpt-3.5-turbo'):
        """Initialize token counter.
        
        Args:
            model: LLM model name
        """
        self.model = model
        self.encoding = None
        
        if TIKTOKEN_AVAILABLE:
            self._init_encoding()
    
    def _init_encoding(self) -> None:
        """Initialize tiktoken encoding for the model."""
        if not TIKTOKEN_AVAILABLE:
            return
        
        try:
            # Try to find the encoding for the model
            encoding_name = None
            for model_prefix, encoding in self.MODEL_ENCODINGS.items():
                if self.model.startswith(model_prefix):
                    encoding_name = encoding
                    break
            
            if encoding_name:
                self.encoding = tiktoken.get_encoding(encoding_name)
            else:
                # Default to cl100k_base for unknown models
                self.encoding = tiktoken.get_encoding('cl100k_base')
        except Exception as e:
            logger.warning(f'Failed to initialize tiktoken encoding: {e}')
            self.encoding = None
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text.
        
        Args:
            text: Text to count tokens for
            
        Returns:
            Token count
        """
        if not text:
            return 0
        
        # Try tiktoken if available and encoding is initialized
        if self.encoding:
            try:
                return len(self.encoding.encode(text))
            except Exception as e:
                logger.warning(f'Tiktoken encoding failed: {e}')
        
        # Fallback: approximate using character count
        return len(text) // self.AVG_CHARS_PER_TOKEN or 1
    
    def count_messages_tokens(self, messages: List[Dict[str, str]]) -> int:
        """Count tokens in a list of messages.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            
        Returns:
            Total token count
        """
        total = 0
        for message in messages:
            # Count content
            content = message.get('content', '')
            total += self.count_tokens(content)
            
            # Count role (small fixed overhead)
            total += self.count_tokens(message.get('role', ''))
        
        return total


class AgentWrapper:
    """Wraps an Agno agent with token counting and credit cap enforcement."""
    
    def __init__(
        self,
        agent: Any,  # agno.Agent
        user_id: int,
        credit_limit: Optional[float] = None,
        token_limit: Optional[int] = None,
        model: str = 'gpt-3.5-turbo',
        db_session = None,
    ):
        """Initialize agent wrapper.
        
        Args:
            agent: Agno agent instance
            user_id: ID of user executing agent
            credit_limit: Maximum credits user can spend (None for unlimited)
            token_limit: Maximum tokens per run (None for unlimited)
            model: LLM model name for token counting
            db_session: Database session for logging
        """
        if not AGNO_AVAILABLE:
            raise ImportError('Agno framework is not installed')
        
        self.agent = agent
        self.user_id = user_id
        self.credit_limit = credit_limit
        self.token_limit = token_limit
        self.db_session = db_session
        
        self.token_counter = TokenCounter(model)
        self.token_usage = TokenUsage()
        self.execution_start_time: Optional[datetime] = None
        self.execution_end_time: Optional[datetime] = None
        
        # Execution statistics
        self.execution_count = 0
        self.total_execution_time_ms = 0
        self.total_tokens_used = 0
        self.total_cost_usd = 0.0
        
        logger.info(f'Initialized AgentWrapper for user {user_id}')
    
    def _check_credit_limit(self, estimated_cost: float = 0.0) -> None:
        """Check if user has sufficient credits.
        
        Args:
            estimated_cost: Estimated cost of this execution
            
        Raises:
            CreditExhausted: If credits are insufficient
        """
        if self.credit_limit is None:
            return
        
        # In a real implementation, we would fetch user's current credit balance
        # For now, we'll assume credits are managed elsewhere
        # This is a placeholder for credit checking logic
        pass
    
    def _check_token_limit(self, prompt: str, messages: Optional[List[Dict]] = None) -> None:
        """Check if token limit would be exceeded.
        
        Args:
            prompt: Prompt text
            messages: List of messages (if using chat format)
            
        Raises:
            TokenLimitExceeded: If token limit would be exceeded
        """
        if self.token_limit is None:
            return
        
        # Count tokens in input
        input_tokens = 0
        if messages:
            input_tokens = self.token_counter.count_messages_tokens(messages)
        else:
            input_tokens = self.token_counter.count_tokens(prompt)
        
        # Add buffer for completion (estimate 100 tokens)
        estimated_total = input_tokens + 100
        
        if estimated_total > self.token_limit:
            raise TokenLimitExhausted(
                limit=self.token_limit,
                actual=estimated_total,
                agent_id=getattr(self.agent, 'id', None)
            )
    
    def _update_token_usage(self, prompt: str, completion: str) -> None:
        """Update token usage statistics.
        
        Args:
            prompt: Prompt text
            completion: Completion text
        """
        prompt_tokens = self.token_counter.count_tokens(prompt)
        completion_tokens = self.token_counter.count_tokens(completion)
        
        self.token_usage.add_prompt_tokens(prompt_tokens)
        self.token_usage.add_completion_tokens(completion_tokens)
        self.total_tokens_used += prompt_tokens + completion_tokens
        
        logger.debug(
            f'Token usage: {prompt_tokens} prompt, {completion_tokens} completion '
            f'(total: {self.token_usage.total_tokens})'
        )
    
    def _calculate_cost(self) -> float:
        """Calculate cost based on token usage.
        
        Returns:
            Cost in USD
        """
        # Simplified cost calculation
        # In production, use actual model pricing
        cost_per_1k_tokens = 0.002  # $0.002 per 1K tokens (example)
        return (self.token_usage.total_tokens / 1000) * cost_per_1k_tokens
    
    def _log_execution(
        self,
        prompt: str,
        completion: str,
        success: bool = True,
        error_message: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> None:
        """Log agent execution to database.
        
        Args:
            prompt: Prompt text
            completion: Completion text (or error message)
            success: Whether execution was successful
            error_message: Error message if any
            metadata: Additional metadata
        """
        if not self.db_session:
            return
        
        try:
            # This would create an AgentRun record
            # Placeholder for actual logging implementation
            execution_time_ms = 0
            if self.execution_start_time and self.execution_end_time:
                delta = self.execution_end_time - self.execution_start_time
                execution_time_ms = int(delta.total_seconds() * 1000)
            
            log_entry = {
                'user_id': self.user_id,
                'agent_id': getattr(self.agent, 'id', None),
                'prompt': prompt[:1000],  # Truncate for logging
                'completion': completion[:1000] if completion else None,
                'success': success,
                'error_message': error_message,
                'execution_time_ms': execution_time_ms,
                'token_usage': self.token_usage.to_dict(),
                'cost_usd': self._calculate_cost(),
                'metadata': metadata or {},
                'timestamp': datetime.utcnow(),
            }
            
            # In production, this would save to AgentRun table
            logger.info(f'Agent execution logged: {log_entry}')
            
        except Exception as e:
            logger.error(f'Failed to log agent execution: {e}')
    
    @contextmanager
    def _execution_context(self):
        """Context manager for agent execution tracking."""
        self.execution_start_time = datetime.utcnow()
        self.token_usage.reset()
        
        try:
            yield
        finally:
            self.execution_end_time = datetime.utcnow()
            self.execution_count += 1
    
    def run(
        self,
        prompt: str,
        messages: Optional[List[Dict]] = None,
        **kwargs,
    ) -> str:
        """Run agent with prompt and return completion.
        
        Args:
            prompt: Prompt text (if not using messages)
            messages: List of messages for chat format
            **kwargs: Additional arguments to pass to agent
            
        Returns:
            Agent completion text
            
        Raises:
            AgentError: If agent execution fails
            TokenLimitExceeded: If token limit exceeded
            CreditExhausted: If credits exhausted
        """
        # Check limits
        self._check_token_limit(prompt, messages)
        self._check_credit_limit()
        
        with self._execution_context():
            try:
                # Run agent
                # Assuming agno agent has a run method
                if hasattr(self.agent, 'run'):
                    if messages:
                        # Convert messages to agno format if needed
                        completion = self.agent.run(messages=messages, **kwargs)
                    else:
                        completion = self.agent.run(prompt=prompt, **kwargs)
                elif hasattr(self.agent, 'invoke'):
                    # Alternative method name
                    if messages:
                        completion = self.agent.invoke(messages=messages, **kwargs)
                    else:
                        completion = self.agent.invoke(prompt=prompt, **kwargs)
                else:
                    raise AgentError('Agent does not have a run or invoke method')
                
                # Update token usage
                # Note: We might need to extract the actual prompt and completion
                # from the agent's internal state. For now, use provided prompt
                # and returned completion.
                self._update_token_usage(prompt, str(completion))
                
                # Calculate cost and check credit limit again
                cost = self._calculate_cost()
                self.total_cost_usd += cost
                self._check_credit_limit(cost)
                
                # Log successful execution
                self._log_execution(prompt, str(completion), success=True)
                
                return str(completion)
                
            except Exception as e:
                error_msg = f'Agent execution failed: {str(e)}'
                logger.error(error_msg)
                
                # Log failed execution
                self._log_execution(
                    prompt, '',
                    success=False,
                    error_message=error_msg,
                )
                
                # Convert specific exceptions
                if 'rate limit' in str(e).lower():
                    raise RateLimitExceeded()
                elif 'token' in str(e).lower() and 'limit' in str(e).lower():
                    raise TokenLimitExceeded(
                        limit=self.token_limit or 0,
                        actual=self.token_usage.total_tokens,
                    )
                else:
                    raise AgentError(f'Agent execution failed: {str(e)}')
    
    async def run_stream(
        self,
        prompt: str,
        messages: Optional[List[Dict]] = None,
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        """Run agent with streaming response.
        
        Args:
            prompt: Prompt text
            messages: List of messages for chat format
            **kwargs: Additional arguments
            
        Yields:
            Chunks of completion text
            
        Raises:
            AgentError: If agent execution fails
        """
        # Check limits
        self._check_token_limit(prompt, messages)
        self._check_credit_limit()
        
        with self._execution_context():
            try:
                completion_text = ''
                
                # Assuming agno agent supports streaming
                if hasattr(self.agent, 'run_stream'):
                    stream_method = self.agent.run_stream
                elif hasattr(self.agent, 'stream'):
                    stream_method = self.agent.stream
                else:
                    # Fallback to non-streaming
                    completion = self.run(prompt, messages, **kwargs)
                    yield completion
                    return
                
                # Execute streaming
                if messages:
                    stream = stream_method(messages=messages, **kwargs)
                else:
                    stream = stream_method(prompt=prompt, **kwargs)
                
                # Process stream
                async for chunk in stream:
                    completion_text += chunk
                    yield chunk
                
                # Update token usage after completion
                self._update_token_usage(prompt, completion_text)
                
                # Calculate cost
                cost = self._calculate_cost()
                self.total_cost_usd += cost
                self._check_credit_limit(cost)
                
                # Log successful execution
                self._log_execution(prompt, completion_text, success=True)
                
            except Exception as e:
                error_msg = f'Agent streaming execution failed: {str(e)}'
                logger.error(error_msg)
                
                self._log_execution(
                    prompt, '',
                    success=False,
                    error_message=error_msg,
                )
                
                raise AgentError(f'Agent streaming execution failed: {str(e)}')
    
    def get_stats(self) -> Dict[str, Any]:
        """Get execution statistics.
        
        Returns:
            Dictionary with execution statistics
        """
        return {
            'execution_count': self.execution_count,
            'total_tokens_used': self.total_tokens_used,
            'total_cost_usd': round(self.total_cost_usd, 4),
            'total_execution_time_ms': self.total_execution_time_ms,
            'average_execution_time_ms': (
                self.total_execution_time_ms / self.execution_count
                if self.execution_count else 0
            ),
        }