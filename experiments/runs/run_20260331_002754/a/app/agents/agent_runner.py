"""app/agents/agent_runner.py — Agent runner with streaming and credit management.

exports: run_agent_stream, AgentRunner, AgentRunRecord
used_by: app/services/agno_integration.py → execute_agent_streaming, app/api/v1/agents.py → run endpoint
rules:   Streams SSE chunks; updates agent run record; deducts credits; enforces rate limits
agent:   AgentIntegrator | 2024-12-05 | implemented agent runner with streaming and credit management
         message: "implement concurrent execution with asyncio semaphore"
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import AsyncGenerator, Dict, Any, Optional, List
from dataclasses import dataclass, field

from app.exceptions import CreditExhaustedError, AgentError, AgentTimeoutError
from app.agents.agent_wrapper import AgentWrapper
from app.agents.memory_manager import memory_manager

logger = logging.getLogger(__name__)


@dataclass
class AgentRunRecord:
    """Record of an agent run for tracking and billing."""
    run_id: str
    agent_id: str
    organization_id: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    prompt: str = ""
    response: str = ""
    tokens_used: int = 0
    tokens_input: int = 0
    tokens_output: int = 0
    credits_used: float = 0.0
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    status: str = "pending"  # pending, running, completed, failed, cancelled
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def duration_ms(self) -> Optional[int]:
        """Duration in milliseconds."""
        if self.end_time and self.start_time:
            return int((self.end_time - self.start_time).total_seconds() * 1000)
        return None


class AgentRunner:
    """Manages agent execution with streaming, credit management, and persistence."""
    
    def __init__(
        self,
        db_connection: Any = None,  # Database connection for storing run records
        rate_limit_per_minute: int = 60,
        max_concurrent_runs: int = 10,
    ):
        """Initialize agent runner.
        
        Args:
            db_connection: Database connection for storing run records
            rate_limit_per_minute: Rate limit for agent executions
            max_concurrent_runs: Maximum concurrent agent runs
        """
        self.db = db_connection
        self.rate_limit_per_minute = rate_limit_per_minute
        self.max_concurrent_runs = max_concurrent_runs
        
        # Tracking
        self.active_runs: Dict[str, AgentRunRecord] = {}
        self.run_history: List[AgentRunRecord] = []
        
        # Rate limiting
        self.request_timestamps: List[datetime] = []
        self.semaphore = asyncio.Semaphore(max_concurrent_runs)
        
        logger.info(f"AgentRunner initialized (max concurrent: {max_concurrent_runs})")
    
    async def _check_rate_limit(self) -> bool:
        """Check if rate limit is exceeded.
        
        Returns:
            True if allowed, False if rate limited
        """
        now = datetime.now()
        minute_ago = now.replace(minute=now.minute - 1) if now.minute > 0 else now.replace(minute=59, hour=now.hour - 1)
        
        # Remove old timestamps
        self.request_timestamps = [ts for ts in self.request_timestamps if ts > minute_ago]
        
        if len(self.request_timestamps) >= self.rate_limit_per_minute:
            return False
        
        self.request_timestamps.append(now)
        return True
    
    async def _store_run_record(self, record: AgentRunRecord) -> None:
        """Store run record in database.
        
        Args:
            record: Agent run record
            
        Note:
            In real implementation, this would insert into SQL database
            For now, store in memory and log
        """
        # Store in memory history
        self.run_history.append(record)
        
        # Remove from active runs if completed
        if record.status in ["completed", "failed", "cancelled"]:
            if record.run_id in self.active_runs:
                del self.active_runs[record.run_id]
        
        # Log the run
        log_data = {
            "run_id": record.run_id,
            "agent_id": record.agent_id,
            "organization_id": record.organization_id,
            "tokens_used": record.tokens_used,
            "credits_used": record.credits_used,
            "duration_ms": record.duration_ms,
            "status": record.status,
        }
        
        if record.status == "completed":
            logger.info(f"Agent run completed: {log_data}")
        elif record.status == "failed":
            logger.error(f"Agent run failed: {log_data}, error: {record.error_message}")
        else:
            logger.debug(f"Agent run {record.status}: {log_data}")
    
    async def run_agent_stream(
        self,
        agent_wrapper: AgentWrapper,
        prompt: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        stream: bool = True,
        timeout_seconds: int = 300,
        **kwargs,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Run agent with streaming response.
        
        Args:
            agent_wrapper: AgentWrapper instance
            prompt: User prompt
            user_id: Optional user ID
            session_id: Optional session ID for conversation continuity
            stream: Whether to stream response (always True for this method)
            timeout_seconds: Execution timeout
            **kwargs: Additional arguments for agent
            
        Yields:
            Streaming response chunks
            
        Raises:
            CreditExhaustedError: If insufficient credits
            AgentError: If agent execution fails
            AgentTimeoutError: If execution times out
        """
        run_id = str(uuid.uuid4())
        
        # Create run record
        record = AgentRunRecord(
            run_id=run_id,
            agent_id=agent_wrapper.agent_id,
            organization_id=agent_wrapper.organization_id,
            user_id=user_id,
            session_id=session_id,
            prompt=prompt,
            status="running",
            metadata={
                "stream": stream,
                "timeout_seconds": timeout_seconds,
                **kwargs,
            },
        )
        
        self.active_runs[run_id] = record
        
        try:
            # Check rate limit
            if not await self._check_rate_limit():
                raise AgentError("Rate limit exceeded. Please try again later.")
            
            # Check credits (handled by AgentWrapper)
            
            # Acquire semaphore for concurrent execution limit
            async with self.semaphore:
                # Execute with timeout
                try:
                    if stream:
                        # Get streaming response
                        response_stream = await asyncio.wait_for(
                            agent_wrapper.run(prompt, stream=True, session_id=session_id, **kwargs),
                            timeout=timeout_seconds,
                        )
                        
                        # Stream response chunks
                        full_response = ""
                        async for chunk in response_stream:
                            # In real implementation, chunk would be parsed from agno response
                            # For now, simulate streaming
                            chunk_data = {
                                "type": "chunk",
                                "content": chunk if isinstance(chunk, str) else str(chunk),
                                "run_id": run_id,
                            }
                            full_response += chunk_data["content"]
                            
                            yield chunk_data
                        
                        # Final completion message
                        record.response = full_response
                        record.status = "completed"
                        
                        # Estimate tokens (in real implementation, get from agent_wrapper)
                        record.tokens_used = len(full_response) // 4 + len(prompt) // 4
                        record.tokens_input = len(prompt) // 4
                        record.tokens_output = len(full_response) // 4
                        record.credits_used = record.tokens_used / 1000 * 0.01  # Simplified pricing
                        
                    else:
                        # Non-streaming execution
                        response = await asyncio.wait_for(
                            agent_wrapper.run(prompt, stream=False, session_id=session_id, **kwargs),
                            timeout=timeout_seconds,
                        )
                        
                        record.response = response if isinstance(response, str) else str(response)
                        record.status = "completed"
                        
                        # Estimate tokens
                        record.tokens_used = len(record.response) // 4 + len(prompt) // 4
                        record.tokens_input = len(prompt) // 4
                        record.tokens_output = len(record.response) // 4
                        record.credits_used = record.tokens_used / 1000 * 0.01
                        
                        yield {
                            "type": "complete",
                            "content": record.response,
                            "run_id": run_id,
                            "tokens_used": record.tokens_used,
                            "credits_used": record.credits_used,
                        }
                
                except asyncio.TimeoutError:
                    raise AgentTimeoutError(
                        f"Agent execution timed out after {timeout_seconds} seconds"
                    )
                except CreditExhaustedError:
                    raise
                except Exception as e:
                    raise AgentError(f"Agent execution failed: {e}")
        
        except (CreditExhaustedError, AgentError, AgentTimeoutError) as e:
            # Update record with error
            record.status = "failed"
            record.error_message = str(e)
            record.end_time = datetime.now()
            
            await self._store_run_record(record)
            
            # Yield error message
            yield {
                "type": "error",
                "error": str(e),
                "run_id": run_id,
            }
            
            # Re-raise for proper HTTP error handling
            raise
        
        finally:
            # Update end time and store record
            record.end_time = datetime.now()
            await self._store_run_record(record)
            
            # Yield final stats
            yield {
                "type": "stats",
                "run_id": run_id,
                "tokens_used": record.tokens_used,
                "credits_used": record.credits_used,
                "duration_ms": record.duration_ms,
                "status": record.status,
            }
    
    async def run_agent_non_streaming(
        self,
        agent_wrapper: AgentWrapper,
        prompt: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        timeout_seconds: int = 300,
        **kwargs,
    ) -> Dict[str, Any]:
        """Run agent with non-streaming response.
        
        Args:
            agent_wrapper: AgentWrapper instance
            prompt: User prompt
            user_id: Optional user ID
            session_id: Optional session ID
            timeout_seconds: Execution timeout
            **kwargs: Additional arguments
            
        Returns:
            Complete response with metadata
        """
        # Use streaming runner but collect all chunks
        response_chunks = []
        final_stats = {}
        
        try:
            async for chunk in self.run_agent_stream(
                agent_wrapper=agent_wrapper,
                prompt=prompt,
                user_id=user_id,
                session_id=session_id,
                stream=False,  # Non-streaming mode
                timeout_seconds=timeout_seconds,
                **kwargs,
            ):
                if chunk["type"] == "complete":
                    response_chunks.append(chunk["content"])
                    final_stats = {
                        "tokens_used": chunk.get("tokens_used", 0),
                        "credits_used": chunk.get("credits_used", 0),
                    }
                elif chunk["type"] == "error":
                    raise AgentError(chunk["error"])
                elif chunk["type"] == "stats":
                    final_stats.update(chunk)
        
        except AgentError as e:
            raise
        
        return {
            "response": "".join(response_chunks),
            "run_id": final_stats.get("run_id", ""),
            "tokens_used": final_stats.get("tokens_used", 0),
            "credits_used": final_stats.get("credits_used", 0),
            "duration_ms": final_stats.get("duration_ms", 0),
        }
    
    def get_active_runs(self, organization_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get active agent runs.
        
        Args:
            organization_id: Optional organization filter
            
        Returns:
            List of active run information
        """
        runs = self.active_runs.values()
        
        if organization_id:
            runs = [r for r in runs if r.organization_id == organization_id]
        
        return [
            {
                "run_id": r.run_id,
                "agent_id": r.agent_id,
                "organization_id": r.organization_id,
                "status": r.status,
                "start_time": r.start_time.isoformat(),
                "duration_ms": r.duration_ms,
            }
            for r in runs
        ]
    
    def get_run_history(
        self,
        organization_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Get agent run history.
        
        Args:
            organization_id: Optional organization filter
            agent_id: Optional agent filter
            limit: Maximum results
            offset: Pagination offset
            
        Returns:
            List of run history entries
        """
        runs = self.run_history
        
        if organization_id:
            runs = [r for r in runs if r.organization_id == organization_id]
        
        if agent_id:
            runs = [r for r in runs if r.agent_id == agent_id]
        
        # Sort by start time descending
        runs.sort(key=lambda r: r.start_time, reverse=True)
        
        paginated = runs[offset:offset + limit]
        
        return [
            {
                "run_id": r.run_id,
                "agent_id": r.agent_id,
                "organization_id": r.organization_id,
                "status": r.status,
                "tokens_used": r.tokens_used,
                "credits_used": r.credits_used,
                "start_time": r.start_time.isoformat(),
                "end_time": r.end_time.isoformat() if r.end_time else None,
                "duration_ms": r.duration_ms,
                "error_message": r.error_message,
            }
            for r in paginated
        ]
    
    def cancel_run(self, run_id: str) -> bool:
        """Cancel an active agent run.
        
        Args:
            run_id: Run ID to cancel
            
        Returns:
            True if cancelled, False if not found
        """
        if run_id not in self.active_runs:
            return False
        
        record = self.active_runs[run_id]
        record.status = "cancelled"
        record.end_time = datetime.now()
        
        # In real implementation, would cancel the actual async task
        # For now, just mark as cancelled
        
        logger.info(f"Cancelled agent run: {run_id}")
        return True


# Global agent runner instance
agent_runner = AgentRunner()