"""Log Role Repository - Data access layer for role audit logs."""

from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import DatabaseError
from db.model import LogRole
from .base import BaseRepository


class LogRoleRepository(BaseRepository[LogRole]):
    """Repository for LogRole entity."""

        super().__init__(session)

    async def create(self, log_data: dict) -> LogRole:
        """Create a new role audit log entry."""
        try:
            log = LogRole(**log_data)
            self.session.add(log)
            await self.session.flush()
            return log
        except Exception as e:
            await self.session.rollback()
            raise DatabaseError(f"Failed to create role audit log: {str(e)}")

    async def get_by_id(self, log_id: str) -> Optional[LogRole]:
        """Get a role audit log by ID."""
        result = await self.session.execute(
            select(LogRole).where(LogRole.id == log_id)
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        session: AsyncSession,
        page: int = 1,
        per_page: int = 25,
        admin_id: Optional[str] = None,
        role_id: Optional[str] = None,
        action: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> Tuple[List[LogRole], int]:
        """List role audit logs with optional filtering."""
        from core.pagination import calculate_offset

        query = select(LogRole)

        # Apply filters
        filters = []
        if admin_id is not None:
            filters.append(LogRole.admin_id == admin_id)
        if role_id is not None:
            filters.append(LogRole.role_id == role_id)
        if action is not None:
            filters.append(LogRole.action == action)
        if from_date is not None:
            filters.append(LogRole.timestamp >= from_date)
        if to_date is not None:
            filters.append(LogRole.timestamp <= to_date)

        if filters:
            query = query.where(and_(*filters))

        # Order by timestamp descending (most recent first)
        query = query.order_by(LogRole.timestamp.desc())

        # Get total count
        count_query = select(func.count()).select_from((query).subquery())
        count_result = await self.session.execute(count_query)
        total = count_result.scalar() or 0

        # Apply pagination
        offset = calculate_offset(page, per_page)
        result = await self.session.execute(query.offset(offset).limit(per_page))
        return list(result.scalars().all()), total

    async def get_by_role_id(
        self,
        session: AsyncSession,
        role_id: str,
        limit: int = 50
    ) -> List[LogRole]:
        """Get audit logs for a specific role."""
        result = await self.session.execute(
            select(LogRole)
            .where(LogRole.role_id == role_id)
            .order_by(LogRole.timestamp.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def get_by_admin_id(
        self,
        session: AsyncSession,
        admin_id: str,
        limit: int = 50
    ) -> List[LogRole]:
        """Get audit logs for a specific admin."""
        result = await self.session.execute(
            select(LogRole)
            .where(LogRole.admin_id == admin_id)
            .order_by(LogRole.timestamp.desc())
            .limit(limit)
        )
        return result.scalars().all()
