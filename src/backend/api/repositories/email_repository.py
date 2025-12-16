"""Email Repository."""

from typing import List, Optional, Tuple

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import DatabaseError, NotFoundError
from db.models import Email, EmailRole


class EmailRepository:
    """Repository for Email entity."""

    def __init__(self):
        pass

    async def create(self, session: AsyncSession, email: Email) -> Email:
        try:
            session.add(email)
            await session.flush()
            return email
        except Exception as e:
            await session.rollback()
            raise DatabaseError(f"Failed to create email: {str(e)}")

    async def get_by_id(self, session: AsyncSession, email_id: int) -> Optional[Email]:
        result = await session.execute(
            select(Email).where(Email.id == email_id)
        )
        return result.scalar_one_or_none()

    async def get_by_address(self, session: AsyncSession, address: str) -> Optional[Email]:
        result = await session.execute(
            select(Email).where(Email.address == address)
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        session: AsyncSession,
        page: int = 1,
        per_page: int = 25,
        role_id: Optional[int] = None,
    ) -> Tuple[List[Email], int]:
        from core.pagination import calculate_offset

        query = select(Email)

        if role_id is not None:
            query = query.where(Email.role_id == role_id)

        # Optimized count query


        count_query = select(func.count()).select_from((query).subquery())


        count_result = await session.execute(count_query)


        total = count_result.scalar() or 0

        offset = calculate_offset(page, per_page)
        result = await session.execute(query.offset(offset).limit(per_page))
        return result.scalars().all(), total

    async def update(self, session: AsyncSession, email_id: int, email_data: dict) -> Email:
        email = await self.get_by_id(session, email_id)
        if not email:
            raise NotFoundError(entity="Email", identifier=email_id)

        try:
            for key, value in email_data.items():
                if value is not None and hasattr(email, key):
                    setattr(email, key, value)

            await session.flush()
            return email
        except Exception as e:
            await session.rollback()
            raise DatabaseError(f"Failed to update email: {str(e)}")

    async def delete(self, session: AsyncSession, email_id: int) -> None:
        email = await self.get_by_id(session, email_id)
        if not email:
            raise NotFoundError(entity="Email", identifier=email_id)

        await session.delete(email)
        await session.flush()

    # Specialized CRUD compatibility methods
    async def create_role(self, session: AsyncSession, email_role: EmailRole) -> EmailRole:
        """Create an email role."""
        try:
            session.add(email_role)
            await session.flush()
            return email_role
        except Exception as e:
            await session.rollback()
            raise DatabaseError(f"Failed to create email role: {str(e)}")
