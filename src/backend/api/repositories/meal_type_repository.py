"""Meal Type Repository."""

from typing import List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import DatabaseError, NotFoundError
from db.model import MealType
from .base import BaseRepository


class MealTypeRepository(BaseRepository[MealType]):
    """Repository for MealType entity."""

        super().__init__(session)

    async def create(self, meal_type: MealType) -> MealType:
        """Create a new meal type."""
        try:
            self.session.add(meal_type)
            await self.session.flush()
            return meal_type
        except Exception as e:
            await self.session.rollback()
            raise DatabaseError(f"Failed to create meal type: {str(e)}")

    async def get_by_id(self, meal_type_id: int) -> Optional[MealType]:
        """Get a meal type by ID."""
        result = await self.session.execute(
            select(MealType).where(MealType.id == meal_type_id, ~MealType.is_deleted)
        )
        return result.scalar_one_or_none()

    async def get_by_name_en(self, name_en: str) -> Optional[MealType]:
        """Get a meal type by English name."""
        result = await self.session.execute(
            select(MealType).where(MealType.name_en == name_en, ~MealType.is_deleted)
        )
        return result.scalar_one_or_none()

    async def get_active_meal_types(self) -> List[MealType]:
        """Get all active meal types (not deleted and active=true), ordered by priority DESC."""
        result = await self.session.execute(
            select(MealType).where(
                MealType.is_active,
                ~MealType.is_deleted
            ).order_by(MealType.priority.desc(), MealType.id)
        )
        return result.scalars().all()

    async def list(
        self,
        session: AsyncSession,
        page: int = 1,
        per_page: int = 25,
        active_only: bool = False,
    ) -> Tuple[List[MealType], int]:
        """List meal types with pagination."""
        from core.pagination import calculate_offset
        from sqlalchemy import func

        query = select(MealType).where(~MealType.is_deleted)

        if active_only:
            query = query.where(MealType.is_active)

        # Optimized count query
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await self.session.execute(count_query)
        total = count_result.scalar() or 0

        offset = calculate_offset(page, per_page)
        result = await self.session.execute(
            query.offset(offset).limit(per_page).order_by(MealType.priority.desc(), MealType.id)
        )
        return list(result.scalars().all()), total

    async def update(self, meal_type_id: int, meal_type_data: dict) -> MealType:
        """Update a meal type."""
        meal_type = await self.get_by_id(meal_type_id)
        if not meal_type:
            raise NotFoundError(f"MealType with ID {meal_type_id} not found")

        try:
            for key, value in meal_type_data.items():
                if hasattr(meal_type, key):
                    setattr(meal_type, key, value)

            await self.session.flush()
            return meal_type
        except Exception as e:
            await self.session.rollback()
            raise DatabaseError(f"Failed to update meal type: {str(e)}")

    async def soft_delete(self, meal_type_id: int) -> None:
        """Soft delete a meal type by setting is_deleted=True."""
        meal_type = await self.get_by_id(meal_type_id)
        if not meal_type:
            raise NotFoundError(f"MealType with ID {meal_type_id} not found")

        meal_type.is_deleted = True
        await self.session.flush()

    async def delete(self, meal_type_id: int) -> None:
        """Hard delete a meal type (use with caution)."""
        meal_type = await self.get_by_id(meal_type_id)
        if not meal_type:
            raise NotFoundError(f"MealType with ID {meal_type_id} not found")

        await self.session.delete(meal_type)
        await self.session.flush()
