"""
Task scheduling using APScheduler.
"""

import pytz
from typing import Callable, Optional
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from ..utils.logger import get_logger

logger = get_logger()


class TaskScheduler:
    """Schedule periodic organization tasks."""

    def __init__(
        self,
        schedule: str = "0 2 * * 0",
        timezone: str = "UTC"
    ):
        """
        Initialize task scheduler.

        Args:
            schedule: Cron schedule string (default: 2 AM every Sunday)
            timezone: Timezone for schedule
        """
        self.schedule = schedule
        self.timezone = pytz.timezone(timezone)

        self.scheduler = BlockingScheduler(timezone=self.timezone)

        logger.info(f"Task scheduler initialized: {schedule} ({timezone})")

    def add_job(
        self,
        func: Callable,
        job_id: str = "organize_task",
        **kwargs
    ) -> None:
        """
        Add scheduled job.

        Args:
            func: Function to call
            job_id: Unique job identifier
            **kwargs: Additional arguments for func
        """
        try:
            # Parse cron schedule
            cron_parts = self.schedule.split()

            if len(cron_parts) != 5:
                raise ValueError(
                    f"Invalid cron schedule: {self.schedule}. "
                    f"Expected 5 parts (minute hour day month day_of_week)"
                )

            minute, hour, day, month, day_of_week = cron_parts

            trigger = CronTrigger(
                minute=minute,
                hour=hour,
                day=day,
                month=month,
                day_of_week=day_of_week,
                timezone=self.timezone
            )

            self.scheduler.add_job(
                func,
                trigger=trigger,
                id=job_id,
                kwargs=kwargs,
                replace_existing=True
            )

            logger.info(f"Added scheduled job: {job_id}")
            logger.info(f"Next run time: {self.scheduler.get_job(job_id).next_run_time}")

        except Exception as e:
            logger.error(f"Failed to add scheduled job: {e}")
            raise

    def start(self) -> None:
        """Start the scheduler (blocking)."""
        logger.info("Starting scheduler...")
        logger.info("Press Ctrl+C to stop")

        try:
            self.scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            logger.info("Scheduler stopped")

    def shutdown(self) -> None:
        """Shutdown the scheduler."""
        logger.info("Shutting down scheduler...")
        self.scheduler.shutdown()

    def list_jobs(self) -> list:
        """
        List all scheduled jobs.

        Returns:
            List of job information
        """
        jobs = []

        for job in self.scheduler.get_jobs():
            jobs.append({
                'id': job.id,
                'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None,
                'trigger': str(job.trigger)
            })

        return jobs


def run_scheduled_task(organize_func: Callable, **kwargs) -> None:
    """
    Wrapper for scheduled organization task.

    Args:
        organize_func: Organization function to call
        **kwargs: Arguments for organize_func
    """
    logger.info("=" * 60)
    logger.info("SCHEDULED ORGANIZATION TASK STARTED")
    logger.info("=" * 60)

    try:
        result = organize_func(**kwargs)

        if result.get('status') == 'success':
            stats = result.get('stats', {})
            logger.info(f"Scheduled task completed successfully")
            logger.info(f"Files moved: {stats.get('files_moved', 0)}")
        else:
            logger.error(f"Scheduled task failed: {result.get('error')}")

    except Exception as e:
        logger.error(f"Scheduled task error: {e}")

    logger.info("=" * 60)
    logger.info("SCHEDULED TASK COMPLETE")
    logger.info("=" * 60)
