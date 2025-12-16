"""
Attendance Sync Background Job - Syncs attendance data from TMS to local database.

This module provides the background job entry point for attendance synchronization.
It is designed to be used with APScheduler in both the main app and replicate.py.

The sync is line-scoped:
- Only syncs attendance for existing MealRequestLine rows
- Never performs blind/full TMS attendance copy
- Groups by date for efficient batch queries
"""

import logging
from datetime import datetime, timezone

from api.deps import get_session
from api.services.attendance_sync_service import AttendanceSyncService
from api.services.log_replication_service import LogReplicationService
from db.hris_database import get_hris_session
from settings import settings

logger = logging.getLogger(__name__)


async def run_attendance_sync() -> None:
    """
    Background job to sync attendance data from TMS.

    Called by APScheduler at configured intervals.

    Only syncs attendance for existing MealRequestLines - never blind TMS copy.
    Uses sliding window approach (configurable months_back).
    """
    logger.info("Starting attendance sync job...")

    hris_session = None
    app_session = None
    start_time = datetime.now(timezone.utc)

    try:
        # Get database sessions using async generators
        hris_session_gen = get_hris_session()
        hris_session = await hris_session_gen.__anext__()

        app_session_gen = get_session()
        app_session = await app_session_gen.__anext__()

        # Run the sync
        service = AttendanceSyncService()
        result = await service.sync_sliding_window(
            session=app_session,
            hris_session=hris_session,
            months_back=settings.ATTENDANCE_SYNC_MONTHS_BACK,
        )

        logger.info(
            f"Attendance sync completed: "
            f"{result.synced}/{result.total} synced, "
            f"{result.unchanged} unchanged, "
            f"{result.not_found} not found, "
            f"{result.errors} errors"
        )

        # Log replication success
        duration_ms = int(
            (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        )
        log_service = LogReplicationService()
        await log_service.log_replication(
            session=app_session,
            operation_type="attendance_sync",
            is_successful=True,
            admin_id=None,  # Background job - no user context in sync_attendance.py
            records_processed=result.total,
            records_created=result.synced,
            records_skipped=result.unchanged,
            records_failed=result.errors,
            source_system="TMS",
            duration_ms=duration_ms,
            result={
                "synced": result.synced,
                "unchanged": result.unchanged,
                "not_found": result.not_found,
                "errors": result.errors,
            },
        )

    except Exception as e:
        logger.exception(f"Error during attendance sync: {e}")
        # Log replication failure
        duration_ms = int(
            (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        )
        if app_session:
            log_service = LogReplicationService()
            await log_service.log_replication(
                session=app_session,
                operation_type="attendance_sync",
                is_successful=False,
                admin_id=None,  # Background job - no user context in sync_attendance.py
                source_system="TMS",
                duration_ms=duration_ms,
                error_message=str(e),
            )
            await app_session.rollback()
        raise
    finally:
        # Clean up sessions
        if hris_session:
            await hris_session.close()
        if app_session:
            await app_session.close()


def register_attendance_sync_job(scheduler) -> None:
    """
    Register the attendance sync job with APScheduler.

    Args:
        scheduler: APScheduler AsyncIOScheduler instance
    """
    scheduler.add_job(
        run_attendance_sync,
        "interval",
        minutes=settings.ATTENDANCE_SYNC_INTERVAL_MINUTES,
        id="attendance_sync",
        name="Sync MealRequestLine attendance from TMS",
        replace_existing=True,
    )
    logger.info(
        f"Registered attendance sync job "
        f"(interval: {settings.ATTENDANCE_SYNC_INTERVAL_MINUTES} minutes)"
    )
