"""
User Repository - Data access layer for User entity.
"""

from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import ConflictError, DatabaseError, NotFoundError
from core.security import hash_password
from db.model import User
from .base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repository for User entity operations."""

    def __init__(self, session: AsyncSession):
        """Initialize repository with session."""
        super().__init__(session)

    async def create(self, user: User) -> User:
        """
        Create a new user.

        Args:
            user: User instance to create

        Returns:
            Created user with ID populated

        Raises:
            ConflictError: If username or email already exists
            DatabaseError: If database operation fails
        """
        try:
            return await super().create(user)
        except IntegrityError as e:
            await self.session.rollback()
            error_msg = str(e.orig).lower()

            if "duplicate entry" in error_msg:
                if "username" in error_msg:
                    raise ConflictError(f"Username '{user.username}' already exists")
                elif "email" in error_msg:
                    raise ConflictError(f"Email '{user.email}' already exists")

            raise DatabaseError(f"Failed to create user: {str(e)}")

    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        """
        Read a user by ID.

        Args:
            user_id: UUID of user to read

        Returns:
            User if found, None otherwise
        """
        # Convert UUID to string since User.id is CHAR(36) in database
        result = await self.session.execute(select(User).where(User.id == str(user_id)))
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> Optional[User]:
        """
        Read a user by username.

        Args:
            username: Username to search for

        Returns:
            User if found, None otherwise
        """
        result = await self.session.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        """
        Read a user by email.

        Args:
            email: Email to search for

        Returns:
            User if found, None otherwise
        """
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def list(
        self,
        page: int = 1,
        per_page: int = 25,
        is_active: Optional[bool] = None,
        username: Optional[str] = None,
        role_id: Optional[str] = None,
    ) -> Tuple[List[User], int]:
        """
        Read multiple users with pagination and filtering.

        Args:
            page: Page number (1-indexed)
            per_page: Number of items per page
            is_active: Filter by active status (True/False/None for all)
            username: Filter by username (partial match)
            role_id: Filter by role ID

        Returns:
            Tuple of (users list, total count)
        """
        from core.pagination import calculate_offset
        from sqlalchemy import func
        from db.model import RolePermission

        # Build base query with filters
        query = select(User)
        count_query = select(func.count(User.id))

        # Always exclude super admin users
        query = query.where(~User.is_super_admin)
        count_query = count_query.where(~User.is_super_admin)

        # Apply is_active filter
        if is_active is not None:
            query = query.where(User.is_active == is_active)
            count_query = count_query.where(User.is_active == is_active)

        # Apply username filter (partial match, case-insensitive)
        if username:
            query = query.where(User.username.ilike(f"%{username}%"))
            count_query = count_query.where(User.username.ilike(f"%{username}%"))

        # Apply role filter
        if role_id:
            # Join with RolePermission to filter by role
            # Use DISTINCT to prevent duplicate users if multiple role permissions exist
            query = (
                query.join(RolePermission, User.id == RolePermission.user_id)
                .where(RolePermission.role_id == role_id)
                .distinct()
            )
            count_query = (
                count_query.join(RolePermission, User.id == RolePermission.user_id)
                .where(RolePermission.role_id == role_id)
                .distinct()
            )

        # Get total count
        count_result = await self.session.execute(count_query)
        total = count_result.scalar() or 0

        # Get paginated results
        offset = calculate_offset(page, per_page)
        result = await self.session.execute(query.offset(offset).limit(per_page))
        users = result.scalars().all()

        return list(users), total

    async def update(self, user_id: UUID, user_data: dict) -> User:
        """
        Update an existing user.

        Args:
            user_id: UUID of user to update
            user_data: Dictionary of fields to update

        Returns:
            Updated user

        Raises:
            NotFoundError: If user not found
            ConflictError: If unique constraint violated
            DatabaseError: If database operation fails
        """
        user = await self.get_by_id(user_id)
        if not user:
            raise NotFoundError(f"User with ID {user_id} not found")

        try:
            for key, value in user_data.items():
                if value is not None and hasattr(user, key):
                    setattr(user, key, value)

            await self.session.flush()
            return user
        except IntegrityError as e:
            await self.session.rollback()
            raise DatabaseError(f"Failed to update user: {str(e)}")

    async def delete(self, user_id: UUID) -> None:
        """
        Soft delete a user (mark as inactive).

        Args:
            user_id: UUID of user to delete

        Raises:
            NotFoundError: If user not found
        """
        user = await self.get_by_id(user_id)
        if not user:
            raise NotFoundError(f"User with ID {user_id} not found")

        user.is_active = False
        await self.session.flush()

    async def update_preferred_locale(self, user_id: str, locale: str) -> User:
        """
        Update user's preferred locale.

        Args:
            user_id: User ID (UUID as string)
            locale: Locale code (2-letter, e.g., 'en', 'ar')

        Returns:
            Updated user

        Raises:
            NotFoundError: If user not found
            DatabaseError: If database operation fails
        """
        from core.config import settings

        # Validate locale
        if locale not in settings.locale.supported_locales:
            raise DatabaseError(
                f"Invalid locale '{locale}'. Supported locales: {', '.join(settings.locale.supported_locales)}"
            )

        # Get user
        result = await self.session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            raise NotFoundError(f"User with ID {user_id} not found")

        # Update preferred locale
        user.preferred_locale = locale
        await self.session.flush()
        return user

    # CRUD compatibility methods (for backward compatibility during migration)
    async def read_account(
        self,
        username: Optional[str] = None,
        account_id: Optional[int] = None,
    ) -> Optional[User]:
        """
        Compatibility wrapper for CRUD read_account function.
        Reads a user by username or ID.
        """
        if username:
            return await self.get_by_username(username)
        elif account_id:
            return await self.get_by_id(
                UUID(int=account_id) if isinstance(account_id, int) else account_id
            )
        return None

    async def create_account(self, user_create) -> User:
        """
        Compatibility wrapper for CRUD create_account function.
        Creates or updates a user by username.
        Automatically hashes password if provided.
        """
        # Check if user already exists
        existing = await self.get_by_username(user_create.username)
        if existing:
            # Update existing user
            user_data = user_create.model_dump(exclude_unset=True)
            # Hash password if provided and it's not already a hash
            if "password" in user_data and user_data["password"]:
                # Only hash if it doesn't look like a bcrypt hash (bcrypt hashes start with $2b$)
                if not user_data["password"].startswith("$2b$"):
                    user_data["password"] = hash_password(user_data["password"])

            for key, value in user_data.items():
                if hasattr(existing, key) and value is not None:
                    setattr(existing, key, value)
            await self.session.flush()
            return existing

        # Create new user
        user_data = user_create.model_dump()
        # Hash password if provided and not already hashed
        if "password" in user_data and user_data["password"]:
            if not user_data["password"].startswith("$2b$"):
                user_data["password"] = hash_password(user_data["password"])

        user = User(**user_data)
        return await self.create(user)

    # Bulk Operations
    async def bulk_create(self, users: List[User]) -> List[User]:
        """
        Create multiple users in a single operation.

        Args:
            users: List of User instances to create

        Returns:
            List of created users

        Raises:
            ConflictError: If any username or email already exists
            DatabaseError: If database operation fails
        """
        try:
            for user in users:
                self.session.add(user)
            await self.session.flush()
            for user in users:
                await self.session.refresh(user)
            return users
        except IntegrityError as e:
            await self.session.rollback()
            error_msg = str(e.orig).lower()
            if "duplicate entry" in error_msg:
                raise ConflictError(f"Duplicate username or email in bulk operation")
            raise DatabaseError(f"Failed to bulk create users: {str(e)}")

    async def bulk_update_status(
        self,
        user_ids: List[UUID],
        is_active: bool,
    ) -> int:
        """
        Update active status for multiple users in a single operation.

        Args:
            user_ids: List of user IDs to update
            is_active: New active status

        Returns:
            Number of users updated

        Raises:
            DatabaseError: If database operation fails
        """
        from sqlalchemy import update

        try:
            stmt = (
                update(User)
                .where(User.id.in_([str(uid) for uid in user_ids]))
                .values(is_active=is_active)
            )
            result = await self.session.execute(stmt)
            await self.session.flush()
            return result.rowcount
        except Exception as e:
            await self.session.rollback()
            raise DatabaseError(f"Failed to bulk update user status: {str(e)}")

    async def bulk_delete(self, user_ids: List[UUID]) -> int:
        """
        Soft delete multiple users in a single operation.

        Args:
            user_ids: List of user IDs to delete

        Returns:
            Number of users deleted

        Raises:
            DatabaseError: If database operation fails
        """
        from sqlalchemy import update

        try:
            stmt = (
                update(User)
                .where(User.id.in_([str(uid) for uid in user_ids]))
                .values(is_active=False)
            )
            result = await self.session.execute(stmt)
            await self.session.flush()
            return result.rowcount
        except Exception as e:
            await self.session.rollback()
            raise DatabaseError(f"Failed to bulk delete users: {str(e)}")
