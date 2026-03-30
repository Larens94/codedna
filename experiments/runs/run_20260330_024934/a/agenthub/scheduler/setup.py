"""setup.py — APScheduler setup and job management.

exports: scheduler, add_scheduled_job, remove_scheduled_job, get_scheduled_jobs
used_by: main.py (startup), scheduler.py router, admin interface
rules:   must persist jobs to database; must handle timezone correctly; must be thread-safe
agent:   DataEngineer | 2024-01-15 | created APScheduler setup with SQLAlchemy job store
         message: "implement job recovery after server restart and cluster coordination"
"""

import logging
import atexit
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from uuid import uuid4

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_MISSED, EVENT_JOB_EXECUTED
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session

from agenthub.config import settings
from agenthub.db.session import engine
from agenthub.scheduler.runner import execute_scheduled_task

logger = logging.getLogger(__name__)


class SchedulerManager:
    """Manage APScheduler instance and job operations."""
    
    _instance = None
    _scheduler = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SchedulerManager, cls).__new__(cls)
            cls._instance._initialize_scheduler()
        return cls._instance
    
    def _initialize_scheduler(self):
        """Initialize APScheduler with SQLAlchemy job store."""
        try:
            # Configure job stores
            jobstores = {
                'default': SQLAlchemyJobStore(
                    engine=engine,
                    tablename='apscheduler_jobs'
                )
            }
            
            # Configure executors
            executors = {
                'default': ThreadPoolExecutor(20),
                'processpool': ProcessPoolExecutor(5)
            }
            
            # Configure job defaults
            job_defaults = {
                'coalesce': True,  # Combine multiple pending executions
                'max_instances': 3,  # Maximum concurrent instances per job
                'misfire_grace_time': 300  # 5 minutes grace period
            }
            
            # Create scheduler
            self._scheduler = BackgroundScheduler(
                jobstores=jobstores,
                executors=executors,
                job_defaults=job_defaults,
                timezone='UTC'  # Always use UTC for consistency
            )
            
            # Add event listeners
            self._scheduler.add_listener(
                self._job_executed_listener,
                EVENT_JOB_EXECUTED | EVENT_JOB_ERROR | EVENT_JOB_MISSED
            )
            
            logger.info("APScheduler initialized with SQLAlchemy job store")
            
        except Exception as e:
            logger.error(f"Failed to initialize scheduler: {e}")
            raise
    
    def _job_executed_listener(self, event):
        """Handle scheduler events."""
        job_id = event.job_id
        job = self._scheduler.get_job(job_id)
        
        if event.code == EVENT_JOB_EXECUTED:
            logger.info(f"Job {job_id} executed successfully")
            
        elif event.code == EVENT_JOB_ERROR:
            logger.error(f"Job {job_id} failed with error: {event.exception}")
            
            # Retry logic could be implemented here
            # For now, just log the error
            
        elif event.code == EVENT_JOB_MISSED:
            logger.warning(f"Job {job_id} missed scheduled execution at {event.scheduled_run_time}")
            
            # Optionally execute missed job
            # if job:
            #     self._scheduler.add_job(
            #         job.func,
            #         trigger='date',
            #         run_date=datetime.utcnow(),
            #         args=job.args,
            #         kwargs=job.kwargs,
            #         id=f"{job_id}_recovery_{uuid4().hex[:8]}"
            #     )
    
    def start(self):
        """Start the scheduler."""
        if self._scheduler and not self._scheduler.running:
            self._scheduler.start()
            logger.info("Scheduler started")
            
            # Register shutdown hook
            atexit.register(self.shutdown)
    
    def shutdown(self, wait: bool = True):
        """Shutdown the scheduler."""
        if self._scheduler and self._scheduler.running:
            self._scheduler.shutdown(wait=wait)
            logger.info("Scheduler shutdown")
    
    def add_scheduled_job(
        self,
        task_id: int,
        user_id: int,
        agent_id: int,
        cron_expression: Optional[str] = None,
        interval_seconds: Optional[int] = None,
        start_date: Optional[datetime] = None,
        kwargs: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """Add a scheduled job to the scheduler.
        
        Args:
            task_id: Scheduled task ID from database
            user_id: User ID
            agent_id: Agent ID
            cron_expression: Cron expression for scheduling
            interval_seconds: Interval in seconds for scheduling
            start_date: When to start the job (default: now)
            kwargs: Additional keyword arguments for the job
            
        Returns:
            Tuple of (success, job_id, error_message)
        """
        if not self._scheduler:
            return False, None, "Scheduler not initialized"
        
        if not cron_expression and not interval_seconds:
            return False, None, "Either cron_expression or interval_seconds must be provided"
        
        try:
            # Create job ID
            job_id = f"task_{task_id}_user_{user_id}"
            
            # Determine trigger
            if cron_expression:
                trigger = CronTrigger.from_crontab(cron_expression)
            else:
                trigger = IntervalTrigger(seconds=interval_seconds)
            
            # Set start date if provided
            if start_date:
                trigger.start_date = start_date
            
            # Prepare job arguments
            job_kwargs = {
                'task_id': task_id,
                'user_id': user_id,
                'agent_id': agent_id,
                **(kwargs or {})
            }
            
            # Add job to scheduler
            job = self._scheduler.add_job(
                func=execute_scheduled_task,
                trigger=trigger,
                kwargs=job_kwargs,
                id=job_id,
                name=f"Scheduled Task {task_id}",
                replace_existing=True,  # Replace if job already exists
                max_instances=1  # Only one instance at a time
            )
            
            logger.info(f"Added scheduled job {job_id} with trigger: {trigger}")
            return True, job_id, None
            
        except Exception as e:
            logger.error(f"Error adding scheduled job: {e}")
            return False, None, str(e)
    
    def remove_scheduled_job(self, job_id: str) -> Tuple[bool, Optional[str]]:
        """Remove a scheduled job.
        
        Args:
            job_id: Job ID to remove
            
        Returns:
            Tuple of (success, error_message)
        """
        if not self._scheduler:
            return False, "Scheduler not initialized"
        
        try:
            if self._scheduler.get_job(job_id):
                self._scheduler.remove_job(job_id)
                logger.info(f"Removed scheduled job {job_id}")
                return True, None
            else:
                return False, f"Job {job_id} not found"
                
        except Exception as e:
            logger.error(f"Error removing scheduled job: {e}")
            return False, str(e)
    
    def pause_scheduled_job(self, job_id: str) -> Tuple[bool, Optional[str]]:
        """Pause a scheduled job.
        
        Args:
            job_id: Job ID to pause
            
        Returns:
            Tuple of (success, error_message)
        """
        if not self._scheduler:
            return False, "Scheduler not initialized"
        
        try:
            job = self._scheduler.get_job(job_id)
            if job:
                job.pause()
                logger.info(f"Paused scheduled job {job_id}")
                return True, None
            else:
                return False, f"Job {job_id} not found"
                
        except Exception as e:
            logger.error(f"Error pausing scheduled job: {e}")
            return False, str(e)
    
    def resume_scheduled_job(self, job_id: str) -> Tuple[bool, Optional[str]]:
        """Resume a paused scheduled job.
        
        Args:
            job_id: Job ID to resume
            
        Returns:
            Tuple of (success, error_message)
        """
        if not self._scheduler:
            return False, "Scheduler not initialized"
        
        try:
            job = self._scheduler.get_job(job_id)
            if job:
                job.resume()
                logger.info(f"Resumed scheduled job {job_id}")
                return True, None
            else:
                return False, f"Job {job_id} not found"
                
        except Exception as e:
            logger.error(f"Error resuming scheduled job: {e}")
            return False, str(e)
    
    def get_scheduled_jobs(self, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get list of scheduled jobs.
        
        Args:
            user_id: Optional user ID to filter jobs
            
        Returns:
            List of job information dictionaries
        """
        if not self._scheduler:
            return []
        
        jobs = []
        for job in self._scheduler.get_jobs():
            # Extract task_id from job ID
            job_info = {
                'id': job.id,
                'name': job.name,
                'next_run_time': job.next_run_time,
                'trigger': str(job.trigger),
                'paused': job.pending,  # APScheduler uses 'pending' for paused jobs
            }
            
            # Filter by user_id if specified
            if user_id is not None:
                # Extract user_id from job ID or kwargs
                if f"_user_{user_id}" in job.id:
                    jobs.append(job_info)
            else:
                jobs.append(job_info)
        
        return jobs
    
    def run_job_now(self, job_id: str) -> Tuple[bool, Optional[str]]:
        """Run a scheduled job immediately.
        
        Args:
            job_id: Job ID to run
            
        Returns:
            Tuple of (success, error_message)
        """
        if not self._scheduler:
            return False, "Scheduler not initialized"
        
        try:
            job = self._scheduler.get_job(job_id)
            if job:
                # Create a one-time job to run immediately
                temp_job_id = f"{job_id}_manual_{uuid4().hex[:8]}"
                self._scheduler.add_job(
                    func=job.func,
                    trigger='date',
                    run_date=datetime.utcnow(),
                    args=job.args,
                    kwargs=job.kwargs,
                    id=temp_job_id
                )
                logger.info(f"Scheduled immediate execution of job {job_id} as {temp_job_id}")
                return True, None
            else:
                return False, f"Job {job_id} not found"
                
        except Exception as e:
            logger.error(f"Error running job immediately: {e}")
            return False, str(e)
    
    def reschedule_job(
        self,
        job_id: str,
        cron_expression: Optional[str] = None,
        interval_seconds: Optional[int] = None,
        start_date: Optional[datetime] = None
    ) -> Tuple[bool, Optional[str]]:
        """Reschedule an existing job.
        
        Args:
            job_id: Job ID to reschedule
            cron_expression: New cron expression
            interval_seconds: New interval in seconds
            start_date: New start date
            
        Returns:
            Tuple of (success, error_message)
        """
        if not self._scheduler:
            return False, "Scheduler not initialized"
        
        if not cron_expression and not interval_seconds:
            return False, "Either cron_expression or interval_seconds must be provided"
        
        try:
            job = self._scheduler.get_job(job_id)
            if not job:
                return False, f"Job {job_id} not found"
            
            # Determine new trigger
            if cron_expression:
                new_trigger = CronTrigger.from_crontab(cron_expression)
            else:
                new_trigger = IntervalTrigger(seconds=interval_seconds)
            
            if start_date:
                new_trigger.start_date = start_date
            
            # Reschedule job
            job.reschedule(trigger=new_trigger)
            logger.info(f"Rescheduled job {job_id} with new trigger: {new_trigger}")
            return True, None
            
        except Exception as e:
            logger.error(f"Error rescheduling job: {e}")
            return False, str(e)
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed status of a job.
        
        Args:
            job_id: Job ID
            
        Returns:
            Job status dictionary or None if not found
        """
        if not self._scheduler:
            return None
        
        job = self._scheduler.get_job(job_id)
        if not job:
            return None
        
        return {
            'id': job.id,
            'name': job.name,
            'next_run_time': job.next_run_time,
            'prev_run_time': job.previous_fire_time,
            'trigger': str(job.trigger),
            'paused': job.pending,
            'max_instances': job.max_instances,
            'misfire_grace_time': job.misfire_grace_time,
            'coalesce': job.coalesce,
        }


# Global scheduler instance
scheduler_manager = SchedulerManager()

# Convenience functions
def get_scheduler() -> Optional[BackgroundScheduler]:
    """Get the scheduler instance."""
    return scheduler_manager._scheduler if scheduler_manager else None

def add_scheduled_job(
    task_id: int,
    user_id: int,
    agent_id: int,
    cron_expression: Optional[str] = None,
    interval_seconds: Optional[int] = None,
    start_date: Optional[datetime] = None,
    kwargs: Optional[Dict[str, Any]] = None
) -> Tuple[bool, Optional[str], Optional[str]]:
    """Add a scheduled job."""
    return scheduler_manager.add_scheduled_job(
        task_id, user_id, agent_id, cron_expression, interval_seconds, start_date, kwargs
    )

def remove_scheduled_job(job_id: str) -> Tuple[bool, Optional[str]]:
    """Remove a scheduled job."""
    return scheduler_manager.remove_scheduled_job(job_id)

def get_scheduled_jobs(user_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """Get list of scheduled jobs."""
    return scheduler_manager.get_scheduled_jobs(user_id)

def start_scheduler():
    """Start the scheduler."""
    scheduler_manager.start()

def shutdown_scheduler(wait: bool = True):
    """Shutdown the scheduler."""
    scheduler_manager.shutdown(wait)