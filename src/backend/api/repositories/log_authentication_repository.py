"""Log Authentication Repository - Data access for authentication audit logs."""

from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import DatabaseError, NotFoundError
from db.models import LogAuthentication
from api.schemas.log_authentication_schemas import LogAuthenticationCreate


class LogAuthenticationRepository:
    """Repository for LogAuthentication entity."""

    def __init__(self):
        pass

    async def create(
        self, session: AsyncSession, log_data: LogAuthenticationCreate
    ) -> LogAuthentication:
        """
        Create a new authentication log entry.

        Args:
            session: Database session
            log_data: Authentication log data

        Returns:
            Created LogAuthentication object

        Raises:
            DatabaseError: If creation fails
        """
        try:
            log = LogAuthentication(
                user_id=log_data.user_id,
                action=log_data.action,
                is_successful=log_data.is_successful,
                ip_address=log_data.ip_address,
                user_agent=log_data.user_agent,
                device_fingerprint=log_data.device_fingerprint,
                result=log_data.result,
            )
            session.add(log)
            await session.flush()
            return log
        except Exception as e:
            await session.rollback()
            raise DatabaseError(f"Failed to create authentication log: {str(e)}")

    async def get_by_id(
        self, session: AsyncSession, log_id: str
    ) -> Optional[LogAuthentication]:
        """
        Get an authentication log by ID.

        Args:
            session: Database session
            log_id: Log ID (UUID as string)

        Returns:
            LogAuthentication object or None if not found
        """
        result = await session.execute(
            select(LogAuthentication).where(LogAuthentication.id == log_id)
        )
        return result.scalar_one_or_none()

    async def query(
        self,
        session: AsyncSession,
        page: int = 1,
        per_page: int = 25,
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        is_successful: Optional[bool] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> Tuple[List[LogAuthentication], int]:
        """
        Query authentication logs with filters.

        Args:
            session: Database session
            page: Page number (1-indexed)
            per_page: Items per page
            user_id: Filter by user ID
            action: Filter by action type
            is_successful: Filter by success status
            from_date: Filter by start date
            to_date: Filter by end date

        Returns:
            Tuple of (list of logs, total count)
        """
        from core.pagination import calculate_offset

        query = select(LogAuthentication)

        # Apply filters
        if user_id is not None:
            query = query.where(LogAuthentication.user_id == user_id)
        if action is not None:
            query = query.where(LogAuthentication.action == action)
        if is_successful is not None:
            query = query.where(LogAuthentication.is_successful == is_successful)
        if from_date is not None:
            query = query.where(LogAuthentication.timestamp >= from_date)
        if to_date is not None:
            query = query.where(LogAuthentication.timestamp <= to_date)

        # Order by timestamp descending (most recent first)
        query = query.order_by(LogAuthentication.timestamp.desc())

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await session.execute(count_query)
        total = count_result.scalar() or 0

        # Paginate
        offset = calculate_offset(page, per_page)
        result = await session.execute(query.offset(offset).limit(per_page))
        return list(result.scalars().all()), total

    async def get_recent(
        self, session: AsyncSession, user_id: Optional[str] = None, limit: int = 10
    ) -> List[LogAuthentication]:
        """
        Get recent authentication logs for dashboard.

        Args:
            session: Database session
            user_id: Optional user ID to filter by
            limit: Maximum number of logs to return

        Returns:
            List of recent LogAuthentication objects
        """
        query = select(LogAuthentication)

        if user_id is not None:
            query = query.where(LogAuthentication.user_id == user_id)

        query = query.order_by(LogAuthentication.timestamp.desc()).limit(limit)

        result = await session.execute(query)
        return list(result.scalars().all())

    async def delete(self, session: AsyncSession, log_id: str) -> None:
        """
        Delete an authentication log.

        Args:
            session: Database session
            log_id: Log ID (UUID as string)

        Raises:
            NotFoundError: If log not found
        """
        log = await self.get_by_id(session, log_id)
        if not log:
            raise NotFoundError(entity="LogAuthentication", identifier=log_id)

        await session.delete(log)
        await session.flush()
