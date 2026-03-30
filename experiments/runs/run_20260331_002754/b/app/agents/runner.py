"""Agent runner for executing agents with streaming and error handling."""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, AsyncGenerator
from decimal import Decimal

from sqlalchemy.orm import Session

from app import db
from app.models.agent_run import AgentRun, AgentRunStatus, AgentRunLog
from app.agents.agent_wrapper import AgentWrapper
from app.agents.exceptions import (
    AgentError, TokenLimitExceeded, CreditExhausted,
    RateLimitExceeded, ConfigurationError
)
from app.agents.memory import PersistentMemory


logger = logging.getLogger(__name__)


class AgentRunner:
    """Orchestrates agent execution with database logging and error handling."""
    
    def __init__(self, db_session: Optional[Session] = None):
        """Initialize agent runner.
        
        Args:
            db_session: Database session (uses default if None)
        """
        self.db_session = db_session or db.session
    
    def run_agent(
        self,
        agent_wrapper: AgentWrapper,
        prompt: str,
        user_id: int,
        agent_id: int,
        agent_version_id: Optional[int] = None,
        input_data: Optional[Dict] = None,
        metadata: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Run an agent and return result with full logging.
        
        Args:
            agent_wrapper: AgentWrapper instance
            prompt: Prompt text
            user_id: User ID executing the agent
            agent_id: Agent ID in database
            agent_version_id: Agent version ID (optional)
            input_data: Additional input data (optional)
            metadata: Additional metadata (optional)
            
        Returns:
            Dictionary with execution results
            
        Raises:
            AgentError: If execution fails
        """
        # Create agent run record
        agent_run = AgentRun(
            agent_id=agent_id,
            agent_version_id=agent_version_id,
            user_id=user_id,
            status=AgentRunStatus.PENDING,
            input_data=json.dumps({
                'prompt': prompt,
                'input_data': input_data or {},
                'metadata': metadata or {},
            }),
        )
        
        self.db_session.add(agent_run)
        self.db_session.commit()
        
        try:
            # Mark as running
            agent_run.start()
            self.db_session.commit()
            
            # Create start log
            start_log = AgentRunLog(
                run_id=agent_run.id,
                level='info',
                message='Agent execution started',
                metadata=json.dumps({
                    'prompt_preview': prompt[:100] + '...' if len(prompt) > 100 else prompt,
                    'user_id': user_id,
                    'agent_id': agent_id,
                })
            )
            self.db_session.add(start_log)
            self.db_session.commit()
            
            # Execute agent
            start_time = time.time()
            completion = agent_wrapper.run(prompt, **{'input_data': input_data} if input_data else {})
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            # Mark as completed
            agent_run.complete({'text': completion})
            agent_run.execution_time_ms = execution_time_ms
            
            # Calculate cost from token usage
            token_usage = agent_wrapper.token_usage.to_dict()
            cost_usd = agent_wrapper._calculate_cost()
            agent_run.cost_usd = Decimal(str(cost_usd))
            
            # Create completion log
            completion_log = AgentRunLog(
                run_id=agent_run.id,
                level='info',
                message='Agent execution completed successfully',
                metadata=json.dumps({
                    'execution_time_ms': execution_time_ms,
                    'token_usage': token_usage,
                    'cost_usd': cost_usd,
                    'completion_preview': completion[:100] + '...' if len(completion) > 100 else completion,
                })
            )
            self.db_session.add(completion_log)
            self.db_session.commit()
            
            logger.info(
                f'Agent run {agent_run.id} completed in {execution_time_ms}ms '
                f'with {token_usage["total_tokens"]} tokens'
            )
            
            return {
                'success': True,
                'run_id': agent_run.id,
                'completion': completion,
                'execution_time_ms': execution_time_ms,
                'token_usage': token_usage,
                'cost_usd': cost_usd,
                'agent_run': agent_run.to_dict(),
            }
            
        except TokenLimitExceeded as e:
            logger.warning(f'Token limit exceeded for agent run {agent_run.id}: {e}')
            agent_run.fail(f'Token limit exceeded: {e.limit} tokens')
            error_log = AgentRunLog(
                run_id=agent_run.id,
                level='error',
                message=f'Token limit exceeded: {e.limit} tokens',
                metadata=json.dumps({'limit': e.limit, 'actual': e.actual})
            )
            self.db_session.add(error_log)
            self.db_session.commit()
            
            return {
                'success': False,
                'run_id': agent_run.id,
                'error': 'token_limit_exceeded',
                'error_message': str(e),
                'details': {'limit': e.limit, 'actual': e.actual},
            }
            
        except CreditExhausted as e:
            logger.warning(f'Credit exhausted for agent run {agent_run.id}: {e}')
            agent_run.fail(f'Credit exhausted: {e.available} credits available')
            error_log = AgentRunLog(
                run_id=agent_run.id,
                level='error',
                message=f'Credit exhausted: {e.available} credits available',
                metadata=json.dumps({'available': e.available, 'required': e.required})
            )
            self.db_session.add(error_log)
            self.db_session.commit()
            
            return {
                'success': False,
                'run_id': agent_run.id,
                'error': 'credit_exhausted',
                'error_message': str(e),
                'details': {'available': e.available, 'required': e.required},
            }
            
        except RateLimitExceeded as e:
            logger.warning(f'Rate limit exceeded for agent run {agent_run.id}: {e}')
            agent_run.fail(f'Rate limit exceeded')
            error_log = AgentRunLog(
                run_id=agent_run.id,
                level='error',
                message='Rate limit exceeded',
                metadata=json.dumps({'retry_after': e.retry_after})
            )
            self.db_session.add(error_log)
            self.db_session.commit()
            
            return {
                'success': False,
                'run_id': agent_run.id,
                'error': 'rate_limit_exceeded',
                'error_message': str(e),
                'details': {'retry_after': e.retry_after},
            }
            
        except AgentError as e:
            logger.error(f'Agent error for run {agent_run.id}: {e}')
            agent_run.fail(str(e))
            error_log = AgentRunLog(
                run_id=agent_run.id,
                level='error',
                message=f'Agent error: {str(e)}',
                metadata=json.dumps({'error_type': type(e).__name__})
            )
            self.db_session.add(error_log)
            self.db_session.commit()
            
            return {
                'success': False,
                'run_id': agent_run.id,
                'error': 'agent_error',
                'error_message': str(e),
            }
            
        except Exception as e:
            logger.error(f'Unexpected error for agent run {agent_run.id}: {e}')
            agent_run.fail(f'Unexpected error: {str(e)}')
            error_log = AgentRunLog(
                run_id=agent_run.id,
                level='error',
                message=f'Unexpected error: {str(e)}',
                metadata=json.dumps({'error_type': type(e).__name__})
            )
            self.db_session.add(error_log)
            self.db_session.commit()
            
            return {
                'success': False,
                'run_id': agent_run.id,
                'error': 'unexpected_error',
                'error_message': str(e),
            }
    
    async def run_agent_stream(
        self,
        agent_wrapper: AgentWrapper,
        prompt: str,
        user_id: int,
        agent_id: int,
        agent_version_id: Optional[int] = None,
        input_data: Optional[Dict] = None,
        metadata: Optional[Dict] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Run an agent with streaming response.
        
        Args:
            agent_wrapper: AgentWrapper instance
            prompt: Prompt text
            user_id: User ID executing the agent
            agent_id: Agent ID in database
            agent_version_id: Agent version ID (optional)
            input_data: Additional input data (optional)
            metadata: Additional metadata (optional)
            
        Yields:
            Dictionary with streaming chunks or final result
            
        Raises:
            AgentError: If execution fails
        """
        # Create agent run record
        agent_run = AgentRun(
            agent_id=agent_id,
            agent_version_id=agent_version_id,
            user_id=user_id,
            status=AgentRunStatus.PENDING,
            input_data=json.dumps({
                'prompt': prompt,
                'input_data': input_data or {},
                'metadata': metadata or {},
            }),
        )
        
        self.db_session.add(agent_run)
        self.db_session.commit()
        
        start_time = time.time()
        completion_text = ''
        
        try:
            # Mark as running
            agent_run.start()
            self.db_session.commit()
            
            # Create start log
            start_log = AgentRunLog(
                run_id=agent_run.id,
                level='info',
                message='Agent streaming execution started',
                metadata=json.dumps({
                    'prompt_preview': prompt[:100] + '...' if len(prompt) > 100 else prompt,
                    'user_id': user_id,
                    'agent_id': agent_id,
                })
            )
            self.db_session.add(start_log)
            self.db_session.commit()
            
            # Yield start event
            yield {
                'type': 'start',
                'run_id': agent_run.id,
                'timestamp': datetime.utcnow().isoformat(),
            }
            
            # Execute agent with streaming
            async for chunk in agent_wrapper.run_stream(
                prompt,
                **{'input_data': input_data} if input_data else {}
            ):
                completion_text += chunk
                
                # Yield chunk
                yield {
                    'type': 'chunk',
                    'chunk': chunk,
                    'run_id': agent_run.id,
                    'timestamp': datetime.utcnow().isoformat(),
                }
            
            # Mark as completed
            execution_time_ms = int((time.time() - start_time) * 1000)
            agent_run.complete({'text': completion_text})
            agent_run.execution_time_ms = execution_time_ms
            
            # Calculate cost from token usage
            token_usage = agent_wrapper.token_usage.to_dict()
            cost_usd = agent_wrapper._calculate_cost()
            agent_run.cost_usd = Decimal(str(cost_usd))
            
            # Create completion log
            completion_log = AgentRunLog(
                run_id=agent_run.id,
                level='info',
                message='Agent streaming execution completed successfully',
                metadata=json.dumps({
                    'execution_time_ms': execution_time_ms,
                    'token_usage': token_usage,
                    'cost_usd': cost_usd,
                    'completion_length': len(completion_text),
                })
            )
            self.db_session.add(completion_log)
            self.db_session.commit()
            
            # Yield completion event
            yield {
                'type': 'completion',
                'run_id': agent_run.id,
                'success': True,
                'execution_time_ms': execution_time_ms,
                'token_usage': token_usage,
                'cost_usd': cost_usd,
                'completion': completion_text,
                'timestamp': datetime.utcnow().isoformat(),
            }
            
            logger.info(
                f'Agent streaming run {agent_run.id} completed in {execution_time_ms}ms '
                f'with {token_usage["total_tokens"]} tokens'
            )
            
        except TokenLimitExceeded as e:
            logger.warning(f'Token limit exceeded for streaming agent run {agent_run.id}: {e}')
            agent_run.fail(f'Token limit exceeded: {e.limit} tokens')
            error_log = AgentRunLog(
                run_id=agent_run.id,
                level='error',
                message=f'Token limit exceeded: {e.limit} tokens',
                metadata=json.dumps({'limit': e.limit, 'actual': e.actual})
            )
            self.db_session.add(error_log)
            self.db_session.commit()
            
            yield {
                'type': 'error',
                'run_id': agent_run.id,
                'error': 'token_limit_exceeded',
                'error_message': str(e),
                'details': {'limit': e.limit, 'actual': e.actual},
                'timestamp': datetime.utcnow().isoformat(),
            }
            
        except CreditExhausted as e:
            logger.warning(f'Credit exhausted for streaming agent run {agent_run.id}: {e}')
            agent_run.fail(f'Credit exhausted: {e.available} credits available')
            error_log = AgentRunLog(
                run_id=agent_run.id,
                level='error',
                message=f'Credit exhausted: {e.available} credits available',
                metadata=json.dumps({'available': e.available, 'required': e.required})
            )
            self.db_session.add(error_log)
            self.db_session.commit()
            
            yield {
                'type': 'error',
                'run_id': agent_run.id,
                'error': 'credit_exhausted',
                'error_message': str(e),
                'details': {'available': e.available, 'required': e.required},
                'timestamp': datetime.utcnow().isoformat(),
            }
            
        except RateLimitExceeded as e:
            logger.warning(f'Rate limit exceeded for streaming agent run {agent_run.id}: {e}')
            agent_run.fail(f'Rate limit exceeded')
            error_log = AgentRunLog(
                run_id=agent_run.id,
                level='error',
                message='Rate limit exceeded',
                metadata=json.dumps({'retry_after': e.retry_after})
            )
            self.db_session.add(error_log)
            self.db_session.commit()
            
            yield {
                'type': 'error',
                'run_id': agent_run.id,
                'error': 'rate_limit_exceeded',
                'error_message': str(e),
                'details': {'retry_after': e.retry_after},
                'timestamp': datetime.utcnow().isoformat(),
            }
            
        except AgentError as e:
            logger.error(f'Agent error for streaming run {agent_run.id}: {e}')
            agent_run.fail(str(e))
            error_log = AgentRunLog(
                run_id=agent_run.id,
                level='error',
                message=f'Agent error: {str(e)}',
                metadata=json.dumps({'error_type': type(e).__name__})
            )
            self.db_session.add(error_log)
            self.db_session.commit()
            
            yield {
                'type': 'error',
                'run_id': agent_run.id,
                'error': 'agent_error',
                'error_message': str(e),
                'timestamp': datetime.utcnow().isoformat(),
            }
            
        except Exception as e:
            logger.error(f'Unexpected error for streaming agent run {agent_run.id}: {e}')
            agent_run.fail(f'Unexpected error: {str(e)}')
            error_log = AgentRunLog(
                run_id=agent_run.id,
                level='error',
                message=f'Unexpected error: {str(e)}',
                metadata=json.dumps({'error_type': type(e).__name__})
            )
            self.db_session.add(error_log)
            self.db_session.commit()
            
            yield {
                'type': 'error',
                'run_id': agent_run.id,
                'error': 'unexpected_error',
                'error_message': str(e),
                'timestamp': datetime.utcnow().isoformat(),
            }


# Convenience functions
def run_agent(
    agent_wrapper: AgentWrapper,
    prompt: str,
    user_id: int,
    agent_id: int,
    db_session: Optional[Session] = None,
    **kwargs,
) -> Dict[str, Any]:
    """Run an agent (convenience function).
    
    Args:
        agent_wrapper: AgentWrapper instance
        prompt: Prompt text
        user_id: User ID
        agent_id: Agent ID
        db_session: Database session (optional)
        **kwargs: Additional arguments for AgentRunner.run_agent
        
    Returns:
        Dictionary with execution results
    """
    runner = AgentRunner(db_session)
    return runner.run_agent(agent_wrapper, prompt, user_id, agent_id, **kwargs)


async def run_agent_stream(
    agent_wrapper: AgentWrapper,
    prompt: str,
    user_id: int,
    agent_id: int,
    db_session: Optional[Session] = None,
    **kwargs,
) -> AsyncGenerator[Dict[str, Any], None]:
    """Run an agent with streaming (convenience function).
    
    Args:
        agent_wrapper: AgentWrapper instance
        prompt: Prompt text
        user_id: User ID
        agent_id: Agent ID
        db_session: Database session (optional)
        **kwargs: Additional arguments for AgentRunner.run_agent_stream
        
    Yields:
        Dictionary with streaming chunks or final result
    """
    runner = AgentRunner(db_session)
    async for chunk in runner.run_agent_stream(
        agent_wrapper, prompt, user_id, agent_id, **kwargs
    ):
        yield chunk