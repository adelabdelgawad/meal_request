"""
Structured logging utility for scheduler execution tracking.

Provides JSON-formatted logging with correlation IDs, execution context,
and timestamp tracking for debugging task cascades and race conditions.
"""

import json
import logging
import time
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import uuid4

# Context variables for tracking request/execution flow
correlation_id_var: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)
execution_context_var: ContextVar[Dict[str, Any]] = ContextVar("execution_context", default={})


class StructuredLogger:
    """
    Structured logger that outputs JSON-formatted logs with execution context.

    Features:
    - Correlation ID tracking across async boundaries
    - Execution context (job_id, execution_id, user_id, etc.)
    - Timestamp tracking (absolute and relative deltas)
    - Parent/child execution lineage tracking
    - Task metadata for debugging cascades
    """

    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self._start_times: Dict[str, float] = {}  # execution_id -> start timestamp

    def _get_correlation_id(self) -> Optional[str]:
        """Get current correlation ID from context."""
        return correlation_id_var.get()

    def _get_execution_context(self) -> Dict[str, Any]:
        """Get current execution context from context."""
        return execution_context_var.get() or {}

    def _build_log_entry(
        self,
        event: str,
        level: str,
        message: str,
        **metadata: Any
    ) -> Dict[str, Any]:
        """
        Build structured log entry with full context.

        Args:
            event: Event type (e.g., "API_ENTRY", "EXEC_CREATE_START")
            level: Log level (INFO, WARNING, ERROR)
            message: Human-readable message
            **metadata: Additional metadata fields

        Returns:
            Dictionary ready for JSON serialization
        """
        correlation_id = self._get_correlation_id()
        exec_context = self._get_execution_context()

        # Current timestamp
        now = datetime.now(timezone.utc)
        timestamp_ns = time.time_ns()

        # Calculate delta if we have a start time
        execution_id = metadata.get("execution_id") or exec_context.get("execution_id")
        delta_ms = None
        if execution_id and execution_id in self._start_times:
            start_ns = self._start_times[execution_id]
            delta_ms = (timestamp_ns - start_ns) / 1_000_000  # Convert to milliseconds

        log_entry = {
            "timestamp": now.isoformat(),
            "timestamp_ns": timestamp_ns,
            "event": event,
            "level": level,
            "message": message,
            "correlation_id": correlation_id,
        }

        # Add execution context
        if exec_context:
            log_entry["execution_context"] = exec_context

        # Add delta if available
        if delta_ms is not None:
            log_entry["delta_ms"] = round(delta_ms, 2)

        # Add all additional metadata
        log_entry.update(metadata)

        return log_entry

    def _log(self, level: str, event: str, message: str, **metadata: Any):
        """Internal logging method."""
        log_entry = self._build_log_entry(event, level, message, **metadata)
        json_str = json.dumps(log_entry, default=str)

        # Log to appropriate level
        log_method = getattr(self.logger, level.lower())
        log_method(json_str)

    def info(self, event: str, message: str, **metadata: Any):
        """Log INFO level structured message."""
        self._log("INFO", event, message, **metadata)

    def warning(self, event: str, message: str, **metadata: Any):
        """Log WARNING level structured message."""
        self._log("WARNING", event, message, **metadata)

    def error(self, event: str, message: str, **metadata: Any):
        """Log ERROR level structured message."""
        self._log("ERROR", event, message, **metadata)

    def debug(self, event: str, message: str, **metadata: Any):
        """Log DEBUG level structured message."""
        self._log("DEBUG", event, message, **metadata)

    def track_execution_start(self, execution_id: str):
        """
        Start tracking execution time for delta calculations.

        Args:
            execution_id: Execution ID to track
        """
        self._start_times[execution_id] = time.time_ns()

    def track_execution_end(self, execution_id: str) -> Optional[float]:
        """
        End tracking execution time and return total duration.

        Args:
            execution_id: Execution ID to stop tracking

        Returns:
            Duration in milliseconds, or None if not tracked
        """
        if execution_id in self._start_times:
            start_ns = self._start_times.pop(execution_id)
            end_ns = time.time_ns()
            return (end_ns - start_ns) / 1_000_000  # Convert to milliseconds
        return None

    def log_api_entry(
        self,
        job_id: str,
        action: str,
        user_id: Optional[str] = None,
        **metadata: Any
    ):
        """Log API endpoint entry point."""
        self.info(
            event="API_ENTRY",
            message=f"Trigger request received for job {job_id}",
            job_id=job_id,
            action=action,
            user_id=user_id,
            **metadata
        )

    def log_duplicate_check(
        self,
        job_id: str,
        job_key: str,
        running_execution_found: bool,
        running_execution_id: Optional[str] = None,
        **metadata: Any
    ):
        """Log duplicate execution check."""
        if running_execution_found:
            self.warning(
                event="DUPLICATE_CHECK_REJECTED",
                message=f"Job {job_key} already running (execution_id={running_execution_id})",
                job_id=job_id,
                job_key=job_key,
                running_execution_id=running_execution_id,
                check_result="REJECTED",
                **metadata
            )
        else:
            self.info(
                event="DUPLICATE_CHECK_PASSED",
                message=f"No running execution found for job {job_key}",
                job_id=job_id,
                job_key=job_key,
                check_result="PASSED",
                **metadata
            )

    def log_execution_create_start(
        self,
        job_id: str,
        job_key: str,
        execution_id: str,
        trigger_source: str,
        parent_execution_id: Optional[str] = None,
        **metadata: Any
    ):
        """Log start of execution record creation."""
        # Start tracking this execution
        self.track_execution_start(execution_id)

        self.info(
            event="EXEC_CREATE_START",
            message=f"Creating execution record for job {job_key}",
            job_id=job_id,
            job_key=job_key,
            execution_id=execution_id,
            trigger_source=trigger_source,
            parent_execution_id=parent_execution_id,
            lineage={
                "execution_id": execution_id,
                "parent_execution_id": parent_execution_id,
                "trigger_source": trigger_source
            },
            **metadata
        )

    def log_execution_create_committed(
        self,
        job_id: str,
        job_key: str,
        execution_id: str,
        status: str,
        **metadata: Any
    ):
        """Log successful execution record commit."""
        self.info(
            event="EXEC_CREATE_COMMITTED",
            message=f"Execution record committed for job {job_key}",
            job_id=job_id,
            job_key=job_key,
            execution_id=execution_id,
            status=status,
            **metadata
        )

    def log_background_task_launch(
        self,
        job_id: str,
        job_key: str,
        execution_id: str,
        triggered_by: Optional[str] = None,
        **metadata: Any
    ):
        """Log background task launch."""
        self.info(
            event="BACKGROUND_LAUNCH",
            message=f"Launching background task for job {job_key}",
            job_id=job_id,
            job_key=job_key,
            execution_id=execution_id,
            triggered_by=triggered_by or "SCHEDULED",
            **metadata
        )

    def log_lock_attempt(
        self,
        job_id: str,
        execution_id: str,
        instance_id: str,
        **metadata: Any
    ):
        """Log lock acquisition attempt."""
        self.info(
            event="LOCK_ATTEMPT",
            message=f"Attempting to acquire lock for execution {execution_id}",
            job_id=job_id,
            execution_id=execution_id,
            instance_id=instance_id,
            **metadata
        )

    def log_lock_acquired(
        self,
        job_id: str,
        execution_id: str,
        lock_id: int,
        **metadata: Any
    ):
        """Log successful lock acquisition."""
        self.info(
            event="LOCK_ACQUIRED",
            message=f"Lock acquired for execution {execution_id}",
            job_id=job_id,
            execution_id=execution_id,
            lock_id=lock_id,
            lock_result="SUCCESS",
            **metadata
        )

    def log_lock_failed(
        self,
        job_id: str,
        execution_id: str,
        reason: str,
        **metadata: Any
    ):
        """Log lock acquisition failure."""
        self.warning(
            event="LOCK_FAILED",
            message=f"Failed to acquire lock for execution {execution_id}: {reason}",
            job_id=job_id,
            execution_id=execution_id,
            reason=reason,
            lock_result="FAILED",
            **metadata
        )

    def log_celery_dispatch_attempt(
        self,
        job_key: str,
        execution_id: str,
        task_metadata: Dict[str, Any],
        **metadata: Any
    ):
        """Log Celery task dispatch attempt."""
        self.info(
            event="CELERY_DISPATCH_ATTEMPT",
            message=f"Attempting to dispatch job {job_key} to Celery",
            job_key=job_key,
            execution_id=execution_id,
            task_metadata=task_metadata,
            **metadata
        )

    def log_celery_dispatch_success(
        self,
        job_key: str,
        execution_id: str,
        celery_task_id: str,
        **metadata: Any
    ):
        """Log successful Celery dispatch."""
        self.info(
            event="CELERY_DISPATCH_SUCCESS",
            message=f"Successfully dispatched job {job_key} to Celery",
            job_key=job_key,
            execution_id=execution_id,
            celery_task_id=celery_task_id,
            dispatch_result="SUCCESS",
            **metadata
        )

    def log_celery_dispatch_failed(
        self,
        job_key: str,
        execution_id: str,
        error: str,
        **metadata: Any
    ):
        """Log failed Celery dispatch."""
        self.warning(
            event="CELERY_DISPATCH_FAILED",
            message=f"Failed to dispatch job {job_key} to Celery: {error}",
            job_key=job_key,
            execution_id=execution_id,
            error=error,
            dispatch_result="FAILED",
            fallback_to_inline=True,
            **metadata
        )

    def log_celery_task_start(
        self,
        task_name: str,
        execution_id: str,
        celery_task_id: str,
        worker_host: str,
        triggered_by: Optional[str] = None,
        **metadata: Any
    ):
        """Log Celery task start."""
        self.info(
            event="CELERY_TASK_START",
            message=f"Celery task {task_name} started",
            task_name=task_name,
            execution_id=execution_id,
            celery_task_id=celery_task_id,
            worker_host=worker_host,
            triggered_by=triggered_by or "SCHEDULED",
            **metadata
        )

    def log_celery_task_complete(
        self,
        task_name: str,
        execution_id: str,
        final_status: str,
        duration_ms: float,
        **metadata: Any
    ):
        """Log Celery task completion."""
        # Track execution end and get total duration from wrapper
        total_duration_ms = self.track_execution_end(execution_id)

        self.info(
            event="CELERY_TASK_COMPLETE",
            message=f"Celery task {task_name} completed with status {final_status}",
            task_name=task_name,
            execution_id=execution_id,
            final_status=final_status,
            task_duration_ms=duration_ms,
            total_duration_ms=total_duration_ms,
            **metadata
        )

    def log_apscheduler_trigger(
        self,
        job_key: str,
        execution_id: str,
        scheduled_at: datetime,
        **metadata: Any
    ):
        """Log APScheduler job trigger."""
        self.info(
            event="APSCHEDULER_TRIGGER",
            message=f"APScheduler triggered job {job_key}",
            job_key=job_key,
            execution_id=execution_id,
            scheduled_at=scheduled_at.isoformat(),
            trigger_source="APSCHEDULER",
            **metadata
        )


def set_correlation_id(correlation_id: Optional[str] = None) -> str:
    """
    Set correlation ID for current context.

    Args:
        correlation_id: Correlation ID to set, or None to generate new UUID

    Returns:
        The correlation ID that was set
    """
    if correlation_id is None:
        correlation_id = str(uuid4())
    correlation_id_var.set(correlation_id)
    return correlation_id


def get_correlation_id() -> Optional[str]:
    """Get current correlation ID from context."""
    return correlation_id_var.get()


def set_execution_context(**context: Any):
    """
    Set execution context for current context.

    Args:
        **context: Context fields to set (job_id, execution_id, user_id, etc.)
    """
    current = execution_context_var.get() or {}
    updated = {**current, **context}
    execution_context_var.set(updated)


def get_execution_context() -> Dict[str, Any]:
    """Get current execution context from context."""
    return execution_context_var.get() or {}


def clear_execution_context():
    """Clear execution context for current context."""
    execution_context_var.set({})


def get_structured_logger(name: str) -> StructuredLogger:
    """
    Get structured logger instance.

    Args:
        name: Logger name (usually __name__)

    Returns:
        StructuredLogger instance
    """
    logger = logging.getLogger(name)
    return StructuredLogger(logger)
