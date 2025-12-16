"""
Celery Attendance Sync Tasks.

Handles attendance synchronization from TMS to local database with
automatic retry logic for network failures.
"""

import asyncio
import logging
from typing import List, Optional

from celery import shared_task
from settings import settings

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
    default_retry_delay=120,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    soft_time_limit=300,
    time_limit=360,
)
def sync_attendance_task(
    self,
    execution_id: str = None,
    months_back: Optional[int] = None,
    triggered_by_user_id: str = None,
) -> dict:
    """
    Celery task for sliding window attendance sync.

    This task wraps the existing AttendanceSyncService with Celery's
    retry mechanism for handling HRIS connection failures.

    Args:
        execution_id: Scheduler execution ID to update status when complete
        months_back: Number of months to look back (default from settings)
        triggered_by_user_id: User ID who manually triggered (None for scheduled tasks)

    Returns:
        dict with sync statistics
    """
    from datetime import datetime, timezone

    async def _execute():
        from api.repositories.scheduler_repository import SchedulerRepository
        from api.services.attendance_sync_service import AttendanceSyncService
        from db.maria_database import DatabaseSessionLocal, database_engine
        from db.hris_database import _get_hris_session_maker, dispose_hris_engine

        scheduler_repo = SchedulerRepository()
        started_at = datetime.now(timezone.utc)
        success = False
        error_message = None
        result_dict = None

        try:
            # Create sessions directly from sessionmakers within the new event loop
            async with DatabaseSessionLocal() as app_session:
                HrisSessionLocal = _get_hris_session_maker()
                async with HrisSessionLocal() as hris_session:
                    try:
                        # Run the sync
                        service = AttendanceSyncService()
                        lookback = months_back if months_back is not None else settings.ATTENDANCE_SYNC_MONTHS_BACK

                        result = await service.sync_sliding_window(
                            session=app_session,
                            hris_session=hris_session,
                            months_back=lookback,
                        )

                        # Commit changes
                        await app_session.commit()
                        logger.info("Attendance sync completed successfully")

                        success = True
                        result_dict = {
                            "status": "success",
                            "total": result.total,
                            "synced": result.synced,
                            "unchanged": result.unchanged,
                            "not_found": result.not_found,
                            "errors": result.errors,
                        }

                    except Exception as e:
                        logger.error(f"Error during attendance sync: {e}", exc_info=True)
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
                                                "result_summary": f"Synced {result.synced}/{result.total} records",
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
            logger.error(f"Error during Celery attendance sync: {e}")
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

        return result_dict

    try:
        logger.info(f"Starting Celery attendance sync task (execution_id: {execution_id}, triggered_by: {triggered_by_user_id or 'scheduled'})")
        result = _run_async(_execute())
        logger.info(
            f"Attendance sync completed: "
            f"{result['synced']}/{result['total']} synced, "
            f"{result['unchanged']} unchanged, "
            f"{result['not_found']} not found, "
            f"{result['errors']} errors"
        )
        return result

    except Exception as e:
        logger.error(f"Error during Celery attendance sync: {e}")
        raise


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def sync_attendance_for_lines_task(
    self,
    meal_request_line_ids: List[int],
) -> dict:
    """
    Celery task for targeted attendance sync of specific request lines.

    Used for on-demand sync when viewing request details or manual refresh.

    Args:
        meal_request_line_ids: List of MealRequestLine IDs to sync

    Returns:
        dict with sync statistics
    """
    async def _execute():
        from api.services.attendance_sync_service import AttendanceSyncService
        from db.maria_database import DatabaseSessionLocal, database_engine
        from db.hris_database import _get_hris_session_maker, dispose_hris_engine

        result_dict = None

        try:
            # Create sessions directly from sessionmakers within the new event loop
            async with DatabaseSessionLocal() as app_session:
                HrisSessionLocal = _get_hris_session_maker()
                async with HrisSessionLocal() as hris_session:
                    service = AttendanceSyncService()
                    result = await service.sync_for_request_lines(
                        session=app_session,
                        hris_session=hris_session,
                        meal_request_line_ids=meal_request_line_ids,
                    )

                    result_dict = {
                        "status": "success",
                        "total": result.total,
                        "synced": result.synced,
                        "unchanged": result.unchanged,
                        "not_found": result.not_found,
                        "errors": result.errors,
                    }

        except Exception as e:
            logger.error(f"Error during targeted attendance sync: {e}")
            raise
        finally:
            # Dispose engines before event loop closes
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

        return result_dict

    try:
        logger.info(
            f"Starting targeted attendance sync for {len(meal_request_line_ids)} lines")
        result = _run_async(_execute())
        logger.info(
            f"Targeted sync completed: {result['synced']}/{result['total']} synced")
        return result

    except Exception as e:
        logger.error(f"Error during targeted attendance sync: {e}")
        raise


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def fetch_attendance_for_meal_request_task(
    self,
    meal_request_id: int,
) -> dict:
    """
    Celery task to fetch TMS_Attendance records for all lines in a meal request.

    This task runs asynchronously after meal request creation to populate
    attendance_time for each meal_request_line from the HRIS TMS_Attendance table.

    Once complete (success or failure), updates the meal request status to Pending (1).

    Args:
        meal_request_id: ID of the MealRequest to fetch attendance for

    Returns:
        dict with processing statistics and status
    """
    async def _execute():
        from datetime import date
        from api.repositories.hris_repository import HRISRepository
        from api.repositories.meal_request_line_repository import MealRequestLineRepository
        from api.repositories.meal_request_repository import MealRequestRepository
        from db.maria_database import DatabaseSessionLocal, database_engine
        from db.hris_database import _get_hris_session_maker, dispose_hris_engine
        from db.models import Employee
        from sqlalchemy import select

        result_dict = None

        try:
            # Create sessions directly from sessionmakers within the new event loop
            async with DatabaseSessionLocal() as app_session:
                HrisSessionLocal = _get_hris_session_maker()
                async with HrisSessionLocal() as hris_session:
                    try:
                        # Get all lines for this meal request
                        line_repo = MealRequestLineRepository()
                        lines = await line_repo.get_by_request(app_session, meal_request_id)

                        if not lines:
                            logger.warning(f"No lines found for meal request {meal_request_id}")
                            result_dict = {
                                "status": "completed",
                                "total": 0,
                                "synced": 0,
                                "errors": 0,
                            }
                        else:
                            hris_repo = HRISRepository()
                            synced_count = 0
                            error_count = 0
                            total_lines = len(lines)

                            # Process each line to fetch attendance
                            for line in lines:
                                try:
                                    # Fetch employee
                                    employee_stmt = select(Employee).where(Employee.id == line.employee_id)
                                    employee_result = await app_session.execute(employee_stmt)
                                    employee = employee_result.scalar_one_or_none()

                                    if not employee:
                                        logger.warning(
                                            f"Employee {line.employee_id} not found for line {line.id}"
                                        )
                                        error_count += 1
                                        continue

                                    # Fetch sign-in time from TMS_Attendance
                                    # employee.id is the HRIS employee ID (used as primary key)
                                    sign_in_time = await hris_repo.get_today_sign_in_time(
                                        session=hris_session,
                                        employee_id=employee.id,
                                        target_date=date.today(),
                                    )

                                    # Update the line with attendance_time
                                    if sign_in_time:
                                        await line_repo.update(
                                            app_session,
                                            line.id,
                                            {"attendance_time": sign_in_time}
                                        )
                                        synced_count += 1
                                        logger.info(
                                            f"Updated line {line.id} with attendance time: {sign_in_time}"
                                        )
                                    else:
                                        logger.info(
                                            f"No attendance found for employee {employee.id} on {date.today()}"
                                        )

                                except Exception as line_err:
                                    logger.error(
                                        f"Error fetching attendance for line {line.id}: {line_err}"
                                    )
                                    error_count += 1

                            # Update meal request status to Pending (1) regardless of success/failure
                            request_repo = MealRequestRepository()
                            await request_repo.update(
                                app_session,
                                meal_request_id,
                                {"status_id": 1}  # Pending status
                            )
                            await app_session.commit()

                            logger.info(
                                f"Completed attendance fetch for meal request {meal_request_id}: "
                                f"{synced_count}/{total_lines} synced, {error_count} errors"
                            )

                            result_dict = {
                                "status": "completed",
                                "total": total_lines,
                                "synced": synced_count,
                                "errors": error_count,
                            }

                    except Exception as e:
                        logger.error(
                            f"Error processing meal request {meal_request_id}: {e}",
                            exc_info=True
                        )
                        # Still try to update status to Pending even if there was an error
                        try:
                            request_repo = MealRequestRepository()
                            await request_repo.update(
                                app_session,
                                meal_request_id,
                                {"status_id": 1}
                            )
                            await app_session.commit()
                        except Exception as status_err:
                            logger.error(
                                f"Failed to update status for meal request {meal_request_id}: {status_err}"
                            )
                        raise

        except Exception as e:
            logger.error(f"Error in fetch_attendance_for_meal_request_task: {e}")
            raise
        finally:
            # Dispose engines before event loop closes
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

        return result_dict

    try:
        logger.info(f"Starting attendance fetch for meal request {meal_request_id}")
        result = _run_async(_execute())
        logger.info(
            f"Attendance fetch completed: {result['synced']}/{result['total']} synced, "
            f"{result['errors']} errors"
        )
        return result

    except Exception as e:
        logger.error(f"Error in fetch_attendance_for_meal_request_task: {e}")
        raise
