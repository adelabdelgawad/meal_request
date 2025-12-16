"""Log Permission Repository."""

from typing import List, Optional, Tuple

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import DatabaseError, NotFoundError
from db.models import LogPermission


class LogPermissionRepository:
    """Repository for LogPermission entity."""

    def __init__(self):
        pass

    async def create(self, session: AsyncSession, log: LogPermission) -> LogPermission:
        try:
            session.add(log)
            await session.flush()
            return log
        except Exception as e:
            await session.rollback()
            raise DatabaseError(f"Failed to create permission log: {str(e)}")

    async def get_by_id(self, session: AsyncSession, log_id: int) -> Optional[LogPermission]:
        result = await session.execute(
            select(LogPermission).where(LogPermission.id == log_id)
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        session: AsyncSession,
        page: int = 1,
        per_page: int = 25,
        account_id: Optional[int] = None,
        admin_id: Optional[int] = None,
        action: Optional[str] = None,
    ) -> Tuple[List[LogPermission], int]:
        from core.pagination import calculate_offset

        query = select(LogPermission)

        if account_id is not None:
            query = query.where(LogPermission.account_id == account_id)
        if admin_id is not None:
            query = query.where(LogPermission.admin_id == admin_id)
        if action is not None:
            query = query.where(LogPermission.action == action)

        # Optimized count query


        count_query = select(func.count()).select_from((query).subquery())


        count_result = await session.execute(count_query)


        total = count_result.scalar() or 0

        offset = calculate_offset(page, per_page)
        result = await session.execute(query.offset(offset).limit(per_page))
        return result.scalars().all(), total

    async def delete(self, session: AsyncSession, log_id: int) -> None:
        log = await self.get_by_id(session, log_id)
        if not log:
            raise NotFoundError(entity="LogPermission", identifier=log_id)

        await session.delete(log)
        await session.flush()
