"""Service for logging replication operations."""

import json
import logging
from datetime import datetime
from typing import Optional, Tuple, List, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession

from api.repositories.log_replication_repository import LogReplicationRepository
from api.schemas.log_replication_schemas import LogReplicationCreate
from db.model import LogReplication

logger = logging.getLogger(__name__)


class LogReplicationService:
    """Service for creating and querying replication audit logs."""

    def __init__(self):
        self.repository = LogReplicationRepository()

    async def log_replication(
        self,
        session: AsyncSession,
        operation_type: str,
        is_successful: bool,
        admin_id: Optional[str] = None,
        records_processed: Optional[int] = None,
        records_created: Optional[int] = None,
        records_updated: Optional[int] = None,
        records_skipped: Optional[int] = None,
        records_failed: Optional[int] = None,
        source_system: Optional[str] = None,
        duration_ms: Optional[int] = None,
        error_message: Optional[str] = None,
        result: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log a replication operation.

        Args:
            session: Async database session
            operation_type: Type of replication (hris_department_sync, hris_employee_sync, etc.)
            is_successful: Whether the operation succeeded
            admin_id: User ID who triggered the operation (None for scheduled jobs)
            records_processed: Total records processed
            records_created: Records created
            records_updated: Records updated
            records_skipped: Records skipped
            records_failed: Records failed
            source_system: Source system name (HRIS, TMS, etc.)
            duration_ms: Operation duration in milliseconds
            error_message: Error message if failed
            result: Additional result data as dict

        Returns:
            None (non-blocking logging)
        """
        try:
            log_data = LogReplicationCreate(
                operation_type=operation_type,
                is_successful=is_successful,
                admin_id=admin_id,
                records_processed=records_processed,
                records_created=records_created,
                records_updated=records_updated,
                records_skipped=records_skipped,
                records_failed=records_failed,
                source_system=source_system,
                duration_ms=duration_ms,
                error_message=error_message,
                result=json.dumps(result, default=str) if result else None,
            )
            await self.repository.create(session, log_data.model_dump(by_alias=False))
            logger.debug(
                f"Logged replication event: operation_type={operation_type}, "
                f"is_successful={is_successful}"
            )
        except Exception as e:
            # Non-blocking: log error but don't raise to prevent audit failures from breaking operations
            logger.error(
                f"Failed to log replication event: {e}",
                exc_info=True,
            )

    async def get_log(self, session: AsyncSession, log_id: str) -> Optional[LogReplication]:
        """
        Get a replication log by ID.

        Args:
            session: Async database session
            log_id: Log ID

        Returns:
            LogReplication instance or None
        """
        return await self.repository.get_by_id(session, log_id)

    async def query_logs(
        self,
        session: AsyncSession,
        operation_type: Optional[str] = None,
        is_successful: Optional[bool] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        page: int = 1,
        per_page: int = 25,
    ) -> Tuple[List[LogReplication], int]:
        """
        Query replication logs with filters.

        Args:
            session: Async database session
            operation_type: Filter by operation type
            is_successful: Filter by success status
            from_date: Filter from date
            to_date: Filter to date
            page: Page number
            per_page: Records per page

        Returns:
            Tuple of (logs, total_count)
        """
        return await self.repository.query(
            session=session,
            operation_type=operation_type,
            is_successful=is_successful,
            from_date=from_date,
            to_date=to_date,
            page=page,
            per_page=per_page,
        )

    async def delete_log(self, session: AsyncSession, log_id: str) -> bool:
        """
        Delete a replication log.

        Args:
            session: Async database session
            log_id: Log ID

        Returns:
            True if deleted, False if not found
        """
        return await self.repository.delete(session, log_id)
