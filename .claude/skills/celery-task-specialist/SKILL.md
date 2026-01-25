---
name: celery-task-specialist
description: |
  Create and modify Celery background tasks with the mandatory async event loop handling pattern.
  Use when creating new Celery tasks, adding database operations to tasks, implementing retry logic,
  or troubleshooting "Event loop is closed" errors. Covers gevent compatibility, execution tracking,
  and APScheduler integration.
allowed-tools: Read, Write, Edit, Grep, Glob, Bash
---

# Celery Task Specialist

## Overview

This skill teaches how to create Celery background tasks that properly handle async database operations in a gevent worker environment. The key challenge is that Celery workers with `-P gevent` create an event loop that conflicts with simple `asyncio.run()` calls.

**Core Technologies:**
- **Celery** - Distributed task queue
- **Gevent** - Worker pool for async task handling
- **SQLAlchemy** - Async database operations
- **APScheduler** - Job scheduling integration

> **CRITICAL**: All async Celery tasks MUST follow the `_run_async()` pattern. Failure causes production crashes.

## When to Use This Skill

Activate when request involves:

- Creating new Celery background tasks
- Adding async database operations to tasks
- Implementing task retry logic
- Troubleshooting event loop errors
- Integrating tasks with APScheduler
- Adding execution tracking to tasks
- Handling multi-database operations in tasks
- Disposing database connections properly

## Quick Reference

### Backend Locations

| Component | Path |
|-----------|------|
| HRIS Tasks | `src/backend/tasks/hris.py` |
| Email Tasks | `src/backend/tasks/email.py` |
| Attendance Tasks | `src/backend/tasks/attendance.py` |
| Scheduler Tasks | `src/backend/tasks/scheduler.py` |
| Celery App | `src/backend/celery_app.py` |
| Celery Bridge | `src/backend/celery_bridge.py` |

### The Problem

```python
# ❌ WRONG - Will fail in Celery/gevent environment
@shared_task
def bad_task():
    asyncio.run(my_async_function())  # Event loop conflict!
```

**Error Messages You'll See:**
- `RuntimeError: Task got Future attached to a different loop`
- `Event loop is closed`
- `Database connection cleanup failures`

## Core Pattern (MANDATORY)

Every async Celery task MUST follow this structure:

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
            # Don't close - might be reused by Celery
            pass


@shared_task(bind=True, max_retries=3, autoretry_for=(Exception,))
def my_async_task(self, execution_id: str = None, **kwargs) -> dict:
    """Celery task with async database operations."""

    async def _execute():
        from db.maria_database import DatabaseSessionLocal, database_engine

        # Initialize result BEFORE try block
        result = None

        try:
            async with DatabaseSessionLocal() as session:
                try:
                    # === YOUR ASYNC LOGIC HERE ===
                    # All database operations inside this block

                    result = {"status": "success", "data": "..."}

                except Exception as e:
                    logger.error(f"Error in task logic: {e}")
                    raise

        except Exception as e:
            logger.error(f"Session error: {e}")
            raise
        finally:
            # CRITICAL: Dispose engine BEFORE event loop closes
            logger.debug("Disposing database engine...")
            try:
                await database_engine.dispose()
                logger.debug("Database engine disposed")
            except Exception as e:
                logger.warning(f"Failed to dispose engine: {e}")

        # Return AFTER finally block
        return result

    try:
        logger.info(f"Starting task (execution_id={execution_id})")
        result = _run_async(_execute())
        logger.info("Task completed successfully")
        return result
    except Exception as e:
        logger.error(f"Task failed: {e}")
        raise
```

## Multi-Database Pattern

When accessing multiple databases (HRIS, BioStar):

```python
async def _execute():
    from db.maria_database import DatabaseSessionLocal, database_engine
    from db.hris_database import _get_hris_session_maker, dispose_hris_engine

    result = None

    try:
        async with DatabaseSessionLocal() as app_session:
            HrisSessionLocal = _get_hris_session_maker()
            async with HrisSessionLocal() as hris_session:
                try:
                    # Work with both sessions
                    # app_session for local MariaDB
                    # hris_session for HRIS SQL Server

                    result = {"status": "success"}

                except Exception as e:
                    logger.error(f"Error: {e}")
                    raise

    except Exception as e:
        logger.error(f"Outer error: {e}")
        raise
    finally:
        # Dispose in correct order: external first, then primary
        logger.debug("Disposing database engines...")
        try:
            await dispose_hris_engine()
            logger.debug("HRIS engine disposed")
        except Exception as e:
            logger.warning(f"Failed to dispose HRIS engine: {e}")

        try:
            await database_engine.dispose()
            logger.debug("Maria engine disposed")
        except Exception as e:
            logger.warning(f"Failed to dispose Maria engine: {e}")

    return result
