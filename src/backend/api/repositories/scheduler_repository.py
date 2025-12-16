"""Scheduler Repository for APScheduler task management."""

import logging
import socket
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.exceptions import DatabaseError, NotFoundError
from db.models import (
    ScheduledJob,
    ScheduledJobExecution,
    ScheduledJobLock,
    SchedulerInstance,
    TaskFunction,
    SchedulerJobType,
    SchedulerExecutionStatus,
)

logger = logging.getLogger(__name__)


class SchedulerRepository:
    """Repository for scheduler-related database operations."""

    def __init__(self):
        pass

    # -------------------
    # Lookup Table Operations
    # -------------------

    async def list_task_functions(
        self, session: AsyncSession, is_active: Optional[bool] = True
    ) -> List[TaskFunction]:
        """Get all task functions."""
        query = select(TaskFunction)
        if is_active is not None:
            query = query.where(TaskFunction.is_active == is_active)
        query = query.order_by(TaskFunction.name_en)
        result = await session.execute(query)
        return list(result.scalars().all())

    async def get_task_function_by_id(
        self, session: AsyncSession, task_function_id: int
    ) -> Optional[TaskFunction]:
        """Get a task function by ID."""
        result = await session.execute(
            select(TaskFunction).where(TaskFunction.id == task_function_id)
        )
        return result.scalar_one_or_none()

    async def get_task_function_by_key(
        self, session: AsyncSession, key: str
    ) -> Optional[TaskFunction]:
        """Get a task function by its unique key."""
        result = await session.execute(
            select(TaskFunction).where(TaskFunction.key == key)
        )
        return result.scalar_one_or_none()

    async def list_job_types(
        self, session: AsyncSession, is_active: Optional[bool] = True
    ) -> List[SchedulerJobType]:
        """Get all job types."""
        query = select(SchedulerJobType)
        if is_active is not None:
            query = query.where(SchedulerJobType.is_active == is_active)
        query = query.order_by(SchedulerJobType.sort_order)
        result = await session.execute(query)
        return list(result.scalars().all())

    async def get_job_type_by_id(
        self, session: AsyncSession, job_type_id: int
    ) -> Optional[SchedulerJobType]:
        """Get a job type by ID."""
        result = await session.execute(
            select(SchedulerJobType).where(SchedulerJobType.id == job_type_id)
        )
        return result.scalar_one_or_none()

    async def get_job_type_by_code(
        self, session: AsyncSession, code: str
    ) -> Optional[SchedulerJobType]:
        """Get a job type by its code."""
        result = await session.execute(
            select(SchedulerJobType).where(SchedulerJobType.code == code)
        )
        return result.scalar_one_or_none()

    async def list_execution_statuses(
        self, session: AsyncSession, is_active: Optional[bool] = True
    ) -> List[SchedulerExecutionStatus]:
        """Get all execution statuses."""
        query = select(SchedulerExecutionStatus)
        if is_active is not None:
            query = query.where(SchedulerExecutionStatus.is_active == is_active)
        query = query.order_by(SchedulerExecutionStatus.sort_order)
        result = await session.execute(query)
        return list(result.scalars().all())

    async def get_execution_status_by_id(
        self, session: AsyncSession, status_id: int
    ) -> Optional[SchedulerExecutionStatus]:
        """Get an execution status by ID."""
        result = await session.execute(
            select(SchedulerExecutionStatus).where(SchedulerExecutionStatus.id == status_id)
        )
        return result.scalar_one_or_none()

    async def get_execution_status_by_code(
        self, session: AsyncSession, code: str
    ) -> Optional[SchedulerExecutionStatus]:
        """Get an execution status by its code."""
        result = await session.execute(
            select(SchedulerExecutionStatus).where(SchedulerExecutionStatus.code == code)
        )
        return result.scalar_one_or_none()

    # -------------------
    # Job CRUD Operations
    # -------------------

    async def create_job(
        self, session: AsyncSession, job: ScheduledJob
    ) -> ScheduledJob:
        """Create a new scheduled job."""
        try:
            session.add(job)
            await session.flush()
            await session.refresh(job, ["task_function", "job_type_ref"])
            return job
        except Exception as e:
            await session.rollback()
            raise DatabaseError(f"Failed to create scheduled job: {str(e)}")

    async def get_job_by_id(
        self, session: AsyncSession, job_id: str, include_relations: bool = True
    ) -> Optional[ScheduledJob]:
        """Get a job by its ID."""
        query = select(ScheduledJob).where(
            and_(ScheduledJob.id == job_id, ScheduledJob.is_active)
        )
        if include_relations:
            query = query.options(
                selectinload(ScheduledJob.task_function),
                selectinload(ScheduledJob.job_type_ref),
            )
        result = await session.execute(query)
        return result.scalar_one_or_none()

    async def get_job_by_task_function(
        self, session: AsyncSession, task_function_id: int
    ) -> Optional[ScheduledJob]:
        """Get a job by its task function ID."""
        result = await session.execute(
            select(ScheduledJob)
            .where(
                and_(
                    ScheduledJob.task_function_id == task_function_id,
                    ScheduledJob.is_active,
                )
            )
            .options(
                selectinload(ScheduledJob.task_function),
                selectinload(ScheduledJob.job_type_ref),
            )
        )
        return result.scalar_one_or_none()

    async def list_jobs(
        self,
        session: AsyncSession,
        page: int = 1,
        per_page: int = 25,
        is_enabled: Optional[bool] = None,
        job_type_id: Optional[int] = None,
        task_function_id: Optional[int] = None,
    ) -> Tuple[List[ScheduledJob], int]:
        """List jobs with pagination and filters."""
        from core.pagination import calculate_offset

        query = (
            select(ScheduledJob)
            .where(ScheduledJob.is_active)
            .options(
                selectinload(ScheduledJob.task_function),
                selectinload(ScheduledJob.job_type_ref),
            )
        )

        if is_enabled is not None:
            query = query.where(ScheduledJob.is_enabled == is_enabled)
        if job_type_id is not None:
            query = query.where(ScheduledJob.job_type_id == job_type_id)
        if task_function_id is not None:
            query = query.where(ScheduledJob.task_function_id == task_function_id)

        # Order by priority (desc), then by task function name
        query = query.order_by(ScheduledJob.priority.desc(), ScheduledJob.created_at.desc())

        # Count query
        count_query = select(func.count()).select_from(
            select(ScheduledJob.id)
            .where(ScheduledJob.is_active)
            .where(True if is_enabled is None else ScheduledJob.is_enabled == is_enabled)
            .where(True if job_type_id is None else ScheduledJob.job_type_id == job_type_id)
            .where(True if task_function_id is None else ScheduledJob.task_function_id == task_function_id)
            .subquery()
        )
        count_result = await session.execute(count_query)
        total = count_result.scalar() or 0

        # Paginate
        offset = calculate_offset(page, per_page)
        result = await session.execute(query.offset(offset).limit(per_page))
        return list(result.scalars().all()), total

    async def get_enabled_jobs(
        self, session: AsyncSession
    ) -> List[ScheduledJob]:
        """Get all enabled and active jobs."""
        result = await session.execute(
            select(ScheduledJob)
            .where(
                and_(
                    ScheduledJob.is_active,
                    ScheduledJob.is_enabled,
                )
            )
            .options(
                selectinload(ScheduledJob.task_function),
                selectinload(ScheduledJob.job_type_ref),
            )
            .order_by(ScheduledJob.priority.desc())
        )
        return list(result.scalars().all())

    async def update_job(
        self, session: AsyncSession, job_id: str, update_data: dict
    ) -> ScheduledJob:
        """Update an existing job."""
        job = await self.get_job_by_id(session, job_id, include_relations=False)
        if not job:
            raise NotFoundError(entity="ScheduledJob", identifier=job_id)

        try:
            for key, value in update_data.items():
                if value is not None and hasattr(job, key):
                    setattr(job, key, value)

            await session.flush()
            await session.refresh(job, ["task_function", "job_type_ref"])
            return job
        except Exception as e:
            await session.rollback()
            raise DatabaseError(f"Failed to update scheduled job: {str(e)}")

    async def soft_delete_job(
        self, session: AsyncSession, job_id: str
    ) -> ScheduledJob:
        """Soft delete a job by setting is_active to False."""
        job = await self.get_job_by_id(session, job_id, include_relations=False)
        if not job:
            raise NotFoundError(entity="ScheduledJob", identifier=job_id)

        try:
            job.is_active = False
            job.is_enabled = False
            await session.flush()
            return job
        except Exception as e:
            await session.rollback()
            raise DatabaseError(f"Failed to delete scheduled job: {str(e)}")

    # -------------------
    # Execution Operations
    # -------------------

    async def create_execution(
        self, session: AsyncSession, execution: ScheduledJobExecution
    ) -> ScheduledJobExecution:
        """Create a new execution record."""
        try:
            session.add(execution)
            await session.flush()
            await session.refresh(execution, ["status_ref"])
            return execution
        except Exception as e:
            await session.rollback()
            raise DatabaseError(f"Failed to create execution record: {str(e)}")

    async def get_execution_by_id(
        self, session: AsyncSession, execution_id: str, include_relations: bool = True
    ) -> Optional[ScheduledJobExecution]:
        """Get an execution by its execution_id."""
        query = select(ScheduledJobExecution).where(
            ScheduledJobExecution.execution_id == execution_id
        )
        if include_relations:
            query = query.options(selectinload(ScheduledJobExecution.status_ref))
        result = await session.execute(query)
        return result.scalar_one_or_none()

    async def update_execution(
        self, session: AsyncSession, execution_id: str, update_data: dict
    ) -> ScheduledJobExecution:
        """Update an existing execution record."""
        execution = await self.get_execution_by_id(session, execution_id, include_relations=False)
        if not execution:
            raise NotFoundError(entity="ScheduledJobExecution", identifier=execution_id)

        try:
            for key, value in update_data.items():
                if value is not None and hasattr(execution, key):
                    setattr(execution, key, value)

            await session.flush()
            await session.refresh(execution, ["status_ref"])
            return execution
        except Exception as e:
            await session.rollback()
            raise DatabaseError(f"Failed to update execution record: {str(e)}")

    async def list_job_executions(
        self,
        session: AsyncSession,
        job_id: Optional[str] = None,
        status_id: Optional[int] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        page: int = 1,
        per_page: int = 25,
    ) -> Tuple[List[ScheduledJobExecution], int]:
        """List execution history with filters."""
        from core.pagination import calculate_offset

        query = select(ScheduledJobExecution).options(
            selectinload(ScheduledJobExecution.status_ref)
        )

        if job_id:
            query = query.where(ScheduledJobExecution.job_id == job_id)
        if status_id is not None:
            query = query.where(ScheduledJobExecution.status_id == status_id)
        if from_date:
            query = query.where(ScheduledJobExecution.scheduled_at >= from_date)
        if to_date:
            query = query.where(ScheduledJobExecution.scheduled_at <= to_date)

        # Order by scheduled_at descending (most recent first)
        query = query.order_by(ScheduledJobExecution.scheduled_at.desc())

        # Count query
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await session.execute(count_query)
        total = count_result.scalar() or 0

        # Paginate
        offset = calculate_offset(page, per_page)
        result = await session.execute(query.offset(offset).limit(per_page))
        return list(result.scalars().all()), total

    async def get_last_execution(
        self, session: AsyncSession, job_id: str
    ) -> Optional[ScheduledJobExecution]:
        """Get the most recent execution for a job."""
        result = await session.execute(
            select(ScheduledJobExecution)
            .where(ScheduledJobExecution.job_id == job_id)
            .options(selectinload(ScheduledJobExecution.status_ref))
            .order_by(ScheduledJobExecution.scheduled_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_running_execution(
        self, session: AsyncSession, job_id: str
    ) -> Optional[ScheduledJobExecution]:
        """Get any running or pending execution for a job."""
        # Get running and pending status IDs
        running_status = await self.get_execution_status_by_code(session, "running")
        pending_status = await self.get_execution_status_by_code(session, "pending")

        status_ids = []
        if running_status:
            status_ids.append(running_status.id)
        if pending_status:
            status_ids.append(pending_status.id)

        if not status_ids:
            return None

        result = await session.execute(
            select(ScheduledJobExecution)
            .where(ScheduledJobExecution.job_id == job_id)
            .where(ScheduledJobExecution.status_id.in_(status_ids))
            .options(selectinload(ScheduledJobExecution.status_ref))
            .order_by(ScheduledJobExecution.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_recent_executions(
        self, session: AsyncSession, limit: int = 10
    ) -> List[ScheduledJobExecution]:
        """Get recent executions across all jobs."""
        result = await session.execute(
            select(ScheduledJobExecution)
            .options(selectinload(ScheduledJobExecution.status_ref))
            .order_by(ScheduledJobExecution.scheduled_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def cleanup_old_executions(
        self, session: AsyncSession, retention_days: int = 30
    ) -> int:
        """Delete execution records older than retention_days."""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)

        try:
            # Get count first
            count_query = select(func.count()).select_from(
                select(ScheduledJobExecution)
                .where(ScheduledJobExecution.created_at < cutoff_date)
                .subquery()
            )
            count_result = await session.execute(count_query)
            count = count_result.scalar() or 0

            if count > 0:
                # Delete in batches to avoid locking
                from sqlalchemy import delete
                await session.execute(
                    delete(ScheduledJobExecution).where(
                        ScheduledJobExecution.created_at < cutoff_date
                    )
                )
                await session.flush()

            return count
        except Exception as e:
            await session.rollback()
            raise DatabaseError(f"Failed to cleanup old executions: {str(e)}")

    # -------------------
    # Lock Operations
    # -------------------

    async def acquire_lock(
        self,
        session: AsyncSession,
        job_id: str,
        execution_id: str,
        executor_id: str,
        lock_duration_seconds: int = 3600,
    ) -> Optional[ScheduledJobLock]:
        """
        Attempt to acquire a lock for a job execution.
        Returns the lock if successful, None if lock already held.
        """
        host_name = socket.gethostname()
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=lock_duration_seconds)

        # Check for existing active lock
        existing = await session.execute(
            select(ScheduledJobLock).where(
                and_(
                    ScheduledJobLock.job_id == job_id,
                    ScheduledJobLock.released_at.is_(None),
                    ScheduledJobLock.expires_at > now,
                )
            )
        )
        existing_lock = existing.scalar_one_or_none()

        if existing_lock:
            logger.debug(
                f"Lock already held for job {job_id} by {existing_lock.executor_id}"
            )
            return None

        # Create new lock
        try:
            lock = ScheduledJobLock(
                job_id=job_id,
                execution_id=execution_id,
                executor_id=executor_id,
                host_name=host_name,
                expires_at=expires_at,
            )
            session.add(lock)
            await session.flush()
            return lock
        except Exception as e:
            # Another instance may have acquired the lock
            logger.warning(f"Failed to acquire lock for job {job_id}: {e}")
            await session.rollback()
            return None

    async def release_lock(
        self, session: AsyncSession, job_id: str, execution_id: str
    ) -> bool:
        """Release a lock for a job execution."""
        try:
            result = await session.execute(
                select(ScheduledJobLock).where(
                    and_(
                        ScheduledJobLock.job_id == job_id,
                        ScheduledJobLock.execution_id == execution_id,
                        ScheduledJobLock.released_at.is_(None),
                    )
                )
            )
            lock = result.scalar_one_or_none()

            if lock:
                lock.released_at = datetime.now(timezone.utc)
                await session.flush()
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to release lock for job {job_id}: {e}")
            return False

    async def cleanup_expired_locks(self, session: AsyncSession) -> int:
        """Clean up expired locks."""
        now = datetime.now(timezone.utc)

        try:
            # Update expired locks to released
            result = await session.execute(
                select(ScheduledJobLock).where(
                    and_(
                        ScheduledJobLock.released_at.is_(None),
                        ScheduledJobLock.expires_at < now,
                    )
                )
            )
            expired_locks = list(result.scalars().all())

            for lock in expired_locks:
                lock.released_at = now

            await session.flush()
            return len(expired_locks)
        except Exception as e:
            await session.rollback()
            raise DatabaseError(f"Failed to cleanup expired locks: {str(e)}")

    # -------------------
    # Instance Operations
    # -------------------

    async def register_instance(
        self,
        session: AsyncSession,
        instance_name: str,
        mode: str,
    ) -> SchedulerInstance:
        """Register a new scheduler instance."""
        import os

        try:
            instance = SchedulerInstance(
                id=str(uuid.uuid4()),
                instance_name=instance_name,
                host_name=socket.gethostname(),
                process_id=os.getpid(),
                mode=mode,
                status="starting",
                last_heartbeat=datetime.now(timezone.utc),
            )
            session.add(instance)
            await session.flush()
            return instance
        except Exception as e:
            await session.rollback()
            raise DatabaseError(f"Failed to register scheduler instance: {str(e)}")

    async def update_heartbeat(
        self, session: AsyncSession, instance_id: str
    ) -> bool:
        """Update the heartbeat timestamp for an instance."""
        try:
            result = await session.execute(
                select(SchedulerInstance).where(SchedulerInstance.id == instance_id)
            )
            instance = result.scalar_one_or_none()

            if instance:
                instance.last_heartbeat = datetime.now(timezone.utc)
                await session.flush()
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to update heartbeat for instance {instance_id}: {e}")
            return False

    async def update_instance_status(
        self, session: AsyncSession, instance_id: str, status: str
    ) -> bool:
        """Update the status of an instance."""
        try:
            result = await session.execute(
                select(SchedulerInstance).where(SchedulerInstance.id == instance_id)
            )
            instance = result.scalar_one_or_none()

            if instance:
                instance.status = status
                if status == "stopped":
                    instance.stopped_at = datetime.now(timezone.utc)
                await session.flush()
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to update status for instance {instance_id}: {e}")
            return False

    async def get_active_instances(
        self, session: AsyncSession
    ) -> List[SchedulerInstance]:
        """Get all active scheduler instances."""
        result = await session.execute(
            select(SchedulerInstance).where(
                SchedulerInstance.status.in_(["starting", "running", "paused"])
            ).order_by(SchedulerInstance.started_at.desc())
        )
        return list(result.scalars().all())

    async def cleanup_stale_instances(
        self, session: AsyncSession, stale_threshold_minutes: int = 5
    ) -> int:
        """Mark instances with no heartbeat as stopped."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=stale_threshold_minutes)

        try:
            result = await session.execute(
                select(SchedulerInstance).where(
                    and_(
                        SchedulerInstance.status.in_(["starting", "running", "paused"]),
                        SchedulerInstance.last_heartbeat < cutoff_time,
                    )
                )
            )
            stale_instances = list(result.scalars().all())

            now = datetime.now(timezone.utc)
            for instance in stale_instances:
                instance.status = "stopped"
                instance.stopped_at = now
                logger.warning(
                    f"Marked stale instance {instance.instance_name} as stopped"
                )

            await session.flush()
            return len(stale_instances)
        except Exception as e:
            await session.rollback()
            raise DatabaseError(f"Failed to cleanup stale instances: {str(e)}")

    # -------------------
    # Statistics
    # -------------------

    async def get_job_stats(self, session: AsyncSession) -> dict:
        """Get statistics about scheduled jobs."""
        total_query = select(func.count()).where(ScheduledJob.is_active)
        enabled_query = select(func.count()).where(
            and_(ScheduledJob.is_active, ScheduledJob.is_enabled)
        )

        total_result = await session.execute(total_query)
        enabled_result = await session.execute(enabled_query)

        total = total_result.scalar() or 0
        enabled = enabled_result.scalar() or 0

        return {
            "total_jobs": total,
            "enabled_jobs": enabled,
            "disabled_jobs": total - enabled,
        }
