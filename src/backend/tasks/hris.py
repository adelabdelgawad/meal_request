"""
Celery HRIS Replication Tasks.

Handles HRIS data replication from SQL Server to local MariaDB with
automatic retry logic for network failures.

Uses gevent-compatible async execution without manual event loop creation.
Gevent is applied via worker pool (-P gevent) at startup, which patches asyncio.
"""

import logging
import socket
from datetime import datetime, timezone
from celery import shared_task
from utils.structured_logger import get_structured_logger

logger = logging.getLogger(__name__)
structured_logger = get_structured_logger(__name__)


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
def hris_replication_task(self, execution_id: str = None, triggered_by_user_id: str = None) -> dict:
    """
    Celery task for HRIS data replication.

    Uses asyncio.run() which works correctly with gevent-patched asyncio.
    This avoids manual event loop creation/closing that caused issues.

    Args:
        execution_id: Scheduler execution ID to update status when complete
        triggered_by_user_id: User ID who manually triggered the sync (None for scheduled tasks)

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
                        await replicate(hris_session, app_session, triggered_by_user_id=triggered_by_user_id)
                        await app_session.commit()
                        logger.info("HRIS replication completed successfully")

                        result = {"status": "success", "message": "HRIS replication completed"}

                        # Update execution status if needed
                        if execution_id:
                            try:
                                completed_at = datetime.now(timezone.utc)
                                duration_ms = int((completed_at - started_at).total_seconds() * 1000)
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
                                    logger.info(f"✅ Updated execution {execution_id} to SUCCESS")

                                    # INSTRUMENTATION POINT 8: Celery task completion
                                    structured_logger.log_celery_task_complete(
                                        task_name="hris_replication",
                                        execution_id=execution_id,
                                        final_status="SUCCESS",
                                        duration_ms=duration_ms
                                    )
                            except Exception as update_err:
                                logger.error(f"Failed to update execution status: {update_err}")

                    except Exception as e:
                        logger.error(f"Error during HRIS replication: {e}", exc_info=True)
                        error_message = str(e)

                        try:
                            await app_session.rollback()
                        except Exception:
                            pass

                        # Update execution status to failed if needed
                        if execution_id:
                            try:
                                completed_at = datetime.now(timezone.utc)
                                duration_ms = int((completed_at - started_at).total_seconds() * 1000)
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

                                    # INSTRUMENTATION POINT 8: Celery task completion (failure)
                                    structured_logger.log_celery_task_complete(
                                        task_name="hris_replication",
                                        execution_id=execution_id,
                                        final_status="FAILED",
                                        duration_ms=duration_ms,
                                        error_message=error_message
                                    )
                            except Exception as update_err:
                                logger.error(f"Failed to update execution status in error handler: {update_err}")

                        raise

        except Exception as e:
            logger.error(f"Error during Celery HRIS replication: {e}")
            raise
        finally:
            # Dispose engines before event loop closes to prevent "Event loop is closed" warnings
            # This is critical for Celery tasks since asyncio.run() creates/destroys loops per task
            # The singleton pattern in hris_database will recreate the engine on next task
            logger.debug("Disposing database engines to prevent event loop cleanup warnings...")
            try:
                await dispose_hris_engine()
                logger.debug("HRIS engine disposed and globals reset")
            except Exception as e:
                logger.warning(f"Failed to dispose HRIS engine: {e}")

            try:
                await database_engine.dispose()
                logger.debug("Maria database engine disposed")
            except Exception as e:
                logger.warning(f"Failed to dispose Maria engine: {e}")

        return result

    try:
        logger.info(f"Starting Celery HRIS replication task (execution_id: {execution_id}, triggered_by: {triggered_by_user_id or 'scheduled'})")

        # INSTRUMENTATION POINT 7: Celery task start
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
                "time_limit": 660
            }
        )

        result = _run_async(_execute())
        logger.info("HRIS replication completed successfully")
        return result

    except Exception as e:
        logger.error(f"Error during Celery HRIS replication: {e}")
        raise
