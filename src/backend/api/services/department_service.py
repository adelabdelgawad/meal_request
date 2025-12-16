"""Department Service - Business logic for department management."""

from typing import List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from api.repositories.department_repository import DepartmentRepository
from core.exceptions import ConflictError, NotFoundError
from db.models import Department


class DepartmentService:
    """Service for department management operations."""

    def __init__(self):
        """Initialize service."""
        self._repo = DepartmentRepository()

    async def create_department(
        self,
        session: AsyncSession,
        name_en: str,
        name_ar: str,
    ) -> Department:
        """
        Create a new department.

        Args:
            session: Database session
            name_en: Department name in English
            name_ar: Department name in Arabic

        Returns:
            Created Department

        Raises:
            ConflictError: If department name already exists
        """
        # Check if department exists by English name
        existing = await self._repo.get_by_name_en(session, name_en)
        if existing:
            # Update existing department with new names (for replication)
            return await self._repo.update(
                session,
                existing.id,
                {"name_en": name_en, "name_ar": name_ar}
            )

        department = Department(
            name_en=name_en,
            name_ar=name_ar,
        )

        return await self._repo.create(session, department)

    async def get_department(self, session: AsyncSession, department_id: int) -> Department:
        """Get a department by ID."""
        department = await self._repo.get_by_id(session, department_id)
        if not department:
            raise NotFoundError(entity="Department", identifier=department_id)
        return department

    async def get_department_by_name(self, session: AsyncSession, name: str, locale: str = "en") -> Department:
        """Get a department by name."""
        if locale == "ar":
            department = await self._repo.get_by_name_ar(session, name)
        else:
            department = await self._repo.get_by_name_en(session, name)
        if not department:
            raise NotFoundError(entity="Department", identifier=name)
        return department

    async def list_departments(
        self,
        session: AsyncSession,
        page: int = 1,
        per_page: int = 25,
    ) -> Tuple[List[Department], int]:
        """List departments with pagination."""
        return await self._repo.list(session, page=page, per_page=per_page)

    async def update_department(
        self,
        session: AsyncSession,
        department_id: int,
        name_en: Optional[str] = None,
        name_ar: Optional[str] = None,
        parent_id: Optional[int] = None,
    ) -> Department:
        """Update a department."""
        # If name_en is being updated, check for conflicts
        if name_en:
            existing = await self._repo.get_by_name_en(session, name_en)
            if existing and existing.id != department_id:
                raise ConflictError(entity="Department", field="name_en", value=name_en)

        update_data = {}
        if name_en is not None:
            update_data["name_en"] = name_en
        if name_ar is not None:
            update_data["name_ar"] = name_ar
        if parent_id is not None:
            update_data["parent_id"] = parent_id

        return await self._repo.update(session, department_id, update_data)

    async def delete_department(self, session: AsyncSession, department_id: int) -> None:
        """Delete a department."""
        await self._repo.delete(session, department_id)
