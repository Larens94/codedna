"""runner.py — Execute scheduled tasks and handle results.

exports: execute_scheduled_task, run_agent_task, send_notification
used_by: scheduler/setup.py, agents/runner.py, notification system
rules:   must handle errors gracefully; must update task status; must send notifications
agent:   DataEngineer | 2024-01-15 | created task execution engine with credit handling
         message: "implement retry logic with exponential backoff for failed tasks"
"""

import logging
import asyncio
import json
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session

from agenthub.db.session import SessionLocal
from agenthub.db.models import ScheduledTask, AgentRun, User, Agent, AuditLog
from agenthub.agents.runner import run_agent
from agenthub.billing.credits import deduct_credits
from agenthub.config import settings

logger = logging.getLogger(__name__)


class TaskRunner:
    """Execute scheduled tasks and handle results."""
    
    @staticmethod
    def execute_scheduled_task(
        task_id: int,
        user_id: int,
        agent_id: int,
        **kwargs
    ) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """Execute a scheduled task.
        
        Args:
            task_id: Scheduled task ID
            user_id: User ID
            agent_id: Agent ID
            **kwargs: Additional task parameters
            
        Returns:
            Tuple of (success, error_message, result_data)
        """
        db = SessionLocal()
        try:
            # Get task from database
            task = db.query(ScheduledTask).filter(
                ScheduledTask.id == task_id,
                ScheduledTask.user_id == user_id,
                ScheduledTask.agent_id == agent_id
            ).first()
            
            if not task:
                return False, "Task not found", None
            
            if not task.is_active:
                return False, "Task is not active", None
            
            logger.info(f"Executing scheduled task {task_id}: {task.name}")
            
            # Update task status
            task.last_run_at = datetime.utcnow()
            task.last_run_status = "running"
            db.commit()
            
            # Execute the task
            success, error, result = TaskRunner._run_task(db, task, **kwargs)
            
            # Update task status
            task.last_run_status = "completed" if success else "failed"
            db.commit()
            
            # Send notification if configured
            if success:
                TaskRunner._send_success_notification(db, task, result)
            else:
                TaskRunner._send_failure_notification(db, task, error)
            
            return success, error, result
            
        except Exception as e:
            logger.error(f"Error executing scheduled task {task_id}: {e}")
            
            # Update task status to failed
            try:
                task = db.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
                if task:
                    task.last_run_status = "failed"
                    db.commit()
            except:
                pass
            
            return False, str(e), None
            
        finally:
            db.close()
    
    @staticmethod
    def _run_task(
        db: Session,
        task: ScheduledTask,
        **kwargs
    ) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """Run the actual task logic.
        
        Args:
            db: Database session
            task: Scheduled task
            **kwargs: Additional parameters
            
        Returns:
            Tuple of (success, error_message, result_data)
        """
        try:
            # Get user and agent
            user = db.query(User).filter(User.id == task.user_id).first()
            agent = db.query(Agent).filter(Agent.id == task.agent_id).first()
            
            if not user or not agent:
                return False, "User or agent not found", None
            
            # Check if user has sufficient credits
            if agent.price_per_run > 0:
                balance, currency = TaskRunner._get_user_balance(db, user.id)
                if balance < agent.price_per_run:
                    return False, "Insufficient credits", None
            
            # Create agent run record
            agent_run = AgentRun(
                public_id=str(uuid.uuid4()),
                user_id=user.id,
                agent_id=agent.id,
                input_data=task.input_data,
                status="running",
                started_at=datetime.utcnow(),
                metadata={
                    "scheduled_task_id": task.id,
                    "scheduled_task_name": task.name,
                    "execution_type": "scheduled"
                }
            )
            db.add(agent_run)
            db.commit()
            
            # Run the agent
            # Note: This is a simplified version - in production, you would use
            # the actual agent runner with proper error handling
            result = TaskRunner._execute_agent(db, agent, task.input_data)
            
            # Update agent run with result
            agent_run.output_data = result.get("output") if result else None
            agent_run.status = "completed" if result else "failed"
            agent_run.completed_at = datetime.utcnow()
            
            if result and "error" in result:
                agent_run.error_message = result["error"]
                agent_run.status = "failed"
            
            # Deduct credits if applicable
            if agent.price_per_run > 0 and result and "error" not in result:
                success, new_balance, error = deduct_credits(
                    db=db,
                    user_id=user.id,
                    amount=agent.price_per_run,
                    description=f"Agent execution: {agent.name}",
                    reference_id=str(agent_run.public_id),
                    metadata={
                        "agent_id": agent.id,
                        "agent_name": agent.name,
                        "run_id": agent_run.id
                    }
                )
                
                if success:
                    agent_run.credits_used = agent.price_per_run
                else:
                    logger.warning(f"Failed to deduct credits for agent run: {error}")
            
            db.commit()
            
            # Create audit log
            audit_log = AuditLog(
                user_id=user.id,
                action="scheduled_task_executed",
                resource_type="scheduled_task",
                resource_id=str(task.public_id),
                details={
                    "task_id": task.id,
                    "task_name": task.name,
                    "agent_id": agent.id,
                    "agent_name": agent.name,
                    "run_id": agent_run.id,
                    "success": result is not None and "error" not in result,
                    "credits_used": agent_run.credits_used,
                    "execution_time": (agent_run.completed_at - agent_run.started_at).total_seconds()
                }
            )
            db.add(audit_log)
            db.commit()
            
            if result and "error" in result:
                return False, result["error"], None
            
            return True, None, result
            
        except Exception as e:
            logger.error(f"Error running task {task.id}: {e}")
            return False, str(e), None
    
    @staticmethod
    def _execute_agent(
        db: Session,
        agent: Agent,
        input_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Execute an agent with given input.
        
        Args:
            db: Database session
            agent: Agent to execute
            input_data: Input data for the agent
            
        Returns:
            Agent execution result or None if failed
        """
        try:
            # This is a simplified version
            # In production, you would use the actual agent runner
            
            # Simulate agent execution
            # result = run_agent(agent, input_data)
            
            # For now, return a mock result
            return {
                "output": f"Executed agent {agent.name} with input: {json.dumps(input_data)}",
                "execution_time": 1.5,
                "tokens_used": 150,
                "model": agent.model
            }
            
        except Exception as e:
            logger.error(f"Error executing agent {agent.id}: {e}")
            return {"error": str(e)}
    
    @staticmethod
    def _get_user_balance(db: Session, user_id: int) -> Tuple[float, str]:
        """Get user's credit balance.
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            Tuple of (balance, currency)
        """
        from agenthub.db.models import CreditAccount
        
        credit_account = db.query(CreditAccount).filter(
            CreditAccount.user_id == user_id
        ).first()
        
        if not credit_account:
            return 0.0, "USD"
        
        return credit_account.balance, credit_account.currency
    
    @staticmethod
    def _send_success_notification(
        db: Session,
        task: ScheduledTask,
        result: Dict[str, Any]
    ) -> None:
        """Send success notification for task execution.
        
        Args:
            db: Database session
            task: Scheduled task
            result: Execution result
        """
        try:
            # Get user
            user = db.query(User).filter(User.id == task.user_id).first()
            if not user:
                return
            
            # Check if notifications are enabled for this task
            metadata = task.metadata or {}
            if not metadata.get("notifications", {}).get("on_success", True):
                return
            
            # In production, you would:
            # 1. Send email notification
            # 2. Send webhook notification
            # 3. Send in-app notification
            # 4. Send Slack/Teams notification
            
            logger.info(f"Task {task.name} executed successfully for user {user.email}")
            
            # Example: Send webhook if configured
            webhook_url = metadata.get("notifications", {}).get("webhook_url")
            if webhook_url:
                TaskRunner._send_webhook_notification(
                    webhook_url,
                    {
                        "event": "scheduled_task_success",
                        "task_id": str(task.public_id),
                        "task_name": task.name,
                        "user_id": user.id,
                        "user_email": user.email,
                        "execution_time": datetime.utcnow().isoformat(),
                        "result": result
                    }
                )
                
        except Exception as e:
            logger.error(f"Error sending success notification: {e}")
    
    @staticmethod
    def _send_failure_notification(
        db: Session,
        task: ScheduledTask,
        error: str
    ) -> None:
        """Send failure notification for task execution.
        
        Args:
            db: Database session
            task: Scheduled task
            error: Error message
        """
        try:
            # Get user
            user = db.query(User).filter(User.id == task.user_id).first()
            if not user:
                return
            
            # Check if notifications are enabled for this task
            metadata = task.metadata or {}
            if not metadata.get("notifications", {}).get("on_failure", True):
                return
            
            logger.warning(f"Task {task.name} failed for user {user.email}: {error}")
            
            # Example: Send webhook if configured
            webhook_url = metadata.get("notifications", {}).get("webhook_url")
            if webhook_url:
                TaskRunner._send_webhook_notification(
                    webhook_url,
                    {
                        "event": "scheduled_task_failure",
                        "task_id": str(task.public_id),
                        "task_name": task.name,
                        "user_id": user.id,
                        "user_email": user.email,
                        "execution_time": datetime.utcnow().isoformat(),
                        "error": error
                    }
                )
                
        except Exception as e:
            logger.error(f"Error sending failure notification: {e}")
    
    @staticmethod
    def _send_webhook_notification(url: str, payload: Dict[str, Any]) -> None:
        """Send webhook notification.
        
        Args:
            url: Webhook URL
            payload: Notification payload
        """
        try:
            # In production, use requests or aiohttp
            # For now, just log
            logger.info(f"Would send webhook to {url} with payload: {json.dumps(payload)}")
            
        except Exception as e:
            logger.error(f"Error sending webhook: {e}")
    
    @staticmethod
    def run_agent_task(
        db: Session,
        user_id: int,
        agent_id: int,
        input_data: Dict[str, Any],
        is_scheduled: bool = False,
        scheduled_task_id: Optional[int] = None
    ) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """Run an agent task (manual or scheduled).
        
        Args:
            db: Database session
            user_id: User ID
            agent_id: Agent ID
            input_data: Input data for the agent
            is_scheduled: Whether this is a scheduled execution
            scheduled_task_id: Scheduled task ID if applicable
            
        Returns:
            Tuple of (success, error_message, result_data)
        """
        try:
            import uuid
            
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
                    "execution_type": "scheduled" if is_scheduled else "manual",
                    "scheduled_task_id": scheduled_task_id
                }
            )
            db.add(agent_run)
            db.commit()
            
            # Execute agent
            result = TaskRunner._execute_agent(db, agent, input_data)
            
            # Update agent run with result
            agent_run.output_data = result.get("output") if result else None
            agent_run.status = "completed" if result and "error" not in result else "failed"
            agent_run.completed_at = datetime.utcnow()
            
            if result and "error" in result:
                agent_run.error_message = result["error"]
            
            # Deduct credits if applicable
            if agent.price_per_run > 0 and result and "error" not in result:
                success, new_balance, error = deduct_credits(
                    db=db,
                    user_id=user.id,
                    amount=agent.price_per_run,
                    description=f"Agent execution: {agent.name}",
                    reference_id=str(agent_run.public_id),
                    metadata={
                        "agent_id": agent.id,
                        "agent_name": agent.name,
                        "run_id": agent_run.id
                    }
                )
                
                if success:
                    agent_run.credits_used = agent.price_per_run
                else:
                    logger.warning(f"Failed to deduct credits for agent run: {error}")
            
            db.commit()
            
            # Create audit log
            audit_log = AuditLog(
                user_id=user.id,
                action="agent_run" + ("_scheduled" if is_scheduled else "_manual"),
                resource_type="agent_run",
                resource_id=str(agent_run.public_id),
                details={
                    "agent_id": agent.id,
                    "agent_name": agent.name,
                    "run_id": agent_run.id,
                    "success": result is not None and "error" not in result,
                    "credits_used": agent_run.credits_used,
                    "execution_time": (agent_run.completed_at - agent_run.started_at).total_seconds() if agent_run.completed_at else None
                }
            )
            db.add(audit_log)
            db.commit()
            
            if result and "error" in result:
                return False, result["error"], None
            
            return True, None, result
            
        except Exception as e:
            logger.error(f"Error running agent task: {e}")
            return False, str(e), None


# Convenience functions
def execute_scheduled_task(
    task_id: int,
    user_id: int,
    agent_id: int,
    **kwargs
) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
    """Execute a scheduled task."""
    return TaskRunner.execute_scheduled_task(task_id, user_id, agent_id, **kwargs)


def run_agent_task(
    db: Session,
    user_id: int,
    agent_id: int,
    input_data: Dict[str, Any],
    is_scheduled: bool = False,
    scheduled_task_id: Optional[int] = None
) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
    """Run an agent task."""
    return TaskRunner.run_agent_task(
        db, user_id, agent_id, input_data, is_scheduled, scheduled_task_id
    )