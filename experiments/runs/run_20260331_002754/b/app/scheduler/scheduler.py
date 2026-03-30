"""Task scheduler using APScheduler."""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR

from app.core.config import settings
from app import db
from app.models.scheduled_task import ScheduledTask, TaskStatus, TaskRecurrence
from app.scheduler.task_runner import TaskRunner

logger = logging.getLogger(__name__)


class TaskScheduler:
    """Task scheduler for managing recurring agent executions."""
    
    def __init__(self, db_session=None):
        """Initialize task scheduler.
        
        Args:
            db_session: SQLAlchemy database session (optional)
        """
        self.db = db_session
        self.scheduler = None
        self.task_runner = TaskRunner(db_session)
        self._initialize_scheduler()
    
    def _initialize_scheduler(self) -> None:
        """Initialize APScheduler with SQLAlchemy job store."""
        # Configure job store
        jobstores = {
            'default': SQLAlchemyJobStore(
                url=settings.DATABASE_URL,
                engine_options={
                    'pool_recycle': settings.DATABASE_POOL_RECYCLE,
                    'pool_pre_ping': settings.DATABASE_POOL_PRE_PING,
                }
            )
        }
        
        # Create scheduler
        self.scheduler = BackgroundScheduler(
            jobstores=jobstores,
            timezone='UTC',
            daemon=True,
        )
        
        # Add event listeners
        self.scheduler.add_listener(self._job_executed, EVENT_JOB_EXECUTED)
        self.scheduler.add_listener(self._job_error, EVENT_JOB_ERROR)
        
        logger.info("Task scheduler initialized")
    
    def start(self) -> None:
        """Start the scheduler."""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Task scheduler started")
            
            # Load existing scheduled tasks
            self._load_existing_tasks()
    
    def shutdown(self) -> None:
        """Shutdown the scheduler."""
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Task scheduler shutdown")
    
    def _load_existing_tasks(self) -> None:
        """Load existing scheduled tasks from database."""
        try:
            # Get all active scheduled tasks
            tasks = self.db.query(ScheduledTask).filter_by(
                status=TaskStatus.ACTIVE
            ).all()
            
            for task in tasks:
                if task.next_run_at and task.next_run_at > datetime.utcnow():
                    self._schedule_task(task)
            
            logger.info(f"Loaded {len(tasks)} existing scheduled tasks")
            
        except Exception as e:
            logger.error(f"Failed to load existing tasks: {e}")
    
    def _schedule_task(self, task: ScheduledTask) -> None:
        """Schedule a task in APScheduler.
        
        Args:
            task: ScheduledTask instance
        """
        job_id = f"scheduled_task_{task.id}"
        
        # Remove existing job if present
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
        
        # Determine trigger based on recurrence
        trigger = self._create_trigger(task)
        if not trigger:
            logger.warning(f"Cannot schedule task {task.id}: invalid recurrence")
            return
        
        # Add job to scheduler
        job = self.scheduler.add_job(
            func=self._execute_scheduled_task,
            trigger=trigger,
            args=[task.id],
            id=job_id,
            name=task.name,
            replace_existing=True,
            misfire_grace_time=300,  # 5 minutes grace period
            coalesce=True,  # Combine multiple missed runs
        )
        
        logger.info(f"Scheduled task {task.id} ({task.name}) with trigger {trigger}")
    
    def _create_trigger(self, task: ScheduledTask):
        """Create APScheduler trigger for task.
        
        Args:
            task: ScheduledTask instance
            
        Returns:
            APScheduler trigger or None if invalid
        """
        if task.recurrence == TaskRecurrence.ONCE:
            if task.next_run_at:
                return DateTrigger(run_date=task.next_run_at)
            return None
        
        elif task.recurrence == TaskRecurrence.CRON:
            if task.cron_expression:
                try:
                    return CronTrigger.from_crontab(task.cron_expression)
                except Exception as e:
                    logger.error(f"Invalid cron expression for task {task.id}: {task.cron_expression}")
                    return None
            return None
        
        elif task.recurrence == TaskRecurrence.HOURLY:
            if task.interval_seconds:
                return IntervalTrigger(seconds=task.interval_seconds)
            return IntervalTrigger(hours=1)
        
        elif task.recurrence == TaskRecurrence.DAILY:
            if task.interval_seconds:
                return IntervalTrigger(seconds=task.interval_seconds)
            return IntervalTrigger(days=1)
        
        elif task.recurrence == TaskRecurrence.WEEKLY:
            if task.interval_seconds:
                return IntervalTrigger(seconds=task.interval_seconds)
            return IntervalTrigger(weeks=1)
        
        elif task.recurrence == TaskRecurrence.MONTHLY:
            if task.interval_seconds:
                return IntervalTrigger(seconds=task.interval_seconds)
            # APScheduler doesn't have monthly interval, use cron
            return CronTrigger(day=task.next_run_at.day, hour=task.next_run_at.hour, minute=task.next_run_at.minute)
        
        return None
    
    def _execute_scheduled_task(self, task_id: int) -> None:
        """Execute a scheduled task.
        
        Args:
            task_id: ScheduledTask ID
        """
        try:
            # Get fresh database session for this execution
            from app.database import get_scoped_session
            session = get_scoped_session()
            
            # Get task
            task = session.query(ScheduledTask).get(task_id)
            if not task or task.status != TaskStatus.ACTIVE:
                logger.warning(f"Task {task_id} not found or not active")
                return
            
            # Update task as running
            task.mark_as_running()
            session.commit()
            
            # Execute task
            result = self.task_runner.execute_task(task)
            
            # Update task with result
            task.update_run_result(
                status='success' if result.get('success') else 'failed',
                result=result,
            )
            
            # Reschedule if needed
            if task.status == TaskStatus.ACTIVE and task.next_run_at:
                self._schedule_task(task)
            
            logger.info(f"Executed scheduled task {task_id} with result: {result.get('success')}")
            
        except Exception as e:
            logger.error(f"Failed to execute scheduled task {task_id}: {e}")
            
            # Update task with error
            try:
                task.update_run_result(
                    status='failed',
                    result={'error': str(e)},
                )
            except Exception:
                pass
    
    def _job_executed(self, event):
        """Handle job executed event.
        
        Args:
            event: APScheduler event
        """
        logger.debug(f"Job executed: {event.job_id} (retval: {event.retval})")
    
    def _job_error(self, event):
        """Handle job error event.
        
        Args:
            event: APScheduler event
        """
        logger.error(f"Job error: {event.job_id} (exception: {event.exception})")
    
    def create_scheduled_task(
        self,
        user_id: int,
        agent_id: int,
        name: str,
        recurrence: TaskRecurrence,
        cron_expression: Optional[str] = None,
        interval_seconds: Optional[int] = None,
        next_run_at: Optional[datetime] = None,
        parameters: Optional[Dict[str, Any]] = None,
        organization_id: Optional[int] = None,
        description: Optional[str] = None,
    ) -> Optional[ScheduledTask]:
        """Create a new scheduled task.
        
        Args:
            user_id: User ID
            agent_id: Agent ID
            name: Task name
            recurrence: Recurrence pattern
            cron_expression: Cron expression (if recurrence is CRON)
            interval_seconds: Interval in seconds
            next_run_at: When to run next (defaults to now)
            parameters: Agent run parameters
            organization_id: Optional organization ID
            description: Task description
            
        Returns:
            ScheduledTask instance or None if failed
        """
        try:
            # Calculate next run time
            if not next_run_at:
                if recurrence == TaskRecurrence.ONCE:
                    next_run_at = datetime.utcnow()
                else:
                    next_run_at = datetime.utcnow() + timedelta(minutes=1)  # Start in 1 minute
            
            # Create task
            task = ScheduledTask(
                user_id=user_id,
                organization_id=organization_id,
                agent_id=agent_id,
                name=name,
                description=description,
                status=TaskStatus.ACTIVE,
                recurrence=recurrence,
                cron_expression=cron_expression,
                interval_seconds=interval_seconds,
                next_run_at=next_run_at,
                parameters=parameters or {},
            )
            
            self.db.add(task)
            self.db.commit()
            self.db.refresh(task)
            
            # Schedule task
            self._schedule_task(task)
            
            logger.info(f"Created scheduled task {task.id}: {name}")
            return task
            
        except Exception as e:
            logger.error(f"Failed to create scheduled task: {e}")
            self.db.rollback()
            return None
    
    def update_scheduled_task(self, task_id: int, updates: Dict[str, Any]) -> bool:
        """Update an existing scheduled task.
        
        Args:
            task_id: ScheduledTask ID
            updates: Dictionary of updates
            
        Returns:
            True if successful, False otherwise
        """
        try:
            task = self.db.query(ScheduledTask).get(task_id)
            if not task:
                return False
            
            # Update fields
            for key, value in updates.items():
                if hasattr(task, key):
                    setattr(task, key, value)
            
            task.updated_at = datetime.utcnow()
            
            # Reschedule if active
            if task.status == TaskStatus.ACTIVE:
                self._schedule_task(task)
            
            self.db.commit()
            logger.info(f"Updated scheduled task {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update scheduled task {task_id}: {e}")
            self.db.rollback()
            return False
    
    def delete_scheduled_task(self, task_id: int) -> bool:
        """Delete a scheduled task.
        
        Args:
            task_id: ScheduledTask ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            task = self.db.query(ScheduledTask).get(task_id)
            if not task:
                return False
            
            # Remove from scheduler
            job_id = f"scheduled_task_{task_id}"
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
            
            # Delete from database
            self.db.delete(task)
            self.db.commit()
            
            logger.info(f"Deleted scheduled task {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete scheduled task {task_id}: {e}")
            self.db.rollback()
            return False
    
    def pause_scheduled_task(self, task_id: int) -> bool:
        """Pause a scheduled task.
        
        Args:
            task_id: ScheduledTask ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            task = self.db.query(ScheduledTask).get(task_id)
            if not task:
                return False
            
            task.status = TaskStatus.PAUSED
            task.updated_at = datetime.utcnow()
            
            # Remove from scheduler
            job_id = f"scheduled_task_{task_id}"
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
            
            self.db.commit()
            logger.info(f"Paused scheduled task {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to pause scheduled task {task_id}: {e}")
            self.db.rollback()
            return False
    
    def resume_scheduled_task(self, task_id: int) -> bool:
        """Resume a paused scheduled task.
        
        Args:
            task_id: ScheduledTask ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            task = self.db.query(ScheduledTask).get(task_id)
            if not task:
                return False
            
            task.status = TaskStatus.ACTIVE
            task.updated_at = datetime.utcnow()
            
            # Schedule task
            self._schedule_task(task)
            
            self.db.commit()
            logger.info(f"Resumed scheduled task {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to resume scheduled task {task_id}: {e}")
            self.db.rollback()
            return False
    
    def get_scheduled_tasks(
        self,
        user_id: Optional[int] = None,
        organization_id: Optional[int] = None,
        agent_id: Optional[int] = None,
        status: Optional[TaskStatus] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[ScheduledTask]:
        """Get scheduled tasks with filters.
        
        Args:
            user_id: Filter by user ID
            organization_id: Filter by organization ID
            agent_id: Filter by agent ID
            status: Filter by status
            limit: Maximum number of tasks to return
            offset: Offset for pagination
            
        Returns:
            List of ScheduledTask instances
        """
        query = self.db.query(ScheduledTask)
        
        if user_id:
            query = query.filter_by(user_id=user_id)
        
        if organization_id:
            query = query.filter_by(organization_id=organization_id)
        
        if agent_id:
            query = query.filter_by(agent_id=agent_id)
        
        if status:
            query = query.filter_by(status=status)
        
        tasks = query.order_by(ScheduledTask.created_at.desc()).offset(offset).limit(limit).all()
        return tasks
    
    def get_upcoming_tasks(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get upcoming scheduled tasks.
        
        Args:
            limit: Maximum number of tasks to return
            
        Returns:
            List of upcoming task information
        """
        tasks = self.db.query(ScheduledTask).filter(
            ScheduledTask.status == TaskStatus.ACTIVE,
            ScheduledTask.next_run_at > datetime.utcnow(),
        ).order_by(ScheduledTask.next_run_at).limit(limit).all()
        
        return [{
            'id': task.id,
            'name': task.name,
            'next_run_at': task.next_run_at.isoformat() if task.next_run_at else None,
            'agent_id': task.agent_id,
            'user_id': task.user_id,
        } for task in tasks]