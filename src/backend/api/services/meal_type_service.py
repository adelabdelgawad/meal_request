"""Meal Type Service."""

from typing import List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from api.repositories.meal_type_repository import MealTypeRepository
from core.exceptions import NotFoundError
from db.models import MealType


class MealTypeService:
    """Service for meal type management."""

    def __init__(self):
        self._repo = MealTypeRepository()

    async def create_meal_type(
        self,
        session: AsyncSession,
        name_en: str,
        name_ar: str,
        priority: int = 0,
        created_by_id: Optional[str] = None,
    ) -> MealType:
        """Create a new meal type."""
        meal_type = MealType(
            name_en=name_en,
            name_ar=name_ar,
            priority=priority,
            created_by_id=created_by_id,
        )
        return await self._repo.create(session, meal_type)

    async def get_meal_type(self, session: AsyncSession, meal_type_id: int) -> MealType:
        """Get a meal type by ID."""
        meal_type = await self._repo.get_by_id(session, meal_type_id)
        if not meal_type:
            raise NotFoundError(entity="MealType", identifier=meal_type_id)
        return meal_type

    async def list_meal_types(
        self,
        session: AsyncSession,
        page: int = 1,
        per_page: int = 25,
        active_only: bool = False,
    ) -> Tuple[List[MealType], int]:
        """List all meal types."""
        return await self._repo.list(session, page=page, per_page=per_page, active_only=active_only)

    async def get_active_meal_types(self, session: AsyncSession) -> List[MealType]:
        """Get all active meal types (not deleted and active=true)."""
        return await self._repo.get_active_meal_types(session)

    async def update_meal_type(
        self,
        session: AsyncSession,
        meal_type_id: int,
        name_en: Optional[str] = None,
        name_ar: Optional[str] = None,
        priority: Optional[int] = None,
        is_active: Optional[bool] = None,
        updated_by_id: Optional[str] = None,
    ) -> MealType:
        """Update a meal type."""
        update_data = {}
        if name_en is not None:
            update_data["name_en"] = name_en
        if name_ar is not None:
            update_data["name_ar"] = name_ar
        if priority is not None:
            update_data["priority"] = priority
        if is_active is not None:
            update_data["is_active"] = is_active
        if updated_by_id is not None:
            update_data["updated_by_id"] = updated_by_id

        return await self._repo.update(session, meal_type_id, update_data)

    async def delete_meal_type(self, session: AsyncSession, meal_type_id: int) -> None:
        """Soft delete a meal type."""
        await self._repo.soft_delete(session, meal_type_id)
