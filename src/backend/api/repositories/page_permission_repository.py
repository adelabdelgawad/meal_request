"""Page Permission Repository."""

from typing import List, Optional, Tuple

from sqlalchemy import and_, delete, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import DatabaseError, NotFoundError
from db.model import PagePermission
from .base import BaseRepository


class PagePermissionRepository(BaseRepository[PagePermission]):
    """Repository for PagePermission entity."""

    model = PagePermission

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def create(self, permission: PagePermission) -> PagePermission:
        """
        Create a page permission or update if it already exists (upsert logic).
        If a permission with the same role_id and page_id exists, it will be updated.
        """
        # Check if permission with same role and page already exists
        existing = await self.get_by_role_and_page(
            permission.role_id, permission.page_id
        )
        if existing:
            # Update existing permission
            for key, value in permission.__dict__.items():
                if not key.startswith("_") and key != "id" and hasattr(existing, key):
                    setattr(existing, key, value)
            await self.session.flush()
            return existing

        # Use base create method
        return await super().create(permission)

    async def get_by_role_and_page(
        self, role_id: int, page_id: int
    ) -> Optional[PagePermission]:
        """Get permission by role and page."""
        result = await self.session.execute(
            select(PagePermission).where(
                and_(
                    PagePermission.role_id == role_id,
                    PagePermission.page_id == page_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        page: int = 1,
        per_page: int = 25,
        role_id: Optional[int] = None,
        page_id: Optional[int] = None,
    ) -> Tuple[List[PagePermission], int]:
        from core.pagination import calculate_offset

        query = select(PagePermission)

        if role_id is not None:
            query = query.where(PagePermission.role_id == role_id)
        if page_id is not None:
            query = query.where(PagePermission.page_id == page_id)

        # Optimized count query
        count_query = select(func.count()).select_from((query).subquery())
        count_result = await self.session.execute(count_query)
        total = count_result.scalar() or 0

        offset = calculate_offset(page, per_page)
        result = await self.session.execute(query.offset(offset).limit(per_page))
        return list(result.scalars().all()), total

    async def update(self, permission_id: int, permission_data: dict) -> PagePermission:
        permission = await self.get_by_id(permission_id)
        if not permission:
            raise NotFoundError(f"PagePermission with ID {permission_id} not found")

        try:
            for key, value in permission_data.items():
                if value is not None and hasattr(permission, key):
                    setattr(permission, key, value)

            await self.session.flush()
            return permission
        except Exception as e:
            await self.session.rollback()
            raise DatabaseError(f"Failed to update page permission: {str(e)}")

    async def delete_by_id(self, permission_id: int) -> None:
        """Delete a page permission by ID."""
        permission = await self.get_by_id(permission_id)
        if not permission:
            raise NotFoundError(f"PagePermission with ID {permission_id} not found")

        await self.delete(permission)
