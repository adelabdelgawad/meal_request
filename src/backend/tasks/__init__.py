"""
Celery Tasks Package.

This package contains all Celery task definitions for background processing:
- email: Email notification tasks
- attendance: Attendance synchronization tasks
- hris: HRIS data replication tasks
- scheduler: Scheduler maintenance tasks (cleanup, etc.)

Each task is designed with automatic retry logic and can be dispatched
from APScheduler jobs or directly from API endpoints.

The celery_bridge module provides the integration between APScheduler and Celery,
allowing scheduled jobs to be dispatched to Celery workers when CELERY_ENABLED=True.
"""

from tasks.email import send_notification_task
from tasks.attendance import (
    sync_attendance_task,
    sync_attendance_for_lines_task,
    fetch_attendance_for_meal_request_task,
)
from tasks.hris import hris_replication_task
from tasks.scheduler import cleanup_history_task
from tasks.celery_bridge import (
    dispatch_to_celery,
    is_celery_task,
    initialize_celery_tasks,
)

__all__ = [
    "send_notification_task",
    "sync_attendance_task",
    "sync_attendance_for_lines_task",
    "fetch_attendance_for_meal_request_task",
    "hris_replication_task",
    "cleanup_history_task",
    "dispatch_to_celery",
    "is_celery_task",
    "initialize_celery_tasks",
]
