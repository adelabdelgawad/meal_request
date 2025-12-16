"""Department Repository."""

from typing import Dict, List, Optional, Set, Tuple

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import DatabaseError, NotFoundError
from db.models import Department


class DepartmentRepository:
    """Repository for Department entity."""

    def __init__(self):
        pass

    async def create(self, session: AsyncSession, department: Department) -> Department:
        try:
            session.add(department)
            await session.flush()
            return department
        except Exception as e:
            await session.rollback()
            raise DatabaseError(f"Failed to create department: {str(e)}")

    async def get_by_id(self, session: AsyncSession, department_id: int) -> Optional[Department]:
        result = await session.execute(
            select(Department).where(Department.id == department_id)
        )
        return result.scalar_one_or_none()

    async def get_by_name_en(self, session: AsyncSession, name_en: str) -> Optional[Department]:
        result = await session.execute(
            select(Department).where(Department.name_en == name_en)
        )
        return result.scalar_one_or_none()

    async def get_by_name_ar(self, session: AsyncSession, name_ar: str) -> Optional[Department]:
        result = await session.execute(
            select(Department).where(Department.name_ar == name_ar)
        )
        return result.scalar_one_or_none()

    async def list(self, session: AsyncSession, page: int = 1, per_page: int = 25) -> Tuple[List[Department], int]:
        from core.pagination import calculate_offset

        # Optimized count query


        count_query = select(func.count()).select_from((select(Department)).subquery())


        count_result = await session.execute(count_query)


        total = count_result.scalar() or 0

        offset = calculate_offset(page, per_page)
        result = await session.execute(
            select(Department).offset(offset).limit(per_page)
        )
        return result.scalars().all(), total

    async def update(self, session: AsyncSession, department_id: int, department_data: dict) -> Department:
        department = await self.get_by_id(session, department_id)
        if not department:
            raise NotFoundError(entity="Department", identifier=department_id)

        try:
            for key, value in department_data.items():
                if value is not None and hasattr(department, key):
                    setattr(department, key, value)

            await session.flush()
            return department
        except Exception as e:
            await session.rollback()
            raise DatabaseError(f"Failed to update department: {str(e)}")

    async def delete(self, session: AsyncSession, department_id: int) -> None:
        department = await self.get_by_id(session, department_id)
        if not department:
            raise NotFoundError(entity="Department", identifier=department_id)

        await session.delete(department)
        await session.flush()

    async def get_all_with_hierarchy(self, session: AsyncSession) -> Dict[int, dict]:
        """
        Get all departments with their hierarchy info.

        Returns:
            Dict mapping department_id to {id, name_en, name_ar, parent_id}
        """
        result = await session.execute(
            select(
                Department.id,
                Department.name_en,
                Department.name_ar,
                Department.parent_id,
            )
        )
        rows = result.fetchall()
        return {
            row.id: {
                "id": row.id,
                "name_en": row.name_en,
                "name_ar": row.name_ar,
                "parent_id": row.parent_id,
            }
            for row in rows
        }

    async def get_all_children_ids(
        self, session: AsyncSession, parent_id: int
    ) -> Set[int]:
        """
        Get all descendant department IDs for a parent (recursive).

        Args:
            session: Database session
            parent_id: ID of the parent department

        Returns:
            Set of all child department IDs (all levels deep)
        """
        dept_map = await self.get_all_with_hierarchy(session)
        children = set()

        def collect_children(pid: int):
            for dept_id, info in dept_map.items():
                if info["parent_id"] == pid:
                    children.add(dept_id)
                    collect_children(dept_id)

        collect_children(parent_id)
        return children

    async def get_parent_chain(
        self, session: AsyncSession, department_id: int
    ) -> List[int]:
        """
        Get all parent department IDs from a department up to root.

        Args:
            session: Database session
            department_id: ID of the starting department

        Returns:
            List of parent IDs from immediate parent to root
        """
        dept_map = await self.get_all_with_hierarchy(session)
        parents = []
        current_id = department_id

        while current_id in dept_map:
            parent_id = dept_map[current_id]["parent_id"]
            if parent_id is None:
                break
            parents.append(parent_id)
            current_id = parent_id

        return parents

    async def expand_department_ids_with_children(
        self, session: AsyncSession, department_ids: List[int]
    ) -> Set[int]:
        """
        Expand a list of department IDs to include all their children.

        Business rule: If user is assigned to a parent, they should see all children.
        If assigned to children only, they see only those children.

        Args:
            session: Database session
            department_ids: List of assigned department IDs

        Returns:
            Set of department IDs including all descendants
        """
        if not department_ids:
            return set()

        dept_map = await self.get_all_with_hierarchy(session)
        expanded = set(department_ids)

        # For each assigned department, add all its children
        for dept_id in department_ids:
            if dept_id in dept_map:
                # Recursively collect all children
                def collect_children(pid: int):
                    for d_id, info in dept_map.items():
                        if info["parent_id"] == pid:
                            expanded.add(d_id)
                            collect_children(d_id)

                collect_children(dept_id)

        return expanded

    async def get_top_level_parent_id(
        self, session: AsyncSession, department_id: int
    ) -> int:
        """
        Get the top-level parent ID for a department.

        Args:
            session: Database session
            department_id: ID of the department

        Returns:
            ID of the top-level parent, or the same ID if already top-level
        """
        dept_map = await self.get_all_with_hierarchy(session)

        current_id = department_id
        while current_id in dept_map:
            parent_id = dept_map[current_id]["parent_id"]
            if parent_id is None:
                return current_id
            current_id = parent_id

        return department_id
