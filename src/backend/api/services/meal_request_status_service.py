"""Meal Request Status Service."""

from typing import List, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from api.repositories.meal_request_status_repository import MealRequestStatusRepository
from core.exceptions import NotFoundError
from db.model import MealRequestStatus


class MealRequestStatusService:
    """Service for meal request status management."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self._repo = MealRequestStatusRepository(session)

    async def create_status(self, name: str) -> MealRequestStatus:
        """Create a new status."""
        status = MealRequestStatus(name=name)
        return await self._repo.create(status)

    async def get_status(self, status_id: int) -> MealRequestStatus:
        """Get a status by ID."""
        status = await self._repo.get_by_id(status_id)
        if not status:
            raise NotFoundError(entity="MealRequestStatus", identifier=status_id)
        return status

    async def list_statuses(
        self, session: AsyncSession, page: int = 1, per_page: int = 25
    ) -> Tuple[List[MealRequestStatus], int]:
        """List all statuses."""
        return await self._repo.list(session, page=page, per_page=per_page)

    async def delete_status(self, session: AsyncSession, status_id: int) -> None:
        """Delete a status."""
        await self._repo.delete(session, status_id)
