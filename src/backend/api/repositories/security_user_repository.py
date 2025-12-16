"""Security User Repository - Data access layer for SecurityUser entity."""

from typing import List, Optional, Tuple

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import DatabaseError, NotFoundError
from db.models import SecurityUser


class SecurityUserRepository:
    """Repository for SecurityUser entity operations."""

    def __init__(self):
        pass

    async def create(self, session: AsyncSession, security_user: SecurityUser) -> SecurityUser:
        """Create a new security user."""
        try:
            session.add(security_user)
            await session.flush()
            return security_user
        except Exception as e:
            await session.rollback()
            raise DatabaseError(f"Failed to create security user: {str(e)}")

    async def get_by_id(self, session: AsyncSession, user_id: int) -> Optional[SecurityUser]:
        """Get security user by ID."""
        result = await session.execute(
            select(SecurityUser).where(SecurityUser.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_username(self, session: AsyncSession, username: str) -> Optional[SecurityUser]:
        """Get security user by username."""
        result = await session.execute(
            select(SecurityUser).where(SecurityUser.user_name == username)
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        session: AsyncSession,
        page: int = 1,
        per_page: int = 25,
    ) -> Tuple[List[SecurityUser], int]:
        """List security users with pagination."""
        from core.pagination import calculate_offset

        query = select(SecurityUser)

        # Get total count
        # Optimized count query

        count_query = select(func.count()).select_from((query).subquery())

        count_result = await session.execute(count_query)

        total = count_result.scalar() or 0

        # Get paginated results
        offset = calculate_offset(page, per_page)
        result = await session.execute(query.offset(offset).limit(per_page))
        return result.scalars().all(), total

    async def update(self, session: AsyncSession, user_id: int, user_data: dict) -> SecurityUser:
        """Update an existing security user."""
        user = await self.get_by_id(session, user_id)
        if not user:
            raise NotFoundError(entity="SecurityUser", identifier=user_id)

        try:
            for key, value in user_data.items():
                if value is not None and hasattr(user, key):
                    setattr(user, key, value)

            await session.flush()
            return user
        except Exception as e:
            await session.rollback()
            raise DatabaseError(f"Failed to update security user: {str(e)}")

    async def delete(self, session: AsyncSession, user_id: int) -> None:
        """Delete a security user."""
        user = await self.get_by_id(session, user_id)
        if not user:
            raise NotFoundError(entity="SecurityUser", identifier=user_id)

        await session.delete(user)
        await session.flush()

    # Specialized CRUD compatibility methods
    async def deactivate_all(self, session: AsyncSession) -> bool:
        """Deactivate all security users (set is_deleted and is_locked to True)."""
        try:
            stmt = update(SecurityUser).values(is_deleted=True, is_locked=True)
            await session.execute(stmt)
            await session.flush()
            return True
        except Exception as e:
            await session.rollback()
            raise DatabaseError(f"Failed to deactivate all security users: {str(e)}")
