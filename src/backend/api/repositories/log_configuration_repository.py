"""Log Configuration Repository - Data access layer for configuration audit logs."""

from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import DatabaseError
from db.models import LogConfiguration


class LogConfigurationRepository:
    """Repository for LogConfiguration entity."""

    def __init__(self):
        pass

    async def create(self, session: AsyncSession, log_data: dict) -> LogConfiguration:
        """Create a new configuration audit log entry."""
        try:
            log = LogConfiguration(**log_data)
            session.add(log)
            await session.flush()
            return log
        except Exception as e:
            await session.rollback()
            raise DatabaseError(f"Failed to create configuration audit log: {str(e)}")

    async def get_by_id(self, session: AsyncSession, log_id: str) -> Optional[LogConfiguration]:
        """Get a configuration audit log by ID."""
        result = await session.execute(
            select(LogConfiguration).where(LogConfiguration.id == log_id)
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        session: AsyncSession,
        page: int = 1,
        per_page: int = 25,
        admin_id: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        action: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> Tuple[List[LogConfiguration], int]:
        """List configuration audit logs with optional filtering."""
        from core.pagination import calculate_offset

        query = select(LogConfiguration)

        # Apply filters
        filters = []
        if admin_id is not None:
            filters.append(LogConfiguration.admin_id == admin_id)
        if entity_type is not None:
            filters.append(LogConfiguration.entity_type == entity_type)
        if entity_id is not None:
            filters.append(LogConfiguration.entity_id == entity_id)
        if action is not None:
            filters.append(LogConfiguration.action == action)
        if from_date is not None:
            filters.append(LogConfiguration.timestamp >= from_date)
        if to_date is not None:
            filters.append(LogConfiguration.timestamp <= to_date)

        if filters:
            query = query.where(and_(*filters))

        # Order by timestamp descending (most recent first)
        query = query.order_by(LogConfiguration.timestamp.desc())

        # Get total count
        count_query = select(func.count()).select_from((query).subquery())
        count_result = await session.execute(count_query)
        total = count_result.scalar() or 0

        # Apply pagination
        offset = calculate_offset(page, per_page)
        result = await session.execute(query.offset(offset).limit(per_page))
        return result.scalars().all(), total

    async def get_by_entity(
        self,
        session: AsyncSession,
        entity_type: str,
        entity_id: str,
        limit: int = 50
    ) -> List[LogConfiguration]:
        """Get audit logs for a specific entity."""
        result = await session.execute(
            select(LogConfiguration)
            .where(
                and_(
                    LogConfiguration.entity_type == entity_type,
                    LogConfiguration.entity_id == entity_id
                )
            )
            .order_by(LogConfiguration.timestamp.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def get_by_entity_type(
        self,
        session: AsyncSession,
        entity_type: str,
        limit: int = 100
    ) -> List[LogConfiguration]:
        """Get audit logs for a specific entity type."""
        result = await session.execute(
            select(LogConfiguration)
            .where(LogConfiguration.entity_type == entity_type)
            .order_by(LogConfiguration.timestamp.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def get_by_admin_id(
        self,
        session: AsyncSession,
        admin_id: str,
        limit: int = 50
    ) -> List[LogConfiguration]:
        """Get audit logs for a specific admin."""
        result = await session.execute(
            select(LogConfiguration)
            .where(LogConfiguration.admin_id == admin_id)
            .order_by(LogConfiguration.timestamp.desc())
            .limit(limit)
        )
        return result.scalars().all()