```

## Task Decorator Options

### Standard Options

```python
@shared_task(
    bind=True,                      # Access self.request, self.retry()
    max_retries=3,                  # Maximum retry attempts
    default_retry_delay=120,        # Seconds between retries
    autoretry_for=(Exception,),     # Auto-retry on these exceptions
    retry_backoff=True,             # Exponential backoff
    retry_backoff_max=600,          # Max backoff delay
    retry_jitter=True,              # Random jitter to prevent thundering herd
    soft_time_limit=600,            # Warn after 10 minutes
    time_limit=660,                 # Kill after 11 minutes
)
def my_task(self, execution_id: str = None):
    ...
```

### Execution Tracking

```python
@shared_task(bind=True, max_retries=3)
def tracked_task(self, execution_id: str = None, triggered_by_user_id: str = None):
    """Task with execution tracking for APScheduler integration."""

    async def _execute():
        from api.repositories.scheduler_repository import SchedulerRepository
        from db.maria_database import DatabaseSessionLocal, database_engine
        from datetime import datetime, timezone

        scheduler_repo = SchedulerRepository()
        started_at = datetime.now(timezone.utc)
        result = None

        try:
            async with DatabaseSessionLocal() as session:
                try:
                    # Your task logic here
                    result = {"status": "success"}

                    # Update execution status on success
                    if execution_id:
                        completed_at = datetime.now(timezone.utc)
                        duration_ms = int((completed_at - started_at).total_seconds() * 1000)
                        status_obj = await scheduler_repo.get_execution_status_by_code(
                            session, "success"
                        )
                        if status_obj:
                            await scheduler_repo.update_execution(
                                session,
                                execution_id,
                                {
                                    "completed_at": completed_at,
                                    "duration_ms": duration_ms,
                                    "status_id": status_obj.id,
                                    "result_summary": "Task completed",
                                },
                            )
                            await session.commit()

                except Exception as e:
                    # Update execution status on failure
                    if execution_id:
                        completed_at = datetime.now(timezone.utc)
                        duration_ms = int((completed_at - started_at).total_seconds() * 1000)
                        status_obj = await scheduler_repo.get_execution_status_by_code(
                            session, "failed"
                        )
                        if status_obj:
                            await scheduler_repo.update_execution(
                                session,
                                execution_id,
                                {
                                    "completed_at": completed_at,
                                    "duration_ms": duration_ms,
                                    "status_id": status_obj.id,
                                    "error_message": str(e),
                                },
                            )
                            await session.commit()
                    raise

        finally:
            await database_engine.dispose()

        return result

    return _run_async(_execute())
```

## Allowed Operations

**DO:**
- Create new tasks following the `_run_async()` pattern
- Add execution tracking for scheduler-triggered tasks
- Implement retry logic with backoff
- Use `bind=True` to access task metadata
- Dispose database engines in finally blocks
- Log task start, completion, and errors

**DON'T:**
- Use simple `asyncio.run()` without event loop detection
- Return from inside try blocks (prevents finally from executing)
- Forget to dispose database engines
- Dispose engines outside `_execute()` (too late)
- Use `async with` without try/finally for engine disposal
- Create synchronous database operations

## Validation Checklist

Before completing Celery task work:

- [ ] Uses `_run_async()` helper with event loop detection
- [ ] Initializes result variable at start of `_execute()`
- [ ] Wraps async with blocks in try/except/finally
- [ ] Disposes database engines in finally block (inside `_execute()`)
- [ ] Returns result AFTER finally block
- [ ] Never uses simple `asyncio.run()` directly
- [ ] Logs task start and completion
- [ ] Handles exceptions and logs errors
- [ ] Updates execution status if `execution_id` provided

## Additional Resources

- [PATTERNS.md](PATTERNS.md) - Detailed code patterns
- [EXAMPLES.md](EXAMPLES.md) - Complete working examples
- [REFERENCE.md](REFERENCE.md) - API reference

## Trigger Phrases

- "Celery task", "background task", "async task"
- "event loop", "asyncio.run", "gevent"
- "Event loop is closed", "different loop"
- "database connection", "engine dispose"
- "retry logic", "task retry", "autoretry"
- "execution tracking", "scheduler task"
- "HRIS replication", "attendance sync"
