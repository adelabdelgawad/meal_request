"""Email Role Repository."""

from typing import List, Optional, Tuple

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import DatabaseError, NotFoundError
from db.models import EmailRole


class EmailRoleRepository:
    """Repository for EmailRole entity."""

    def __init__(self):
        pass

    async def create(self, session: AsyncSession, role: EmailRole) -> EmailRole:
        """
        Create an email role or update if it already exists (upsert logic).
        If an email role with the same name exists, it will be updated instead of raising an error.
        """
        # Check if email role with same name already exists
        existing = await self.get_by_name(session, role.name)
        if existing:
            # Update existing email role
            for key, value in role.__dict__.items():
                if not key.startswith('_') and key != 'id' and hasattr(existing, key):
                    setattr(existing, key, value)
            await session.flush()
            return existing

        # Create new email role
        try:
            session.add(role)
            await session.flush()
            return role
        except Exception as e:
            await session.rollback()
            raise DatabaseError(f"Failed to create email role: {str(e)}")

    async def get_by_id(self, session: AsyncSession, role_id: int) -> Optional[EmailRole]:
        result = await session.execute(
            select(EmailRole).where(EmailRole.id == role_id)
        )
        return result.scalar_one_or_none()

    async def get_by_name(self, session: AsyncSession, name: str) -> Optional[EmailRole]:
        result = await session.execute(
            select(EmailRole).where(EmailRole.name == name)
        )
        return result.scalar_one_or_none()

    async def list(self, session: AsyncSession, page: int = 1, per_page: int = 25) -> Tuple[List[EmailRole], int]:
        from core.pagination import calculate_offset

        # Optimized count query


        count_query = select(func.count()).select_from((select(EmailRole)).subquery())


        count_result = await session.execute(count_query)


        total = count_result.scalar() or 0

        offset = calculate_offset(page, per_page)
        result = await session.execute(
            select(EmailRole).offset(offset).limit(per_page)
        )
        return result.scalars().all(), total

    async def update(self, session: AsyncSession, role_id: int, role_data: dict) -> EmailRole:
        role = await self.get_by_id(session, role_id)
        if not role:
            raise NotFoundError(entity="EmailRole", identifier=role_id)

        try:
            for key, value in role_data.items():
                if value is not None and hasattr(role, key):
                    setattr(role, key, value)

            await session.flush()
            return role
        except Exception as e:
            await session.rollback()
            raise DatabaseError(f"Failed to update email role: {str(e)}")

    async def delete(self, session: AsyncSession, role_id: int) -> None:
        role = await self.get_by_id(session, role_id)
        if not role:
            raise NotFoundError(entity="EmailRole", identifier=role_id)

        await session.delete(role)
        await session.flush()
