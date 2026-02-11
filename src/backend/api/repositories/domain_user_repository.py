"""DomainUser Repository - Data access layer for DomainUser entity."""

from typing import List, Optional, Tuple

from sqlalchemy import delete, select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import DatabaseError, NotFoundError
from db.model import DomainUser
from .base import BaseRepository


class DomainUserRepository(BaseRepository[DomainUser]):
    """Repository for DomainUser entity."""

        super().__init__(session)

    async def create(self, domain_user: DomainUser) -> DomainUser:
        """Create a new domain user."""
        try:
            self.session.add(domain_user)
            await self.session.flush()
            await self.session.refresh(domain_user)
            return domain_user
        except IntegrityError as e:
            await self.session.rollback()
            raise DatabaseError(f"Failed to create domain user: {str(e)}")

    async def get_by_id(self, user_id: int) -> Optional[DomainUser]:
        """Get domain user by ID."""
        result = await self.session.execute(
            select(DomainUser).where(DomainUser.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> Optional[DomainUser]:
        """Get domain user by username."""
        result = await self.session.execute(
            select(DomainUser).where(DomainUser.username == username)
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        session: AsyncSession,
        page: int = 1,
        per_page: int = 25,
        search: Optional[str] = None,
    ) -> Tuple[List[DomainUser], int]:
        """
        List domain users with pagination and optional search.

        Args:
            session: Database session
            page: Page number (1-indexed)
            per_page: Items per page
            search: Optional search term for username or full_name
        """
        from core.pagination import calculate_offset

        # Build base query
        query = select(DomainUser)
        count_query = select(DomainUser)

        # Apply search filter if provided
        if search:
            search_filter = (
                DomainUser.username.ilike(f"%{search}%") |
                DomainUser.full_name.ilike(f"%{search}%") |
                DomainUser.email.ilike(f"%{search}%")
            )
            query = query.where(search_filter)
            count_query = count_query.where(search_filter)

        # Get total count
        # Optimized count query

        count_query = select(func.count()).select_from((count_query).subquery())

        count_result = await self.session.execute(count_query)

        total = count_result.scalar() or 0

        # Apply pagination
        offset = calculate_offset(page, per_page)
        query = query.offset(offset).limit(per_page)

        result = await self.session.execute(query)
        return list(result.scalars().all()), total

    async def update(
        self,
        session: AsyncSession,
        user_id: int,
        user_data: dict,
    ) -> DomainUser:
        """Update a domain user."""
        domain_user = await self.get_by_id(user_id)
        if not domain_user:
            raise NotFoundError(f"DomainUser with ID str(user_id not found"))

        try:
            for key, value in user_data.items():
                if value is not None and hasattr(domain_user, key):
                    setattr(domain_user, key, value)

            await self.session.flush()
            await self.session.refresh(domain_user)
            return domain_user
        except IntegrityError as e:
            await self.session.rollback()
            raise DatabaseError(f"Failed to update domain user: {str(e)}")

    async def upsert(
        self,
        session: AsyncSession,
        username: str,
        user_data: dict,
    ) -> DomainUser:
        """
        Create or update a domain user by username.

        Useful for syncing data from Active Directory.
        """
        existing = await self.get_by_username(session, username)

        if existing:
            # Update existing user
            return await self.update(session, existing.id, user_data)
        else:
            # Create new user
            domain_user = DomainUser(username=username, **user_data)
            return await self.create(session, domain_user)

    async def delete(self, user_id: int) -> None:
        """Delete a domain user."""
        domain_user = await self.get_by_id(user_id)
        if not domain_user:
            raise NotFoundError(f"DomainUser with ID str(user_id not found"))

        await self.session.delete(domain_user)
        await self.session.flush()

    async def bulk_upsert(
        self,
        session: AsyncSession,
        users_data: List[dict],
    ) -> List[DomainUser]:
        """
        Bulk create or update domain users.

        Each dict in users_data must contain 'username' key.
        """
        results = []
        for user_data in users_data:
            username = user_data.pop("username")
            result = await self.upsert(session, username, user_data)
            results.append(result)
        return results

    async def delete_all(self) -> int:
        """
        Delete all domain users from the table.

        Returns:
            Number of deleted records
        """
        try:
            result = await self.session.execute(delete(DomainUser))
            await self.session.flush()
            return result.rowcount
        except Exception as e:
            await self.session.rollback()
            raise DatabaseError(f"Failed to delete all domain users: {str(e)}")

    async def bulk_create(
        self,
        session: AsyncSession,
        users_data: List[dict],
    ) -> int:
        """
        Bulk create domain users (insert only, no update).

        Args:
            session: Database session
            users_data: List of dicts with user data

        Returns:
            Number of created records
        """
        try:
            count = 0
            for user_data in users_data:
                domain_user = DomainUser(**user_data)
                self.session.add(domain_user)
                count += 1
            await self.session.flush()
            return count
        except IntegrityError as e:
            await self.session.rollback()
            raise DatabaseError(f"Failed to bulk create domain users: {str(e)}")
