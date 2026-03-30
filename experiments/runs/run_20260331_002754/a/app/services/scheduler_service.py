"""app/services/scheduler_service.py — Background task scheduler service.

exports: SchedulerService
used_by: app/services/container.py → ServiceContainer.scheduler, app/main.py → startup/shutdown
rules:   must support persistent job storage; handle cluster deployments; graceful shutdown
agent:   Product Architect | 2024-03-30 | created scheduler service skeleton
         message: "implement job persistence for fault tolerance across restarts"
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Callable
from enum import Enum

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED

from app.exceptions import ServiceUnavailableError
from app.services.container import ServiceContainer

logger = logging.getLogger(__name__)


class JobType(str, Enum):
    """Job type enumeration."""
    USAGE_AGGREGATION = "usage_aggregation"
    SUBSCRIPTION_CHECK = "subscription_check"
    AGENT_HEALTH_CHECK = "agent_health_check"
    TASK_CLEANUP = "task_cleanup"
    AUDIT_LOG_CLEANUP = "audit_log_cleanup"
    EMAIL_NOTIFICATION = "email_notification"
    CUSTOM = "custom"


class SchedulerService:
    """Background task scheduler service using APScheduler.
    
    Rules:
        Jobs must be persistent across restarts (SQLAlchemy job store)
        Must handle multiple worker instances in cluster deployment
        Graceful shutdown required
        Job errors must be logged but not crash scheduler
    """
    
    def __init__(self, container: ServiceContainer):
        """Initialize scheduler service.
        
        Args:
            container: Service container with dependencies
        """
        self.container = container
        self.config = container.config
        
        # Scheduler instance (initialized in start())
        self.scheduler: Optional[AsyncIOScheduler] = None
        
        # Job store URL (uses same database as application)
        self.job_store_url = str(self.config.DATABASE_URL).replace(
            "asyncpg", "postgresql"
        ) + "?application_name=agenthub_scheduler"
        
        logger.info("SchedulerService initialized")
    
    async def start(self) -> None:
        """Start the scheduler.
        
        Raises:
            ServiceUnavailableError: If scheduler fails to start
        """
        if self.scheduler and self.scheduler.running:
            logger.warning("Scheduler already running")
            return
        
        try:
            # Configure job stores
            job_stores = {
                'default': SQLAlchemyJobStore(
                    url=self.job_store_url,
                    engine_options={"pool_pre_ping": True},
                )
            }
            
            # Configure executors
            executors = {
                'default': ThreadPoolExecutor(20),
            }
            
            # Configure job defaults
            job_defaults = {
                'coalesce': True,  # Combine multiple pending executions
                'max_instances': 3,  # Maximum concurrent instances per job
                'misfire_grace_time': 60,  # Seconds after scheduled time job can still run
            }
            
            # Create scheduler
            self.scheduler = AsyncIOScheduler(
                jobstores=job_stores,
                executors=executors,
                job_defaults=job_defaults,
                timezone="UTC",
            )
            
            # Add event listeners
            self.scheduler.add_listener(self._job_executed, EVENT_JOB_EXECUTED)
            self.scheduler.add_listener(self._job_error, EVENT_JOB_ERROR)
            
            # Start scheduler
            self.scheduler.start()
            
            # Schedule system jobs
            await self._schedule_system_jobs()
            
            logger.info(f"Scheduler started with {len(self.scheduler.get_jobs())} jobs")
            
        except Exception as e:
            logger.error(f"Failed to start scheduler: {e}")
            raise ServiceUnavailableError("Task scheduler", str(e))
    
    async def stop(self) -> None:
        """Stop the scheduler gracefully."""
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown(wait=True)
            self.scheduler = None
            logger.info("Scheduler stopped")
    
    async def _schedule_system_jobs(self) -> None:
        """Schedule system maintenance jobs."""
        # Daily usage aggregation (runs at 2 AM UTC)
        self.add_job(
            job_id="usage_aggregation_daily",
            func=self._job_usage_aggregation,
            trigger="cron",
            hour=2,
            minute=0,
            args=[JobType.USAGE_AGGREGATION, "daily"],
            replace_existing=True,
        )
        
        # Hourly subscription checks
        self.add_job(
            job_id="subscription_check_hourly",
            func=self._job_subscription_check,
            trigger="interval",
            hours=1,
            args=[JobType.SUBSCRIPTION_CHECK],
            replace_existing=True,
        )
        
        # Agent health checks every 5 minutes
        self.add_job(
            job_id="agent_health_check",
            func=self._job_agent_health_check,
            trigger="interval",
            minutes=5,
            args=[JobType.AGENT_HEALTH_CHECK],
            replace_existing=True,
        )
        
        # Task cleanup daily at 3 AM
        self.add_job(
            job_id="task_cleanup_daily",
            func=self._job_task_cleanup,
            trigger="cron",
            hour=3,
            minute=0,
            args=[JobType.TASK_CLEANUP, 30],  # Cleanup tasks older than 30 days
            replace_existing=True,
        )
        
        # Audit log cleanup weekly on Sunday at 4 AM
        self.add_job(
            job_id="audit_log_cleanup_weekly",
            func=self._job_audit_log_cleanup,
            trigger="cron",
            day_of_week="sun",
            hour=4,
            minute=0,
            args=[JobType.AUDIT_LOG_CLEANUP, 90],  # Cleanup logs older than 90 days
            replace_existing=True,
        )
        
        logger.info("System jobs scheduled")
    
    # --- Job Management ---
    
    def add_job(
        self,
        job_id: str,
        func: Callable,
        trigger: str,
        args: Optional[list] = None,
        kwargs: Optional[dict] = None,
        replace_existing: bool = False,
        **trigger_args,
    ) -> Optional[str]:
        """Add a scheduled job.
        
        Args:
            job_id: Unique job identifier
            func: Function to execute
            trigger: Trigger type (cron, interval, date)
            args: Arguments to pass to function
            kwargs: Keyword arguments to pass to function
            replace_existing: Whether to replace existing job with same ID
            **trigger_args: Trigger-specific arguments
            
        Returns:
            Job ID or None if job exists and replace_existing=False
            
        Raises:
            RuntimeError: If scheduler not started
        """
        if not self.scheduler:
            raise RuntimeError("Scheduler not started")
        
        # Check if job already exists
        existing_job = self.scheduler.get_job(job_id)
        if existing_job:
            if replace_existing:
                existing_job.remove()
                logger.info(f"Replaced existing job: {job_id}")
            else:
                logger.warning(f"Job already exists: {job_id}")
                return None
        
        # Add job
        job = self.scheduler.add_job(
            func=func,
            trigger=trigger,
            args=args or [],
            kwargs=kwargs or {},
            id=job_id,
            **trigger_args,
        )
        
        logger.info(f"Job scheduled: {job_id} ({trigger})")
        return job.id
    
    def remove_job(self, job_id: str) -> bool:
        """Remove scheduled job.
        
        Args:
            job_id: Job ID to remove
            
        Returns:
            True if job was removed, False if not found
        """
        if not self.scheduler:
            return False
        
        job = self.scheduler.get_job(job_id)
        if job:
            job.remove()
            logger.info(f"Job removed: {job_id}")
            return True
        
        logger.warning(f"Job not found for removal: {job_id}")
        return False
    
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job information.
        
        Args:
            job_id: Job ID
            
        Returns:
            Job information or None if not found
        """
        if not self.scheduler:
            return None
        
        job = self.scheduler.get_job(job_id)
        if not job:
            return None
        
        return {
            "id": job.id,
            "name": job.name,
            "next_run_time": job.next_run_time,
            "trigger": str(job.trigger),
        }
    
    def list_jobs(self) -> List[Dict[str, Any]]:
        """List all scheduled jobs.
        
        Returns:
            List of job information dictionaries
        """
        if not self.scheduler:
            return []
        
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run_time": job.next_run_time,
                "trigger": str(job.trigger),
            })
        
        return jobs
    
    # --- System Job Functions ---
    
    async def _job_usage_aggregation(self, job_type: JobType, period: str) -> None:
        """Job: Aggregate usage records for billing."""
        logger.info(f"Running {job_type.value} job for {period} period")
        
        try:
            # TODO: Implement usage aggregation
            # 1. Get all organizations
            # 2. For each, aggregate usage for previous day
            # 3. Create invoice if needed
            # 4. Record billing events
            
            logger.info(f"Completed {job_type.value} job for {period} period")
        except Exception as e:
            logger.error(f"Error in {job_type.value} job: {e}", exc_info=True)
    
    async def _job_subscription_check(self, job_type: JobType) -> None:
        """Job: Check subscription status and sync with Stripe."""
        logger.info(f"Running {job_type.value} job")
        
        try:
            # TODO: Implement subscription check
            # 1. Get organizations with Stripe subscriptions
            # 2. Check subscription status in Stripe
            # 3. Update local records
            # 4. Handle expired trials, failed payments, etc.
            
            logger.info(f"Completed {job_type.value} job")
        except Exception as e:
            logger.error(f"Error in {job_type.value} job: {e}", exc_info=True)
    
    async def _job_agent_health_check(self, job_type: JobType) -> None:
        """Job: Check agent health and availability."""
        logger.info(f"Running {job_type.value} job")
        
        try:
            # TODO: Implement agent health check
            # 1. Get all active agents
            # 2. Test connectivity to model providers
            # 3. Update agent status
            # 4. Alert on failures
            
            logger.info(f"Completed {job_type.value} job")
        except Exception as e:
            logger.error(f"Error in {job_type.value} job: {e}", exc_info=True)
    
    async def _job_task_cleanup(self, job_type: JobType, days_old: int) -> None:
        """Job: Cleanup old completed tasks."""
        logger.info(f"Running {job_type.value} job for tasks older than {days_old} days")
        
        try:
            # TODO: Implement task cleanup
            # 1. Query old completed tasks
            # 2. Archive or delete based on retention policy
            # 3. Log cleanup statistics
            
            logger.info(f"Completed {job_type.value} job")
        except Exception as e:
            logger.error(f"Error in {job_type.value} job: {e}", exc_info=True)
    
    async def _job_audit_log_cleanup(self, job_type: JobType, days_old: int) -> None:
        """Job: Cleanup old audit logs."""
        logger.info(f"Running {job_type.value} job for logs older than {days_old} days")
        
        try:
            # TODO: Implement audit log cleanup
            # 1. Query old audit logs
            # 2. Archive or delete based on retention policy
            # 3. Log cleanup statistics
            
            logger.info(f"Completed {job_type.value} job")
        except Exception as e:
            logger.error(f"Error in {job_type.value} job: {e}", exc_info=True)
    
    # --- Event Listeners ---
    
    def _job_executed(self, event):
        """Handle job executed event."""
        job = self.scheduler.get_job(event.job_id) if self.scheduler else None
        logger.info(f"Job executed: {event.job_id} (retval: {event.retval})")
    
    def _job_error(self, event):
        """Handle job error event."""
        job = self.scheduler.get_job(event.job_id) if self.scheduler else None
        logger.error(
            f"Job error: {event.job_id} - {event.exception}",
            exc_info=event.traceback,
        )
    
    # --- Utility Methods ---
    
    def is_running(self) -> bool:
        """Check if scheduler is running.
        
        Returns:
            True if scheduler is running
        """
        return self.scheduler is not None and self.scheduler.running
    
    async def run_job_now(self, job_id: str) -> bool:
        """Run a scheduled job immediately.
        
        Args:
            job_id: Job ID to run
            
        Returns:
            True if job was run, False if not found
        """
        if not self.scheduler:
            return False
        
        job = self.scheduler.get_job(job_id)
        if not job:
            return False
        
        try:
            # Run job
            job.modify(next_run_time=datetime.now())
            logger.info(f"Manually triggered job: {job_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to run job {job_id}: {e}")
            return False
    
    async def pause_job(self, job_id: str) -> bool:
        """Pause a scheduled job.
        
        Args:
            job_id: Job ID to pause
            
        Returns:
            True if job was paused, False if not found
        """
        if not self.scheduler:
            return False
        
        job = self.scheduler.get_job(job_id)
        if not job:
            return False
        
        job.pause()
        logger.info(f"Job paused: {job_id}")
        return True
    
    async def resume_job(self, job_id: str) -> bool:
        """Resume a paused job.
        
        Args:
            job_id: Job ID to resume
            
        Returns:
            True if job was resumed, False if not found
        """
        if not self.scheduler:
            return False
        
        job = self.scheduler.get_job(job_id)
        if not job:
            return False
        
        job.resume()
        logger.info(f"Job resumed: {job_id}")
        return True