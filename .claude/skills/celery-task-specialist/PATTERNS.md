# Celery Task Patterns

Critical patterns that MUST be followed when creating Celery tasks with async operations.

## The _run_async Helper (MANDATORY)

This helper is required for all async Celery tasks. Copy it exactly:

```python
def _run_async(coro):
    """
    Run a coroutine, handling both standalone and event-loop contexts.

    When running in Celery with gevent, an event loop already exists.
    When running standalone (e.g., tests), we need to create one.

    This function detects the context and uses the appropriate method.
    """
    import asyncio

    # Try to get the current running loop
    try:
        loop = asyncio.get_running_loop()
        # Loop is running - we need to run in a new thread with a new event loop
        logger.debug("Detected running event loop - running coroutine in new thread")
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(asyncio.run, coro)
            return future.result()
    except RuntimeError:
        # No running loop - try to get existing loop or create one
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Run the coroutine
        logger.debug("No running event loop - using run_until_complete")
        try:
            return loop.run_until_complete(coro)
        finally:
            # Don't close the loop if it's the default event loop
            # as it might be reused by Celery
            pass
```

---

## Single Database Task Pattern

For tasks that only need the primary MariaDB:

```python
@shared_task(bind=True, max_retries=3, autoretry_for=(Exception,))
def single_db_task(self, execution_id: str = None, **kwargs) -> dict:
    """Task with single database connection."""

    async def _execute():
        from db.maria_database import DatabaseSessionLocal, database_engine

        result = None

        try:
            async with DatabaseSessionLocal() as session:
                try:
                    # Your async logic here
                    data = await some_repository.get_data(session)
                    await some_repository.update_data(session, data)
                    await session.commit()

                    result = {"status": "success", "processed": len(data)}

                except Exception as e:
                    logger.error(f"Error: {e}")
                    await session.rollback()
                    raise

        except Exception as e:
            logger.error(f"Session error: {e}")
            raise
        finally:
            # Dispose engine before loop closes
            try:
                await database_engine.dispose()
            except Exception as e:
                logger.warning(f"Dispose failed: {e}")

        return result

    try:
        logger.info(f"Starting single_db_task")
        result = _run_async(_execute())
        logger.info("Task completed")
        return result
    except Exception as e:
        logger.error(f"Task failed: {e}")
        raise
```

---

## Multi-Database Task Pattern

For tasks accessing HRIS, BioStar, or other external databases:

```python
@shared_task(bind=True, max_retries=3, autoretry_for=(Exception,))
def multi_db_task(self, execution_id: str = None) -> dict:
    """Task with multiple database connections."""

    async def _execute():
        from db.maria_database import DatabaseSessionLocal, database_engine
        from db.hris_database import _get_hris_session_maker, dispose_hris_engine
        from db.biostar_database import _get_biostar_session_maker, dispose_biostar_engine

        result = None

        try:
            # Create all sessions
            async with DatabaseSessionLocal() as app_session:
                HrisSession = _get_hris_session_maker()
                async with HrisSession() as hris_session:
                    BiostarSession = _get_biostar_session_maker()
                    async with BiostarSession() as biostar_session:
                        try:
                            # Read from external databases
                            employees = await hris_repo.get_employees(hris_session)
                            attendance = await biostar_repo.get_attendance(biostar_session)

                            # Write to local database
                            await local_repo.sync_data(app_session, employees, attendance)
                            await app_session.commit()

                            result = {
                                "status": "success",
                                "employees": len(employees),
                                "attendance": len(attendance),
                            }

                        except Exception as e:
                            logger.error(f"Sync error: {e}")
                            await app_session.rollback()
                            raise

        except Exception as e:
            logger.error(f"Session error: {e}")
            raise
        finally:
            # Dispose in order: external DBs first, then primary
            logger.debug("Disposing all database engines...")

            for dispose_fn, name in [
                (dispose_biostar_engine, "BioStar"),
                (dispose_hris_engine, "HRIS"),
            ]:
                try:
                    await dispose_fn()
                    logger.debug(f"{name} engine disposed")
                except Exception as e:
                    logger.warning(f"Failed to dispose {name} engine: {e}")

            try:
                await database_engine.dispose()
                logger.debug("Maria engine disposed")
            except Exception as e:
                logger.warning(f"Failed to dispose Maria engine: {e}")

        return result

    try:
        logger.info("Starting multi_db_task")
        result = _run_async(_execute())
        logger.info("Task completed")
        return result
    except Exception as e:
        logger.error(f"Task failed: {e}")
        raise
```

