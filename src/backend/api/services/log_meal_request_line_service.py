"""Log Meal Request Line Service - Business logic for meal request logging."""

from typing import List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from api.repositories.log_meal_request_line_repository import (
    LogMealRequestLineRepository,
)
from core.exceptions import NotFoundError
from db.models import LogMealRequestLine


class LogMealRequestLineService:
    """Service for meal request line log management operations."""

    def __init__(self):
        """Initialize service."""
        self._repo = LogMealRequestLineRepository()

    async def log_meal_request_action(
        self,
        session: AsyncSession,
        meal_request_line_id: int,
        account_id: int,
        action: str,
        is_successful: bool,
        result: Optional[str] = None,
    ) -> LogMealRequestLine:
        """Log a meal request line action."""
        log = LogMealRequestLine(
            meal_request_line_id=meal_request_line_id,
            account_id=account_id,
            action=action,
            is_successful=is_successful,
            result=result,
        )
        return await self._repo.create(session, log)

    async def get_log(self, session: AsyncSession, log_id: int) -> LogMealRequestLine:
        """Get a meal request line log by ID."""
        log = await self._repo.get_by_id(session, log_id)
        if not log:
            raise NotFoundError(entity="LogMealRequestLine", identifier=log_id)
        return log

    async def list_logs(
        self,
        session: AsyncSession,
        page: int = 1,
        per_page: int = 25,
        meal_request_line_id: Optional[int] = None,
        account_id: Optional[int] = None,
        action: Optional[str] = None,
    ) -> Tuple[List[LogMealRequestLine], int]:
        """List meal request line logs with optional filtering."""
        return await self._repo.list(session, 
            page=page,
            per_page=per_page,
            meal_request_line_id=meal_request_line_id,
            account_id=account_id,
            action=action,
        )

    async def delete_log(self, session: AsyncSession, log_id: int) -> None:
        """Delete a meal request line log."""
        await self._repo.delete(session, log_id)
