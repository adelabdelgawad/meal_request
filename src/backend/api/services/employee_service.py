"""Employee Service - Business logic for employee management."""

from typing import Dict, List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from api.repositories.employee_repository import EmployeeRepository
from api.schemas.employee_schemas import DepartmentNode
from core.exceptions import NotFoundError
from db.model import Employee
from utils.app_schemas import RequestsPageRecord


class EmployeeService:
    """Service for employee management operations."""

    def __init__(self, session: AsyncSession):
        """Initialize service."""
        self.session = session
        self._repo = EmployeeRepository(session)

    async def create_employee(
        self,
        id: int,
        code: int,
        department_id: int,
        name_en: Optional[str] = None,
        name_ar: Optional[str] = None,
        title: Optional[str] = None,
    ) -> Employee:
        """
        Create a new employee or update existing one (for replication).

        Args:
            id: HRIS Employee ID (used as primary key)
            code: Unique employee code
            department_id: ID of department
            name_en: Optional employee name in English
            name_ar: Optional employee name in Arabic
            title: Optional job title

        Returns:
            Created or updated Employee

        Raises:
            ConflictError: If employee code already exists (in strict mode)
        """
        # Check if employee already exists by ID
        existing = await self._repo.get_by_id(id)
        if existing:
            # Update existing employee instead of raising error (for replication)
            update_data = {
                "code": code,
                "department_id": department_id,
                "name_en": name_en,
                "name_ar": name_ar,
                "title": title,
                "is_active": True,  # Reactivate if was deactivated
            }

            return await self._repo.update(
                existing.id,
                update_data,
            )

        employee = Employee(
            id=id,
            code=code,
            department_id=department_id,
            name_en=name_en,
            name_ar=name_ar,
            title=title,
            is_active=True,
        )

        return await self._repo.create(employee)

    async def get_employee(self, employee_id: int) -> Employee:
        """Get an employee by ID."""
        employee = await self._repo.get_by_id(employee_id)
        if not employee:
            raise NotFoundError(entity="Employee", identifier=employee_id)
        return employee

    async def get_employee_by_code(self, session: AsyncSession, code: int) -> Employee:
        """Get an employee by code."""
        employee = await self._repo.get_by_code(session, code)
        if not employee:
            raise NotFoundError(entity="Employee", identifier=code)
        return employee

    async def list_employees(
        self,
        page: int = 1,
        per_page: int = 25,
        is_active: Optional[bool] = None,
        department_id: Optional[int] = None,
    ) -> Tuple[List[Employee], int]:
        """List employees with optional filtering."""
        return await self._repo.list(
            page=page,
            per_page=per_page,
            is_active=is_active,
            department_id=department_id,
        )

    async def update_employee(
        self,
        employee_id: int,
        name_en: Optional[str] = None,
        name_ar: Optional[str] = None,
        title: Optional[str] = None,
        is_active: Optional[bool] = None,
        department_id: Optional[int] = None,
    ) -> Employee:
        """Update an employee."""
        update_data = {}
        if name_en is not None:
            update_data["name_en"] = name_en
        if name_ar is not None:
            update_data["name_ar"] = name_ar
        if title is not None:
            update_data["title"] = title
        if is_active is not None:
            update_data["is_active"] = is_active
        if department_id is not None:
            update_data["department_id"] = department_id

        return await self._repo.update(employee_id, update_data)

    async def deactivate_employee(self, employee_id: int) -> None:
        """Deactivate an employee (soft delete)."""
        await self._repo.delete(employee_id)

    async def get_active_employees_grouped_flat(
        self, department_ids: Optional[List[int]] = None
    ) -> Optional[Dict[str, List[RequestsPageRecord]]]:
        """
        Get active employees grouped by department name (flat structure).

        Args:
            department_ids: Optional list of department IDs to filter by.
                           If None or empty, returns all employees.
                           If provided, only returns employees from those departments.

        Returns:
            Dict mapping parent department name to list of employees
        """
        return await self._repo.read_employees_for_request_page_flat(
            department_ids=department_ids
        )

    async def get_active_employees_grouped_hierarchical(
        self,
    ) -> Optional[List[DepartmentNode]]:
        """Get active employees grouped hierarchically by department."""
        return await self._repo.read_employees_for_request_page()
