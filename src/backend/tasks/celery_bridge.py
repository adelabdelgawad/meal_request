"""
Celery Bridge - Dispatch scheduler jobs to Celery workers.

This module provides the bridge between APScheduler and Celery.
When CELERY_ENABLED=True, jobs are dispatched to Celery workers.
When CELERY_ENABLED=False, jobs run inline (direct execution).
"""

import logging
from typing import Optional

from settings import settings

logger = logging.getLogger(__name__)

# Map of job keys to Celery task functions
_CELERY_TASK_REGISTRY = {}


def register_celery_task(job_key: str, task):
    """Register a Celery task for a job key."""
    _CELERY_TASK_REGISTRY[job_key] = task
    logger.info(f"Registered Celery task for job key: {job_key}")


def get_celery_task(job_key: str):
    """Get the Celery task for a job key."""
    return _CELERY_TASK_REGISTRY.get(job_key)


def dispatch_to_celery(job_key: str, execution_id: Optional[str] = None, **kwargs) -> Optional[str]:
    """
    Dispatch a job to Celery if enabled and task is registered.

    Args:
        job_key: The job key (e.g., "attendance_sync", "hris_replication")
        execution_id: Scheduler execution ID to update status when task completes
        **kwargs: Additional arguments to pass to the Celery task

    Returns:
        Celery task ID if dispatched, None if falling back to inline
    """
    if not settings.CELERY_ENABLED:
        logger.debug(f"Celery disabled, running {job_key} inline")
        return None

    task = _CELERY_TASK_REGISTRY.get(job_key)
    if not task:
        logger.debug(
            f"No Celery task registered for {job_key}, running inline")
        return None

    try:
        # Pass execution_id to Celery task so it can update status when done
        result = task.delay(execution_id=execution_id, **kwargs)
        logger.info(
            f"✅ Dispatched job '{job_key}' to Celery, task_id: {result.id}, execution_id: {execution_id}")
        return result.id
    except Exception as e:
        logger.error(f"❌ Failed to dispatch '{job_key}' to Celery: {e}")
        logger.error(f"Falling back to inline execution for '{job_key}'")
        # Fall back to inline execution
        return None


def is_celery_task(job_key: str) -> bool:
    """Check if a job key has a registered Celery task."""
    return job_key in _CELERY_TASK_REGISTRY and settings.CELERY_ENABLED


def initialize_celery_tasks():
    """
    Register all known Celery tasks.

    Called during application startup to map job keys to Celery tasks.
    """
    try:
        from tasks.attendance import sync_attendance_task
        register_celery_task("attendance_sync", sync_attendance_task)
    except ImportError as e:
        logger.warning(f"Could not import attendance Celery task: {e}")

    try:
        from tasks.hris import hris_replication_task
        register_celery_task("hris_replication", hris_replication_task)
    except ImportError as e:
        logger.warning(f"Could not import HRIS Celery task: {e}")

    try:
        from tasks.scheduler import cleanup_history_task
        register_celery_task("history_cleanup", cleanup_history_task)
    except ImportError as e:
        logger.warning(f"Could not import scheduler Celery task: {e}")

    logger.info(
        f"Initialized Celery task registry with {len(_CELERY_TASK_REGISTRY)} tasks")
