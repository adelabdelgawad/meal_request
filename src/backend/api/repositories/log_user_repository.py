"""
User Management Audit Log Repository - Stream 4

Repository for accessing user management audit log data.
"""

from typing import Optional
from datetime import datetime
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import LogUser
from api.schemas.log_user_schemas import LogUserCreate


class LogUserRepository:
    """Repository for user management audit log operations."""

    async def create(self, session: AsyncSession, log_data: LogUserCreate) -> LogUser:
        """
        Create a new user management audit log entry.

        Args:
            session: Database session
            log_data: Log entry data

        Returns:
            Created log entry
        """
        log_entry = LogUser(
            admin_id=log_data.admin_id,
            target_user_id=log_data.target_user_id,
            action=log_data.action,
            is_successful=log_data.is_successful,
            old_value=log_data.old_value,
            new_value=log_data.new_value,
            result=log_data.result,
        )
        session.add(log_entry)
        await session.commit()
        await session.refresh(log_entry)
        return log_entry

    async def get_by_id(self, session: AsyncSession, log_id: str) -> Optional[LogUser]:
        """
        Get a user management audit log entry by ID.

        Args:
            session: Database session
            log_id: Log entry ID

        Returns:
            Log entry if found, None otherwise
        """
        query = select(LogUser).where(LogUser.id == log_id)
        result = await session.execute(query)
        return result.scalar_one_or_none()

    async def query(
        self,
        session: AsyncSession,
        admin_id: Optional[str] = None,
        target_user_id: Optional[str] = None,
        action: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        page: int = 1,
        per_page: int = 25,
    ) -> tuple[list[LogUser], int]:
        """
        Query user management audit logs with filters.

        Args:
            session: Database session
            admin_id: Filter by admin user ID
            target_user_id: Filter by target user ID
            action: Filter by action type
            from_date: Filter by start date
            to_date: Filter by end date
            page: Page number (1-indexed)
            per_page: Items per page

        Returns:
            Tuple of (log entries, total count)
        """
        query = select(LogUser)

        # Apply filters
        if admin_id:
            query = query.where(LogUser.admin_id == admin_id)
        if target_user_id:
            query = query.where(LogUser.target_user_id == target_user_id)
        if action:
            query = query.where(LogUser.action == action)
        if from_date:
            query = query.where(LogUser.timestamp >= from_date)
        if to_date:
            query = query.where(LogUser.timestamp <= to_date)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await session.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination and ordering
        query = query.order_by(LogUser.timestamp.desc())
        query = query.offset((page - 1) * per_page).limit(per_page)

        # Execute query
        result = await session.execute(query)
        logs = result.scalars().all()

        return list(logs), total

    async def get_by_target_user(
        self,
        session: AsyncSession,
        target_user_id: str,
        page: int = 1,
        per_page: int = 25,
    ) -> tuple[list[LogUser], int]:
        """
        Get all audit log entries for a specific target user.

        Args:
            session: Database session
            target_user_id: Target user ID
            page: Page number (1-indexed)
            per_page: Items per page

        Returns:
            Tuple of (log entries, total count)
        """
        return await self.query(
            session=session,
            target_user_id=target_user_id,
            page=page,
            per_page=per_page,
        )
