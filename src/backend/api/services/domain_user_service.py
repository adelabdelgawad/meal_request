"""DomainUser Service - Business logic for DomainUser entity."""

import logging
from dataclasses import dataclass
from typing import List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from api.repositories.domain_user_repository import DomainUserRepository
from core.exceptions import ConflictError, DatabaseError, NotFoundError
from db.models import DomainUser

logger = logging.getLogger(__name__)


@dataclass
class SyncResult:
    """Result of AD sync operation."""

    deleted_count: int
    created_count: int
    ad_users_fetched: int


class DomainUserService:
    """Service for managing domain user cache (Active Directory users)."""

    def __init__(self):
        """Initialize service."""
        self._repo = DomainUserRepository()

    async def create_domain_user(
        self,
        session: AsyncSession,
        username: str,
        email: Optional[str] = None,
        full_name: Optional[str] = None,
        title: Optional[str] = None,
        office: Optional[str] = None,
        phone: Optional[str] = None,
        manager: Optional[str] = None,
    ) -> DomainUser:
        """
        Create a new domain user entry.

        Args:
            session: Database session
            username: AD username (unique)
            email: Email address from AD
            full_name: Full name from AD
            title: Job title from AD
            office: Office location
            phone: Phone number
            manager: Manager's name or username

        Returns:
            Created DomainUser

        Raises:
            ConflictError: If username already exists
        """
        # Check if username exists
        existing = await self._repo.get_by_username(session, username)
        if existing:
            raise ConflictError(entity="DomainUser", field="username", value=username)

        domain_user = DomainUser(
            username=username,
            email=email,
            full_name=full_name,
            title=title,
            office=office,
            phone=phone,
            manager=manager,
        )

        return await self._repo.create(session, domain_user)

    async def get_domain_user(self, session: AsyncSession, user_id: int) -> DomainUser:
        """
        Get a domain user by ID.

        Raises:
            NotFoundError: If user not found
        """
        user = await self._repo.get_by_id(session, user_id)
        if not user:
            raise NotFoundError(entity="DomainUser", identifier=user_id)
        return user

    async def get_domain_user_by_username(
        self, session: AsyncSession, username: str
    ) -> DomainUser:
        """
        Get a domain user by username.

        Raises:
            NotFoundError: If user not found
        """
        user = await self._repo.get_by_username(session, username)
        if not user:
            raise NotFoundError(entity="DomainUser", identifier=username)
        return user

    async def list_domain_users(
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

        Returns:
            Tuple of (list of DomainUser, total count)
        """
        return await self._repo.list(
            session,
            page=page,
            per_page=per_page,
            search=search,
        )

    async def update_domain_user(
        self,
        session: AsyncSession,
        user_id: int,
        email: Optional[str] = None,
        full_name: Optional[str] = None,
        title: Optional[str] = None,
        office: Optional[str] = None,
        phone: Optional[str] = None,
        manager: Optional[str] = None,
    ) -> DomainUser:
        """
        Update a domain user's information.

        Args:
            session: Database session
            user_id: ID of user to update
            email: Updated email
            full_name: Updated full name
            title: Updated title
            office: Updated office
            phone: Updated phone
            manager: Updated manager

        Returns:
            Updated DomainUser

        Raises:
            NotFoundError: If user not found
        """
        update_data = {}
        if email is not None:
            update_data["email"] = email
        if full_name is not None:
            update_data["full_name"] = full_name
        if title is not None:
            update_data["title"] = title
        if office is not None:
            update_data["office"] = office
        if phone is not None:
            update_data["phone"] = phone
        if manager is not None:
            update_data["manager"] = manager

        return await self._repo.update(session, user_id, update_data)

    async def upsert_domain_user(
        self,
        session: AsyncSession,
        username: str,
        email: Optional[str] = None,
        full_name: Optional[str] = None,
        title: Optional[str] = None,
        office: Optional[str] = None,
        phone: Optional[str] = None,
        manager: Optional[str] = None,
    ) -> DomainUser:
        """
        Create or update a domain user by username.

        Useful for syncing data from Active Directory.

        Args:
            session: Database session
            username: AD username
            email: Email from AD
            full_name: Full name from AD
            title: Job title from AD
            office: Office location
            phone: Phone number
            manager: Manager's name or username

        Returns:
            Created or updated DomainUser
        """
        user_data = {
            "email": email,
            "full_name": full_name,
            "title": title,
            "office": office,
            "phone": phone,
            "manager": manager,
        }
        # Remove None values
        user_data = {k: v for k, v in user_data.items() if v is not None}

        return await self._repo.upsert(session, username, user_data)

    async def delete_domain_user(self, session: AsyncSession, user_id: int) -> None:
        """
        Delete a domain user.

        Args:
            session: Database session
            user_id: ID of user to delete

        Raises:
            NotFoundError: If user not found
        """
        await self._repo.delete(session, user_id)

    async def bulk_upsert_domain_users(
        self,
        session: AsyncSession,
        users_data: List[dict],
    ) -> List[DomainUser]:
        """
        Bulk create or update domain users.

        Useful for batch syncing from Active Directory.

        Args:
            session: Database session
            users_data: List of dicts with 'username' and optional fields

        Returns:
            List of created/updated DomainUser objects
        """
        return await self._repo.bulk_upsert(session, users_data)

    async def sync_from_active_directory(
        self,
        session: AsyncSession,
    ) -> SyncResult:
        """
        Refresh domain users table from Active Directory.

        This operation:
        1. Fetches all enabled domain users from AD
        2. Deletes all existing records from domain_user table
        3. Inserts the fetched AD users into the database

        Args:
            session: Database session

        Returns:
            SyncResult with counts of deleted, created, and fetched records

        Raises:
            DatabaseError: If AD fetch fails or database operations fail
        """
        from starlette.concurrency import run_in_threadpool
        from utils.active_directory import LDAPAuthenticator

        logger.info("Starting domain user sync from Active Directory")

        # Step 1: Fetch all domain users from AD (run in threadpool as it's sync)
        try:
            ldap_auth = LDAPAuthenticator()
            domain_accounts = await run_in_threadpool(ldap_auth.get_domain_accounts)

            if domain_accounts is None:
                raise DatabaseError("Failed to fetch domain users from Active Directory")

            ad_users_fetched = len(domain_accounts)
            logger.info(f"Fetched {ad_users_fetched} users from Active Directory")

        except Exception as e:
            logger.error(f"Failed to fetch domain users from AD: {e}")
            raise DatabaseError(f"Failed to fetch domain users from Active Directory: {str(e)}")

        # Step 2: Delete all existing domain users
        try:
            deleted_count = await self._repo.delete_all(session)
            logger.info(f"Deleted {deleted_count} existing domain users")
        except Exception as e:
            logger.error(f"Failed to delete existing domain users: {e}")
            raise DatabaseError(f"Failed to delete existing domain users: {str(e)}")

        # Step 3: Insert the fetched AD users
        try:
            users_data = [
                {
                    "username": account.username,
                    "email": account.email,
                    "full_name": account.fullName,
                    "title": account.title,
                    "office": account.office,
                    "phone": account.phone,
                    "manager": account.manager,
                }
                for account in domain_accounts
            ]

            created_count = await self._repo.bulk_create(session, users_data)
            logger.info(f"Created {created_count} domain users from AD")

        except Exception as e:
            logger.error(f"Failed to create domain users: {e}")
            raise DatabaseError(f"Failed to create domain users: {str(e)}")

        return SyncResult(
            deleted_count=deleted_count,
            created_count=created_count,
            ad_users_fetched=ad_users_fetched,
        )
