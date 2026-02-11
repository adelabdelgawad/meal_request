"""
Celery Scheduler Maintenance Tasks.

Handles scheduler cleanup operations with automatic retry logic.
"""

import asyncio
import logging

from celery import shared_task

logger = logging.getLogger(__name__)


def _run_async(coro):
    """
    Run a coroutine, handling both standalone and event-loop contexts.

    When running in Celery with gevent, an event loop already exists.
    When running standalone (e.g., tests), we need to create one.

    This function detects the context and uses the appropriate method.
    """
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


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    soft_time_limit=120,
    time_limit=180,
)
def cleanup_history_task(
    self,
    execution_id: str = None,
    retention_days: int = 30,
    triggered_by_user_id: str = None,
) -> dict:
    """
    Celery task for scheduler history cleanup.

    This task cleans up old execution history, expired locks, and stale
    scheduler instances with Celery's retry mechanism.

    Cleans up:
    - Old execution records (older than retention_days)
    - Expired locks
    - Stale scheduler instances

    Args:
        execution_id: Scheduler execution ID to update status when complete
        retention_days: Number of days to retain execution history (default: 30)
        triggered_by_user_id: User ID who manually triggered (None for scheduled)

    Returns:
        dict with cleanup statistics
    """
    from datetime import datetime, timezone

    async def _execute():
        from api.repositories.scheduler_repository import SchedulerRepository
        from api.services.scheduler_service import get_scheduler_service
        from db.database import DatabaseSessionLocal, database_engine

        scheduler_repo = SchedulerRepository()
        started_at = datetime.now(timezone.utc)
        success = False
        error_message = None
        result_dict = None

        try:
            # Create sessions directly from sessionmakers within the new event loop
            async with DatabaseSessionLocal() as app_session:
                try:
                    # Run cleanup
                    logger.info(f"Starting scheduler history cleanup (retention: {retention_days} days)...")
                    service = get_scheduler_service()
                    result = await service.cleanup_history(app_session, retention_days)

                    logger.info(
                        f"Cleanup completed: {result['deleted_executions']} executions, "
                        f"{result['deleted_locks']} locks, {result['deleted_instances']} instances"
                    )

                    success = True
                    result_dict = {
                        "status": "success",
                        "deleted_executions": result["deleted_executions"],
                        "deleted_locks": result["deleted_locks"],
                        "deleted_instances": result["deleted_instances"],
                    }

                except Exception as e:
                    logger.error(f"Error during cleanup: {e}", exc_info=True)
                    error_message = str(e)

                    # Rollback on error
                    if app_session:
                        try:
                            await app_session.rollback()
                        except Exception:
                            pass

                    # Re-raise the exception
                    raise

                finally:
                    # Update execution status regardless of success/failure
                    if execution_id and app_session:
                        try:
                            completed_at = datetime.now(timezone.utc)
                            duration_ms = int((completed_at - started_at).total_seconds() * 1000)

                            if success:
                                # Get success status
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
                                            "result_summary": f"Cleaned {result_dict['deleted_executions']} executions, {result_dict['deleted_locks']} locks, {result_dict['deleted_instances']} instances",
                                        },
                                    )
                                    await app_session.commit()
                                    logger.info(f"✅ Updated execution {execution_id} to SUCCESS")
                            else:
                                # Get failed status
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
                                    logger.info(f"❌ Updated execution {execution_id} to FAILED: {error_message}")
                        except Exception as update_err:
                            logger.error(f"Failed to update execution status in finally block: {update_err}")

        except Exception as e:
            logger.error(f"Error during Celery cleanup: {e}")
            raise
        finally:
            # Dispose engines before event loop closes
            logger.debug("Disposing database engines to prevent event loop cleanup warnings...")
            try:
                await database_engine.dispose()
                logger.debug("Maria database engine disposed")
            except Exception as e:
                logger.warning(f"Failed to dispose Maria engine: {e}")

        return result_dict

    try:
        logger.info(f"Starting Celery cleanup history task (execution_id: {execution_id})")
        result = _run_async(_execute())
        logger.info("Cleanup completed successfully")
        return result

    except Exception as e:
        logger.error(f"Error during Celery cleanup: {e}")
        raise
