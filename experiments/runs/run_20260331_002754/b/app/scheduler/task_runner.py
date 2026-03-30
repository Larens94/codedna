"""Task runner for executing scheduled agent runs."""

import logging
import json
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.scheduled_task import ScheduledTask, TaskRun
from app.models.agent_run import AgentRun, AgentRunStatus
from app.models.agent import Agent
from app.models.user import User
from app.models.usage_log import UsageLog, UsageType, ProviderType
from app.models.credit import CreditTransactionType
from app.billing.credit_engine import CreditEngine
from app.agents.runner import AgentRunner

logger = logging.getLogger(__name__)


class TaskRunnerError(Exception):
    """Base exception for task runner errors."""
    pass


class TaskRunner:
    """Task runner for executing scheduled agent runs."""
    
    def __init__(self, db_session: Session):
        """Initialize task runner.
        
        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session
        self.credit_engine = CreditEngine(db_session)
    
    def execute_task(self, scheduled_task: ScheduledTask) -> Dict[str, Any]:
        """Execute a scheduled task.
        
        Args:
            scheduled_task: ScheduledTask instance
            
        Returns:
            Execution result
        """
        task_run = None
        agent_run = None
        
        try:
            # Create task run record
            task_run = TaskRun(
                scheduled_task_id=scheduled_task.id,
                started_at=datetime.utcnow(),
                status='running',
            )
            self.db.add(task_run)
            self.db.commit()
            
            # Get agent and user
            agent = self.db.query(Agent).get(scheduled_task.agent_id)
            if not agent:
                raise TaskRunnerError(f"Agent {scheduled_task.agent_id} not found")
            
            user = self.db.query(User).get(scheduled_task.user_id)
            if not user:
                raise TaskRunnerError(f"User {scheduled_task.user_id} not found")
            
            # Check if user has sufficient credits
            # TODO: Calculate estimated cost based on agent complexity
            estimated_cost = 10  # Default 10 credits per run
            
            available_credits = self.credit_engine.get_available_balance(
                scheduled_task.user_id,
                scheduled_task.organization_id,
            )
            
            if available_credits < estimated_cost:
                raise TaskRunnerError(
                    f"Insufficient credits: {available_credits} available, {estimated_cost} estimated required"
                )
            
            # Create agent run
            agent_run = AgentRun(
                user_id=scheduled_task.user_id,
                organization_id=scheduled_task.organization_id,
                agent_id=scheduled_task.agent_id,
                status=AgentRunStatus.PENDING,
                input_data=json.dumps(scheduled_task.get_parameters_dict()),
                created_at=datetime.utcnow(),
            )
            self.db.add(agent_run)
            self.db.commit()
            
            # Update task run with agent run ID
            task_run.agent_run_id = agent_run.id
            self.db.commit()
            
            # Execute agent (synchronous for now)
            # In production, this should be async via Celery
            result = self._execute_agent(agent, agent_run, scheduled_task)
            
            # Deduct credits for the run
            actual_cost = result.get('credits_used', estimated_cost)
            self.credit_engine.deduct(
                user_id=scheduled_task.user_id,
                amount=actual_cost,
                transaction_type=CreditTransactionType.AGENT_RUN,
                reference_id=agent_run.id,
                reference_type='agent_run',
                description=f"Scheduled task execution: {scheduled_task.name}",
                organization_id=scheduled_task.organization_id,
            )
            
            # Create usage log
            usage_log = UsageLog(
                user_id=scheduled_task.user_id,
                organization_id=scheduled_task.organization_id,
                agent_id=scheduled_task.agent_id,
                agent_run_id=agent_run.id,
                usage_type=UsageType.AGENT_RUN,
                provider=ProviderType.AGNO,
                model=agent.model or 'default',
                prompt_tokens=result.get('prompt_tokens', 0),
                completion_tokens=result.get('completion_tokens', 0),
                total_tokens=result.get('total_tokens', 0),
                credits_used=actual_cost,
                logged_at=datetime.utcnow(),
                metadata={
                    'scheduled_task_id': scheduled_task.id,
                    'task_run_id': task_run.id,
                    'execution_time': result.get('execution_time'),
                }
            )
            self.db.add(usage_log)
            
            # Update task run as completed
            task_run.completed_at = datetime.utcnow()
            task_run.status = 'success'
            task_run.result = {
                'agent_run_id': agent_run.id,
                'success': True,
                'execution_time': result.get('execution_time'),
                'credits_used': actual_cost,
            }
            
            self.db.commit()
            
            logger.info(f"Successfully executed scheduled task {scheduled_task.id}, agent run {agent_run.id}")
            
            return {
                'success': True,
                'agent_run_id': agent_run.id,
                'task_run_id': task_run.id,
                'credits_used': actual_cost,
                'execution_time': result.get('execution_time'),
            }
            
        except Exception as e:
            logger.error(f"Failed to execute scheduled task {scheduled_task.id}: {e}")
            
            # Update task run as failed
            if task_run:
                task_run.completed_at = datetime.utcnow()
                task_run.status = 'failed'
                task_run.error_message = str(e)
                task_run.result = {'error': str(e)}
                
                if agent_run:
                    agent_run.status = AgentRunStatus.FAILED
                    agent_run.completed_at = datetime.utcnow()
                    agent_run.error_message = str(e)
            
            try:
                self.db.commit()
            except Exception as commit_error:
                logger.error(f"Failed to commit error state: {commit_error}")
                self.db.rollback()
            
            return {
                'success': False,
                'error': str(e),
                'agent_run_id': agent_run.id if agent_run else None,
                'task_run_id': task_run.id if task_run else None,
            }
    
    def _execute_agent(self, agent: Agent, agent_run: AgentRun, scheduled_task: ScheduledTask) -> Dict[str, Any]:
        """Execute agent run.
        
        Args:
            agent: Agent instance
            agent_run: AgentRun instance
            scheduled_task: ScheduledTask instance
            
        Returns:
            Execution result
        """
        from app.agents.runner import AgentRunner
        
        # Update agent run status
        agent_run.status = AgentRunStatus.RUNNING
        self.db.commit()
        
        # Execute agent
        start_time = datetime.utcnow()
        
        try:
            # Parse input data
            input_data = {}
            if agent_run.input_data:
                input_data = json.loads(agent_run.input_data)
            
            # Merge with task parameters
            task_params = scheduled_task.get_parameters_dict()
            if task_params:
                input_data.update(task_params)
            
            # Create agent runner
            runner = AgentRunner(self.db)
            
            # Execute agent (simplified - actual implementation would use Agno API)
            # result = runner.run_agent(agent, input_data)
            
            # For now, simulate execution
            # TODO: Integrate with actual agent runner
            import time
            time.sleep(1)  # Simulate execution time
            
            # Simulate result
            result = {
                'output': f"Executed agent {agent.name} with parameters: {input_data}",
                'prompt_tokens': 100,
                'completion_tokens': 50,
                'total_tokens': 150,
                'success': True,
            }
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Update agent run with result
            agent_run.status = AgentRunStatus.COMPLETED
            agent_run.completed_at = datetime.utcnow()
            agent_run.output_data = json.dumps(result)
            agent_run.execution_time = execution_time
            
            self.db.commit()
            
            return {
                **result,
                'execution_time': execution_time,
                'credits_used': 15,  # Based on token usage
            }
            
        except Exception as e:
            logger.error(f"Agent execution failed: {e}")
            
            agent_run.status = AgentRunStatus.FAILED
            agent_run.completed_at = datetime.utcnow()
            agent_run.error_message = str(e)
            
            self.db.commit()
            raise TaskRunnerError(f"Agent execution failed: {e}")
    
    def execute_immediate_task(
        self,
        user_id: int,
        agent_id: int,
        parameters: Dict[str, Any],
        organization_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Execute an immediate (non-scheduled) task.
        
        Args:
            user_id: User ID
            agent_id: Agent ID
            parameters: Agent run parameters
            organization_id: Optional organization ID
            
        Returns:
            Execution result
        """
        try:
            # Create a one-time scheduled task
            scheduled_task = ScheduledTask(
                user_id=user_id,
                organization_id=organization_id,
                agent_id=agent_id,
                name=f"Immediate task for agent {agent_id}",
                status='active',
                recurrence='once',
                next_run_at=datetime.utcnow(),
                parameters=parameters,
            )
            
            self.db.add(scheduled_task)
            self.db.commit()
            
            # Execute immediately
            result = self.execute_task(scheduled_task)
            
            # Clean up the temporary task
            self.db.delete(scheduled_task)
            self.db.commit()
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to execute immediate task: {e}")
            self.db.rollback()
            return {'success': False, 'error': str(e)}
    
    def retry_task_run(self, task_run_id: int) -> Dict[str, Any]:
        """Retry a failed task run.
        
        Args:
            task_run_id: TaskRun ID
            
        Returns:
            Execution result
        """
        try:
            task_run = self.db.query(TaskRun).get(task_run_id)
            if not task_run:
                raise TaskRunnerError(f"Task run {task_run_id} not found")
            
            scheduled_task = task_run.scheduled_task
            if not scheduled_task:
                raise TaskRunnerError(f"Scheduled task for task run {task_run_id} not found")
            
            # Create new task run for retry
            new_task_run = TaskRun(
                scheduled_task_id=scheduled_task.id,
                started_at=datetime.utcnow(),
                status='running',
            )
            self.db.add(new_task_run)
            self.db.commit()
            
            # Execute task
            result = self.execute_task(scheduled_task)
            
            # Update new task run
            new_task_run.completed_at = datetime.utcnow()
            new_task_run.status = 'success' if result.get('success') else 'failed'
            new_task_run.result = result
            
            self.db.commit()
            
            return {
                **result,
                'task_run_id': new_task_run.id,
                'original_task_run_id': task_run_id,
            }
            
        except Exception as e:
            logger.error(f"Failed to retry task run {task_run_id}: {e}")
            self.db.rollback()
            return {'success': False, 'error': str(e)}