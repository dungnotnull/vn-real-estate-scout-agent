"""Scheduler for automated scraping with APScheduler."""
from typing import Callable, Optional, Dict, Any, List
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor
import logging

logger = logging.getLogger(__name__)


class ScraperScheduler:
    """Scheduler for automated scraping operations."""

    def __init__(self, db_path: Optional[str] = None):
        """Initialize scheduler.

        Args:
            db_path: Path for job store database
        """
        from src.config import DATA_DIR

        jobstore_path = db_path or (DATA_DIR / "scheduler_jobs.sqlite")

        jobstores = {
            'default': SQLAlchemyJobStore(url=f'sqlite:///{jobstore_path}')
        }

        executors = {
            'default': ThreadPoolExecutor(20),
            'processpool': ProcessPoolExecutor(5)
        }

        job_defaults = {
            'coalesce': True,
            'max_instances': 3,
            'misfire_grace_time': 300  # 5 minutes
        }

        self.scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone='Asia/Ho_Chi_Minh'
        )

        self.jobs = {}

    def start(self):
        """Start the scheduler."""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Scheduler started")

    def shutdown(self, wait: bool = True):
        """Shutdown the scheduler.

        Args:
            wait: Wait for jobs to complete
        """
        if self.scheduler.running:
            self.scheduler.shutdown(wait=wait)
            logger.info("Scheduler shutdown")

    def add_interval_job(
        self,
        func: Callable,
        job_id: str,
        hours: int = 4,
        minutes: Optional[int] = None,
        **kwargs
    ):
        """Add interval-based job.

        Args:
            func: Function to execute
            job_id: Unique job identifier
            hours: Interval in hours
            minutes: Additional interval in minutes
            **kwargs: Additional arguments for the job
        """
        trigger = IntervalTrigger(hours=hours, minutes=minutes or 0)

        self.scheduler.add_job(
            func,
            trigger=trigger,
            id=job_id,
            name=job_id,
            replace_existing=True,
            **kwargs
        )

        self.jobs[job_id] = {'type': 'interval', 'hours': hours, 'minutes': minutes}
        logger.info(f"Added interval job: {job_id} every {hours}h {minutes}m")

    def add_cron_job(
        self,
        func: Callable,
        job_id: str,
        cron: str = "0 */4 * * *",
        **kwargs
    ):
        """Add cron-based job.

        Args:
            func: Function to execute
            job_id: Unique job identifier
            cron: Cron expression
            **kwargs: Additional job arguments
        """
        # Parse cron expression
        parts = cron.split()
        if len(parts) != 5:
            raise ValueError(f"Invalid cron expression: {cron}")

        minute, hour, day, month, day_of_week = parts

        trigger = CronTrigger(
            minute=minute,
            hour=hour,
            day=day,
            month=month,
            day_of_week=day_of_week,
            timezone='Asia/Ho_Chi_Minh'
        )

        self.scheduler.add_job(
            func,
            trigger=trigger,
            id=job_id,
            name=job_id,
            replace_existing=True,
            **kwargs
        )

        self.jobs[job_id] = {'type': 'cron', 'expression': cron}
        logger.info(f"Added cron job: {job_id} with schedule '{cron}'")

    def remove_job(self, job_id: str):
        """Remove a job.

        Args:
            job_id: Job identifier
        """
        try:
            self.scheduler.remove_job(job_id)
            if job_id in self.jobs:
                del self.jobs[job_id]
            logger.info(f"Removed job: {job_id}")
        except Exception as e:
            logger.error(f"Failed to remove job {job_id}: {e}")

    def pause_job(self, job_id: str):
        """Pause a job.

        Args:
            job_id: Job identifier
        """
        try:
            self.scheduler.pause_job(job_id)
            logger.info(f"Paused job: {job_id}")
        except Exception as e:
            logger.error(f"Failed to pause job {job_id}: {e}")

    def resume_job(self, job_id: str):
        """Resume a paused job.

        Args:
            job_id: Job identifier
        """
        try:
            self.scheduler.resume_job(job_id)
            logger.info(f"Resumed job: {job_id}")
        except Exception as e:
            logger.error(f"Failed to resume job {job_id}: {e}")

    def get_job_info(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a job.

        Args:
            job_id: Job identifier

        Returns:
            Job information dict or None
        """
        job = self.scheduler.get_job(job_id)
        if job:
            return {
                'id': job.id,
                'name': job.name,
                'next_run_time': job.next_run_time,
                'trigger': str(job.trigger)
            }
        return None

    def get_all_jobs(self) -> List[Dict[str, Any]]:
        """Get information about all jobs.

        Returns:
            List of job information dicts
        """
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                'id': job.id,
                'name': job.name,
                'next_run_time': job.next_run_time,
                'trigger': str(job.trigger)
            })
        return jobs

    def run_job_now(self, job_id: str):
        """Run a job immediately.

        Args:
            job_id: Job identifier
        """
        try:
            job = self.scheduler.get_job(job_id)
            if job:
                job.modify(next_run_time=datetime.now())
                logger.info(f"Scheduled job {job_id} to run now")
        except Exception as e:
            logger.error(f"Failed to run job {job_id}: {e}")

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()


class ScrapingManager:
    """Manage scraping schedules for multiple platforms."""

    def __init__(self):
        """Initialize scraping manager."""
        self.scheduler = ScraperScheduler()
        self.scrape_callbacks = {}

    def register_platform(self, platform: str, scrape_func: Callable, interval_hours: int = 4):
        """Register a platform for scheduled scraping.

        Args:
            platform: Platform name
            scrape_func: Async scraping function
            interval_hours: Scraping interval
        """
        job_id = f"scrape_{platform}"
        self.scrape_callbacks[platform] = scrape_func

        self.scheduler.add_interval_job(
            func=scrape_func,
            job_id=job_id,
            hours=interval_hours
        )

        logger.info(f"Registered platform: {platform} (scrape every {interval_hours}h)")

    async def scrape_platform_now(self, platform: str):
        """Scrape a platform immediately.

        Args:
            platform: Platform name
        """
        if platform not in self.scrape_callbacks:
            logger.error(f"Platform not registered: {platform}")
            return

        job_id = f"scrape_{platform}"
        self.scheduler.run_job_now(job_id)

    def get_platform_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all platform scraping jobs.

        Returns:
            Dict of platform -> job status
        """
        status = {}
        for platform in self.scrape_callbacks:
            job_id = f"scrape_{platform}"
            job_info = self.scheduler.get_job_info(job_id)
            status[platform] = job_info or {'status': 'not_scheduled'}
        return status

    def start(self):
        """Start all scheduled scraping."""
        self.scheduler.start()

    def stop(self):
        """Stop all scheduled scraping."""
        self.scheduler.shutdown()
