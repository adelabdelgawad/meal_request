"""Email Role Service - Business logic for email role management."""

from typing import List, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from api.repositories.email_role_repository import EmailRoleRepository
from core.exceptions import ConflictError, NotFoundError
from db.model import EmailRole


class EmailRoleService:
    """Service for email role management operations."""

    def __init__(self, session: AsyncSession):
        """Initialize service."""
        self.session = session
        self._repo = EmailRoleRepository(session)

    async def create_email_role(self, name: str) -> EmailRole:
        """Create a new email role."""
        # Check if email role exists
        existing = await self._repo.get_by_name(name)
        if existing:
            raise ConflictError(entity="EmailRole", field="name", value=name)

        role = EmailRole(name=name)
        return await self._repo.create(role)

    async def get_email_role(self, role_id: int) -> EmailRole:
        """Get an email role by ID."""
        role = await self._repo.get_by_id(role_id)
        if not role:
            raise NotFoundError(entity="EmailRole", identifier=role_id)
        return role

    async def get_email_role_by_name(
        self, session: AsyncSession, name: str
    ) -> EmailRole:
        """Get an email role by name."""
        role = await self._repo.get_by_name(session, name)
        if not role:
            raise NotFoundError(entity="EmailRole", identifier=name)
        return role

    async def list_email_roles(
        self, page: int = 1, per_page: int = 25
    ) -> Tuple[List[EmailRole], int]:
        """List email roles with pagination."""
        return await self._repo.list(page=page, per_page=per_page)

    async def update_email_role(self, role_id: int, name: str) -> EmailRole:
        """Update an email role."""
        # If name is being updated, check for conflicts
        existing = await self._repo.get_by_name(name)
        if existing and existing.id != role_id:
            raise ConflictError(entity="EmailRole", field="name", value=name)

        return await self._repo.update(role_id, {"name": name})

    async def delete_email_role(self, role_id: int) -> None:
        """Delete an email role."""
        await self._repo.delete(role_id)
