"""Role Service - Business logic for role management."""

from typing import List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from api.repositories.role_repository import RoleRepository
from api.repositories.role_permission_repository import RolePermissionRepository
from core.exceptions import NotFoundError
from db.model import Role, RolePermission
from db.schemas import RolePermissionCreate


class RoleService:
    """Service for role management."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self._repo = RoleRepository(session)
        self._role_permission_repo = RolePermissionRepository(session)

    async def create_role(
        self,
        name_en: str,
        name_ar: str,
        description_en: Optional[str] = None,
        description_ar: Optional[str] = None,
    ) -> Role:
        """Create a new role with bilingual support."""
        role = Role(
            name_en=name_en,
            name_ar=name_ar,
            description_en=description_en,
            description_ar=description_ar,
        )
        return await self._repo.create(role)

    async def get_role(self, role_id: int) -> Role:
        """Get a role by ID."""
        role = await self._repo.get_by_id(role_id)
        if not role:
            raise NotFoundError(entity="Role", identifier=role_id)
        return role

    async def list_roles(
        self,
        page: int = 1,
        per_page: int = 25,
        name_filter: Optional[str] = None,
    ) -> Tuple[List[Role], int]:
        """List all roles with optional name filtering."""
        return await self._repo.list(
            page=page, per_page=per_page, name_filter=name_filter
        )

    async def update_role(
        self,
        role_id: int,
        name_en: Optional[str] = None,
        name_ar: Optional[str] = None,
        description_en: Optional[str] = None,
        description_ar: Optional[str] = None,
    ) -> Role:
        """Update a role with bilingual support."""
        update_data = {}
        if name_en is not None:
            update_data["name_en"] = name_en
        if name_ar is not None:
            update_data["name_ar"] = name_ar
        if description_en is not None:
            update_data["description_en"] = description_en
        if description_ar is not None:
            update_data["description_ar"] = description_ar

        return await self._repo.update(role_id, update_data)

    async def update_role_status(
        self,
        role_id: int,
        is_active: bool,
    ) -> Role:
        """Toggle role active/inactive status."""
        update_data = {"is_active": is_active}
        return await self._repo.update(role_id, update_data)

    async def delete_role(self, role_id: int) -> None:
        """Delete a role."""
        await self._repo.delete(role_id)

    async def create_role_permission(
        self,
        role_permission: RolePermissionCreate,
    ) -> RolePermission:
        """Create a role permission (assign role to user)."""
        return await self._role_permission_repo.assign_role_to_user(
            user_id=role_permission.user_id,
            role_id=role_permission.role_id,
        )

    async def delete_role_permission(
        self,
        user_id: str,
        role_id: int,
    ) -> bool:
        """Delete a role permission (remove role from user)."""
        try:
            await self._role_permission_repo.revoke_role_from_user(
                user_id=user_id,
                role_id=role_id,
            )
            return True
        except NotFoundError:
            return False

    async def get_all_role_permissions(
        self,
    ) -> List[Tuple[str, List[str]]]:
        """Get all role permissions grouped by username."""
        from sqlalchemy import select
        from db.model import User

        query = (
            select(User.username, RolePermission.role_id)
            .join(RolePermission, User.id == RolePermission.user_id)
            .where(~User.is_super_admin)
        )
        result = await self.session.execute(query)
        rows = result.all()

        # Group by username
        permissions_by_user = {}
        for username, role_id in rows:
            if username not in permissions_by_user:
                permissions_by_user[username] = []
            permissions_by_user[username].append(str(role_id))

        return [
            (username, role_ids) for username, role_ids in permissions_by_user.items()
        ]

    async def get_all_roles(self, session: AsyncSession) -> List[Role]:
        """Get all roles."""
        roles, _ = await self._repo.list(session, page=1, per_page=1000)
        return roles

    async def get_user_role_names(
        self, session: AsyncSession, user_id: str
    ) -> List[str]:
        """
        Get list of role names for a user (e.g., ['requester', 'ordertaker']).

        This method fetches the English names of all active roles assigned to a user.
        Role names are used as scopes in JWT tokens for authorization.

        Args:
            user_id: User ID (UUID as string)

        Returns:
            List of role names (e.g., ['requester', 'admin'])
        """
        from sqlalchemy import select

        query = (
            select(Role.name_en)
            .join(RolePermission, Role.id == RolePermission.role_id)
            .where(RolePermission.user_id == user_id, Role.is_active)
        )
        result = await self.session.execute(query)
        role_names = [row[0] for row in result.fetchall()]
        return role_names

    async def get_role_pages(
        self,
        role_id: int,
        include_inactive: bool = False,
    ) -> List[dict]:
        """Get all pages assigned to a role."""
        from sqlalchemy import select
        from db.model import PagePermission, Page

        # First verify role exists
        role = await self._repo.get_by_id(role_id)
        if not role:
            raise NotFoundError(entity="Role", identifier=role_id)

        query = (
            select(Page)
            .join(PagePermission, Page.id == PagePermission.page_id)
            .where(PagePermission.role_id == role_id)
        )

        if not include_inactive:
            query = query.where(Page.is_active)

        result = await self.session.execute(query)
        pages = result.scalars().all()

        return [
            {
                "id": page.id,
                "name_en": page.name_en,
                "name_ar": page.name_ar,
            }
            for page in pages
        ]

    async def update_role_pages(
        self,
        role_id: int,
        page_ids: List[int],
        created_by_id: str,
    ) -> List[dict]:
        """Update pages assigned to a role (replace all)."""
        from sqlalchemy import delete
        from db.model import PagePermission

        # First verify role exists
        role = await self._repo.get_by_id(role_id)
        if not role:
            raise NotFoundError(entity="Role", identifier=role_id)

        # Delete existing page permissions for this role
        await self.session.execute(
            delete(PagePermission).where(PagePermission.role_id == role_id)
        )

        # Add new page permissions
        for page_id in page_ids:
            permission = PagePermission(
                role_id=role_id,
                page_id=page_id,
                created_by_id=created_by_id,
            )
            self.session.add(permission)

        await self.session.flush()

        # Return updated pages
        return await self.get_role_pages(role_id, include_inactive=True)

    async def get_role_users(
        self,
        role_id: int,
        include_inactive: bool = False,
    ) -> List[dict]:
        """Get all users assigned to a role."""
        # First verify role exists
        role = await self._repo.get_by_id(role_id)
        if not role:
            raise NotFoundError(entity="Role", identifier=role_id)

        # Get users via repository
        users = await self._role_permission_repo.get_users_by_role(role_id)

        # Return updated users
        return await self.get_role_users(role_id, include_inactive=True)
