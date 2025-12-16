"""Department Assignment Repository."""

from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import and_, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import DatabaseError, NotFoundError
from db.models import DepartmentAssignment


class DepartmentAssignmentRepository:
    """Repository for DepartmentAssignment entity."""

    def __init__(self):
        pass

    async def create(self, session: AsyncSession, assignment: DepartmentAssignment) -> DepartmentAssignment:
        try:
            session.add(assignment)
            await session.flush()
            return assignment
        except Exception as e:
            await session.rollback()
            raise DatabaseError(f"Failed to create assignment: {str(e)}")

    async def get_by_id(self, session: AsyncSession, assignment_id: int) -> Optional[DepartmentAssignment]:
        result = await session.execute(
            select(DepartmentAssignment).where(DepartmentAssignment.id == assignment_id)
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        session: AsyncSession,
        page: int = 1,
        per_page: int = 25,
        user_id: Optional[UUID] = None,
        department_id: Optional[int] = None,
    ) -> Tuple[List[DepartmentAssignment], int]:
        from core.pagination import calculate_offset

        query = select(DepartmentAssignment)

        if user_id is not None:
            query = query.where(DepartmentAssignment.user_id == user_id)
        if department_id is not None:
            query = query.where(DepartmentAssignment.department_id == department_id)

        # Optimized count query


        count_query = select(func.count()).select_from((query).subquery())


        count_result = await session.execute(count_query)


        total = count_result.scalar() or 0

        offset = calculate_offset(page, per_page)
        result = await session.execute(
            query.offset(offset).limit(per_page)
        )
        return result.scalars().all(), total

    async def get_by_employee_and_department(
        self,
        session: AsyncSession,
        user_id: str,
        department_id: int,
    ) -> Optional[DepartmentAssignment]:
        """Get department assignment by user and department."""
        result = await session.execute(
            select(DepartmentAssignment).where(
                and_(
                    DepartmentAssignment.user_id == user_id,
                    DepartmentAssignment.department_id == department_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_manual_assignments(
        self,
        session: AsyncSession,
        user_id: str
    ) -> List[DepartmentAssignment]:
        """
        Get all manual (non-HRIS) assignments for a user.

        Args:
            session: AsyncSession
            user_id: User UUID

        Returns:
            List of active manual department assignments
        """
        result = await session.execute(
            select(DepartmentAssignment).where(
                and_(
                    DepartmentAssignment.user_id == user_id,
                    not DepartmentAssignment.is_synced_from_hris,
                    DepartmentAssignment.is_active
                )
            )
        )
        return list(result.scalars().all())

    async def deactivate_hris_assignments(self, session: AsyncSession) -> int:
        """
        Deactivate existing HRIS-synced department assignments only.

        Only deactivates records where is_synced_from_hris=True.
        Preserves manual assignments (is_synced_from_hris=False).

        Args:
            session: AsyncSession

        Returns:
            Number of records deactivated
        """
        from sqlalchemy import update

        stmt = (
            update(DepartmentAssignment)
            .where(
                and_(
                    DepartmentAssignment.is_synced_from_hris,
                    DepartmentAssignment.is_active,
                )
            )
            .values(is_active=False, updated_at=func.now())
        )
        result = await session.execute(stmt)
        return result.rowcount or 0

    async def update(self, session: AsyncSession, assignment_id: int, assignment_data: dict) -> DepartmentAssignment:
        assignment = await self.get_by_id(session, assignment_id)
        if not assignment:
            raise NotFoundError(entity="DepartmentAssignment", identifier=assignment_id)

        try:
            for key, value in assignment_data.items():
                if value is not None and hasattr(assignment, key):
                    setattr(assignment, key, value)

            await session.flush()
            return assignment
        except Exception as e:
            await session.rollback()
            raise DatabaseError(f"Failed to update assignment: {str(e)}")

    async def delete(self, session: AsyncSession, assignment_id: int) -> None:
        assignment = await self.get_by_id(session, assignment_id)
        if not assignment:
            raise NotFoundError(entity="DepartmentAssignment", identifier=assignment_id)

        await session.delete(assignment)
        await session.flush()
