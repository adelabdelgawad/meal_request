"""Meal Request Status Repository."""

from typing import List, Optional, Tuple

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import DatabaseError, NotFoundError
from db.models import MealRequestStatus


class MealRequestStatusRepository:
    """Repository for MealRequestStatus entity."""

    def __init__(self):
        pass

    async def create(self, session: AsyncSession, status: MealRequestStatus) -> MealRequestStatus:
        """
        Create a status or update if it already exists (upsert logic).
        If a status with the same English name exists, it will be updated instead of raising an error.
        """
        # Check if status with same English name already exists
        existing = await self.get_by_name_en(session, status.name_en)
        if existing:
            # Update existing status
            for key, value in status.__dict__.items():
                if not key.startswith('_') and key != 'id' and hasattr(existing, key):
                    setattr(existing, key, value)
            await session.flush()
            return existing

        # Create new status
        try:
            session.add(status)
            await session.flush()
            return status
        except Exception as e:
            await session.rollback()
            raise DatabaseError(f"Failed to create status: {str(e)}")

    async def get_by_id(self, session: AsyncSession, status_id: int) -> Optional[MealRequestStatus]:
        result = await session.execute(
            select(MealRequestStatus).where(MealRequestStatus.id == status_id)
        )
        return result.scalar_one_or_none()

    async def get_by_name_en(self, session: AsyncSession, name_en: str) -> Optional[MealRequestStatus]:
        """Get status by English name."""
        result = await session.execute(
            select(MealRequestStatus).where(func.lower(MealRequestStatus.name_en) == name_en.lower())
        )
        return result.scalar_one_or_none()

    async def get_by_name_ar(self, session: AsyncSession, name_ar: str) -> Optional[MealRequestStatus]:
        """Get status by Arabic name."""
        result = await session.execute(
            select(MealRequestStatus).where(func.lower(MealRequestStatus.name_ar) == name_ar.lower())
        )
        return result.scalar_one_or_none()

    async def get_active_statuses(self, session: AsyncSession) -> List[MealRequestStatus]:
        """Get all active statuses."""
        result = await session.execute(
            select(MealRequestStatus)
            .where(MealRequestStatus.is_active)
            .order_by(MealRequestStatus.id)
        )
        return result.scalars().all()

    async def list(self, session: AsyncSession, page: int = 1, per_page: int = 25, active_only: bool = False) -> Tuple[List[MealRequestStatus], int]:
        from core.pagination import calculate_offset

        # Build base query
        base_query = select(MealRequestStatus)
        if active_only:
            base_query = base_query.where(MealRequestStatus.is_active)

        # Optimized count query
        count_query = select(func.count()).select_from(base_query.subquery())
        count_result = await session.execute(count_query)
        total = count_result.scalar() or 0

        # Apply pagination
        offset = calculate_offset(page, per_page)
        result = await session.execute(
            base_query.order_by(MealRequestStatus.id).offset(offset).limit(per_page)
        )
        return result.scalars().all(), total

    async def delete(self, session: AsyncSession, status_id: int) -> None:
        status = await self.get_by_id(session, status_id)
        if not status:
            raise NotFoundError(entity="MealRequestStatus", identifier=status_id)

        await session.delete(status)
        await session.flush()
