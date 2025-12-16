"""Meal Type Repository."""

from typing import List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import DatabaseError, NotFoundError
from db.models import MealType


class MealTypeRepository:
    """Repository for MealType entity."""

    def __init__(self):
        pass

    async def create(self, session: AsyncSession, meal_type: MealType) -> MealType:
        """Create a new meal type."""
        try:
            session.add(meal_type)
            await session.flush()
            return meal_type
        except Exception as e:
            await session.rollback()
            raise DatabaseError(f"Failed to create meal type: {str(e)}")

    async def get_by_id(self, session: AsyncSession, meal_type_id: int) -> Optional[MealType]:
        """Get a meal type by ID."""
        result = await session.execute(
            select(MealType).where(MealType.id == meal_type_id, ~MealType.is_deleted)
        )
        return result.scalar_one_or_none()

    async def get_by_name_en(self, session: AsyncSession, name_en: str) -> Optional[MealType]:
        """Get a meal type by English name."""
        result = await session.execute(
            select(MealType).where(MealType.name_en == name_en, ~MealType.is_deleted)
        )
        return result.scalar_one_or_none()

    async def get_active_meal_types(self, session: AsyncSession) -> List[MealType]:
        """Get all active meal types (not deleted and active=true), ordered by priority DESC."""
        result = await session.execute(
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
        count_result = await session.execute(count_query)
        total = count_result.scalar() or 0

        offset = calculate_offset(page, per_page)
        result = await session.execute(
            query.offset(offset).limit(per_page).order_by(MealType.priority.desc(), MealType.id)
        )
        return result.scalars().all(), total

    async def update(self, session: AsyncSession, meal_type_id: int, meal_type_data: dict) -> MealType:
        """Update a meal type."""
        meal_type = await self.get_by_id(session, meal_type_id)
        if not meal_type:
            raise NotFoundError(entity="MealType", identifier=meal_type_id)

        try:
            for key, value in meal_type_data.items():
                if hasattr(meal_type, key):
                    setattr(meal_type, key, value)

            await session.flush()
            return meal_type
        except Exception as e:
            await session.rollback()
            raise DatabaseError(f"Failed to update meal type: {str(e)}")

    async def soft_delete(self, session: AsyncSession, meal_type_id: int) -> None:
        """Soft delete a meal type by setting is_deleted=True."""
        meal_type = await self.get_by_id(session, meal_type_id)
        if not meal_type:
            raise NotFoundError(entity="MealType", identifier=meal_type_id)

        meal_type.is_deleted = True
        await session.flush()

    async def delete(self, session: AsyncSession, meal_type_id: int) -> None:
        """Hard delete a meal type (use with caution)."""
        meal_type = await self.get_by_id(session, meal_type_id)
        if not meal_type:
            raise NotFoundError(entity="MealType", identifier=meal_type_id)

        await session.delete(meal_type)
        await session.flush()
