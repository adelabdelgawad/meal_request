# Celery Task Examples

Complete working examples for common Celery task patterns.

## Example 1: HRIS Replication Task

Reference implementation from `src/backend/tasks/hris.py`:

```python
"""
Celery HRIS Replication Task.

Handles HRIS data replication from SQL Server to local MariaDB with
automatic retry logic for network failures.
"""

import logging
import socket
from datetime import datetime, timezone
from celery import shared_task
from utils.structured_logger import get_structured_logger

logger = logging.getLogger(__name__)
structured_logger = get_structured_logger(__name__)


def _run_async(coro):
    """Run a coroutine, handling both standalone and event-loop contexts."""
    import asyncio

    try:
        loop = asyncio.get_running_loop()
        logger.debug("Detected running event loop - running in new thread")
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(asyncio.run, coro)
            return future.result()
    except RuntimeError:
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
            pass


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=120,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    soft_time_limit=600,
    time_limit=660,
)
def hris_replication_task(
    self,
    execution_id: str = None,
    triggered_by_user_id: str = None,
) -> dict:
    """
    Celery task for HRIS data replication.

    Args:
        execution_id: Scheduler execution ID for status updates
        triggered_by_user_id: User ID who manually triggered (None for scheduled)

    Returns:
        dict with replication status
    """
    async def _execute():
        from api.repositories.scheduler_repository import SchedulerRepository
        from db.maria_database import DatabaseSessionLocal, database_engine
        from db.hris_database import _get_hris_session_maker, dispose_hris_engine
        from utils.replicate_hris import replicate

        scheduler_repo = SchedulerRepository()
        started_at = datetime.now(timezone.utc)
        error_message = None
        result = None

        try:
            async with DatabaseSessionLocal() as app_session:
                HrisSessionLocal = _get_hris_session_maker()
                async with HrisSessionLocal() as hris_session:
                    try:
                        logger.info("Starting HRIS replication...")
                        await replicate(
                            hris_session,
                            app_session,
                            triggered_by_user_id=triggered_by_user_id,
                        )
                        await app_session.commit()
                        logger.info("HRIS replication completed successfully")

                        result = {
                            "status": "success",
                            "message": "HRIS replication completed",
                        }

                        # Update execution status on success
                        if execution_id:
                            try:
                                completed_at = datetime.now(timezone.utc)
                                duration_ms = int(
                                    (completed_at - started_at).total_seconds() * 1000
                                )
                                status_obj = await scheduler_repo.get_execution_status_by_code(
                                    app_session, "success"
                                )
                                if status_obj:
                                    await scheduler_repo.update_execution(
                                        app_session,
                                        execution_id,
                                        {
                                            "completed_at": completed_at,
                                            "duration_ms": duration_ms,
                                            "status_id": status_obj.id,
                                            "result_summary": "HRIS replication completed",
                                        },
                                    )
                                    await app_session.commit()
                                    logger.info(
                                        f"Updated execution {execution_id} to SUCCESS"
                                    )

                                    structured_logger.log_celery_task_complete(
                                        task_name="hris_replication",
                                        execution_id=execution_id,
                                        final_status="SUCCESS",
                                        duration_ms=duration_ms,
                                    )
                            except Exception as update_err:
                                logger.error(
                                    f"Failed to update execution status: {update_err}"
                                )

                    except Exception as e:
                        logger.error(f"Error during HRIS replication: {e}", exc_info=True)
                        error_message = str(e)

                        try:
                            await app_session.rollback()
                        except Exception:
                            pass

                        # Update execution status on failure
                        if execution_id:
                            try:
                                completed_at = datetime.now(timezone.utc)
                                duration_ms = int(
                                    (completed_at - started_at).total_seconds() * 1000
                                )
                                status_obj = await scheduler_repo.get_execution_status_by_code(
                                    app_session, "failed"
                                )
                                if status_obj:
                                    await scheduler_repo.update_execution(
                                        app_session,
                                        execution_id,
                                        {
                                            "completed_at": completed_at,
                                            "duration_ms": duration_ms,
                                            "status_id": status_obj.id,
                                            "error_message": error_message,
                                        },
                                    )
                                    await app_session.commit()

                                    structured_logger.log_celery_task_complete(
                                        task_name="hris_replication",
                                        execution_id=execution_id,
                                        final_status="FAILED",
                                        duration_ms=duration_ms,
                                        error_message=error_message,
                                    )
                            except Exception as update_err:
                                logger.error(
                                    f"Failed to update execution status: {update_err}"
                                )

                        raise

        except Exception as e:
            logger.error(f"Error during Celery HRIS replication: {e}")
            raise
        finally:
            # Dispose engines before event loop closes
            logger.debug("Disposing database engines...")
            try:
                await dispose_hris_engine()
                logger.debug("HRIS engine disposed")
            except Exception as e:
                logger.warning(f"Failed to dispose HRIS engine: {e}")

            try:
                await database_engine.dispose()
                logger.debug("Maria database engine disposed")
            except Exception as e:
                logger.warning(f"Failed to dispose Maria engine: {e}")

        return result

    try:
        logger.info(
            f"Starting Celery HRIS replication task "
            f"(execution_id: {execution_id}, triggered_by: {triggered_by_user_id or 'scheduled'})"
        )

        structured_logger.log_celery_task_start(
            task_name="hris_replication",
            execution_id=execution_id or "NONE",
            celery_task_id=self.request.id,
            worker_host=socket.gethostname(),
            triggered_by=triggered_by_user_id,
            task_metadata={
                "retries": self.request.retries,
                "max_retries": self.max_retries,
                "soft_time_limit": 600,
                "time_limit": 660,
            },
        )

        result = _run_async(_execute())
        logger.info("HRIS replication completed successfully")
        return result

    except Exception as e:
        logger.error(f"Error during Celery HRIS replication: {e}")
        raise
```

