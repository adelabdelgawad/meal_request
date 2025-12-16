"""Log Meal Request Repository - Data access for meal request audit logs."""

from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import DatabaseError, NotFoundError
from db.models import LogMealRequest
from api.schemas.log_meal_request_schemas import LogMealRequestCreate


class LogMealRequestRepository:
    """Repository for LogMealRequest entity."""

    def __init__(self):
        pass

    async def create(
        self, session: AsyncSession, log_data: LogMealRequestCreate
    ) -> LogMealRequest:
        """
        Create a new meal request audit log entry.

        Args:
            session: Database session
            log_data: Log data to create

        Returns:
            Created LogMealRequest instance

        Raises:
            DatabaseError: If creation fails
        """
        try:
            log = LogMealRequest(
                user_id=log_data.user_id,
                meal_request_id=log_data.meal_request_id,
                action=log_data.action,
                is_successful=log_data.is_successful,
                old_value=log_data.old_value,
                new_value=log_data.new_value,
                result=log_data.result,
            )
            session.add(log)
            await session.flush()
            return log
        except Exception as e:
            await session.rollback()
            raise DatabaseError(f"Failed to create meal request log: {str(e)}")

    async def get_by_id(
        self, session: AsyncSession, log_id: str
    ) -> Optional[LogMealRequest]:
        """
        Get a meal request audit log by ID.

        Args:
            session: Database session
            log_id: Log ID (UUID string)

        Returns:
            LogMealRequest instance or None
        """
        result = await session.execute(
            select(LogMealRequest).where(LogMealRequest.id == log_id)
        )
        return result.scalar_one_or_none()

    async def get_by_meal_request_id(
        self,
        session: AsyncSession,
        meal_request_id: int,
        page: int = 1,
        per_page: int = 25,
    ) -> Tuple[List[LogMealRequest], int]:
        """
        Get audit logs for a specific meal request.

        Args:
            session: Database session
            meal_request_id: Meal request ID
            page: Page number (1-indexed)
            per_page: Items per page

        Returns:
            Tuple of (list of logs, total count)
        """
        from core.pagination import calculate_offset

        query = select(LogMealRequest).where(
            LogMealRequest.meal_request_id == meal_request_id
        ).order_by(LogMealRequest.timestamp.desc())

        # Count query
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await session.execute(count_query)
        total = count_result.scalar() or 0

        # Paginated results
        offset = calculate_offset(page, per_page)
        result = await session.execute(query.offset(offset).limit(per_page))
        return result.scalars().all(), total

    async def query(
        self,
        session: AsyncSession,
        user_id: Optional[str] = None,
        meal_request_id: Optional[int] = None,
        action: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        page: int = 1,
        per_page: int = 25,
    ) -> Tuple[List[LogMealRequest], int]:
        """
        Query meal request audit logs with filters.

        Args:
            session: Database session
            user_id: Filter by user ID
            meal_request_id: Filter by meal request ID
            action: Filter by action type
            from_date: Filter by timestamp >= from_date
            to_date: Filter by timestamp <= to_date
            page: Page number (1-indexed)
            per_page: Items per page

        Returns:
            Tuple of (list of logs, total count)
        """
        from core.pagination import calculate_offset

        query = select(LogMealRequest)

        # Apply filters
        if user_id is not None:
            query = query.where(LogMealRequest.user_id == user_id)
        if meal_request_id is not None:
            query = query.where(LogMealRequest.meal_request_id == meal_request_id)
        if action is not None:
            query = query.where(LogMealRequest.action == action)
        if from_date is not None:
            query = query.where(LogMealRequest.timestamp >= from_date)
        if to_date is not None:
            query = query.where(LogMealRequest.timestamp <= to_date)

        # Order by timestamp descending (most recent first)
        query = query.order_by(LogMealRequest.timestamp.desc())

        # Count query
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await session.execute(count_query)
        total = count_result.scalar() or 0

        # Paginated results
        offset = calculate_offset(page, per_page)
        result = await session.execute(query.offset(offset).limit(per_page))
        return result.scalars().all(), total

    async def delete(self, session: AsyncSession, log_id: str) -> None:
        """
        Delete a meal request audit log by ID.

        Args:
            session: Database session
            log_id: Log ID (UUID string)

        Raises:
            NotFoundError: If log not found
        """
        log = await self.get_by_id(session, log_id)
        if not log:
            raise NotFoundError(entity="LogMealRequest", identifier=log_id)

        await session.delete(log)
        await session.flush()
