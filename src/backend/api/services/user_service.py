"""
User Service - Business logic for user management.
"""

import logging
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from api.repositories.user_repository import UserRepository
from api.repositories.role_permission_repository import RolePermissionRepository
from core.exceptions import ConflictError, NotFoundError, ValidationError
from core.security import hash_password, verify_password
from db.model import User

logger = logging.getLogger(__name__)


class UserService:
    """Service for user management operations."""

    def __init__(self, session: AsyncSession):
        """Initialize service with session."""
        self.session = session
        self._repo = UserRepository(session)
        self._role_permission_repo = RolePermissionRepository(session)

    async def create_user(
        self,
        username: str,
        password: Optional[str] = None,
        email: Optional[str] = None,
        full_name: Optional[str] = None,
        title: Optional[str] = None,
        is_domain_user: bool = True,
    ) -> User:
        """
        Register a new user.

        Args:
            username: Unique username
            password: Password (required for local users)
            email: Optional email address
            full_name: Optional full name
            title: Optional job title
            is_domain_user: Whether user authenticates via domain (LDAP/AD)

        Returns:
            Created User

        Raises:
            ValidationError: If inputs are invalid
            ConflictError: If username/email already exists
        """
        # Validate inputs
        if not username or len(username) < 3:
            raise ValidationError("Username must be at least 3 characters")

        if not is_domain_user and (not password or len(password) < 8):
            raise ValidationError(
                "Password must be at least 8 characters for local users"
            )

        # Check if username exists
        existing = await self._repo.get_by_username(username)
        if existing:
            raise ConflictError(f"Username '{username}' already exists")

        # Check if email exists
        if email:
            existing_email = await self._repo.get_by_email(email)
            if existing_email:
                raise ConflictError(f"Email '{email}' already exists")

        # Create user
        hashed_pwd = hash_password(password) if password else None
        user = User(
            username=username,
            email=email,
            password=hashed_pwd,
            full_name=full_name,
            title=title,
            is_domain_user=is_domain_user,
        )

        created_user = await self._repo.create(user)

        # AUTO-ASSIGN REQUESTER ROLE if user has no roles
        from api.repositories.role_repository import RoleRepository
        from db.schemas import RolePermissionCreate
        from db.model import RolePermission
        from sqlalchemy import select

        role_repo = RoleRepository(self.session)

        # Check if user has any roles
        existing_roles = await self.session.execute(
            select(RolePermission).where(RolePermission.user_id == created_user.id)
        )
        if existing_roles.scalar_one_or_none() is None:
            # No roles - assign Requester
            requester_role = await role_repo.get_by_name_en("Requester")
            if requester_role:
                from api.services.role_service import RoleService

                role_service = RoleService(self.session)
                await role_service.create_role_permission(
                    RolePermissionCreate(
                        role_id=str(requester_role.id), user_id=str(created_user.id)
                    )
                )
                logger.info(f"Auto-assigned Requester role to new user: {username}")

        return created_user

    async def authenticate(self, username: str, password: str) -> User:
        """
        Authenticate a user with password.

        Args:
            username: Username
            password: Password to verify

        Returns:
            Authenticated User

        Raises:
            NotFoundError: If user not found
            ValidationError: If credentials are invalid
        """
        user = await self._repo.get_by_username(username)

        if not user:
            raise NotFoundError(f"User '{username}' not found")

        if not user.is_active:
            raise ValidationError("User account is inactive")

        if not user.password:
            raise ValidationError("User does not have password authentication enabled")

        if not verify_password(password, user.password):
            raise ValidationError("Invalid username or password")

        return user

    async def get_user(self, user_id: UUID) -> User:
        """Get a user by ID."""
        user = await self._repo.get_by_id(user_id)
        if not user:
            raise NotFoundError(f"User with ID {user_id} not found")
        return user

    async def get_user_by_username(self, username: str) -> User:
        """Get a user by username."""
        user = await self._repo.get_by_username(username)
        if not user:
            raise NotFoundError(f"User '{username}' not found")
        return user

    async def list_users(
        self,
        page: int = 1,
        per_page: int = 25,
        is_active: Optional[bool] = None,
        username: Optional[str] = None,
        role_id: Optional[str] = None,
    ) -> Tuple[List[User], int]:
        """List users with pagination and filtering."""
        return await self._repo.list(
            page=page,
            per_page=per_page,
            is_active=is_active,
            username=username,
            role_id=role_id,
        )

    async def update_user(
        self,
        user_id: UUID,
        email: Optional[str] = None,
        full_name: Optional[str] = None,
        title: Optional[str] = None,
        is_active: Optional[bool] = None,
        role_id: Optional[int] = None,
    ) -> User:
        """Update user profile information."""
        update_data = {}
        if email is not None:
            update_data["email"] = email
        if full_name is not None:
            update_data["full_name"] = full_name
        if title is not None:
            update_data["title"] = title
        if is_active is not None:
            update_data["is_active"] = is_active
        if role_id is not None:
            update_data["role_id"] = role_id

        return await self._repo.update(user_id, update_data)

    async def deactivate_user(self, user_id: UUID) -> None:
        """Deactivate a user account."""
        await self._repo.delete(user_id)

    async def update_user_status(
        self,
        user_id: UUID,
        is_active: bool,
    ) -> User:
        """
        Update user active status.

        Args:
            user_id: User ID (UUID)
            is_active: New active status

        Returns:
            Updated User

        Raises:
            NotFoundError: If user not found
        """
        user = await self._repo.get_by_id(user_id)
        if not user:
            raise NotFoundError(f"User with ID {user_id} not found")

        return await self._repo.update(user_id, {"is_active": is_active})

    async def bulk_update_user_status(
        self,
        user_ids: List[UUID],
        is_active: bool,
    ) -> List[User]:
        """
        Bulk update user active status.

        Args:
            user_ids: List of User IDs (UUIDs)
            is_active: New active status

        Returns:
            List of updated Users

        Raises:
            NotFoundError: If any user not found
        """
        updated_users = []
        for user_id in user_ids:
            user = await self._repo.get_by_id(user_id)
            if not user:
                raise NotFoundError(f"User with ID {user_id} not found")
            updated_user = await self._repo.update(user_id, {"is_active": is_active})
            updated_users.append(updated_user)
        return updated_users

    async def update_user_roles(
        self,
        user_id: UUID,
        role_ids: List[str],
    ) -> User:
        """
        Update user roles by replacing all existing role assignments.

        Args:
            user_id: User ID (UUID)
            role_ids: List of role IDs (UUIDs) to assign

        Returns:
            Updated User

        Raises:
            NotFoundError: If user not found
        """
        from sqlalchemy import select
        from db.model import Role

        # Verify user exists
        user = await self._repo.get_by_id(user_id)
        if not user:
            raise NotFoundError(f"User with ID {user_id} not found")

        # Verify all roles exist before assignment
        verified_role_ids = []
        for role_id in role_ids:
            role_query = select(Role).where(Role.id == role_id)
            role_result = await self.session.execute(role_query)
            role = role_result.scalar_one_or_none()
            if role:
                verified_role_ids.append(UUID(role_id))

        # Use repository to replace all role assignments
        await self._role_permission_repo.assign_roles_to_user(
            user_id=user_id,
            role_ids=verified_role_ids,
        )

        return user
