"""Security User Service - Business logic for SecurityUser entity."""

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from api.repositories.security_user_repository import SecurityUserRepository
from core.exceptions import ValidationError
from db.models import SecurityUser


class SecurityUserService:
    """Service for SecurityUser entity operations."""

    def __init__(self):
        """Initialize security user service."""
        self._repo = SecurityUserRepository()

    async def create_security_user(
        self,
        session: AsyncSession,
        user_name: str,
        is_deleted: bool = False,
        is_locked: bool = False,
    ) -> SecurityUser:
        """
        Create a new security user.

        Args:
            session: Database session
            user_name: Username
            is_deleted: Whether user is deleted
            is_locked: Whether user is locked

        Returns:
            Created SecurityUser

        Raises:
            ValidationError: If inputs are invalid
            ConflictError: If username already exists
        """
        # Validate inputs
        if not user_name or len(user_name) < 2:
            raise ValidationError("Username must be at least 2 characters")

        # Check if username exists
        existing = await self._repo.get_by_username(session, user_name)
        if existing:
            # Update existing security user instead of creating
            return await self._repo.update(
                session,
                existing.id,
                {
                    "is_deleted": is_deleted,
                    "is_locked": is_locked,
                },
            )

        # Create new security user
        security_user = SecurityUser(
            user_name=user_name,
            is_deleted=is_deleted,
            is_locked=is_locked,
        )

        return await self._repo.create(session, security_user)

    async def get_security_user(
        self, session: AsyncSession, user_id: int
    ) -> Optional[SecurityUser]:
        """
        Get security user by ID.

        Args:
            session: Database session
            user_id: Security user ID

        Returns:
            SecurityUser or None
        """
        return await self._repo.get_by_id(session, user_id)

    async def get_by_username(
        self, session: AsyncSession, user_name: str
    ) -> Optional[SecurityUser]:
        """
        Get security user by username.

        Args:
            session: Database session
            user_name: Username

        Returns:
            SecurityUser or None
        """
        return await self._repo.get_by_username(session, user_name)

    async def deactivate_all_security_users(self, session: AsyncSession) -> None:
        """
        Deactivate all security users before replication.

        Args:
            session: Database session
        """
        await self._repo.deactivate_all(session)
