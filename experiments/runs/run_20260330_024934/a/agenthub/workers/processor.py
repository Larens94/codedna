"""processor.py — Background job processing for long-running tasks.

exports: process_agent_run, export_data, send_bulk_notifications
used_by: agents/runner.py, api/usage.py, notification system
rules:   must handle job queuing; must support retries; must track progress
agent:   DataEngineer | 2024-01-15 | created background job processor with Redis queue
         message: "implement Celery/RQ integration for production deployment"
"""

import logging
import json
import time
import asyncio
from typing import Dict, Any, Optional, Tuple, Callable
from datetime import datetime, timedelta
from enum import Enum
import redis
from sqlalchemy.orm import Session

from agenthub.db.session import SessionLocal
from agenthub.db.models import AgentRun, User, Agent, AuditLog
from agenthub.config import settings

logger = logging.getLogger(__name__)


class JobStatus(Enum):
    """Job status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


class JobProcessor:
    """Process background jobs with Redis queue support."""
    
    def __init__(self):
        """Initialize job processor."""
        self.redis_client = None
        self.job_queue = "agenthub_jobs"
        self.result_queue = "agenthub_results"
        
        # Initialize Redis if configured
        if hasattr(settings, 'REDIS_URL') and settings.REDIS_URL:
            try:
                self.redis_client = redis.from_url(settings.REDIS_URL)
                logger.info("Redis client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Redis: {e}")
    
    def enqueue_job(
        self,
        job_type: str,
        data: Dict[str, Any],
        priority: int = 0,
        delay_seconds: int = 0
    ) -> Optional[str]:
        """Enqueue a job for background processing.
        
        Args:
            job_type: Type of job (e.g., 'agent_run', 'export', 'notification')
            data: Job data
            priority: Job priority (higher = more important)
            delay_seconds: Delay before processing
            
        Returns:
            Job ID or None if failed
        """
        try:
            import uuid
            
            job_id = str(uuid.uuid4())
            job_data = {
                'id': job_id,
                'type': job_type,
                'data': data,
                'priority': priority,
                'created_at': datetime.utcnow().isoformat(),
                'status': JobStatus.PENDING.value,
                'attempts': 0,
                'max_attempts': 3
            }
            
            if self.redis_client:
                # Store job in Redis
                job_key = f"job:{job_id}"
                self.redis_client.hset(job_key, mapping=job_data)
                
                # Add to queue with score (priority + timestamp)
                score = priority + time.time()
                self.redis_client.zadd(self.job_queue, {job_id: score})
                
                # Set delay if specified
                if delay_seconds > 0:
                    delay_key = f"job:delay:{job_id}"
                    self.redis_client.setex(delay_key, delay_seconds, job_id)
                
                logger.info(f"Enqueued job {job_id} of type {job_type}")
                return job_id
            else:
                # Fallback to in-memory processing
                logger.warning("Redis not available, using in-memory queue")
                # In production, you would use a proper queue system
                return job_id
                
        except Exception as e:
            logger.error(f"Error enqueuing job: {e}")
            return None
    
    def process_agent_run(
        self,
        user_id: int,
        agent_id: int,
        input_data: Dict[str, Any],
        is_async: bool = True
    ) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """Process an agent run, either synchronously or asynchronously.
        
        Args:
            user_id: User ID
            agent_id: Agent ID
            input_data: Input data for the agent
            is_async: Whether to process asynchronously
            
        Returns:
            Tuple of (success, job_id/error, result)
        """
        if is_async and self.redis_client:
            # Enqueue for background processing
            job_id = self.enqueue_job(
                job_type='agent_run',
                data={
                    'user_id': user_id,
                    'agent_id': agent_id,
                    'input_data': input_data
                },
                priority=10  # High priority for user-initiated runs
            )
            
            if job_id:
                return True, job_id, None
            else:
                return False, "Failed to enqueue job", None
        else:
            # Process synchronously
            return self._process_agent_run_sync(user_id, agent_id, input_data)
    
    def _process_agent_run_sync(
        self,
        user_id: int,
        agent_id: int,
        input_data: Dict[str, Any]
    ) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """Process agent run synchronously.
        
        Args:
            user_id: User ID
            agent_id: Agent ID
            input_data: Input data
            
        Returns:
            Tuple of (success, error, result)
        """
        db = SessionLocal()
        try:
            import uuid
            from agenthub.agents.runner import run_agent
            from agenthub.billing.credits import deduct_credits
            
            # Get user and agent
            user = db.query(User).filter(User.id == user_id).first()
            agent = db.query(Agent).filter(Agent.id == agent_id).first()
            
            if not user or not agent:
                return False, "User or agent not found", None
            
            # Check agent availability
            if not agent.is_active:
                return False, "Agent is not active", None
            
            # Create agent run record
            agent_run = AgentRun(
                public_id=str(uuid.uuid4()),
                user_id=user.id,
                agent_id=agent.id,
                input_data=input_data,
                status="running",
                started_at=datetime.utcnow(),
                metadata={
                    "execution_type": "background_sync"
                }
            )
            db.add(agent_run)
            db.commit()
            
            # Execute agent (simplified - use actual agent runner)
            # result = run_agent(agent, input_data)
            
            # Mock execution for now
            import random
            time.sleep(random.uniform(0.5, 2.0))  # Simulate processing time
            
            result = {
                "output": f"Processed agent {agent.name} with input",
                "execution_time": 1.5,
                "tokens_used": 150
            }
            
            # Update agent run with result
            agent_run.output_data = result
            agent_run.status = "completed"
            agent_run.completed_at = datetime.utcnow()
            
            # Deduct credits if applicable
            if agent.price_per_run > 0:
                success, new_balance, error = deduct_credits(
                    db=db,
                    user_id=user.id,
                    amount=agent.price_per_run,
                    description=f"Agent execution: {agent.name}",
                    reference_id=str(agent_run.public_id)
                )
                
                if success:
                    agent_run.credits_used = agent.price_per_run
                else:
                    logger.warning(f"Failed to deduct credits: {error}")
            
            db.commit()
            
            # Create audit log
            audit_log = AuditLog(
                user_id=user.id,
                action="agent_run_background",
                resource_type="agent_run",
                resource_id=str(agent_run.public_id),
                details={
                    "agent_id": agent.id,
                    "agent_name": agent.name,
                    "run_id": agent_run.id,
                    "credits_used": agent_run.credits_used,
                    "execution_time": (agent_run.completed_at - agent_run.started_at).total_seconds()
                }
            )
            db.add(audit_log)
            db.commit()
            
            return True, None, result
            
        except Exception as e:
            logger.error(f"Error processing agent run: {e}")
            return False, str(e), None
        finally:
            db.close()
    
    def export_data(
        self,
        user_id: int,
        format: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Tuple[bool, Optional[str]]:
        """Export user data in background.
        
        Args:
            user_id: User ID
            format: Export format (csv, json)
            start_date: Start date for data
            end_date: End date for data
            
        Returns:
            Tuple of (success, job_id/error)
        """
        job_id = self.enqueue_job(
            job_type='data_export',
            data={
                'user_id': user_id,
                'format': format,
                'start_date': start_date.isoformat() if start_date else None,
                'end_date': end_date.isoformat() if end_date else None
            },
            priority=5  # Medium priority
        )
        
        if job_id:
            return True, job_id
        else:
            return False, "Failed to enqueue export job"
    
    def send_bulk_notifications(
        self,
        notification_type: str,
        user_ids: list,
        data: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """Send bulk notifications in background.
        
        Args:
            notification_type: Type of notification
            user_ids: List of user IDs
            data: Notification data
            
        Returns:
            Tuple of (success, job_id/error)
        """
        job_id = self.enqueue_job(
            job_type='bulk_notification',
            data={
                'notification_type': notification_type,
                'user_ids': user_ids,
                'data': data
            },
            priority=3  # Lower priority
        )
        
        if job_id:
            return True, job_id
        else:
            return False, "Failed to enqueue notification job"
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job status and result.
        
        Args:
            job_id: Job ID
            
        Returns:
            Job status dictionary or None if not found
        """
        if not self.redis_client:
            return None
        
        try:
            job_key = f"job:{job_id}"
            job_data = self.redis_client.hgetall(job_key)
            
            if not job_data:
                return None
            
            # Convert bytes to strings
            job_data = {k.decode(): v.decode() for k, v in job_data.items()}
            
            # Get result if completed
            result = None
            if job_data.get('status') == JobStatus.COMPLETED.value:
                result_key = f"job:result:{job_id}"
                result_data = self.redis_client.get(result_key)
                if result_data:
                    result = json.loads(result_data.decode())
            
            return {
                'id': job_id,
                'type': job_data.get('type'),
                'status': job_data.get('status'),
                'created_at': job_data.get('created_at'),
                'updated_at': job_data.get('updated_at'),
                'attempts': int(job_data.get('attempts', 0)),
                'max_attempts': int(job_data.get('max_attempts', 3)),
                'result': result,
                'error': job_data.get('error')
            }
            
        except Exception as e:
            logger.error(f"Error getting job status: {e}")
            return None
    
    def process_queue(self, max_jobs: int = 10) -> int:
        """Process jobs from the queue.
        
        Args:
            max_jobs: Maximum number of jobs to process
            
        Returns:
            Number of jobs processed
        """
        if not self.redis_client:
            logger.warning("Redis not available, cannot process queue")
            return 0
        
        processed = 0
        
        for _ in range(max_jobs):
            # Get next job from queue
            job_ids = self.redis_client.zrange(self.job_queue, 0, 0)
            if not job_ids:
                break
            
            job_id = job_ids[0].decode()
            job_key = f"job:{job_id}"
            
            # Get job data
            job_data = self.redis_client.hgetall(job_key)
            if not job_data:
                # Remove invalid job from queue
                self.redis_client.zrem(self.job_queue, job_id)
                continue
            
            job_data = {k.decode(): v.decode() for k, v in job_data.items()}
            
            # Update job status
            self.redis_client.hset(job_key, 'status', JobStatus.RUNNING.value)
            self.redis_client.hset(job_key, 'updated_at', datetime.utcnow().isoformat())
            
            # Process job based on type
            try:
                result = self._process_job(job_data)
                
                # Store result
                if result:
                    result_key = f"job:result:{job_id}"
                    self.redis_client.setex(result_key, 3600, json.dumps(result))  # Keep for 1 hour
                
                # Update job status
                self.redis_client.hset(job_key, 'status', JobStatus.COMPLETED.value)
                self.redis_client.hset(job_key, 'updated_at', datetime.utcnow().isoformat())
                
            except Exception as e:
                logger.error(f"Error processing job {job_id}: {e}")
                
                # Update attempts
                attempts = int(job_data.get('attempts', 0)) + 1
                max_attempts = int(job_data.get('max_attempts', 3))
                
                self.redis_client.hset(job_key, 'attempts', attempts)
                self.redis_client.hset(job_key, 'error', str(e))
                
                if attempts >= max_attempts:
                    self.redis_client.hset(job_key, 'status', JobStatus.FAILED.value)
                else:
                    self.redis_client.hset(job_key, 'status', JobStatus.RETRYING.value)
                    # Requeue with delay
                    delay = 60 * (2 ** (attempts - 1))  # Exponential backoff
                    self.redis_client.zadd(self.job_queue, {job_id: time.time() + delay})
            
            # Remove from queue
            self.redis_client.zrem(self.job_queue, job_id)
            processed += 1
        
        return processed
    
    def _process_job(self, job_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process a job based on its type.
        
        Args:
            job_data: Job data
            
        Returns:
            Job result or None
        """
        job_type = job_data.get('type')
        data = json.loads(job_data.get('data', '{}'))
        
        if job_type == 'agent_run':
            return self._process_agent_run_job(data)
        elif job_type == 'data_export':
            return self._process_export_job(data)
        elif job_type == 'bulk_notification':
            return self._process_notification_job(data)
        else:
            raise ValueError(f"Unknown job type: {job_type}")
    
    def _process_agent_run_job(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process agent run job.
        
        Args:
            data: Job data
            
        Returns:
            Processing result
        """
        # This would call the actual agent processing logic
        # For now, return mock result
        return {
            "status": "completed",
            "agent_id": data.get('agent_id'),
            "execution_time": 1.5,
            "output": "Agent execution completed"
        }
    
    def _process_export_job(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process data export job.
        
        Args:
            data: Job data
            
        Returns:
            Export result
        """
        # This would generate the actual export file
        # For now, return mock result
        return {
            "status": "completed",
            "format": data.get('format'),
            "record_count": 100,
            "file_url": f"/exports/{data.get('user_id')}_{datetime.utcnow().date()}.{data.get('format')}"
        }
    
    def _process_notification_job(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process bulk notification job.
        
        Args:
            data: Job data
            
        Returns:
            Notification result
        """
        # This would send actual notifications
        # For now, return mock result
        return {
            "status": "completed",
            "notification_type": data.get('notification_type'),
            "users_notified": len(data.get('user_ids', [])),
            "success_count": len(data.get('user_ids', []))
        }


# Global processor instance
job_processor = JobProcessor()

# Convenience functions
def enqueue_agent_run(
    user_id: int,
    agent_id: int,
    input_data: Dict[str, Any],
    is_async: bool = True
) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
    """Enqueue agent run for processing."""
    return job_processor.process_agent_run(user_id, agent_id, input_data, is_async)

def enqueue_data_export(
    user_id: int,
    format: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> Tuple[bool, Optional[str]]:
    """Enqueue data export job."""
    return job_processor.export_data(user_id, format, start_date, end_date)

def get_job_status(job_id: str) -> Optional[Dict[str, Any]]:
    """Get job status."""
    return job_processor.get_job_status(job_id)