---

## Execution Tracking Pattern

For tasks triggered by APScheduler that need execution status updates:

```python
@shared_task(bind=True, max_retries=3)
def tracked_task(self, execution_id: str = None, triggered_by_user_id: str = None) -> dict:
    """Task with execution status tracking."""

    async def _execute():
        from api.repositories.scheduler_repository import SchedulerRepository
        from db.maria_database import DatabaseSessionLocal, database_engine
        from datetime import datetime, timezone

        scheduler_repo = SchedulerRepository()
        started_at = datetime.now(timezone.utc)
        error_message = None
        result = None

        try:
            async with DatabaseSessionLocal() as session:
                try:
                    # === MAIN TASK LOGIC ===
                    logger.info("Executing task logic...")
                    # ... your code here ...

                    result = {"status": "success", "message": "Completed"}

                    # Update execution status on SUCCESS
                    if execution_id:
                        try:
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
                                        "result_summary": "Task completed successfully",
                                    },
                                )
                                await session.commit()
                                logger.info(f"Updated execution {execution_id} to SUCCESS")
                        except Exception as update_err:
                            logger.error(f"Failed to update execution status: {update_err}")

                except Exception as e:
                    logger.error(f"Task error: {e}", exc_info=True)
                    error_message = str(e)

                    try:
                        await session.rollback()
                    except Exception:
                        pass

                    # Update execution status on FAILURE
                    if execution_id:
                        try:
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
                                        "error_message": error_message,
                                    },
                                )
                                await session.commit()
                                logger.info(f"Updated execution {execution_id} to FAILED")
                        except Exception as update_err:
                            logger.error(f"Failed to update execution status: {update_err}")

                    raise

        except Exception as e:
            logger.error(f"Session error: {e}")
            raise
        finally:
            try:
                await database_engine.dispose()
            except Exception as e:
                logger.warning(f"Dispose failed: {e}")

        return result

    try:
        logger.info(f"Starting tracked_task (execution_id={execution_id})")
        result = _run_async(_execute())
        logger.info("Task completed")
        return result
    except Exception as e:
        logger.error(f"Task failed: {e}")
        raise
```

---

## Retry Pattern with Backoff

For tasks that need sophisticated retry behavior:

```python
@shared_task(
    bind=True,
    max_retries=5,
    default_retry_delay=60,              # Base delay: 60 seconds
    autoretry_for=(
        ConnectionError,
        TimeoutError,
        OperationalError,                # SQLAlchemy operational errors
    ),
    retry_backoff=True,                  # Exponential backoff
    retry_backoff_max=3600,              # Max 1 hour between retries
    retry_jitter=True,                   # Random jitter
    soft_time_limit=300,                 # Warning at 5 minutes
    time_limit=360,                      # Kill at 6 minutes
)
def robust_task(self, data_id: str) -> dict:
    """Task with robust retry behavior."""

    async def _execute():
        from db.maria_database import DatabaseSessionLocal, database_engine

        result = None

        try:
            async with DatabaseSessionLocal() as session:
                try:
                    # Your logic here - will auto-retry on configured exceptions
                    result = await process_data(session, data_id)

                except Exception as e:
                    logger.error(f"Processing error: {e}")
                    raise

        finally:
            try:
                await database_engine.dispose()
            except Exception:
                pass

        return result

    try:
        logger.info(f"Attempt {self.request.retries + 1}/{self.max_retries + 1}")
        result = _run_async(_execute())
        return result
    except Exception as e:
        logger.error(f"Task failed after {self.request.retries} retries: {e}")
        raise
```

---

## Structured Logging Pattern

For production-ready task observability:

