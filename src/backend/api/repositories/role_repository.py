"""Role Repository - Data access layer for Role entity."""

from typing import List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import DatabaseError, NotFoundError
from db.model import Role
from .base import BaseRepository


class RoleRepository(BaseRepository[Role]):
    """Repository for Role entity."""

    model = Role

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def create(self, role: Role) -> Role:
        """
        Create a role or update if it already exists (upsert logic).
        If a role with the same name_en exists, it will be updated instead of raising an error.
        """
        # Check if role with same name_en already exists
        existing = await self.get_by_name_en(role.name_en)
        if existing:
            # Update existing role
            for key, value in role.__dict__.items():
                if not key.startswith("_") and key != "id" and hasattr(existing, key):
                    setattr(existing, key, value)
            await self.session.flush()
            # Refresh to get server-side defaults (updated_at, etc.)
            await self.session.refresh(existing)
            return existing

        # Create new role
        try:
            self.session.add(role)
            await self.session.flush()
            # Refresh to get server-side defaults (created_at, updated_at, etc.)
            await self.session.refresh(role)
            return role
        except IntegrityError as e:
            await self.session.rollback()
            raise DatabaseError(f"Failed to create role: {str(e)}")

    async def get_by_name(
        self, name: str, locale: Optional[str] = None
    ) -> Optional[Role]:
        """
        Get role by name. If locale is specified, search in the corresponding language field.
        Otherwise, search in both name_en and name_ar.
        """
        if locale == "ar":
            result = await self.session.execute(
                select(Role).where(Role.name_ar == name)
            )
        elif locale == "en":
            result = await self.session.execute(
                select(Role).where(Role.name_en == name)
            )
        else:
            # Search in both fields
            result = await self.session.execute(
                select(Role).where((Role.name_en == name) | (Role.name_ar == name))
            )
        return result.scalar_one_or_none()

    async def get_by_name_en(self, name_en: str) -> Optional[Role]:
        """Get role by English name."""
        result = await self.session.execute(select(Role).where(Role.name_en == name_en))
        return result.scalar_one_or_none()

    async def get_by_name_ar(self, name_ar: str) -> Optional[Role]:
        """Get role by Arabic name."""
        result = await self.session.execute(select(Role).where(Role.name_ar == name_ar))
        return result.scalar_one_or_none()

    async def list(
        self, page: int = 1, per_page: int = 25, name_filter: Optional[str] = None
    ) -> Tuple[List[Role], int]:
        from core.pagination import calculate_offset
        from sqlalchemy import func, or_

        # Base query
        query = select(Role)

        # Apply name filter if provided (search in both English and Arabic names)
        if name_filter and name_filter.strip():
            search_term = f"%{name_filter.strip()}%"
            query = query.where(
                or_(Role.name_en.ilike(search_term), Role.name_ar.ilike(search_term))
            )

        # Count query with same filters
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await self.session.execute(count_query)
        total = count_result.scalar() or 0

        # Apply pagination
        offset = calculate_offset(page, per_page)
        result = await self.session.execute(query.offset(offset).limit(per_page))
        return result.scalars().all(), total

    async def update(self, role_id: int, role_data: dict) -> Role:
        role = await self.get_by_id(role_id)
        if not role:
            raise NotFoundError(entity="Role", identifier=role_id)

        try:
            for key, value in role_data.items():
                if value is not None and hasattr(role, key):
                    setattr(role, key, value)

            await self.session.flush()
            # Refresh to get server-side defaults (updated_at, etc.)
            await self.session.refresh(role)
            return role
        except IntegrityError as e:
            await self.session.rollback()
            raise DatabaseError(f"Failed to update role: {str(e)}")
            # Refresh to get server-side defaults (updated_at, etc.)
            await session.refresh(existing)
            return existing

        # Create new role
        try:
            session.add(role)
            await session.flush()
            # Refresh to get server-side defaults (created_at, updated_at, etc.)
            await session.refresh(role)
            return role
        except IntegrityError as e:
            await session.rollback()
            raise DatabaseError(f"Failed to create role: {str(e)}")

    async def get_by_id(self, role_id: int) -> Optional[Role]:
        result = await session.execute(select(Role).where(Role.id == role_id))
        return result.scalar_one_or_none()

    async def get_by_name(
        self, session: AsyncSession, name: str, locale: Optional[str] = None
    ) -> Optional[Role]:
        """
        Get role by name. If locale is specified, search in the corresponding language field.
        Otherwise, search in both name_en and name_ar.
        """
        if locale == "ar":
            result = await session.execute(select(Role).where(Role.name_ar == name))
        elif locale == "en":
            result = await session.execute(select(Role).where(Role.name_en == name))
        else:
            # Search in both fields
            result = await session.execute(
                select(Role).where((Role.name_en == name) | (Role.name_ar == name))
            )
        return result.scalar_one_or_none()

    async def get_by_name_en(
        self, session: AsyncSession, name_en: str
    ) -> Optional[Role]:
        """Get role by English name."""
        result = await session.execute(select(Role).where(Role.name_en == name_en))
        return result.scalar_one_or_none()

    async def get_by_name_ar(
        self, session: AsyncSession, name_ar: str
    ) -> Optional[Role]:
        """Get role by Arabic name."""
        result = await session.execute(select(Role).where(Role.name_ar == name_ar))
        return result.scalar_one_or_none()

    async def list(
        self,
        session: AsyncSession,
        page: int = 1,
        per_page: int = 25,
        name_filter: Optional[str] = None,
    ) -> Tuple[List[Role], int]:
        from core.pagination import calculate_offset
        from sqlalchemy import func, or_

        # Base query
        query = select(Role)

        # Apply name filter if provided (search in both English and Arabic names)
        if name_filter and name_filter.strip():
            search_term = f"%{name_filter.strip()}%"
            query = query.where(
                or_(Role.name_en.ilike(search_term), Role.name_ar.ilike(search_term))
            )

        # Count query with same filters
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await session.execute(count_query)
        total = count_result.scalar() or 0

        # Apply pagination
        offset = calculate_offset(page, per_page)
        result = await session.execute(query.offset(offset).limit(per_page))
        return result.scalars().all(), total

    async def update(
        self, session: AsyncSession, role_id: int, role_data: dict
    ) -> Role:
        role = await self.get_by_id(session, role_id)
        if not role:
            raise NotFoundError(entity="Role", identifier=role_id)

        try:
            for key, value in role_data.items():
                if value is not None and hasattr(role, key):
                    setattr(role, key, value)

            await session.flush()
            # Refresh to get server-side defaults (updated_at, etc.)
            await session.refresh(role)
            return role
        except IntegrityError as e:
            await session.rollback()
            raise DatabaseError(f"Failed to update role: {str(e)}")

    async def delete(self, role_id: int) -> None:
        role = await self.get_by_id(session, role_id)
        if not role:
            raise NotFoundError(entity="Role", identifier=role_id)

        await session.delete(role)
        await session.flush()
