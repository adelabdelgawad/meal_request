"""Repository for LogReplication audit logs."""

from datetime import datetime
from typing import Optional, Tuple, List

from sqlalchemy import delete, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import LogReplication


class LogReplicationRepository:
    """Data access layer for replication logs."""

    async def create(
        self, session: AsyncSession, log_data: dict
    ) -> LogReplication:
        """
        Create a new replication log entry.

        Args:
            session: Async database session
            log_data: Dictionary with log fields

        Returns:
            Created LogReplication instance
        """
        try:
            log = LogReplication(**log_data)
            session.add(log)
            await session.flush()
            return log
        except Exception as e:
            await session.rollback()
            raise Exception(f"Failed to create replication log: {str(e)}")

    async def get_by_id(self, session: AsyncSession, log_id: str) -> Optional[LogReplication]:
        """
        Get a replication log by ID.

        Args:
            session: Async database session
            log_id: Log ID

        Returns:
            LogReplication instance or None
        """
        stmt = select(LogReplication).where(LogReplication.id == log_id)
        result = await session.execute(stmt)
        return result.scalars().first()

    async def query(
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
        Query replication logs with filters and pagination.

        Args:
            session: Async database session
            operation_type: Filter by operation type
            is_successful: Filter by success status
            from_date: Filter from date
            to_date: Filter to date
            page: Page number (1-indexed)
            per_page: Records per page

        Returns:
            Tuple of (logs, total_count)
        """
        stmt = select(LogReplication)

        # Apply filters
        if operation_type:
            stmt = stmt.where(LogReplication.operation_type == operation_type)
        if is_successful is not None:
            stmt = stmt.where(LogReplication.is_successful == is_successful)
        if from_date:
            stmt = stmt.where(LogReplication.timestamp >= from_date)
        if to_date:
            stmt = stmt.where(LogReplication.timestamp <= to_date)

        # Get total count before pagination
        count_stmt = select(func.count(LogReplication.id)).select_from(
            select(LogReplication).where(
                (LogReplication.operation_type == operation_type)
                if operation_type
                else True
            )
            .where(
                (LogReplication.is_successful == is_successful)
                if is_successful is not None
                else True
            )
            .where((LogReplication.timestamp >= from_date) if from_date else True)
            .where((LogReplication.timestamp <= to_date) if to_date else True)
            .subquery()
        )

        count_result = await session.execute(count_stmt)
        total_count = count_result.scalar() or 0

        # Order by timestamp descending
        stmt = stmt.order_by(desc(LogReplication.timestamp))

        # Pagination
        offset = (page - 1) * per_page
        stmt = stmt.offset(offset).limit(per_page)

        result = await session.execute(stmt)
        logs = result.scalars().all()

        return logs, total_count

    async def delete(self, session: AsyncSession, log_id: str) -> bool:
        """
        Delete a replication log entry.

        Args:
            session: Async database session
            log_id: Log ID

        Returns:
            True if deleted, False if not found
        """
        stmt = delete(LogReplication).where(LogReplication.id == log_id)
        result = await session.execute(stmt)
        return result.rowcount > 0

    async def delete_older_than(
        self, session: AsyncSession, cutoff_date: datetime
    ) -> int:
        """
        Delete replication logs older than the cutoff date (cleanup operation).

        Args:
            session: Async database session
            cutoff_date: Cutoff datetime

        Returns:
            Number of records deleted
        """
        stmt = delete(LogReplication).where(LogReplication.timestamp < cutoff_date)
        result = await session.execute(stmt)
        return result.rowcount