```python
from utils.structured_logger import get_structured_logger
import socket

structured_logger = get_structured_logger(__name__)


@shared_task(bind=True, max_retries=3)
def observable_task(self, execution_id: str = None) -> dict:
    """Task with structured logging."""

    # Log task start
    structured_logger.log_celery_task_start(
        task_name="observable_task",
        execution_id=execution_id or "NONE",
        celery_task_id=self.request.id,
        worker_host=socket.gethostname(),
        task_metadata={
            "retries": self.request.retries,
            "max_retries": self.max_retries,
        }
    )

    async def _execute():
        from db.maria_database import DatabaseSessionLocal, database_engine
        from datetime import datetime, timezone

        started_at = datetime.now(timezone.utc)
        result = None

        try:
            async with DatabaseSessionLocal() as session:
                # Your logic here
                result = {"status": "success"}

        finally:
            await database_engine.dispose()

            # Log task completion
            completed_at = datetime.now(timezone.utc)
            duration_ms = int((completed_at - started_at).total_seconds() * 1000)

            structured_logger.log_celery_task_complete(
                task_name="observable_task",
                execution_id=execution_id or "NONE",
                final_status="SUCCESS" if result else "FAILED",
                duration_ms=duration_ms,
            )

        return result

    return _run_async(_execute())
```

---

## Celery Bridge Registration

Tasks triggered by APScheduler must be registered in the bridge:

```python
# src/backend/celery_bridge.py

from tasks.hris import hris_replication_task
from tasks.attendance import (
    sync_attendance_task,
    calculate_compliance_task,
)
from tasks.my_module import my_new_task  # Add new task import

# Task function registry - maps task_function.code to Celery task
TASK_REGISTRY = {
    "hris_replication": hris_replication_task,
    "sync_attendance": sync_attendance_task,
    "calculate_compliance": calculate_compliance_task,
    "my_new_task": my_new_task,  # Register new task
}


def dispatch_task(task_code: str, execution_id: str, **kwargs) -> str:
    """
    Dispatch a task to Celery by its task_function code.

    Args:
        task_code: Code matching task_function.code in database
        execution_id: Scheduler execution ID for tracking
        **kwargs: Additional task arguments

    Returns:
        Celery task ID
    """
    task_fn = TASK_REGISTRY.get(task_code)
    if not task_fn:
        raise ValueError(f"Unknown task code: {task_code}")

    result = task_fn.delay(execution_id=execution_id, **kwargs)
    return result.id
```

---

## Synchronous Task Pattern

For tasks that don't need async (e.g., sending emails):

```python
@shared_task(bind=True, max_retries=3, autoretry_for=(Exception,))
def send_email_task(
    self,
    recipients: list[str],
    subject: str,
    body: str,
) -> dict:
    """
    Synchronous task - no async operations needed.

    Email sending uses a synchronous client, no database operations.
    """
    from utils.mail_sender import EmailSender

    try:
        logger.info(f"Sending email to {len(recipients)} recipients")

        sender = EmailSender()
        success = sender.send(
            recipients=recipients,
            subject=subject,
            body=body,
        )

        if success:
            logger.info("Email sent successfully")
            return {"status": "success", "recipients": len(recipients)}
        else:
            raise Exception("Email sending failed")

    except Exception as e:
        logger.error(f"Email task failed: {e}")
        raise
```

---

## Anti-Patterns to Avoid

### 1. Simple asyncio.run()

```python
# ❌ WRONG
@shared_task
def bad_task():
    asyncio.run(my_async_function())  # Will conflict with gevent loop
```

### 2. Disposing Outside _execute()

```python
# ❌ WRONG
@shared_task
def bad_task():
    result = _run_async(_execute())
    await engine.dispose()  # Too late - loop already closed
    return result
```

### 3. Returning Inside Try Block

```python
# ❌ WRONG
async def _execute():
    try:
        result = await do_something()
        return result  # Prevents finally from running properly
    finally:
        await engine.dispose()
```

### 4. Not Handling Exceptions

```python
# ❌ WRONG
@shared_task
def bad_task():
    async def _execute():
        async with DatabaseSessionLocal() as session:
            # No try/except - errors won't be logged
            await risky_operation(session)
    return _run_async(_execute())
```

### 5. Missing Engine Disposal

```python
# ❌ WRONG
async def _execute():
    async with DatabaseSessionLocal() as session:
        result = await do_something(session)
    # No engine.dispose() - connection leak!
    return result
```

---

## Validation Checklist

Before deploying a Celery task:

- [ ] `_run_async()` helper present with event loop detection
- [ ] Result initialized before try block
- [ ] Database engines disposed in finally (inside `_execute()`)
- [ ] Return after finally block, not inside try
- [ ] Error handling with logging
- [ ] Execution status updates if scheduler-triggered
- [ ] Task registered in `celery_bridge.py` if needed
- [ ] Retry configuration appropriate for task type
- [ ] Time limits set for long-running tasks
