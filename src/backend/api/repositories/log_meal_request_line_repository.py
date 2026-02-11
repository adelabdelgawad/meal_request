"""Log Meal Request Line Repository."""

from typing import List, Optional, Tuple

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import DatabaseError, NotFoundError
from db.model import LogMealRequestLine
from .base import BaseRepository


class LogMealRequestLineRepository(BaseRepository[LogMealRequestLine]):
    """Repository for LogMealRequestLine entity."""

        super().__init__(session)

    async def create(self, log: LogMealRequestLine) -> LogMealRequestLine:
        try:
            self.session.add(log)
            await self.session.flush()
            return log
        except Exception as e:
            await self.session.rollback()
            raise DatabaseError(
                f"Failed to create meal request line log: {str(e)}"
            )

    async def get_by_id(self, log_id: int) -> Optional[LogMealRequestLine]:
        result = await self.session.execute(
            select(LogMealRequestLine).where(LogMealRequestLine.id == log_id)
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        session: AsyncSession,
        page: int = 1,
        per_page: int = 25,
        meal_request_line_id: Optional[int] = None,
        account_id: Optional[int] = None,
        action: Optional[str] = None,
    ) -> Tuple[List[LogMealRequestLine], int]:
        from core.pagination import calculate_offset

        query = select(LogMealRequestLine)

        if meal_request_line_id is not None:
            query = query.where(
                LogMealRequestLine.meal_request_line_id == meal_request_line_id
            )
        if account_id is not None:
            query = query.where(LogMealRequestLine.account_id == account_id)
        if action is not None:
            query = query.where(LogMealRequestLine.action == action)

        # Optimized count query


        count_query = select(func.count()).select_from((query).subquery())


        count_result = await self.session.execute(count_query)


        total = count_result.scalar() or 0

        offset = calculate_offset(page, per_page)
        result = await self.session.execute(query.offset(offset).limit(per_page))
        return list(result.scalars().all()), total

    async def delete(self, log_id: int) -> None:
        log = await self.get_by_id(log_id)
        if not log:
            raise NotFoundError(f"LogMealRequestLine with ID {log_id} not found")

        await self.session.delete(log)
        await self.session.flush()
