"""
Audit log retention policy enforcement.

Deletes audit logs older than retention period to prevent unbounded table growth.
Runs daily at 3:00 AM UTC via scheduler (if configured).
"""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import (
    LogAuthentication,
    LogConfiguration,
    LogMealRequest,
    LogMealRequestLine,
    LogPermission,
    LogReplication,
    LogRole,
    LogUser,
)

logger = logging.getLogger(__name__)

# Retention policies per table type
RETENTION_DAYS = {
    "log_authentication": 90,  # Security events: 3 months
    "log_meal_request": 365,  # Business operations: 1 year
    "log_user": 1825,  # User management: 5 years (regulatory)
    "log_role": 1825,  # Role management: 5 years (regulatory)
    "log_configuration": 1825,  # Configuration: 5 years (regulatory)
    "log_traffic": 30,  # HTTP traffic: 1 month (legacy, being removed)
    "log_permission": 365,  # Permissions: 1 year
    "log_meal_request_line": 365,  # Meal request lines: 1 year
    "log_replication": 90,  # Replication: 3 months (operational)
}


async def cleanup_audit_logs(
    session: AsyncSession, retention_days_override: int = None
) -> dict:
    """
    Delete audit logs older than their retention period.

    Args:
        session: AsyncSession for database operations
        retention_days_override: Override retention days for all tables (for testing/manual runs)

    Returns:
        dict: Counts of deleted records per table
    """
    deleted_counts = {}

    audit_tables = [
        ("log_authentication", LogAuthentication),
        ("log_meal_request", LogMealRequest),
        ("log_user", LogUser),
        ("log_role", LogRole),
        ("log_configuration", LogConfiguration),
        ("log_permission", LogPermission),
        ("log_meal_request_line", LogMealRequestLine),
        ("log_replication", LogReplication),
    ]

    logger.info("Starting audit cleanup with per-table retention policies")

    for table_name, model in audit_tables:
        try:
            # Get retention days for this table (or use override)
            retention_days = retention_days_override or RETENTION_DAYS.get(
                table_name, 60
            )
            cutoff_date = datetime.now(timezone.utc) - timedelta(
                days=retention_days
            )

            # Delete records older than cutoff_date
            stmt = delete(model).where(model.timestamp < cutoff_date)
            result = await session.execute(stmt)
            deleted_counts[table_name] = result.rowcount

            logger.info(
                f"Deleted {result.rowcount} records from {table_name} "
                f"(retention: {retention_days} days, cutoff: {cutoff_date})"
            )
        except Exception as e:
            logger.error(f"Failed to cleanup {table_name}: {e}")
            deleted_counts[table_name] = 0

    # Commit all deletions
    await session.commit()

    total_deleted = sum(deleted_counts.values())
    logger.info(
        f"Audit cleanup complete: {total_deleted} total records deleted"
    )

    return deleted_counts


async def get_audit_log_statistics(session: AsyncSession) -> dict:
    """
    Get statistics about audit log table sizes and age.

    Args:
        session: AsyncSession for database operations

    Returns:
        dict: Statistics per table including count, oldest, newest timestamps
    """
    from sqlalchemy import func, select

    audit_tables = [
        ("log_authentication", LogAuthentication),
        ("log_meal_request", LogMealRequest),
        ("log_user", LogUser),
        ("log_role", LogRole),
        ("log_configuration", LogConfiguration),
        ("log_permission", LogPermission),
        ("log_meal_request_line", LogMealRequestLine),
        ("log_replication", LogReplication),
    ]

    statistics = {}

    for table_name, model in audit_tables:
        try:
            # Count total records
            count_stmt = select(func.count()).select_from(model)
            count_result = await session.execute(count_stmt)
            total_count = count_result.scalar()

            # Get oldest and newest timestamps
            stats_stmt = select(
                func.min(model.timestamp), func.max(model.timestamp)
            )
            stats_result = await session.execute(stats_stmt)
            oldest, newest = stats_result.one()

            retention_days = RETENTION_DAYS.get(table_name, 60)

            statistics[table_name] = {
                "total_count": total_count,
                "oldest_timestamp": oldest.isoformat() if oldest else None,
                "newest_timestamp": newest.isoformat() if newest else None,
                "retention_days": retention_days,
            }
        except Exception as e:
            logger.error(f"Failed to get statistics for {table_name}: {e}")
            statistics[table_name] = {
                "total_count": 0,
                "oldest_timestamp": None,
                "newest_timestamp": None,
                "retention_days": RETENTION_DAYS.get(table_name, 60),
                "error": str(e),
            }

    return statistics
