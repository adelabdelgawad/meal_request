"""
Scheduler Service for APScheduler task management.

Provides full job management including:
- Creating/updating/deleting jobs
- Starting/stopping/triggering jobs
- Execution tracking and history
- Distributed locking across instances
"""

import asyncio
import importlib
import logging
import socket
import time
import traceback
import uuid
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional, Tuple

from api.repositories.scheduler_repository import SchedulerRepository
from api.schemas.scheduler_schemas import (
    JobExecutionResponse,
    ScheduledJobCreate,
    ScheduledJobCronCreate,
    ScheduledJobIntervalCreate,
    ScheduledJobResponse,
    ScheduledJobUpdate,
    SchedulerExecutionStatusResponse,
    SchedulerInstanceResponse,
    SchedulerJobTypeResponse,
    SchedulerStatusResponse,
    TaskFunctionResponse,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from core.exceptions import NotFoundError, ValidationError
from db.model import ScheduledJob, ScheduledJobExecution
from core.config import settings
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from utils.structured_logger import get_structured_logger, set_execution_context

logger = logging.getLogger(__name__)
structured_logger = get_structured_logger(__name__)


def _get_celery_bridge():
    """Lazy import of celery bridge to avoid circular imports."""
    try:
        from tasks.celery_bridge import dispatch_to_celery, is_celery_task

        return dispatch_to_celery, is_celery_task
    except ImportError:
        return None, None


class SchedulerService:
    """
    Service for managing APScheduler jobs with database persistence.

    Supports both embedded (FastAPI) and standalone modes with
    distributed locking for coordination.
    """

    _instance: Optional["SchedulerService"] = None
    _scheduler: Optional[AsyncIOScheduler] = None
    _instance_id: Optional[str] = None
    _mode: Optional[str] = None
    _job_functions: Dict[str, Callable] = {}
    _is_running: bool = False
    _heartbeat_task: Optional[asyncio.Task] = None

    def __init__(self):
        self._repo = SchedulerRepository(self.session)

    @classmethod
    def get_instance(cls) -> "SchedulerService":
        """Get singleton instance of SchedulerService."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # -------------------
    # Lookup Table Methods
    # -------------------

    async def list_task_functions(
        self, session: AsyncSession, is_active: Optional[bool] = True
    ) -> List[TaskFunctionResponse]:
        """Get all available task functions."""
        task_functions = await self._repo.list_task_functions(session, is_active)
        return [
            TaskFunctionResponse.model_validate(tf, from_attributes=True)
            for tf in task_functions
        ]

    async def list_job_types(
        self, session: AsyncSession, is_active: Optional[bool] = True
    ) -> List[SchedulerJobTypeResponse]:
        """Get all available job types."""
        job_types = await self._repo.list_job_types(session, is_active)
        return [
            SchedulerJobTypeResponse.model_validate(jt, from_attributes=True)
            for jt in job_types
        ]

    async def list_execution_statuses(
        self, session: AsyncSession, is_active: Optional[bool] = True
    ) -> List[SchedulerExecutionStatusResponse]:
        """Get all execution statuses."""
        statuses = await self._repo.list_execution_statuses(session, is_active)
        return [
            SchedulerExecutionStatusResponse.model_validate(s, from_attributes=True)
            for s in statuses
        ]

    # -------------------
    # Job Function Registry
    # -------------------

    def register_job_function(self, job_key: str, func: Callable) -> None:
        """
        Register a callable function for a job key.

        Args:
            job_key: Unique identifier for the job
            func: Async callable to execute
        """
        self._job_functions[job_key] = func
        logger.info(f"Registered job function for key: {job_key}")

    def get_job_function(self, job_key: str) -> Optional[Callable]:
        """Get registered function for a job key."""
        return self._job_functions.get(job_key)

    def _import_job_function(self, job_function_path: str) -> Optional[Callable]:
        """
        Dynamically import a job function from its path.

        Args:
            job_function_path: e.g., "utils.sync_attendance.run_attendance_sync"
        """
        try:
            module_path, func_name = job_function_path.rsplit(".", 1)
            module = importlib.import_module(module_path)
            return getattr(module, func_name)
        except Exception as e:
            logger.error(f"Failed to import job function {job_function_path}: {e}")
            return None

    # -------------------
    # Scheduler Lifecycle
    # -------------------

    async def initialize(
        self,
        session: AsyncSession,
        mode: str = "embedded",
        instance_name: Optional[str] = None,
    ) -> str:
        """
        Initialize the scheduler service.

        Args:
            session: Database session
            mode: "embedded" or "standalone"
            instance_name: Human-readable name for this instance

        Returns:
            Instance ID
        """
        if instance_name is None:
            instance_name = f"{mode}-{socket.gethostname()}"

        # Register this instance
        instance = await self._repo.register_instance(session, instance_name, mode)
        await session.commit()

        self._instance_id = instance.id
        self._mode = mode

        # Create scheduler
        self._scheduler = AsyncIOScheduler()

        logger.info(f"Scheduler initialized: {instance_name} ({self._instance_id})")
        return self._instance_id

    async def start(self, session: AsyncSession) -> None:
        """Start the scheduler and load jobs from database."""
        if not self._scheduler:
            raise RuntimeError("Scheduler not initialized. Call initialize() first.")

        if self._is_running:
            logger.warning("Scheduler is already running")
            return

        # Initialize Celery task registry (if Celery is enabled)
        if settings.celery.enabled:
            try:
                from tasks.celery_bridge import get_celery_task, initialize_celery_tasks

                initialize_celery_tasks()

                # Verify that critical tasks are registered
                critical_tasks = ["hris_replication", "attendance_sync"]
                registered_count = 0
                for task_key in critical_tasks:
                    if get_celery_task(task_key):
                        registered_count += 1
                        logger.info(f"✓ Celery task registered: {task_key}")
                    else:
                        logger.warning(f"⚠ Celery task not registered: {task_key}")

                if registered_count > 0:
                    logger.info(
                        f"Celery task registry initialized with {registered_count} critical tasks"
                    )
                else:
                    logger.warning("⚠ No critical Celery tasks were registered")

            except ImportError as e:
                logger.warning(f"Celery tasks not available: {e}")
            except Exception as e:
                logger.error(f"Failed to initialize Celery tasks: {e}")

        # Clean up stale instances
        await self._repo.cleanup_stale_instances(session)

        # Load and schedule enabled jobs
        await self._sync_jobs_from_db(session)

        # Start the scheduler
        self._scheduler.start()
        self._is_running = True

        # Update instance status
        await self._repo.update_instance_status(session, self._instance_id, "running")
        await session.commit()

        # Start heartbeat task
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop(session))

        logger.info("Scheduler started")

    async def stop(self, session: AsyncSession, wait: bool = True) -> None:
        """Stop the scheduler."""
        if not self._is_running:
            return

        # Cancel heartbeat task
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass

        # Shutdown scheduler
        if self._scheduler:
            self._scheduler.shutdown(wait=wait)

        self._is_running = False

        # Update instance status
        if self._instance_id:
            await self._repo.update_instance_status(
                session, self._instance_id, "stopped"
            )
            await session.commit()

        logger.info("Scheduler stopped")

    async def _heartbeat_loop(self, session: AsyncSession) -> None:
        """Background task to update heartbeat."""
        while self._is_running:
            try:
                await asyncio.sleep(30)  # Heartbeat every 30 seconds
                if self._instance_id:
                    await self._repo.update_heartbeat(session, self._instance_id)
                    await session.commit()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")

    async def _sync_jobs_from_db(self, session: AsyncSession) -> None:
        """Load enabled jobs from database and schedule them."""
        jobs = await self._repo.get_enabled_jobs(session)

        for job in jobs:
            try:
                await self._schedule_job(job)
            except Exception as e:
                logger.error(f"Failed to schedule job {job.job_key}: {e}")

        logger.info(f"Loaded {len(jobs)} jobs from database")

    async def _schedule_job(self, job: ScheduledJob) -> None:
        """Add a job to the APScheduler."""
        if not self._scheduler:
            return

        # Get job_key and function_path from task_function
        job_key = job.job_key  # This uses the property that gets from task_function
        # This uses the property that gets from task_function
        job_function_path = job.job_function
        job_type_code = (
            job.job_type
        )  # This uses the property that gets from job_type_ref

        if not job_key or not job_function_path:
            logger.error(f"Job {job.id} has no task function defined")
            return

        # Get or import the job function
        func = self.get_job_function(job_key)
        if not func:
            func = self._import_job_function(job_function_path)
            if func:
                self.register_job_function(job_key, func)

        if not func:
            logger.error(f"No function found for job {job_key}")
            return

        # Create trigger based on job type
        if job_type_code == "interval":
            trigger = IntervalTrigger(
                seconds=job.interval_seconds or 0,
                minutes=job.interval_minutes or 0,
                hours=job.interval_hours or 0,
                days=job.interval_days or 0,
            )
        elif job_type_code == "cron":
            # Parse cron expression (minute hour day month day_of_week)
            parts = job.cron_expression.split() if job.cron_expression else []
            if len(parts) >= 5:
                trigger = CronTrigger(
                    minute=parts[0],
                    hour=parts[1],
                    day=parts[2],
                    month=parts[3],
                    day_of_week=parts[4],
                )
            else:
                logger.error(f"Invalid cron expression for job {job_key}")
                return
        else:
            logger.error(f"Unknown job type {job_type_code} for job {job_key}")
            return

        # Wrap function for execution tracking
        wrapped_func = self._create_execution_wrapper(job.id, job_key, func)

        # Get display name (from job override or task_function)
        display_name = job.get_name("en")

        # Add job to scheduler
        self._scheduler.add_job(
            wrapped_func,
            trigger,
            id=job_key,
            name=display_name,
            max_instances=job.max_instances,
            coalesce=job.coalesce,
            misfire_grace_time=job.misfire_grace_time,
            replace_existing=True,
        )

        logger.info(f"Scheduled job: {job_key}")

    def _create_execution_wrapper(
        self, job_id: str, job_key: str, func: Callable
    ) -> Callable:
        """Create a wrapper that tracks job execution."""

        async def wrapper():
            execution_id = str(uuid.uuid4())
            scheduled_at = datetime.now(timezone.utc)
            started_at = None
            completed_at = None
            error_message = None
            error_traceback_str = None
            result_summary = None

            # Import here to avoid circular imports
            from db.database import get_maria_session

            async for session in get_maria_session():
                try:
                    # Get status IDs
                    pending_status = await self._repo.get_execution_status_by_code(
                        session, "pending"
                    )
                    running_status = await self._repo.get_execution_status_by_code(
                        session, "running"
                    )
                    success_status = await self._repo.get_execution_status_by_code(
                        session, "success"
                    )
                    failed_status = await self._repo.get_execution_status_by_code(
                        session, "failed"
                    )

                    if not all(
                        [pending_status, running_status, success_status, failed_status]
                    ):
                        logger.error("Missing execution status records in database")
                        return

                    # Try to acquire lock
                    lock = await self._repo.acquire_lock(
                        session,
                        job_id,
                        execution_id,
                        self._instance_id or "unknown",
                    )

                    if not lock:
                        logger.info(
                            f"Skipping job {job_key} - lock held by another instance"
                        )
                        result_summary = "Lock held by another instance"
                        # Don't create execution record for skipped runs
                        return

                    # Create execution record
                    execution = ScheduledJobExecution(
                        job_id=job_id,
                        execution_id=execution_id,
                        scheduled_at=scheduled_at,
                        status_id=running_status.id,
                        executor_id=self._instance_id,
                        host_name=socket.gethostname(),
                    )
                    await self._repo.create_execution(session, execution)
                    await session.commit()

                    # Check if we should dispatch to Celery
                    dispatch_to_celery, is_celery_task = _get_celery_bridge()

                    # Log Celery status for debugging
                    celery_available = (
                        dispatch_to_celery is not None and is_celery_task is not None
                    )
                    is_celery_enabled_task = (
                        is_celery_task(job_key) if is_celery_task else False
                    )

                    logger.debug(
                        f"Job '{job_key}' execution context: "
                        f"celery_available={celery_available}, "
                        f"celery_enabled={settings.celery.enabled}, "
                        f"is_celery_task={is_celery_enabled_task}"
                    )

                    # Execute the job
                    started_at = datetime.now(timezone.utc)
                    final_status_id = success_status.id
                    try:
                        # Try Celery dispatch first
                        if celery_available and is_celery_enabled_task:
                            celery_task_id = dispatch_to_celery(job_key)
                            if celery_task_id:
                                result_summary = (
                                    f"Dispatched to Celery (task_id: {celery_task_id})"
                                )
                                logger.info(
                                    f"✅ Job '{job_key}' dispatched to Celery: {celery_task_id}"
                                )
                            else:
                                # Fallback to inline execution
                                logger.warning(
                                    f"⚠ Celery dispatch failed for '{job_key}', falling back to inline execution"
                                )
                                if asyncio.iscoroutinefunction(func):
                                    result = await func()
                                else:
                                    result = func()
                                result_summary = (
                                    str(result)[:500] if result else "Success"
                                )
                        else:
                            # Direct execution (Celery disabled or no task registered)
                            reason = (
                                "Celery not available"
                                if not celery_available
                                else "Task not registered as Celery task"
                            )
                            logger.info(f"📋 Running '{job_key}' inline: {reason}")
                            if asyncio.iscoroutinefunction(func):
                                result = await func()
                            else:
                                result = func()
                            result_summary = str(result)[:500] if result else "Success"
                    except Exception as e:
                        final_status_id = failed_status.id
                        error_message = str(e)
                        error_traceback_str = traceback.format_exc()
                        logger.error(f"Job {job_key} failed: {e}")

                    completed_at = datetime.now(timezone.utc)

                    # Update execution record
                    duration_ms = None
                    if started_at and completed_at:
                        duration_ms = int(
                            (completed_at - started_at).total_seconds() * 1000
                        )

                    await self._repo.update_execution(
                        session,
                        execution_id,
                        {
                            "started_at": started_at,
                            "completed_at": completed_at,
                            "duration_ms": duration_ms,
                            "status_id": final_status_id,
                            "error_message": error_message,
                            "error_traceback": error_traceback_str,
                            "result_summary": result_summary,
                        },
                    )

                    # Release lock
                    await self._repo.release_lock(session, job_id, execution_id)
                    await session.commit()

                except Exception as e:
                    logger.error(f"Error in job wrapper for {job_key}: {e}")
                    await session.rollback()

        return wrapper

    def _create_manual_execution_wrapper(
        self,
        job_id: str,
        job_key: str,
        func: Callable,
        triggered_by_user_id: str = None,
    ) -> Callable:
        """
        Create a wrapper for manual job execution that returns execution_id.
        Creates execution record with 'running' status immediately,
        then executes asynchronously.

        Args:
            job_id: Job ID
            job_key: Job key
            func: Function to execute
            triggered_by_user_id: User ID who manually triggered (None for scheduled)
        """

        async def wrapper() -> str:
            execution_id = str(uuid.uuid4())
            scheduled_at = datetime.now(timezone.utc)

            # INSTRUMENTATION POINT 3: Execution create start
            structured_logger.log_execution_create_start(
                job_id=job_id,
                job_key=job_key,
                execution_id=execution_id,
                trigger_source="MANUAL",
                triggered_by_user_id=triggered_by_user_id,
                job_function=func.__name__ if hasattr(func, "__name__") else str(func),
            )

            # Import here to avoid circular imports
            from db.database import get_maria_session

            async for session in get_maria_session():
                try:
                    # Get running status ID
                    running_status = await self._repo.get_execution_status_by_code(
                        session, "running"
                    )

                    if not running_status:
                        logger.error(
                            "Missing running execution status record in database"
                        )
                        return execution_id

                    # STEP 1: Create execution record with RUNNING status IMMEDIATELY
                    started_at = datetime.now(timezone.utc)
                    execution = ScheduledJobExecution(
                        job_id=job_id,
                        execution_id=execution_id,
                        scheduled_at=scheduled_at,
                        started_at=started_at,
                        status_id=running_status.id,  # STATUS = RUNNING
                        executor_id=self._instance_id,
                        host_name=socket.gethostname(),
                    )
                    await self._repo.create_execution(session, execution)
                    await session.commit()

                    # INSTRUMENTATION POINT 3b: Execution committed
                    structured_logger.log_execution_create_committed(
                        job_id=job_id,
                        job_key=job_key,
                        execution_id=execution_id,
                        status="RUNNING",
                        executor_id=self._instance_id,
                        host_name=socket.gethostname(),
                    )

                    # STEP 2: Update job's last_run_at timestamp
                    await self._repo.update_job(
                        session, job_id, {"last_run_at": started_at}
                    )
                    await session.commit()

                    # INSTRUMENTATION POINT 4: Background task launch
                    structured_logger.log_background_task_launch(
                        job_id=job_id,
                        job_key=job_key,
                        execution_id=execution_id,
                        triggered_by=triggered_by_user_id,
                    )

                    # STEP 3: Launch background task for actual execution
                    # (execution is already running, will transition to success/failed)
                    asyncio.create_task(
                        self._execute_job_async(
                            job_id, execution_id, job_key, func, triggered_by_user_id
                        )
                    )

                except Exception as e:
                    logger.error(f"Error creating running execution for {job_key}: {e}")
                    await session.rollback()

            return execution_id

        return wrapper

    async def _execute_job_async(
        self,
        job_id: str,
        execution_id: str,
        job_key: str,
        func: Callable,
        triggered_by_user_id: str = None,
    ) -> None:
        """
        Background task that executes the job function.
        Execution is already in 'running' state, will transition to success/failed.

        Args:
            job_id: Job ID
            execution_id: Execution ID
            job_key: Job key
            func: Function to execute
            triggered_by_user_id: User ID who manually triggered (None for scheduled)
        """
        # Import here to avoid circular imports
        from db.database import get_maria_session

        async for session in get_maria_session():
            try:
                # Get status IDs
                success_status = await self._repo.get_execution_status_by_code(
                    session, "success"
                )
                failed_status = await self._repo.get_execution_status_by_code(
                    session, "failed"
                )

                if not all([success_status, failed_status]):
                    logger.error("Missing execution status records in database")
                    return

                # INSTRUMENTATION POINT 5: Lock attempt
                structured_logger.log_lock_attempt(
                    job_id=job_id,
                    execution_id=execution_id,
                    instance_id=self._instance_id or "unknown",
                )

                # Acquire lock
                lock = await self._repo.acquire_lock(
                    session, job_id, execution_id, self._instance_id or "unknown"
                )

                if not lock:
                    # INSTRUMENTATION POINT 5b: Lock failed
                    structured_logger.log_lock_failed(
                        job_id=job_id,
                        execution_id=execution_id,
                        reason="Another instance is running this job",
                    )

                    # Lock failed - mark as failed
                    await self._repo.update_execution(
                        session,
                        execution_id,
                        {
                            "status_id": failed_status.id,
                            "completed_at": datetime.now(timezone.utc),
                            "error_message": "Could not acquire lock - another instance is running this job",
                        },
                    )
                    await session.commit()
                    logger.warning(
                        f"Could not acquire lock for job {job_key}, execution {execution_id}"
                    )
                    return

                # INSTRUMENTATION POINT 5c: Lock acquired
                structured_logger.log_lock_acquired(
                    job_id=job_id, execution_id=execution_id, lock_id=lock.id
                )

                # Execution is already in RUNNING state, just log it
                logger.info(
                    f"Job {job_key} execution {execution_id} executing (already in running state)"
                )

                # Execute job function with 15-second timeout
                JOB_EXECUTION_TIMEOUT = 15  # seconds
                started_at = datetime.now(timezone.utc)
                final_status_id = success_status.id
                error_message = None
                error_traceback_str = None
                result_summary = None
                celery_dispatched = False  # Track if dispatched to Celery
                try:
                    # Check if we should dispatch to Celery
                    dispatch_to_celery, is_celery_task = _get_celery_bridge()

                    # Log Celery status for debugging
                    celery_available = (
                        dispatch_to_celery is not None and is_celery_task is not None
                    )
                    is_celery_enabled_task = (
                        is_celery_task(job_key) if is_celery_task else False
                    )

                    logger.debug(
                        f"Job '{job_key}' execution context: "
                        f"celery_available={celery_available}, "
                        f"celery_enabled={settings.celery.enabled}, "
                        f"is_celery_task={is_celery_enabled_task}"
                    )

                    # Try Celery dispatch first
                    if celery_available and is_celery_enabled_task:
                        # INSTRUMENTATION POINT 6: Celery dispatch attempt
                        task_metadata = {
                            "job_key": job_key,
                            "job_function": func.__name__
                            if hasattr(func, "__name__")
                            else str(func),
                            "triggered_by_user_id": triggered_by_user_id,
                            "celery_enabled": settings.celery.enabled,
                        }
                        structured_logger.log_celery_dispatch_attempt(
                            job_key=job_key,
                            execution_id=execution_id,
                            task_metadata=task_metadata,
                        )

                        # Pass execution_id and user_id to Celery task
                        celery_task_id = dispatch_to_celery(
                            job_key,
                            execution_id=execution_id,
                            triggered_by_user_id=triggered_by_user_id,
                        )
                        if celery_task_id:
                            # INSTRUMENTATION POINT 6b: Celery dispatch success
                            structured_logger.log_celery_dispatch_success(
                                job_key=job_key,
                                execution_id=execution_id,
                                celery_task_id=celery_task_id,
                            )

                            # ✅ FIX: Keep status as RUNNING, don't mark as SUCCESS yet
                            # The Celery task will update the status when it actually completes
                            result_summary = (
                                f"Dispatched to Celery (task_id: {celery_task_id})"
                            )
                            celery_dispatched = True
                            logger.info(
                                f"✅ Job '{job_key}' dispatched to Celery: {celery_task_id}, "
                                f"execution will remain RUNNING until Celery task completes"
                            )
                        else:
                            # INSTRUMENTATION POINT 6c: Celery dispatch failed
                            structured_logger.log_celery_dispatch_failed(
                                job_key=job_key,
                                execution_id=execution_id,
                                error="dispatch_to_celery returned None",
                            )

                            # Fallback to inline execution
                            logger.warning(
                                f"⚠ Celery dispatch failed for '{job_key}', falling back to inline execution"
                            )
                            if asyncio.iscoroutinefunction(func):
                                result = await asyncio.wait_for(
                                    func(), timeout=JOB_EXECUTION_TIMEOUT
                                )
                            else:
                                # For sync functions, run in executor with timeout
                                loop = asyncio.get_event_loop()
                                result = await asyncio.wait_for(
                                    loop.run_in_executor(None, func),
                                    timeout=JOB_EXECUTION_TIMEOUT,
                                )
                            result_summary = str(result)[:500] if result else "Success"
                    else:
                        # Direct execution (Celery disabled or no task registered)
                        reason = (
                            "Celery not available"
                            if not celery_available
                            else "Task not registered as Celery task"
                        )
                        logger.info(f"📋 Running '{job_key}' inline: {reason}")
                        if asyncio.iscoroutinefunction(func):
                            result = await asyncio.wait_for(
                                func(), timeout=JOB_EXECUTION_TIMEOUT
                            )
                        else:
                            # For sync functions, run in executor with timeout
                            loop = asyncio.get_event_loop()
                            result = await asyncio.wait_for(
                                loop.run_in_executor(None, func),
                                timeout=JOB_EXECUTION_TIMEOUT,
                            )
                        result_summary = str(result)[:500] if result else "Success"

                except asyncio.TimeoutError:
                    final_status_id = failed_status.id
                    error_message = (
                        f"Job execution timed out after {JOB_EXECUTION_TIMEOUT} seconds"
                    )
                    error_traceback_str = None
                    logger.error(
                        f"Job {job_key} timed out after {JOB_EXECUTION_TIMEOUT}s"
                    )
                except Exception as e:
                    final_status_id = failed_status.id
                    error_message = str(e)
                    error_traceback_str = traceback.format_exc()
                    logger.error(f"Job {job_key} failed: {e}")

                # Update execution with final status
                # ✅ FIX: If dispatched to Celery, DON'T update status - leave as RUNNING
                # The Celery task will update it when it completes
                if not celery_dispatched:
                    completed_at = datetime.now(timezone.utc)
                    duration_ms = int(
                        (completed_at - started_at).total_seconds() * 1000
                    )

                    await self._repo.update_execution(
                        session,
                        execution_id,
                        {
                            "completed_at": completed_at,
                            "duration_ms": duration_ms,
                            "status_id": final_status_id,
                            "error_message": error_message,
                            "error_traceback": error_traceback_str,
                            "result_summary": result_summary,
                        },
                    )
                else:
                    # Just update result_summary to show it's been dispatched
                    await self._repo.update_execution(
                        session,
                        execution_id,
                        {
                            "result_summary": result_summary,
                        },
                    )

                # Release lock
                await self._repo.release_lock(session, job_id, execution_id)
                await session.commit()
                logger.info(
                    f"Job {job_key} execution {execution_id} completed with status: {final_status_id}"
                )

            except Exception as e:
                logger.error(f"Background execution failed for {job_key}: {e}")
                await session.rollback()

    # -------------------
    # Job Management
    # -------------------

    async def create_job(
        self,
        session: AsyncSession,
        data: ScheduledJobCreate,
        created_by_id: Optional[str] = None,
    ) -> ScheduledJob:
        """Create a new scheduled job."""
        # Validate task function exists
        task_function = await self._repo.get_task_function_by_id(
            session, data.task_function_id
        )
        if not task_function:
            raise ValidationError(
                f"Task function with ID {data.task_function_id} not found"
            )

        # Validate job type exists
        job_type = await self._repo.get_job_type_by_id(session, data.job_type_id)
        if not job_type:
            raise ValidationError(f"Job type with ID {data.job_type_id} not found")

        # Check for duplicate job (same task function already scheduled)
        existing = await self._repo.get_job_by_task_function(
            session, data.task_function_id
        )
        if existing:
            raise ValidationError(
                f"Job with task function '{task_function.key}' already exists"
            )

        job = ScheduledJob(
            task_function_id=data.task_function_id,
            job_type_id=data.job_type_id,
            name_en=data.name_en,
            name_ar=data.name_ar,
            description_en=data.description_en,
            description_ar=data.description_ar,
            interval_seconds=data.interval_seconds,
            interval_minutes=data.interval_minutes,
            interval_hours=data.interval_hours,
            interval_days=data.interval_days,
            cron_expression=data.cron_expression,
            priority=data.priority,
            max_instances=data.max_instances,
            misfire_grace_time=data.misfire_grace_time,
            coalesce=data.coalesce,
            is_enabled=data.is_enabled,
            is_primary=data.is_primary,
            created_by_id=created_by_id,
        )

        job = await self._repo.create_job(session, job)

        # Schedule if enabled and scheduler is running
        if job.is_enabled and self._is_running:
            await self._schedule_job(job)

        return job

    async def create_interval_job(
        self,
        session: AsyncSession,
        data: ScheduledJobIntervalCreate,
        created_by_id: Optional[str] = None,
    ) -> ScheduledJob:
        """Create a new interval-based job."""
        # Get interval job type
        job_type = await self._repo.get_job_type_by_code(session, "interval")
        if not job_type:
            raise ValidationError("Interval job type not found in database")

        # Create unified job data
        job_data = ScheduledJobCreate(
            task_function_id=data.task_function_id,
            job_type_id=job_type.id,
            name_en=data.name_en,
            name_ar=data.name_ar,
            description_en=data.description_en,
            description_ar=data.description_ar,
            interval_seconds=data.interval_seconds,
            interval_minutes=data.interval_minutes,
            interval_hours=data.interval_hours,
            interval_days=data.interval_days,
            priority=data.priority,
            max_instances=data.max_instances,
            misfire_grace_time=data.misfire_grace_time,
            coalesce=data.coalesce,
            is_enabled=data.is_enabled,
            is_primary=data.is_primary,
        )

        return await self.create_job(session, job_data, created_by_id)

    async def create_cron_job(
        self,
        session: AsyncSession,
        data: ScheduledJobCronCreate,
        created_by_id: Optional[str] = None,
    ) -> ScheduledJob:
        """Create a new cron-based job."""
        # Get cron job type
        job_type = await self._repo.get_job_type_by_code(session, "cron")
        if not job_type:
            raise ValidationError("Cron job type not found in database")

        # Create unified job data
        job_data = ScheduledJobCreate(
            task_function_id=data.task_function_id,
            job_type_id=job_type.id,
            name_en=data.name_en,
            name_ar=data.name_ar,
            description_en=data.description_en,
            description_ar=data.description_ar,
            cron_expression=data.cron_expression,
            priority=data.priority,
            max_instances=data.max_instances,
            misfire_grace_time=data.misfire_grace_time,
            coalesce=data.coalesce,
            is_enabled=data.is_enabled,
            is_primary=data.is_primary,
        )

        return await self.create_job(session, job_data, created_by_id)

    async def get_job(self, session: AsyncSession, job_id: str) -> ScheduledJobResponse:
        """Get a job by ID with computed fields."""
        job = await self._repo.get_job_by_id(session, job_id)
        if not job:
            raise NotFoundError(entity="ScheduledJob", identifier=job_id)

        return await self._to_job_response(session, job)

    async def list_jobs(
        self,
        session: AsyncSession,
        page: int = 1,
        per_page: int = 25,
        is_enabled: Optional[bool] = None,
        job_type_id: Optional[int] = None,
        task_function_id: Optional[int] = None,
    ) -> Tuple[List[ScheduledJobResponse], int]:
        """List jobs with pagination."""
        jobs, total = await self._repo.list_jobs(
            session, page, per_page, is_enabled, job_type_id, task_function_id
        )

        # Get current execution status for all jobs in one query
        execution_status_map = await self._enrich_jobs_with_execution_status(
            session, jobs
        )

        # Add execution status to each job object before converting to response
        for job in jobs:
            if job.id in execution_status_map:
                status_code, execution_id = execution_status_map[job.id]
                setattr(job, "current_execution_status", status_code)
                setattr(job, "current_execution_id", execution_id)
            else:
                setattr(job, "current_execution_status", None)
                setattr(job, "current_execution_id", None)

        responses = []
        for job in jobs:
            responses.append(await self._to_job_response(session, job))

        return responses, total

    async def _enrich_jobs_with_execution_status(
        self, session: AsyncSession, jobs: list[ScheduledJob]
    ) -> dict[str, tuple[str, str]]:
        """
        Get current execution status for a list of jobs.
        Returns a dict mapping job_id -> (status_code, execution_id).
        """
        if not jobs:
            return {}

        # Get all pending/running executions for these jobs
        job_ids = [job.id for job in jobs]

        # First, get the status IDs for pending and running
        pending_status = await self._repo.get_execution_status_by_code(
            session, "pending"
        )
        running_status = await self._repo.get_execution_status_by_code(
            session, "running"
        )

        # Query executions using status_id directly (more efficient)
        stmt = (
            select(ScheduledJobExecution)
            .where(
                and_(
                    ScheduledJobExecution.job_id.in_(job_ids),
                    ScheduledJobExecution.status_id.in_(
                        [pending_status.id, running_status.id]
                    ),
                )
            )
            .options(selectinload(ScheduledJobExecution.status_ref))
        )

        result = await session.execute(stmt)
        executions = list(result.scalars().all())

        # Create map of job_id -> (status_code, execution_id)
        execution_map = {}
        for exec in executions:
            execution_map[exec.job_id] = (exec.status_ref.code, exec.execution_id)

        return execution_map

    async def update_job(
        self,
        session: AsyncSession,
        job_id: str,
        data: ScheduledJobUpdate,
        updated_by_id: Optional[str] = None,
    ) -> ScheduledJob:
        """Update an existing job."""
        update_dict = data.model_dump(exclude_unset=True)
        update_dict["updated_by_id"] = updated_by_id

        # Validate task function if changing
        if "task_function_id" in update_dict:
            task_function = await self._repo.get_task_function_by_id(
                session, update_dict["task_function_id"]
            )
            if not task_function:
                raise ValidationError(
                    f"Task function with ID {update_dict['task_function_id']} not found"
                )

        # Validate job type if changing
        if "job_type_id" in update_dict:
            job_type = await self._repo.get_job_type_by_id(
                session, update_dict["job_type_id"]
            )
            if not job_type:
                raise ValidationError(
                    f"Job type with ID {update_dict['job_type_id']} not found"
                )

        job = await self._repo.update_job(session, job_id, update_dict)

        # Reschedule if needed
        if self._is_running and self._scheduler:
            # Get old job_key to remove
            job_key = job.job_key
            if job_key and self._scheduler.get_job(job_key):
                self._scheduler.remove_job(job_key)

            # Re-add if enabled
            if job.is_enabled:
                await self._schedule_job(job)

        return job

    async def delete_job(self, session: AsyncSession, job_id: str) -> ScheduledJob:
        """Soft delete a job."""
        job = await self._repo.get_job_by_id(session, job_id)
        if not job:
            raise NotFoundError(entity="ScheduledJob", identifier=job_id)

        # Remove from scheduler
        if self._is_running and self._scheduler:
            job_key = job.job_key
            if job_key and self._scheduler.get_job(job_key):
                self._scheduler.remove_job(job_key)

        return await self._repo.soft_delete_job(session, job_id)

    # -------------------
    # Job Actions
    # -------------------

    async def enable_job(self, session: AsyncSession, job_id: str) -> ScheduledJob:
        """Enable a job."""
        job = await self._repo.update_job(session, job_id, {"is_enabled": True})

        # Add to scheduler
        if self._is_running:
            await self._schedule_job(job)

        return job

    async def disable_job(self, session: AsyncSession, job_id: str) -> ScheduledJob:
        """Disable a job."""
        job = await self._repo.get_job_by_id(session, job_id)
        if not job:
            raise NotFoundError(entity="ScheduledJob", identifier=job_id)

        # Remove from scheduler
        if self._is_running and self._scheduler:
            job_key = job.job_key
            if job_key and self._scheduler.get_job(job_key):
                self._scheduler.remove_job(job_key)

        return await self._repo.update_job(session, job_id, {"is_enabled": False})

    async def trigger_job_now(
        self, session: AsyncSession, job_id: str, triggered_by_user_id: str = None
    ) -> tuple[str, ScheduledJob]:
        """
        Trigger a job to run immediately.

        Args:
            session: Async database session
            job_id: Job ID to trigger
            triggered_by_user_id: User ID who manually triggered (None for scheduled)

        Returns (execution_id, updated_job_record).
        """
        job = await self._repo.get_job_by_id(session, job_id)
        if not job:
            raise NotFoundError(entity="ScheduledJob", identifier=job_id)

        job_key = job.job_key
        job_function_path = job.job_function

        # Check if job is already running or pending
        running_execution = await self._repo.get_running_execution(session, job_id)

        # INSTRUMENTATION POINT 2: Duplicate check logging
        structured_logger.log_duplicate_check(
            job_id=job_id,
            job_key=job_key,
            running_execution_found=running_execution is not None,
            running_execution_id=running_execution.execution_id
            if running_execution
            else None,
            triggered_by_user_id=triggered_by_user_id,
        )

        if running_execution:
            raise ValidationError(
                f"Job '{job_key}' is already {running_execution.status}. "
                f"Please wait for it to complete."
            )

        # Get the job function
        func = self.get_job_function(job_key)
        if not func:
            func = self._import_job_function(job_function_path)

        if not func:
            raise ValidationError(f"No function found for job '{job_key}'")

        # Run the wrapper (creates running execution and launches background task)
        wrapper = self._create_manual_execution_wrapper(
            job.id, job_key, func, triggered_by_user_id
        )
        execution_id = await wrapper()

        # Refresh job to get updated last_run_at
        await session.refresh(job)

        # Add current execution status (we just created a running execution)
        # These are computed fields not stored in the model, so we set them as attributes
        setattr(job, "current_execution_status", "running")
        setattr(job, "current_execution_id", execution_id)

        logger.info(
            f"[trigger_job_now] Set execution status on job {job.id}: "
            f"status={getattr(job, 'current_execution_status', None)}, "
            f"exec_id={getattr(job, 'current_execution_id', None)}"
        )

        return execution_id, job

    async def pause_job(self, session: AsyncSession, job_id: str) -> ScheduledJob:
        """Pause a job (keep enabled but don't run)."""
        job = await self._repo.get_job_by_id(session, job_id)
        if not job:
            raise NotFoundError(entity="ScheduledJob", identifier=job_id)

        # Pause in scheduler
        if self._is_running and self._scheduler:
            job_key = job.job_key
            if job_key:
                apscheduler_job = self._scheduler.get_job(job_key)
                if apscheduler_job:
                    apscheduler_job.pause()

        return job

    async def resume_job(self, session: AsyncSession, job_id: str) -> ScheduledJob:
        """Resume a paused job."""
        job = await self._repo.get_job_by_id(session, job_id)
        if not job:
            raise NotFoundError(entity="ScheduledJob", identifier=job_id)

        # Resume in scheduler
        if self._is_running and self._scheduler:
            job_key = job.job_key
            if job_key:
                apscheduler_job = self._scheduler.get_job(job_key)
                if apscheduler_job:
                    apscheduler_job.resume()

        return job

    # -------------------
    # Execution History
    # -------------------

    async def get_job_history(
        self,
        session: AsyncSession,
        job_id: str,
        status_id: Optional[int] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        page: int = 1,
        per_page: int = 25,
    ) -> Tuple[List[JobExecutionResponse], int]:
        """Get execution history for a job."""
        executions, total = await self._repo.list_job_executions(
            session, job_id, status_id, from_date, to_date, page, per_page
        )

        responses = [await self._to_execution_response(ex) for ex in executions]

        return responses, total

    async def get_all_history(
        self,
        session: AsyncSession,
        status_id: Optional[int] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        page: int = 1,
        per_page: int = 25,
    ) -> Tuple[List[JobExecutionResponse], int]:
        """Get execution history across all jobs."""
        executions, total = await self._repo.list_job_executions(
            session, None, status_id, from_date, to_date, page, per_page
        )

        responses = [await self._to_execution_response(ex) for ex in executions]

        return responses, total

    # -------------------
    # Status and Cleanup
    # -------------------

    async def get_status(self, session: AsyncSession) -> SchedulerStatusResponse:
        """Get overall scheduler status."""
        stats = await self._repo.get_job_stats(session)
        active_instances = await self._repo.get_active_instances(session)
        recent_executions = await self._repo.get_recent_executions(session, 5)

        instance_responses = [
            SchedulerInstanceResponse.model_validate(inst, from_attributes=True)
            for inst in active_instances
        ]

        execution_responses = [
            await self._to_execution_response(ex) for ex in recent_executions
        ]

        # Get next scheduled job
        next_job = None
        if self._is_running and self._scheduler:
            jobs = self._scheduler.get_jobs()
            if jobs:
                # Sort by next run time
                sorted_jobs = sorted(
                    jobs,
                    key=lambda j: j.next_run_time
                    or datetime.max.replace(tzinfo=timezone.utc),
                )
                if sorted_jobs and sorted_jobs[0].next_run_time:
                    # Find job by task function key
                    job_key = sorted_jobs[0].id
                    task_function = await self._repo.get_task_function_by_key(
                        session, job_key
                    )
                    if task_function:
                        job = await self._repo.get_job_by_task_function(
                            session, task_function.id
                        )
                        if job:
                            next_job = await self._to_job_response(session, job)

        return SchedulerStatusResponse(
            is_running=self._is_running,
            total_jobs=stats["total_jobs"],
            enabled_jobs=stats["enabled_jobs"],
            disabled_jobs=stats["disabled_jobs"],
            active_instances=instance_responses,
            recent_executions=execution_responses,
            next_scheduled_job=next_job,
        )

    async def cleanup_history(
        self, session: AsyncSession, retention_days: int = 30
    ) -> dict:
        """Clean up old execution history and stale data."""
        deleted_executions = await self._repo.cleanup_old_executions(
            session, retention_days
        )
        deleted_locks = await self._repo.cleanup_expired_locks(session)
        deleted_instances = await self._repo.cleanup_stale_instances(session)

        await session.commit()

        return {
            "deleted_executions": deleted_executions,
            "deleted_locks": deleted_locks,
            "deleted_instances": deleted_instances,
        }

    # -------------------
    # Helper Methods
    # -------------------

    async def _to_job_response(
        self, session: AsyncSession, job: ScheduledJob
    ) -> ScheduledJobResponse:
        """Convert ScheduledJob to response with computed fields."""
        # Get last execution
        last_execution = await self._repo.get_last_execution(session, job.id)

        # Get next run time from scheduler
        next_run_time = None
        job_key = job.job_key
        if self._is_running and self._scheduler and job_key:
            apscheduler_job = self._scheduler.get_job(job_key)
            if apscheduler_job:
                next_run_time = apscheduler_job.next_run_time

        # For last_run_time, prioritize job.last_run_at (updated on manual trigger)
        # Fallback to last execution's timestamp if last_run_at is None
        last_run_time = job.last_run_at
        last_run_status = None
        if last_execution:
            # If no last_run_at, use execution timestamp as fallback
            if not last_run_time:
                last_run_time = last_execution.completed_at or last_execution.started_at
            last_run_status = last_execution.status

        # Build task function response if loaded
        task_function_response = None
        if job.task_function:
            task_function_response = TaskFunctionResponse.model_validate(
                job.task_function, from_attributes=True
            )

        # Build job type response if loaded
        job_type_response = None
        if job.job_type_ref:
            job_type_response = SchedulerJobTypeResponse.model_validate(
                job.job_type_ref, from_attributes=True
            )

        # Get current execution status (might be set via setattr on the job object)
        current_execution_status = getattr(job, "current_execution_status", None)
        current_execution_id = getattr(job, "current_execution_id", None)

        # If not set via setattr, query from database (like list_jobs does)
        if current_execution_status is None:
            execution_map = await self._enrich_jobs_with_execution_status(
                session, [job]
            )
            if job.id in execution_map:
                current_execution_status, current_execution_id = execution_map[job.id]

        logger.info(
            f"[_to_job_response] Job {job.id}: "
            f"current_execution_status={current_execution_status}, "
            f"current_execution_id={current_execution_id}"
        )

        return ScheduledJobResponse(
            id=job.id,
            task_function_id=job.task_function_id,
            job_type_id=job.job_type_id,
            job_key=job.job_key,
            job_function=job.job_function,
            job_type=job.job_type,
            name_en=job.get_name("en"),
            name_ar=job.get_name("ar"),
            description_en=job.get_description("en"),
            description_ar=job.get_description("ar"),
            interval_seconds=job.interval_seconds,
            interval_minutes=job.interval_minutes,
            interval_hours=job.interval_hours,
            interval_days=job.interval_days,
            cron_expression=job.cron_expression,
            priority=job.priority,
            max_instances=job.max_instances,
            misfire_grace_time=job.misfire_grace_time,
            coalesce=job.coalesce,
            is_enabled=job.is_enabled,
            is_active=job.is_active,
            is_primary=job.is_primary,
            created_at=job.created_at,
            updated_at=job.updated_at,
            last_run_at=job.last_run_at,
            created_by_id=job.created_by_id,
            updated_by_id=job.updated_by_id,
            task_function=task_function_response,
            job_type_ref=job_type_response,
            next_run_time=next_run_time,
            last_run_time=last_run_time,
            last_run_status=last_run_status,
            current_execution_status=current_execution_status,
            current_execution_id=current_execution_id,
        )

    async def _to_execution_response(
        self, execution: ScheduledJobExecution
    ) -> JobExecutionResponse:
        """Convert ScheduledJobExecution to response."""
        # Build status response if loaded
        status_response = None
        status_code = ""
        status_name_en = None
        status_name_ar = None

        if execution.status_ref:
            status_response = SchedulerExecutionStatusResponse.model_validate(
                execution.status_ref, from_attributes=True
            )
            status_code = execution.status_ref.code
            status_name_en = execution.status_ref.name_en
            status_name_ar = execution.status_ref.name_ar

        return JobExecutionResponse(
            id=execution.id,
            job_id=execution.job_id,
            execution_id=execution.execution_id,
            run_id=execution.run_id,
            scheduled_at=execution.scheduled_at,
            started_at=execution.started_at,
            completed_at=execution.completed_at,
            duration_ms=execution.duration_ms,
            status_id=execution.status_id,
            status=status_code,
            status_name_en=status_name_en,
            status_name_ar=status_name_ar,
            error_message=execution.error_message,
            error_traceback=execution.error_traceback,
            result_summary=execution.result_summary,
            executor_id=execution.executor_id,
            host_name=execution.host_name,
            created_at=execution.created_at,
            status_ref=status_response,
        )


# Singleton accessor
def get_scheduler_service() -> SchedulerService:
    """Get the singleton scheduler service instance."""
    return SchedulerService.get_instance()


# Cleanup job function (can be scheduled as a job itself)
async def cleanup_history_job() -> str:
    """Job function to clean up old execution history."""
    from db.database import get_maria_session

    async for session in get_maria_session():
        service = get_scheduler_service()
        result = await service.cleanup_history(session, retention_days=30)
        return f"Cleaned up: {result['deleted_executions']} executions, {result['deleted_locks']} locks, {result['deleted_instances']} instances"
