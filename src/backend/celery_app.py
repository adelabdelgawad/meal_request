"""
Celery Application Configuration.

This module configures Celery with Redis as broker and result backend.
The Celery app handles background task execution with retry logic,
while APScheduler continues to handle job scheduling.
"""

import sys
import os
from celery import Celery
from settings import settings

# Create Celery app instance
celery_app = Celery(
    "meal_request",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "tasks.email",
        "tasks.attendance",
        "tasks.hris",
        "tasks.scheduler",
        "tasks.domain_users",
    ],
)

# Fix Python path for Celery workers
celery_app.conf.update(
    # Add current directory to Python path for Celery workers
    worker_hijack_root_logger=False,  # Don't hijack root logger
    worker_log_color=False,  # Disable colored logs in workers
)

# Set up the worker to import from the correct path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Celery configuration
celery_app.conf.update(
    # Serialization
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    # Enable async task support for Celery 5.3+
    task_always_eager=False,
    task_eager_propagates=False,
    # Broker connection settings
    broker_connection_retry_on_startup=True,  # Celery 6.0+ compatibility
    # Reliability settings
    # Acknowledge after task completion (allows retry on worker crash)
    task_acks_late=True,
    task_reject_on_worker_lost=True,  # Requeue task if worker is killed
    task_track_started=True,  # Track when tasks start executing
    # Result expiration (24 hours)
    result_expires=86400,
    # Worker settings
    # Note: Use -P gevent argument when starting worker instead of worker_pool setting
    # to ensure gevent monkey patching is applied early
    worker_prefetch_multiplier=1,  # Fair distribution across workers
    worker_concurrency=10,  # Gevent supports multiple concurrent greenlets
    # Task time limits
    # 5 minutes soft limit (raises SoftTimeLimitExceeded)
    task_soft_time_limit=300,
    task_time_limit=360,  # 6 minutes hard limit (kills worker)
    # Retry defaults (can be overridden per-task)
    task_default_retry_delay=60,  # 1 minute default retry delay
    # Timezone
    timezone="UTC",
    enable_utc=True,
)
