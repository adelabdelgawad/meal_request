# Job Scheduler Implementation Patterns

Critical patterns that MUST be followed when working with the scheduler.

## Celery Task Pattern (MANDATORY)

When creating Celery tasks that use async database operations, follow this exact pattern to avoid event loop conflicts.

### The Problem

Celery workers run with gevent (`-P gevent`) which patches asyncio and creates an event loop. Simply using `asyncio.run()` causes:
- `RuntimeError: Task got Future attached to a different loop`
- `Event loop is closed` errors
- Database connection cleanup failures

### Required Pattern

```python
from celery import shared_task
import logging

logger = logging.getLogger(__name__)


def _run_async(coro):
    """
    Run a coroutine, handling both standalone and event-loop contexts.

    When running in Celery with gevent, an event loop already exists.
    When running standalone (e.g., tests), we need to create one.
    """
    import asyncio

    try:
        loop = asyncio.get_running_loop()
        # Loop is running - run in new thread with new event loop
        logger.debug("Detected running event loop - running in new thread")
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(asyncio.run, coro)
            return future.result()
    except RuntimeError:
        # No running loop - get existing or create new
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        logger.debug("No running event loop - using run_until_complete")
        try:
            return loop.run_until_complete(coro)
        finally:
            # Don't close the loop - might be reused by Celery
            pass


@shared_task(bind=True, max_retries=3, autoretry_for=(Exception,))
def my_async_celery_task(self, execution_id: str, arg1, arg2):
    """Celery task that uses async database operations."""

    async def _execute():
        from db.maria_database import DatabaseSessionLocal, database_engine
        # Import other engines if needed
        # from db.hris_database import _get_hris_session_maker, dispose_hris_engine

        # Initialize result variable BEFORE try block
        result = None

        try:
            async with DatabaseSessionLocal() as session:
                try:
                    # === YOUR ASYNC LOGIC HERE ===
                    # All database operations inside this block

                    # Store result (don't return yet!)
                    result = {"status": "success", "data": "..."}

                except Exception as e:
                    logger.error(f"Error in task logic: {e}")
                    raise

        except Exception as e:
            logger.error(f"Session error: {e}")
            raise
        finally:
            # CRITICAL: Dispose engines BEFORE event loop closes
            logger.debug("Disposing database engines...")
            try:
                await database_engine.dispose()
                logger.debug("Database engine disposed")
            except Exception as e:
                logger.warning(f"Failed to dispose engine: {e}")

        # Return AFTER finally block
        return result

    try:
        logger.info(f"Starting task with execution_id={execution_id}")
        result = _run_async(_execute())
        logger.info(f"Task completed: {result}")
        return result
    except Exception as e:
        logger.error(f"Task failed: {e}")
        raise
```

### Key Requirements Checklist

- [ ] Use sophisticated `_run_async` helper with event loop detection
- [ ] Initialize result variable at start of `_execute()`
- [ ] Wrap async with blocks in try/except/finally
- [ ] Dispose database engines in finally block (inside `_execute()`)
- [ ] Return result AFTER finally block, not inside try
- [ ] Never use simple `asyncio.run()` directly

### DO NOT

```python
# WRONG - Will fail in Celery/gevent environment
@shared_task
def bad_task():
    asyncio.run(my_async_function())  # ❌ Event loop conflict

# WRONG - Disposing outside _execute()
@shared_task
def bad_task():
    result = _run_async(_execute())
    await engine.dispose()  # ❌ Too late, loop already closed

# WRONG - Returning inside try block
async def _execute():
    try:
        return result  # ❌ Prevents finally from executing properly
    finally:
        await engine.dispose()
```

---

## Service Layer Pattern

All business logic must go through the service layer.

### Structure

```
API Route → Service → Repository → Database
```

### Service Method Template

```python
# In src/backend/api/services/scheduler_service.py

async def perform_operation(
    self,
    session: AsyncSession,
    job_id: int,
    data: SomeSchema,
    user_id: Optional[str] = None,
) -> ResultType:
    """
    Describe what this operation does.

    Args:
        session: Database session
        job_id: The job to operate on
        data: Input data schema
        user_id: User performing the action (for audit)

    Returns:
        ResultType with operation result

    Raises:
        HTTPException: If job not found or validation fails
    """
    from api.repositories.scheduler_repository import scheduler_repository
    from fastapi import HTTPException, status

    # 1. Validate inputs
    job = await scheduler_repository.get_job_by_id(session, job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )

    # 2. Check business rules
    if not job.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot operate on deleted job"
        )

    # 3. Perform operation through repository
    result = await scheduler_repository.update_job(
        session,
        job_id,
        {"field": data.field, "updated_by_id": user_id}
    )

    # 4. Handle side effects (APScheduler, notifications, etc.)
    await self._sync_job_with_scheduler(result)

    # 5. Return result
    return result
```

