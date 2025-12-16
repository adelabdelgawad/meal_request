"""Employee Repository."""

from typing import List, Optional, Tuple, Dict
from collections import defaultdict

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import DatabaseError, NotFoundError
from db.models import Employee, Department
from utils.app_schemas import RequestsPageRecord
from api.schemas.employee_schemas import DepartmentNode, EmployeeRecord


class EmployeeRepository:
    """Repository for Employee entity."""

    def __init__(self):
        pass

    async def create(self, session: AsyncSession, employee: Employee) -> Employee:
        try:
            session.add(employee)
            await session.flush()
            return employee
        except Exception as e:
            await session.rollback()
            raise DatabaseError(f"Failed to create employee: {str(e)}")

    async def get_by_id(self, session: AsyncSession, employee_id: int) -> Optional[Employee]:
        result = await session.execute(
            select(Employee).where(Employee.id == employee_id)
        )
        return result.scalar_one_or_none()

    async def get_by_code(self, session: AsyncSession, code: int) -> Optional[Employee]:
        result = await session.execute(
            select(Employee).where(Employee.code == code)
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        session: AsyncSession,
        page: int = 1,
        per_page: int = 25,
        is_active: Optional[bool] = None,
        department_id: Optional[int] = None,
    ) -> Tuple[List[Employee], int]:
        from core.pagination import calculate_offset

        query = select(Employee)

        if is_active is not None:
            query = query.where(Employee.is_active == is_active)
        if department_id is not None:
            query = query.where(Employee.department_id == department_id)

        # Optimized count query


        count_query = select(func.count()).select_from((query).subquery())


        count_result = await session.execute(count_query)


        total = count_result.scalar() or 0

        offset = calculate_offset(page, per_page)
        result = await session.execute(
            query.offset(offset).limit(per_page)
        )
        return result.scalars().all(), total

    async def update(self, session: AsyncSession, employee_id: int, employee_data: dict) -> Employee:
        employee = await self.get_by_id(session, employee_id)
        if not employee:
            raise NotFoundError(entity="Employee", identifier=employee_id)

        try:
            for key, value in employee_data.items():
                if value is not None and hasattr(employee, key):
                    setattr(employee, key, value)

            await session.flush()
            return employee
        except Exception as e:
            await session.rollback()
            raise DatabaseError(f"Failed to update employee: {str(e)}")

    async def delete(self, session: AsyncSession, employee_id: int) -> None:
        employee = await self.get_by_id(session, employee_id)
        if not employee:
            raise NotFoundError(entity="Employee", identifier=employee_id)

        employee.is_active = False
        await session.flush()

    # Specialized CRUD compatibility methods
    async def get_active_employees(self, session: AsyncSession) -> Optional[List[Employee]]:
        """Get all active employees."""
        result = await session.execute(
            select(Employee).where(Employee.is_active)
        )
        return result.scalars().all()

    async def deactivate_all(self, session: AsyncSession) -> bool:
        """Deactivate all employees (set is_active to False)."""
        try:
            stmt = update(Employee).values(is_active=False)
            await session.execute(stmt)
            await session.flush()
            return True
        except Exception as e:
            await session.rollback()
            raise DatabaseError(f"Failed to deactivate all employees: {str(e)}")

    async def read_employees_for_request_page(
        self, session: AsyncSession
    ) -> Optional[List[DepartmentNode]]:
        """Fetch active employees grouped hierarchically by department."""
        stmt = (
            select(
                Employee.id,
                Employee.code,
                Employee.name_en,
                Employee.name_ar,
                Employee.title,
                Department.id.label("department_id"),
                Department.name_en.label("department_en"),
                Department.name_ar.label("department_ar"),
                Department.parent_id,
            )
            .join(Department, Employee.department)
            .where(Employee.is_active)
        )

        try:
            result = await session.execute(stmt)
            rows = result.fetchall()

            if not rows:
                return None

            # Group employees by department_id
            dept_employees = defaultdict(list)
            dept_info = {}  # Map department_id to department metadata

            for row in rows:
                dept_id = row.department_id
                dept_employees[dept_id].append(
                    EmployeeRecord(
                        id=row.id,
                        code=row.code,
                        name_en=row.name_en,
                        name_ar=row.name_ar,
                        title=row.title,
                        department_id=dept_id,
                    )
                )
                dept_info[dept_id] = {
                    "name_en": row.department_en,
                    "name_ar": row.department_ar,
                    "parent_id": row.parent_id,
                }

            # Also fetch departments that have no active employees but have children
            # This ensures parent departments appear even if they have no direct employees
            dept_stmt = select(
                Department.id,
                Department.name_en,
                Department.name_ar,
                Department.parent_id,
            )
            dept_result = await session.execute(dept_stmt)
            dept_rows = dept_result.fetchall()

            for row in dept_rows:
                dept_id = row.id
                if dept_id not in dept_info:
                    dept_info[dept_id] = {
                        "name_en": row.name_en,
                        "name_ar": row.name_ar,
                        "parent_id": row.parent_id,
                    }

            # Build hierarchical structure
            # 1. Create all department nodes
            dept_nodes = {}
            for dept_id, info in dept_info.items():
                dept_nodes[dept_id] = DepartmentNode(
                    id=dept_id,
                    name_en=info["name_en"],
                    name_ar=info["name_ar"],
                    employees=dept_employees.get(dept_id, []),
                    children=[],
                )

            # 2. Link children to parents
            top_level = []
            for dept_id, node in dept_nodes.items():
                parent_id = dept_info[dept_id]["parent_id"]
                if parent_id and parent_id in dept_nodes:
                    # Add as child to parent
                    dept_nodes[parent_id].children.append(node)
                else:
                    # Top-level department (no parent or parent not found)
                    top_level.append(node)

            return top_level if top_level else None

        except Exception as e:
            raise DatabaseError(
                f"Failed to read employees for request page: {str(e)}"
            )

    async def read_employees_for_request_page_flat(
        self, session: AsyncSession, department_ids: Optional[List[int]] = None
    ) -> Optional[Dict[str, List[RequestsPageRecord]]]:
        """
        Fetch active employees grouped by top-level parent department.

        Args:
            session: Database session
            department_ids: Optional list of department IDs to filter by.
                           If None or empty, returns all employees.
                           If provided, only returns employees from those departments.

        Returns:
            Dict mapping parent department name to list of employees
        """
        # Fetch all employees with their department info
        emp_stmt = (
            select(
                Employee.id,
                Employee.code,
                Employee.name_en,
                Employee.name_ar,
                Employee.title,
                Department.id.label("department_id"),
                Department.name_en.label("department_en"),
                Department.name_ar.label("department_ar"),
                Department.parent_id,
            )
            .join(Department, Employee.department)
            .where(Employee.is_active)
        )

        # Apply department filter if provided
        if department_ids:
            emp_stmt = emp_stmt.where(Department.id.in_(department_ids))

        # Fetch all departments to build parent hierarchy
        dept_stmt = select(
            Department.id,
            Department.name_en,
            Department.name_ar,
            Department.parent_id,
        )

        try:
            # Get employees
            emp_result = await session.execute(emp_stmt)
            emp_rows = emp_result.fetchall()

            if not emp_rows:
                return None

            # Get all departments
            dept_result = await session.execute(dept_stmt)
            dept_rows = dept_result.fetchall()

            # Build department hierarchy map
            dept_map = {
                row.id: {
                    "id": row.id,
                    "name_en": row.name_en,
                    "name_ar": row.name_ar,
                    "parent_id": row.parent_id,
                }
                for row in dept_rows
            }

            # Helper function to find top-level parent
            def find_top_level_parent(dept_id: int, visited=None) -> dict:
                """Recursively find the top-level parent department."""
                if visited is None:
                    visited = set()

                # Detect circular reference
                if dept_id in visited:
                    return None

                visited.add(dept_id)

                dept = dept_map.get(dept_id)
                if not dept:
                    return None

                # If no parent, this is the top-level
                if not dept["parent_id"]:
                    return dept

                # Recursively find parent
                parent = find_top_level_parent(dept["parent_id"], visited)
                return parent if parent else dept

            # Group employees by top-level parent department
            department_employees = defaultdict(list)

            for row in emp_rows:
                try:
                    # Find the top-level parent for this employee's department
                    top_parent = find_top_level_parent(row.department_id)

                    if top_parent:
                        # Create employee record
                        record = RequestsPageRecord(
                            id=row.id,
                            code=row.code,
                            name_en=row.name_en,
                            name_ar=row.name_ar,
                            title=row.title,
                            department_id=row.department_id,
                            department_en=row.department_en,
                            department_ar=row.department_ar,
                        )

                        # Group by top-level parent's English name
                        department_employees[top_parent["name_en"]].append(record)
                except Exception as row_error:
                    # Log the error but continue processing other employees
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(
                        f"Error processing employee {getattr(row, 'id', 'unknown')}: {row_error}",
                        exc_info=True
                    )
                    continue

            return dict(department_employees) if department_employees else None

        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error in read_employees_for_request_page_flat: {str(e)}", exc_info=True)
            raise DatabaseError(
                f"Failed to read employees for request page (flat): {str(e)}"
            )

    # Bulk Operations
    async def bulk_create(self, session: AsyncSession, employees: List[Employee]) -> List[Employee]:
        """
        Create multiple employees in a single operation.

        Args:
            session: Database session
            employees: List of Employee instances to create

        Returns:
            List of created employees

        Raises:
            DatabaseError: If database operation fails
        """
        try:
            session.add_all(employees)
            await session.flush()
            return employees
        except Exception as e:
            await session.rollback()
            raise DatabaseError(f"Failed to bulk create employees: {str(e)}")

    async def bulk_update_status(
        self,
        session: AsyncSession,
        employee_ids: List[int],
        is_active: bool,
    ) -> int:
        """
        Update active status for multiple employees in a single operation.

        Args:
            session: Database session
            employee_ids: List of employee IDs to update
            is_active: New active status

        Returns:
            Number of employees updated

        Raises:
            DatabaseError: If database operation fails
        """
        try:
            stmt = (
                update(Employee)
                .where(Employee.id.in_(employee_ids))
                .values(is_active=is_active)
            )
            result = await session.execute(stmt)
            await session.flush()
            return result.rowcount
        except Exception as e:
            await session.rollback()
            raise DatabaseError(f"Failed to bulk update employee status: {str(e)}")

    async def bulk_delete(self, session: AsyncSession, employee_ids: List[int]) -> int:
        """
        Soft delete multiple employees in a single operation.

        Args:
            session: Database session
            employee_ids: List of employee IDs to delete

        Returns:
            Number of employees deleted

        Raises:
            DatabaseError: If database operation fails
        """
        try:
            stmt = (
                update(Employee)
                .where(Employee.id.in_(employee_ids))
                .values(is_active=False)
            )
            result = await session.execute(stmt)
            await session.flush()
            return result.rowcount
        except Exception as e:
            await session.rollback()
            raise DatabaseError(f"Failed to bulk delete employees: {str(e)}")
