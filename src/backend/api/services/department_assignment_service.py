"""Department Assignment Service - Business logic for department assignments."""

from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from api.repositories.department_assignment_repository import (
    DepartmentAssignmentRepository,
)
from core.exceptions import NotFoundError
from db.models import DepartmentAssignment


class DepartmentAssignmentService:
    """Service for department assignment management."""

    def __init__(self):
        """Initialize service."""
        self._repo = DepartmentAssignmentRepository()

    async def assign_user_to_department(
        self,
        session: AsyncSession,
        user_id: str,
        department_id: int,
        created_by_id: Optional[str] = None,
        is_synced_from_hris: bool = False,
    ) -> DepartmentAssignment:
        """
        Assign a user to a department.

        Args:
            session: AsyncSession
            user_id: ID of user
            department_id: ID of department
            created_by_id: Optional ID of user who created this assignment
            is_synced_from_hris: Whether this is from HRIS sync (default False for manual)

        Returns:
            Created DepartmentAssignment
        """
        assignment = DepartmentAssignment(
            user_id=user_id,
            department_id=department_id,
            created_by_id=created_by_id,
            is_synced_from_hris=is_synced_from_hris,
            is_active=True,
        )

        return await self._repo.create(session, assignment)

    async def get_assignment(self, session: AsyncSession, assignment_id: int) -> DepartmentAssignment:
        """Get a department assignment by ID."""
        assignment = await self._repo.get_by_id(session, assignment_id)
        if not assignment:
            raise NotFoundError(entity="DepartmentAssignment", identifier=assignment_id)
        return assignment

    async def list_assignments(
        self,
        session: AsyncSession,
        page: int = 1,
        per_page: int = 25,
        user_id: Optional[UUID] = None,
        department_id: Optional[int] = None,
    ) -> Tuple[List[DepartmentAssignment], int]:
        """List department assignments with optional filtering."""
        return await self._repo.list(session, 
            page=page,
            per_page=per_page,
            user_id=user_id,
            department_id=department_id,
        )

    async def update_assignment(
        self,
        session: AsyncSession,
        assignment_id: int,
        updated_by_id: Optional[str] = None,
        **kwargs,
    ) -> DepartmentAssignment:
        """
        Update a department assignment.

        Args:
            session: AsyncSession
            assignment_id: ID of assignment to update
            updated_by_id: Optional ID of user making this update
            **kwargs: Additional fields to update

        Returns:
            Updated DepartmentAssignment
        """
        update_data = kwargs.copy()
        if updated_by_id is not None:
            update_data["updated_by_id"] = updated_by_id

        return await self._repo.update(session, assignment_id, update_data)

    async def remove_assignment(self, session: AsyncSession, assignment_id: int) -> None:
        """Remove a department assignment."""
        await self._repo.delete(session, assignment_id)