### DO NOT

```python
# WRONG - Bypassing service layer
@router.post("/jobs/{job_id}/action")
async def perform_action(job_id: int, session: AsyncSession = Depends(get_session)):
    # ❌ Direct repository call from route
    job = await scheduler_repository.update_job(session, job_id, {"is_enabled": True})

# WRONG - Business logic in route
@router.post("/jobs/{job_id}/action")
async def perform_action(job_id: int):
    # ❌ APScheduler call from route
    scheduler.add_job(...)
```

---

## Repository Pattern

Database operations are isolated in the repository layer.

### Repository Method Template

```python
# In src/backend/api/repositories/scheduler_repository.py

async def get_jobs_with_filter(
    self,
    session: AsyncSession,
    filters: dict,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[ScheduledJob], int]:
    """
    Get jobs with filtering and pagination.

    Args:
        session: Database session
        filters: Dict of filter conditions
        page: Page number (1-indexed)
        per_page: Items per page

    Returns:
        Tuple of (jobs list, total count)
    """
    from sqlalchemy import select, func
    from db.models import ScheduledJob

    # Build base query
    query = select(ScheduledJob).where(ScheduledJob.is_active == True)

    # Apply filters
    if filters.get("is_enabled") is not None:
        query = query.where(ScheduledJob.is_enabled == filters["is_enabled"])

    if filters.get("job_type_id"):
        query = query.where(ScheduledJob.job_type_id == filters["job_type_id"])

    if filters.get("task_function_id"):
        query = query.where(
            ScheduledJob.task_function_id == filters["task_function_id"]
        )

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = await session.scalar(count_query)

    # Apply pagination
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)

    # Order by priority (descending), then by id
    query = query.order_by(
        ScheduledJob.priority.desc(),
        ScheduledJob.id.asc()
    )

    # Execute
    result = await session.execute(query)
    jobs = list(result.scalars().all())

    return jobs, total
```

---

## Schema Pattern (CamelModel)

All schemas MUST inherit from `CamelModel` for automatic camelCase JSON serialization.

### Correct Pattern

```python
from api.schemas._base import CamelModel
from typing import Optional
from datetime import datetime


class JobFilterRequest(CamelModel):
    """Request schema for filtering jobs."""
    is_enabled: Optional[bool] = None      # → "isEnabled" in JSON
    job_type_id: Optional[int] = None      # → "jobTypeId" in JSON
    task_function_id: Optional[int] = None # → "taskFunctionId" in JSON


class JobSummaryResponse(CamelModel):
    """Response schema for job summary."""
    job_id: int                            # → "jobId" in JSON
    job_name: str                          # → "jobName" in JSON
    is_enabled: bool                       # → "isEnabled" in JSON
    last_run_at: Optional[datetime] = None # → "lastRunAt" in JSON
    next_run_at: Optional[datetime] = None # → "nextRunAt" in JSON
```

### DO NOT

```python
# WRONG - Not inheriting from CamelModel
from pydantic import BaseModel

class JobResponse(BaseModel):  # ❌ Wrong base class
    job_id: int  # Will output as "job_id", not "jobId"

# WRONG - Manual alias
from pydantic import Field

class JobResponse(CamelModel):
    job_id: int = Field(alias="jobId")  # ❌ Unnecessary, CamelModel handles this
```

---

## API Route Pattern

### Route Template

```python
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.scheduler_schemas import (
    SomeRequest,
    SomeResponse,
    PaginatedResponse,
)
from api.services.scheduler_service import scheduler_service
from db.maria_database import get_session
from utils.auth import get_current_super_admin
from db.models import Account

router = APIRouter(prefix="/scheduler", tags=["Scheduler"])


@router.get(
    "/some-endpoint",
    response_model=PaginatedResponse,
    summary="Get something",
    description="Detailed description of what this endpoint does.",
)
async def get_something(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    filter_param: Optional[str] = Query(None, description="Optional filter"),
    session: AsyncSession = Depends(get_session),
    current_user: Account = Depends(get_current_super_admin),
) -> PaginatedResponse:
    """Get something with pagination."""
    items, total = await scheduler_service.get_something(
        session,
        page=page,
        per_page=per_page,
        filters={"param": filter_param},
    )

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
    )


@router.post(
    "/some-endpoint/{id}/action",
    response_model=ActionResponse,
    summary="Perform action",
)
async def perform_action(
    id: int,
    request: ActionRequest,
    session: AsyncSession = Depends(get_session),
    current_user: Account = Depends(get_current_super_admin),
) -> ActionResponse:
    """Perform an action on a resource."""
    result = await scheduler_service.perform_action(
        session,
        id,
        request,
        user_id=str(current_user.id),
    )

    return ActionResponse(
        success=True,
        message="Action completed",
        data=result,
    )
```

