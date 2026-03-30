"""Agent-related Celery tasks."""

import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from celery import group, chain
from sqlalchemy import and_

from app.tasks import celery_app
from app import db
from app.models.agent import AgentRun, AgentRunStatus, Agent
from app.models.user import User
from app.integrations.agno import AgentExecutor, AgnoClient


logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3)
def execute_agent_run(self, run_id: int) -> Dict[str, Any]:
    """Execute an agent run asynchronously.
    
    Args:
        run_id: AgentRun ID
        
    Returns:
        Execution result
    """
    from app import create_app
    app = create_app()
    
    with app.app_context():
        try:
            # Get agent run
            agent_run = AgentRun.query.get(run_id)
            if not agent_run:
                raise ValueError(f'AgentRun {run_id} not found')
            
            # Check if already completed
            if agent_run.status != AgentRunStatus.PENDING:
                logger.warning(f'AgentRun {run_id} is already {agent_run.status.value}')
                return {'status': 'already_processed', 'run_id': run_id}
            
            # Execute agent
            executor = AgentExecutor()
            executor.execute_agent_run(agent_run)
            
            # Save to database
            db.session.commit()
            
            logger.info(f'Successfully executed AgentRun {run_id}')
            return {
                'status': 'success',
                'run_id': run_id,
                'execution_time_ms': agent_run.execution_time_ms,
                'cost_usd': float(agent_run.cost_usd) if agent_run.cost_usd else 0.0,
            }
            
        except Exception as exc:
            logger.error(f'Failed to execute AgentRun {run_id}: {exc}')
            
            # Update run status
            if 'agent_run' in locals():
                agent_run.status = AgentRunStatus.FAILED
                agent_run.error_message = str(exc)
                db.session.commit()
            
            # Retry with exponential backoff
            self.retry(exc=exc, countdown=60 * self.request.retries)
            
            return {'status': 'error', 'run_id': run_id, 'error': str(exc)}


@celery_app.task
def batch_execute_agent_runs(run_ids: list) -> Dict[str, Any]:
    """Execute multiple agent runs in parallel.
    
    Args:
        run_ids: List of AgentRun IDs
        
    Returns:
        Batch execution results
    """
    # Create a group of tasks
    job = group(execute_agent_run.s(run_id) for run_id in run_ids)
    result = job.apply_async()
    
    return {
        'task_id': result.id,
        'run_count': len(run_ids),
        'status': 'started'
    }


@celery_app.task
def cleanup_old_agent_runs(days_old: int = 30) -> Dict[str, Any]:
    """Clean up old agent runs and logs.
    
    Args:
        days_old: Delete runs older than this many days
        
    Returns:
        Cleanup results
    """
    from app import create_app
    app = create_app()
    
    with app.app_context():
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        
        # Find old completed/failed runs
        old_runs = AgentRun.query.filter(
            and_(
                AgentRun.created_at < cutoff_date,
                AgentRun.status.in_([AgentRunStatus.COMPLETED, AgentRunStatus.FAILED, AgentRunStatus.TIMEOUT])
            )
        ).all()
        
        run_count = len(old_runs)
        
        # Delete associated logs first (cascade should handle this, but being explicit)
        for run in old_runs:
            # Delete logs
            for log in run.logs:
                db.session.delete(log)
            # Delete run
            db.session.delete(run)
        
        db.session.commit()
        
        logger.info(f'Cleaned up {run_count} old agent runs')
        
        return {
            'status': 'success',
            'runs_deleted': run_count,
            'cutoff_date': cutoff_date.isoformat()
        }


@celery_app.task
def update_agent_statistics() -> Dict[str, Any]:
    """Update agent statistics (run counts, ratings, etc.).
    
    Returns:
        Update results
    """
    from app import create_app
    app = create_app()
    
    with app.app_context():
        agents_updated = 0
        
        for agent in Agent.query.all():
            # Store old values for comparison
            old_run_count = agent.run_count
            old_review_count = agent.review_count
            old_average_rating = agent.average_rating
            
            # Update counters
            agent.update_counters()
            
            # Check if any values changed
            if (agent.run_count != old_run_count or 
                agent.review_count != old_review_count or
                agent.average_rating != old_average_rating):
                agents_updated += 1
        
        db.session.commit()
        
        logger.info(f'Updated statistics for {agents_updated} agents')
        
        return {
            'status': 'success',
            'agents_updated': agents_updated,
            'total_agents': Agent.query.count()
        }


@celery_app.task
def check_agent_health() -> Dict[str, Any]:
    """Check health of all agents in Agno.
    
    Returns:
        Health check results
    """
    from app import create_app
    app = create_app()
    
    with app.app_context():
        agno_client = AgnoClient()
        unhealthy_agents = []
        
        for agent in Agent.query.filter_by(status='published').all():
            try:
                # Get latest active version
                active_version = next(
                    (v for v in agent.versions if v.is_active), 
                    None
                )
                
                if not active_version:
                    unhealthy_agents.append({
                        'agent_id': agent.id,
                        'name': agent.name,
                        'error': 'No active version'
                    })
                    continue
                
                # Check agent status in Agno
                status = agno_client.get_agent_status(active_version.agno_agent_id)
                
                if status.get('status') != 'active':
                    unhealthy_agents.append({
                        'agent_id': agent.id,
                        'name': agent.name,
                        'error': f"Agent status: {status.get('status')}"
                    })
                    
            except Exception as e:
                unhealthy_agents.append({
                    'agent_id': agent.id,
                    'name': agent.name,
                    'error': str(e)
                })
        
        logger.info(f'Health check complete: {len(unhealthy_agents)} unhealthy agents')
        
        return {
            'status': 'completed',
            'unhealthy_agents': unhealthy_agents,
            'total_checked': Agent.query.filter_by(status='published').count()
        }


@celery_app.task
def process_scheduled_agent_runs() -> Dict[str, Any]:
    """Process scheduled agent runs.
    
    Returns:
        Processing results
    """
    # This would process runs scheduled for specific times
    # Implementation depends on scheduling requirements
    
    return {
        'status': 'not_implemented',
        'message': 'Scheduled runs not yet implemented'
    }