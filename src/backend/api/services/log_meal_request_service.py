"""Log Meal Request Service - Business logic for meal request audit logging."""

import json
import logging
from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from api.repositories.log_meal_request_repository import LogMealRequestRepository
from api.schemas.log_meal_request_schemas import LogMealRequestCreate
from core.exceptions import NotFoundError
from db.model import LogMealRequest

logger = logging.getLogger(__name__)


class LogMealRequestService:
    """Service for meal request audit log management operations."""

    def __init__(self, session: AsyncSession):
        """Initialize service."""
        self.session = session
        self._repo = LogMealRequestRepository(session)

    async def log_meal_request(
        self,
        user_id: str,
        action: str,
        is_successful: bool,
        meal_request_id: Optional[int] = None,
        old_value: Optional[dict] = None,
        new_value: Optional[dict] = None,
        result: Optional[dict] = None,
    ) -> None:
        """
        Log a meal request operation. Non-blocking - errors are logged but not raised.

        Args:
            user_id: ID of user performing action
            action: Action type (create, update_status, delete, copy, approve, reject)
            is_successful: Whether operation succeeded
            meal_request_id: ID of meal request (if applicable)
            old_value: Previous state (dict, will be JSON serialized)
            new_value: New state (dict, will be JSON serialized)
            result: Additional result data (dict, will be JSON serialized)

        Note:
            This method catches and logs all exceptions to prevent audit logging
            from disrupting business operations. It's designed to be non-blocking.
        """
        try:
            log_data = LogMealRequestCreate(
                user_id=user_id,
                meal_request_id=meal_request_id,
                action=action,
                is_successful=is_successful,
                old_value=json.dumps(old_value, default=str) if old_value else None,
                new_value=json.dumps(new_value, default=str) if new_value else None,
                result=json.dumps(result, default=str) if result else None,
            )
            await self._repo.create(session, log_data)
            logger.info(
                f"Logged meal request event: action={action}, "
                f"meal_request_id={meal_request_id}, user_id={user_id}, "
                f"is_successful={is_successful}"
            )
        except Exception as e:
            # Log the error but don't propagate it - audit logging should not break operations
            logger.error(
                f"Failed to log meal request event: action={action}, "
                f"meal_request_id={meal_request_id}, user_id={user_id}, error={e}"
            )

    async def get_log(self, log_id: str) -> LogMealRequest:
        """
        Get a meal request audit log by ID.

        Args:
            log_id: Log ID (UUID string)

        Returns:
            LogMealRequest instance

        Raises:
            NotFoundError: If log not found
        """
        log = await self._repo.get_by_id(log_id)
        if not log:
            raise NotFoundError(entity="LogMealRequest", identifier=log_id)
        return log

    async def get_logs_for_meal_request(
        self,
        meal_request_id: int,
        page: int = 1,
        per_page: int = 25,
    ) -> Tuple[List[LogMealRequest], int]:
        """
        Get audit logs for a specific meal request.

        Args:
            meal_request_id: Meal request ID
            page: Page number (1-indexed)
            per_page: Items per page

        Returns:
            Tuple of (list of logs, total count)
        """
        return await self._repo.get_by_meal_request_id(
            meal_request_id, page=page, per_page=per_page
        )

    async def query_logs(
        self,
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
        return await self._repo.query(
            user_id=user_id,
            meal_request_id=meal_request_id,
            action=action,
            from_date=from_date,
            to_date=to_date,
            page=page,
            per_page=per_page,
        )

    async def delete_log(self, log_id: str) -> None:
        """
        Delete a meal request audit log.

        Args:
            log_id: Log ID (UUID string)

        Raises:
            NotFoundError: If log not found
        """
        await self._repo.delete(log_id)