---

## Distributed Locking Pattern

Prevent duplicate job execution across multiple scheduler instances.

### Lock Acquisition

```python
async def _acquire_lock(
    session: AsyncSession,
    job_id: int,
    execution_id: str,
    instance_id: str,
    lock_duration_seconds: int = 3600,
) -> bool:
    """
    Attempt to acquire a lock for job execution.

    Returns True if lock acquired, False if job already locked.
    """
    from datetime import datetime, timezone, timedelta
    from sqlalchemy import select, delete
    from db.models import ScheduledJobLock

    # Clean up expired locks first
    now = datetime.now(timezone.utc)
    await session.execute(
        delete(ScheduledJobLock).where(ScheduledJobLock.expires_at < now)
    )

    # Check for existing lock
    existing = await session.scalar(
        select(ScheduledJobLock).where(ScheduledJobLock.job_id == job_id)
    )

    if existing:
        # Lock exists and not expired
        return False

    # Create new lock
    lock = ScheduledJobLock(
        job_id=job_id,
        execution_id=execution_id,
        locked_by=instance_id,
        locked_at=now,
        expires_at=now + timedelta(seconds=lock_duration_seconds),
    )
    session.add(lock)
    await session.commit()

    return True


async def _release_lock(
    session: AsyncSession,
    job_id: int,
    execution_id: str,
) -> None:
    """Release a job execution lock."""
    from sqlalchemy import delete
    from db.models import ScheduledJobLock

    await session.execute(
        delete(ScheduledJobLock).where(
            ScheduledJobLock.job_id == job_id,
            ScheduledJobLock.execution_id == execution_id,
        )
    )
    await session.commit()
```

### Usage in Execution Wrapper

```python
async def _execute_with_lock(job_id: int, execution_id: str, func):
    """Execute a job with distributed locking."""
    async with DatabaseSessionLocal() as session:
        # Try to acquire lock
        lock_acquired = await _acquire_lock(
            session, job_id, execution_id, INSTANCE_ID
        )

        if not lock_acquired:
            logger.warning(f"Job {job_id} already locked, skipping")
            return

        try:
            # Execute the job
            result = await func()
            return result
        finally:
            # Always release lock
            await _release_lock(session, job_id, execution_id)
```

---

## Manual Trigger Pattern

Immediate job execution with tracking.

### Pattern

```python
async def trigger_job_now(
    self,
    session: AsyncSession,
    job_id: int,
    triggered_by_user_id: Optional[str] = None,
) -> tuple[str, ScheduledJob]:
    """
    Manually trigger a job for immediate execution.

    1. Create execution record immediately (status=RUNNING)
    2. Return execution_id to caller
    3. Launch background task for actual execution
    4. Update status on completion
    """
    import uuid
    import asyncio
    from datetime import datetime, timezone

    # Get job
    job = await scheduler_repository.get_job_by_id(session, job_id)
    if not job or not job.is_active:
        raise HTTPException(status_code=404, detail="Job not found")

    # Check for already running execution
    running = await self._check_running_execution(session, job_id)
    if running:
        raise HTTPException(
            status_code=400,
            detail="Job already has a running execution"
        )

    # Create execution record IMMEDIATELY
    execution_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    execution = await scheduler_repository.create_execution(
        session,
        {
            "job_id": job_id,
            "execution_id": execution_id,
            "scheduled_at": now,
            "started_at": now,
            "status_id": RUNNING_STATUS_ID,
            "executor_id": INSTANCE_ID,
            "host_name": HOSTNAME,
        }
    )

    # Launch background task (don't await)
    asyncio.create_task(
        self._execute_in_background(
            job_id,
            execution_id,
            triggered_by_user_id,
        )
    )

    return execution_id, job
```

---

## Error Handling Pattern

Consistent error handling across the scheduler.

```python
from fastapi import HTTPException, status
import logging

logger = logging.getLogger(__name__)


async def safe_operation(session, job_id, operation_name):
    """Template for safe operations with proper error handling."""
    try:
        # Validate
        job = await scheduler_repository.get_job_by_id(session, job_id)
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found"
            )

        # Business logic
        result = await do_something(job)

        return result

    except HTTPException:
        # Re-raise HTTP exceptions (already formatted)
        raise

    except ValueError as e:
        # Validation errors → 400
        logger.warning(f"{operation_name} validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    except Exception as e:
        # Unexpected errors → 500
        logger.error(f"{operation_name} failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{operation_name} failed: {str(e)}"
        )
```
