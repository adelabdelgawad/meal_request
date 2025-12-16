"""Role Service - Business logic for role management."""

from typing import List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from api.repositories.role_repository import RoleRepository
from api.repositories.role_permission_repository import RolePermissionRepository
from core.exceptions import NotFoundError
from db.models import Role, RolePermission
from db.schemas import RolePermissionCreate


class RoleService:
    """Service for role management."""

    def __init__(self):
        self._repo = RoleRepository()
        self._role_permission_repo = RolePermissionRepository()

    async def create_role(
        self,
        session: AsyncSession,
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
        return await self._repo.create(session, role)

    async def get_role(self, session: AsyncSession, role_id: int) -> Role:
        """Get a role by ID."""
        role = await self._repo.get_by_id(session, role_id)
        if not role:
            raise NotFoundError(entity="Role", identifier=role_id)
        return role

    async def list_roles(
        self,
        session: AsyncSession,
        page: int = 1,
        per_page: int = 25,
        name_filter: Optional[str] = None,
    ) -> Tuple[List[Role], int]:
        """List all roles with optional name filtering."""
        return await self._repo.list(
            session,
            page=page,
            per_page=per_page,
            name_filter=name_filter
        )

    async def update_role(
        self,
        session: AsyncSession,
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

        return await self._repo.update(session, role_id, update_data)

    async def update_role_status(
        self,
        session: AsyncSession,
        role_id: int,
        is_active: bool,
    ) -> Role:
        """Toggle role active/inactive status."""
        update_data = {"is_active": is_active}
        return await self._repo.update(session, role_id, update_data)

    async def delete_role(self, session: AsyncSession, role_id: int) -> None:
        """Delete a role."""
        await self._repo.delete(session, role_id)

    async def create_role_permission(
        self,
        session: AsyncSession,
        role_permission: RolePermissionCreate,
    ) -> RolePermission:
        """Create a role permission (assign role to user)."""
        return await self._role_permission_repo.assign_role_to_user(
            session,
            user_id=role_permission.user_id,
            role_id=role_permission.role_id,
        )

    async def delete_role_permission(
        self,
        session: AsyncSession,
        user_id: str,
        role_id: int,
    ) -> bool:
        """Delete a role permission (remove role from user)."""
        try:
            await self._role_permission_repo.revoke_role_from_user(
                session,
                user_id=user_id,
                role_id=role_id,
            )
            return True
        except NotFoundError:
            return False

    async def get_all_role_permissions(
        self,
        session: AsyncSession,
    ) -> List[Tuple[str, List[str]]]:
        """Get all role permissions grouped by username."""
        from sqlalchemy import select
        from db.models import User

        query = (
            select(User.username, RolePermission.role_id)
            .join(RolePermission, User.id == RolePermission.user_id)
            .where(~User.is_super_admin)
        )
        result = await session.execute(query)
        rows = result.all()

        # Group by username
        permissions_by_user = {}
        for username, role_id in rows:
            if username not in permissions_by_user:
                permissions_by_user[username] = []
            permissions_by_user[username].append(str(role_id))

        return [(username, role_ids) for username, role_ids in permissions_by_user.items()]

    async def get_all_roles(self, session: AsyncSession) -> List[Role]:
        """Get all roles."""
        roles, _ = await self._repo.list(session, page=1, per_page=1000)
        return roles

    async def get_user_role_names(self, session: AsyncSession, user_id: str) -> List[str]:
        """
        Get list of role names for a user (e.g., ['requester', 'ordertaker']).

        This method fetches the English names of all active roles assigned to a user.
        Role names are used as scopes in JWT tokens for authorization.

        Args:
            session: Database session
            user_id: User ID (UUID as string)

        Returns:
            List of role names (e.g., ['requester', 'admin'])
        """
        from sqlalchemy import select

        query = (
            select(Role.name_en)
            .join(RolePermission, Role.id == RolePermission.role_id)
            .where(
                RolePermission.user_id == user_id,
                Role.is_active
            )
        )
        result = await session.execute(query)
        role_names = [row[0] for row in result.fetchall()]
        return role_names

    async def get_role_pages(
        self,
        session: AsyncSession,
        role_id: int,
        include_inactive: bool = False,
    ) -> List[dict]:
        """Get all pages assigned to a role."""
        from sqlalchemy import select
        from db.models import PagePermission, Page

        # First verify role exists
        role = await self._repo.get_by_id(session, role_id)
        if not role:
            raise NotFoundError(entity="Role", identifier=role_id)

        query = (
            select(Page)
            .join(PagePermission, Page.id == PagePermission.page_id)
            .where(PagePermission.role_id == role_id)
        )

        if not include_inactive:
            query = query.where(Page.is_active)

        result = await session.execute(query)
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
        session: AsyncSession,
        role_id: int,
        page_ids: List[int],
        created_by_id: str,
    ) -> List[dict]:
        """Update pages assigned to a role (replace all)."""
        from sqlalchemy import delete
        from db.models import PagePermission

        # First verify role exists
        role = await self._repo.get_by_id(session, role_id)
        if not role:
            raise NotFoundError(entity="Role", identifier=role_id)

        # Delete existing page permissions for this role
        await session.execute(
            delete(PagePermission).where(PagePermission.role_id == role_id)
        )

        # Add new page permissions
        for page_id in page_ids:
            permission = PagePermission(
                role_id=role_id,
                page_id=page_id,
                created_by_id=created_by_id,
            )
            session.add(permission)

        await session.flush()

        # Return updated pages
        return await self.get_role_pages(session, role_id, include_inactive=True)

    async def get_role_users(
        self,
        session: AsyncSession,
        role_id: int,
        include_inactive: bool = False,
    ) -> List[dict]:
        """Get all users assigned to a role."""
        # First verify role exists
        role = await self._repo.get_by_id(session, role_id)
        if not role:
            raise NotFoundError(entity="Role", identifier=role_id)

        # Get users via repository
        users = await self._role_permission_repo.get_users_by_role(
            session, role_id
        )

        # Filter inactive if needed
        if not include_inactive:
            users = [user for user in users if user.is_active]

        return [
            {
                "id": str(user.id),
                "username": user.username,
                "full_name": user.full_name,
            }
            for user in users
        ]

    async def update_role_users(
        self,
        session: AsyncSession,
        role_id: int,
        user_ids: List[str],
    ) -> List[dict]:
        """Update users assigned to a role (replace all)."""
        # First verify role exists
        role = await self._repo.get_by_id(session, role_id)
        if not role:
            raise NotFoundError(entity="Role", identifier=role_id)

        # Use repository to replace all user assignments
        await self._role_permission_repo.assign_users_to_role(
            session,
            role_id=role_id,
            user_ids=user_ids,
        )

        # Return updated users
        return await self.get_role_users(session, role_id, include_inactive=True)
