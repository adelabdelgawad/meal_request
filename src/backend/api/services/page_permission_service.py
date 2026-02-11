"""Page Permission Service - Business logic for page permission management."""

from typing import List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from api.repositories.page_permission_repository import PagePermissionRepository
from core.exceptions import NotFoundError
from db.model import PagePermission


class PagePermissionService:
    """Service for page permission management operations."""

    def __init__(self, session: AsyncSession):
        """Initialize service."""
        self.session = session
        self._repo = PagePermissionRepository(session)

    async def grant_permission(
        self, role_id: int, page_id: int, created_by_id: int
    ) -> PagePermission:
        """Grant a page permission to a role."""
        permission = PagePermission(
            role_id=role_id,
            page_id=page_id,
            created_by_id=created_by_id,
        )
        return await self._repo.create(permission)

    async def get_permission(self, permission_id: int) -> PagePermission:
        """Get a page permission by ID."""
        permission = await self._repo.get_by_id(permission_id)
        if not permission:
            raise NotFoundError(entity="PagePermission", identifier=permission_id)
        return permission

    async def list_permissions(
        self,
        page: int = 1,
        per_page: int = 25,
        role_id: Optional[int] = None,
        page_id: Optional[int] = None,
    ) -> Tuple[List[PagePermission], int]:
        """List page permissions with optional filtering."""
        return await self._repo.list(
            page=page,
            per_page=per_page,
            role_id=role_id,
            page_id=page_id,
        )

    async def check_permission(self, role_id: int, page_id: int) -> bool:
        """Check if a role has permission for a page."""
        permission = await self._repo.get_by_role_and_page(role_id, page_id)
        return permission is not None

    async def update_permission(
        self,
        permission_id: int,
        role_id: Optional[int] = None,
        page_id: Optional[int] = None,
    ) -> PagePermission:
        """Update a page permission."""
        update_data = {}
        if role_id is not None:
            update_data["role_id"] = role_id
        if page_id is not None:
            update_data["page_id"] = page_id

        return await self._repo.update(permission_id, update_data)

    async def revoke_permission(self, permission_id: int) -> None:
        """Revoke a page permission."""
        await self._repo.delete(permission_id)