---

## Example 2: Simple Data Processing Task

A simpler task without execution tracking:

```python
"""Simple data processing task."""

import logging
from celery import shared_task

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Run a coroutine safely."""
    import asyncio

    try:
        loop = asyncio.get_running_loop()
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(asyncio.run, coro)
            return future.result()
    except RuntimeError:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        try:
            return loop.run_until_complete(coro)
        finally:
            pass


@shared_task(bind=True, max_retries=3, autoretry_for=(Exception,))
def process_batch_task(self, batch_ids: list[str]) -> dict:
    """Process a batch of items."""

    async def _execute():
        from db.maria_database import DatabaseSessionLocal, database_engine
        from api.repositories.item_repository import ItemRepository

        item_repo = ItemRepository()
        result = None
        processed = 0
        failed = 0

        try:
            async with DatabaseSessionLocal() as session:
                try:
                    for item_id in batch_ids:
                        try:
                            item = await item_repo.get_by_id(session, item_id)
                            if item:
                                await item_repo.process(session, item)
                                processed += 1
                        except Exception as e:
                            logger.warning(f"Failed to process {item_id}: {e}")
                            failed += 1

                    await session.commit()
                    result = {
                        "status": "success",
                        "processed": processed,
                        "failed": failed,
                        "total": len(batch_ids),
                    }

                except Exception as e:
                    logger.error(f"Batch processing error: {e}")
                    await session.rollback()
                    raise

        finally:
            try:
                await database_engine.dispose()
            except Exception as e:
                logger.warning(f"Dispose failed: {e}")

        return result

    try:
        logger.info(f"Processing batch of {len(batch_ids)} items")
        result = _run_async(_execute())
        logger.info(f"Batch processing complete: {result}")
        return result
    except Exception as e:
        logger.error(f"Batch processing failed: {e}")
        raise
```

---

## Example 3: Cleanup Task

Periodic cleanup task with time limits:

```python
"""Cleanup task for old data."""

import logging
from datetime import datetime, timedelta, timezone
from celery import shared_task

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Run a coroutine safely."""
    import asyncio

    try:
        loop = asyncio.get_running_loop()
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(asyncio.run, coro)
            return future.result()
    except RuntimeError:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        try:
            return loop.run_until_complete(coro)
        finally:
            pass


@shared_task(
    bind=True,
    max_retries=1,  # Cleanup tasks shouldn't retry much
    soft_time_limit=300,  # 5 minute warning
    time_limit=360,  # 6 minute hard limit
)
def cleanup_old_executions_task(self, days_to_keep: int = 30) -> dict:
    """Clean up execution history older than specified days."""

    async def _execute():
        from db.maria_database import DatabaseSessionLocal, database_engine
        from sqlalchemy import delete, select, func
        from db.models import ScheduledJobExecution

        result = None
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)

        try:
            async with DatabaseSessionLocal() as session:
                try:
                    # Count records to delete
                    count_query = select(func.count()).select_from(
                        ScheduledJobExecution
                    ).where(
                        ScheduledJobExecution.created_at < cutoff_date
                    )
                    count = await session.scalar(count_query)

                    if count == 0:
                        result = {
                            "status": "success",
                            "deleted": 0,
                            "message": "No old records to delete",
                        }
                    else:
                        # Delete in batches to avoid long locks
                        deleted = 0
                        batch_size = 1000

                        while deleted < count:
                            delete_query = delete(ScheduledJobExecution).where(
                                ScheduledJobExecution.created_at < cutoff_date
                            ).limit(batch_size)

                            result_proxy = await session.execute(delete_query)
                            batch_deleted = result_proxy.rowcount
                            deleted += batch_deleted
                            await session.commit()

                            logger.info(f"Deleted {deleted}/{count} records")

                            if batch_deleted == 0:
                                break

                        result = {
                            "status": "success",
                            "deleted": deleted,
                            "cutoff_date": cutoff_date.isoformat(),
                        }

                except Exception as e:
                    logger.error(f"Cleanup error: {e}")
                    await session.rollback()
                    raise

        finally:
            try:
                await database_engine.dispose()
            except Exception as e:
                logger.warning(f"Dispose failed: {e}")

        return result

    try:
        logger.info(f"Starting cleanup task (keeping {days_to_keep} days)")
        result = _run_async(_execute())
        logger.info(f"Cleanup complete: {result}")
        return result
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        raise
```

