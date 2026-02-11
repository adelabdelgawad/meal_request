"""Role Permission Repository."""

from typing import List, Optional, Tuple

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import DatabaseError, NotFoundError
from db.model import Role, RolePermission, User
from .base import BaseRepository


class RolePermissionRepository(BaseRepository[RolePermission]):
    """Repository for RolePermission entity (User-Role junction table)."""

    model = RolePermission

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def create(self, role_permission: RolePermission) -> RolePermission:
        """Create a new role permission assignment."""
        try:
            self.session.add(role_permission)
            await self.session.flush()
            return role_permission
        except Exception as e:
            await self.session.rollback()
            raise DatabaseError(f"Failed to create role permission: {str(e)}")

    async def get_by_user_and_role(
        self, user_id: str, role_id: int
    ) -> Optional[RolePermission]:
        """Get a role permission by user_id and role_id."""
        result = await self.session.execute(
            select(RolePermission).where(
                RolePermission.user_id == user_id,
                RolePermission.role_id == role_id,
            )
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        page: int = 1,
        per_page: int = 25,
    ) -> Tuple[List[RolePermission], int]:
        """List all role permissions with pagination."""
        from core.pagination import calculate_offset
        from sqlalchemy import func

        query = select(RolePermission)

        # Optimized count query
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await self.session.execute(count_query)
        total = count_result.scalar() or 0

        offset = calculate_offset(page, per_page)
        result = await self.session.execute(
            query.offset(offset).limit(per_page).order_by(RolePermission.id)
        )
        return result.scalars().all(), total

    async def get_roles_by_user(self, user_id: str) -> List[Role]:
        """Get all roles assigned to a user."""
        result = await self.session.execute(
            select(Role)
            .join(RolePermission, RolePermission.role_id == Role.id)
            .where(RolePermission.user_id == user_id)
            .order_by(Role.name_en)
        )
        return result.scalars().all()

    async def get_users_by_role(self, role_id: int) -> List[User]:
        """Get all users assigned to a role."""
        result = await self.session.execute(
            select(User)
            .join(RolePermission, RolePermission.user_id == User.id)
            .where(RolePermission.role_id == role_id)
            .order_by(User.username)
        )
        return result.scalars().all()

    async def assign_role_to_user(self, user_id: str, role_id: int) -> RolePermission:
        """
        Assign a role to a user.

        If the assignment already exists, returns the existing record.
        Otherwise, creates a new assignment.
        """
        # Check if assignment already exists
        existing = await self.get_by_user_and_role(user_id, role_id)
        if existing:
            return existing

        # Create new assignment
        role_permission = RolePermission(
            user_id=user_id,
            role_id=role_id,
        )
        return await self.create(role_permission)

    async def revoke_role_from_user(self, user_id: str, role_id: int) -> None:
        """Revoke a role from a user."""
        # Find the permission
        permission = await self.get_by_user_and_role(user_id, role_id)
        if not permission:
            raise NotFoundError(
                entity="RolePermission",
                identifier=f"user_id={user_id}, role_id={role_id}",
            )

        try:
            await self.session.delete(permission)
            await self.session.flush()
        except Exception as e:
            await self.session.rollback()
            raise DatabaseError(f"Failed to revoke role permission: {str(e)}")

    async def revoke_all_roles_from_user(self, user_id: str) -> None:
        """Revoke all roles from a user."""
        try:
            await self.session.execute(
                delete(RolePermission).where(RolePermission.user_id == user_id)
            )
            await self.session.flush()
        except Exception as e:
            await self.session.rollback()
            raise DatabaseError(f"Failed to revoke all roles from user: {str(e)}")

    async def revoke_all_users_from_role(self, role_id: int) -> None:
        """Revoke all users from a role."""
        try:
            await self.session.execute(
                delete(RolePermission).where(RolePermission.role_id == role_id)
            )
            await self.session.flush()
        except Exception as e:
            await self.session.rollback()
            raise DatabaseError(f"Failed to revoke all users from role: {str(e)}")

    async def assign_roles_to_user(
        self, user_id: str, role_ids: List[int]
    ) -> List[RolePermission]:
        """
        Assign multiple roles to a user.

        This replaces all existing role assignments for the user.
        """
        # First, revoke all existing roles
        await self.revoke_all_roles_from_user(user_id)

        # Then, assign new roles
        permissions = []
        for role_id in role_ids:
            permission = await self.assign_role_to_user(user_id, role_id)
            permissions.append(permission)

        return permissions

    async def assign_users_to_role(
        self, role_id: int, user_ids: List[str]
    ) -> List[RolePermission]:
        """
        Assign multiple users to a role.

        This replaces all existing user assignments for the role.
        """
        # First, revoke all existing users
        await self.revoke_all_users_from_role(role_id)

        # Then, assign new users
        permissions = []
        for user_id in user_ids:
            permission = await self.assign_role_to_user(user_id, role_id)
            permissions.append(permission)

        return permissions

    async def count_users_in_role(self, role_id: int) -> int:
        """Count the number of users assigned to a role."""
        from sqlalchemy import func

        count_query = select(func.count()).where(RolePermission.role_id == role_id)
        result = await self.session.execute(count_query)
        return result.scalar() or 0

    async def count_roles_for_user(self, user_id: str) -> int:
        """Count the number of roles assigned to a user."""
        from sqlalchemy import func

        count_query = select(func.count()).where(RolePermission.user_id == user_id)
        result = await self.session.execute(count_query)
        return result.scalar() or 0

    async def has_role(self, user_id: str, role_id: int) -> bool:
        """Check if a user has a specific role."""
        permission = await self.get_by_user_and_role(user_id, role_id)
        return permission is not None
