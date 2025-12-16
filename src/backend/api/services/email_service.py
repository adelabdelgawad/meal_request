"""Email Service - Business logic for email configuration management."""

from typing import List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from api.repositories.email_repository import EmailRepository
from core.exceptions import ConflictError, NotFoundError
from db.models import Email


class EmailService:
    """Service for email configuration management operations."""

    def __init__(self):
        """Initialize service."""
        self._repo = EmailRepository()

    async def add_email(self, session: AsyncSession, address: str, role_id: int) -> Email:
        """Add an email address to the system."""
        # Check if email exists
        existing = await self._repo.get_by_address(session, address)
        if existing:
            raise ConflictError(entity="Email", field="address", value=address)

        email = Email(address=address, role_id=role_id)
        return await self._repo.create(session, email)

    async def get_email(self, session: AsyncSession, email_id: int) -> Email:
        """Get an email by ID."""
        email = await self._repo.get_by_id(session, email_id)
        if not email:
            raise NotFoundError(entity="Email", identifier=email_id)
        return email

    async def get_email_by_address(self, session: AsyncSession, address: str) -> Email:
        """Get an email by address."""
        email = await self._repo.get_by_address(session, address)
        if not email:
            raise NotFoundError(entity="Email", identifier=address)
        return email

    async def list_emails(
        self,
        session: AsyncSession,
        page: int = 1,
        per_page: int = 25,
        role_id: Optional[int] = None,
    ) -> Tuple[List[Email], int]:
        """List emails with optional filtering."""
        return await self._repo.list(session, page=page, per_page=per_page, role_id=role_id)

    async def update_email(
        self, session: AsyncSession, email_id: int, address: Optional[str] = None, role_id: Optional[int] = None
    ) -> Email:
        """Update an email."""
        # If address is being updated, check for conflicts
        if address:
            existing = await self._repo.get_by_address(session, address)
            if existing and existing.id != email_id:
                raise ConflictError(entity="Email", field="address", value=address)

        update_data = {}
        if address is not None:
            update_data["address"] = address
        if role_id is not None:
            update_data["role_id"] = role_id

        return await self._repo.update(session, email_id, update_data)

    async def remove_email(self, session: AsyncSession, email_id: int) -> None:
        """Remove an email from the system."""
        await self._repo.delete(session, email_id)
