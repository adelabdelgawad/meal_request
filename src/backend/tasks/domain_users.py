"""
Celery Domain Users Sync Tasks.

Handles synchronization of domain users (Active Directory/LDAP users)
to the local database with automatic retry logic for failures.

Uses gevent-compatible async execution without manual event loop creation.
"""

import logging
from datetime import datetime, timezone
from celery import shared_task

logger = logging.getLogger(__name__)


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
def sync_domain_users(self) -> dict:
    """
    Celery task for syncing domain users from Active Directory/LDAP.

    Fetches all enabled users from AD and synchronizes them with the
    local domain_user table.

    Returns:
        dict with sync results (deleted_count, created_count, ad_users_fetched)
    """
    async def _execute():
        from api.services.domain_user_service import DomainUserService
        from db.database import DatabaseSessionLocal, database_engine

        service = DomainUserService()
        started_at = datetime.now(timezone.utc)
        error_message = None
        result = None

        try:
            async with DatabaseSessionLocal() as app_session:
                try:
                    logger.info("Starting domain user sync from Active Directory...")

                    # Call the sync service method
                    sync_result = await service.sync_from_active_directory(app_session)

                    # Commit the changes
                    await app_session.commit()

                    # Prepare result
                    result = {
                        "status": "success",
                        "deleted_count": sync_result.deleted_count,
                        "created_count": sync_result.created_count,
                        "ad_users_fetched": sync_result.ad_users_fetched,
                        "started_at": started_at.isoformat(),
                        "completed_at": datetime.now(timezone.utc).isoformat(),
                    }

                    logger.info(
                        f"Domain user sync completed: "
                        f"deleted={sync_result.deleted_count}, "
                        f"created={sync_result.created_count}, "
                        f"fetched={sync_result.ad_users_fetched}"
                    )

                except Exception as e:
                    await app_session.rollback()
                    error_message = str(e)
                    logger.error(f"Domain user sync failed: {e}", exc_info=True)
                    raise

        except Exception as e:
            logger.error(f"Outer error during domain user sync: {e}", exc_info=True)
            raise
        finally:
            # CRITICAL: Dispose engine BEFORE event loop closes
            logger.debug("Disposing database engine...")
            try:
                await database_engine.dispose()
                logger.debug("Database engine disposed")
            except Exception as e:
                logger.warning(f"Failed to dispose database engine: {e}")

        return result

    try:
        logger.info("Executing domain user sync task...")
        result = _run_async(_execute())
        logger.info(f"Domain user sync task completed: {result}")
        return result
    except Exception as e:
        logger.error(f"Domain user sync task failed: {e}")
        raise