---

## Example 4: Email Notification Task (Synchronous)

Tasks that don't need async:

```python
"""Email notification task - synchronous, no database."""

import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def send_notification_email_task(
    self,
    recipients: list[str],
    subject: str,
    body: str,
    html_body: str = None,
) -> dict:
    """
    Send email notification.

    This task is synchronous - no async operations, no database access.
    The EmailSender uses a synchronous SMTP/EWS client.
    """
    from utils.mail_sender import EmailSender

    try:
        logger.info(f"Sending email to {len(recipients)} recipients: {subject}")

        sender = EmailSender()
        success = sender.send(
            recipients=recipients,
            subject=subject,
            body=body,
            html_body=html_body,
        )

        if success:
            logger.info("Email sent successfully")
            return {
                "status": "success",
                "recipients": len(recipients),
                "subject": subject,
            }
        else:
            raise Exception("Email sending returned failure status")

    except Exception as e:
        logger.error(f"Email task failed: {e}")
        raise
```

---

## Example 5: Task with Manual Retry Control

When you need custom retry logic:

```python
"""Task with manual retry control."""

import logging
from celery import shared_task
from celery.exceptions import MaxRetriesExceededError

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Run a coroutine safely."""
    import asyncio

    try:
        loop = asyncio.get_running_loop()
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(asyncio.run, coro)
            return future.result()
    except RuntimeError:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        try:
            return loop.run_until_complete(coro)
        finally:
            pass


class RetryableError(Exception):
    """Error that should trigger a retry."""
    pass


class PermanentError(Exception):
    """Error that should NOT trigger a retry."""
    pass


@shared_task(bind=True, max_retries=5)
def conditional_retry_task(self, external_id: str) -> dict:
    """Task that only retries on specific errors."""

    async def _execute():
        from db.maria_database import DatabaseSessionLocal, database_engine
        import httpx

        result = None

        try:
            async with DatabaseSessionLocal() as session:
                try:
                    # Call external API
                    async with httpx.AsyncClient() as client:
                        response = await client.get(
                            f"https://api.example.com/data/{external_id}",
                            timeout=30,
                        )

                    if response.status_code == 404:
                        # Don't retry - item doesn't exist
                        raise PermanentError(f"Item {external_id} not found")

                    if response.status_code == 429:
                        # Rate limited - should retry
                        raise RetryableError("Rate limited")

                    if response.status_code >= 500:
                        # Server error - should retry
                        raise RetryableError(f"Server error: {response.status_code}")

                    if response.status_code != 200:
                        # Other client errors - don't retry
                        raise PermanentError(
                            f"Unexpected status: {response.status_code}"
                        )

                    # Process response
                    data = response.json()
                    # ... save to database ...

                    result = {"status": "success", "data": data}

                except (RetryableError, PermanentError):
                    raise
                except Exception as e:
                    logger.error(f"Unexpected error: {e}")
                    raise RetryableError(str(e))

        finally:
            try:
                await database_engine.dispose()
            except Exception:
                pass

        return result

    try:
        logger.info(f"Processing external_id={external_id}")
        result = _run_async(_execute())
        return result

    except PermanentError as e:
        # Don't retry - log and return failure
        logger.error(f"Permanent error (no retry): {e}")
        return {"status": "failed", "error": str(e), "retryable": False}

    except RetryableError as e:
        # Retry with exponential backoff
        try:
            countdown = 60 * (2 ** self.request.retries)  # 60, 120, 240, 480, 960
            logger.warning(f"Retryable error, retrying in {countdown}s: {e}")
            raise self.retry(exc=e, countdown=countdown)
        except MaxRetriesExceededError:
            logger.error(f"Max retries exceeded: {e}")
            return {"status": "failed", "error": str(e), "retryable": True}

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise
```

---

## Running Celery Workers

```bash
# Development
celery -A celery_app worker -P gevent --loglevel=info

# Production with concurrency
celery -A celery_app worker -P gevent --concurrency=4 --loglevel=warning

# With beat scheduler
celery -A celery_app worker -P gevent --loglevel=info -B
```

## Testing Tasks

```python
# Test task directly (without Celery)
from tasks.my_task import my_task

# Synchronous execution
result = my_task.apply(args=["arg1", "arg2"]).get()

# Async execution
result = my_task.delay("arg1", "arg2")
print(result.id)  # Task ID
print(result.get(timeout=30))  # Wait for result
```
