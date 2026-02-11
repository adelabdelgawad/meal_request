"""
Employee Endpoints - Employee management.
"""

import logging
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, status
from core.dependencies import SessionDep
from sqlalchemy import select

from core.dependencies import SessionDep, CurrentUserDep, ActiveUserDep get_session
from api.schemas import (
    DepartmentAssignmentCreate,
    DepartmentAssignmentResponse,
    EmployeeCreate,
    EmployeeResponse,
    EmployeeUpdate,
)
from api.schemas.employee_schemas import DepartmentNode
from api.services import DepartmentAssignmentService, EmployeeService
from core.exceptions import (
    ConflictError,
    DatabaseError,
    NotFoundError,
    ValidationError,
)
from db.model import DepartmentAssignment
from utils.app_schemas import RequestsPageRecord
from utils.security import require_admin, require_requester_ordertaker_or_admin

router = APIRouter(prefix="/request/meal-request", tags=["request-meal-request"])
logger = logging.getLogger(__name__)


@router.post("", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
async def create_employee(
    employee_create: EmployeeCreate,
    session: SessionDep,
    payload: dict = Depends(require_admin),
):
    """Create a new employee. Requires Admin role."""
    service = EmployeeService(session)
    try:
        employee = await service.create_employee(
            session,
            id=employee_create.id,
            code=employee_create.code,
            department_id=employee_create.department_id,
            name_en=employee_create.name_en,
            name_ar=employee_create.name_ar,
            title=employee_create.title,
        )
        return employee
    except (ConflictError, ValidationError, DatabaseError):
        raise


@router.get("/grouped", response_model=Dict[str, List[RequestsPageRecord]])
async def get_employees_grouped(
    session: SessionDep,
    payload: dict = Depends(require_requester_ordertaker_or_admin),
):
    """
    Get all active employees grouped by department name (flat structure).
    Requires Requester, Ordertaker, or Admin role.

    Department visibility:
    - If the user has department assignments, only employees from those departments
      (and their children) are shown
    - If the user has NO department assignments, ALL employees are shown
    """
    service = EmployeeService(session)

    # Get user's expanded department IDs for visibility filtering
    user_id = payload.get("user_id") or payload.get("sub")
    department_ids = None

    if user_id:
        # Get department IDs from user's active department assignments
        dept_ids_result = await session.execute(
            select(DepartmentAssignment.department_id)
            .where(DepartmentAssignment.user_id == user_id)
            .where(DepartmentAssignment.is_active)
            .distinct()
        )
        user_dept_ids = [row[0] for row in dept_ids_result]
        if user_dept_ids:
            department_ids = user_dept_ids
            logger.info(
                f"User {user_id} can see departments from assignments: {department_ids}"
            )
        else:
            logger.info(f"User {user_id} has no department restrictions (sees all)")

    result = await service.get_active_employees_grouped_flat(
        session, department_ids=department_ids
    )
    print(result)
    return result or {}


@router.get("/grouped/hierarchy", response_model=List[DepartmentNode])
async def get_employees_grouped_hierarchy(
    session: SessionDep,
    payload: dict = Depends(require_requester_ordertaker_or_admin),
):
    """Get all active employees in hierarchical department structure. Requires Requester, Ordertaker, or Admin role."""
    service = EmployeeService(session)
    result = await service.get_active_employees_grouped_hierarchical(session)
    return result or []


@router.get("/{employee_id}", response_model=EmployeeResponse)
async def get_employee(
    employee_id: int,
    session: SessionDep,
    payload: dict = Depends(require_requester_ordertaker_or_admin),
):
    """Get an employee by ID. Requires Requester, Ordertaker, or Admin role."""
    service = EmployeeService(session)
    try:
        employee = await service.get_employee(session, employee_id)
        return employee
    except NotFoundError:
        raise


@router.get("", response_model=List[EmployeeResponse])
async def list_employees(
    page: int = 1,
    per_page: int = 25,
    is_active: Optional[bool] = None,
    department_id: Optional[int] = None,
    session: SessionDep,
    payload: dict = Depends(require_requester_ordertaker_or_admin),
):
    """List employees with optional filtering. Requires Requester, Ordertaker, or Admin role."""
    service = EmployeeService(session)
    employees, total = await service.list_employees(
        session,
        page=page,
        per_page=per_page,
        is_active=is_active,
        department_id=department_id,
    )
    return employees


@router.put("/{employee_id}", response_model=EmployeeResponse)
async def update_employee(
    employee_id: int,
    employee_update: EmployeeUpdate,
    session: SessionDep,
    payload: dict = Depends(require_admin),
):
    """Update an employee. Requires Admin role."""
    service = EmployeeService(session)
    try:
        employee = await service.update_employee(
            session,
            employee_id=employee_id,
            name_en=employee_update.name_en,
            name_ar=employee_update.name_ar,
            title=employee_update.title,
            is_active=employee_update.is_active,
            department_id=employee_update.department_id,
        )
        return employee
    except (NotFoundError, ValidationError, DatabaseError):
        raise


@router.delete("/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_employee(
    employee_id: int,
    session: SessionDep,
    payload: dict = Depends(require_admin),
):
    """Deactivate an employee. Requires Admin role."""
    service = EmployeeService(session)
    try:
        await service.deactivate_employee(session, employee_id)
    except NotFoundError:
        raise


# Department Assignment Endpoints
@router.post(
    "/{employee_id}/assignments",
    response_model=DepartmentAssignmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def assign_employee_to_department(
    employee_id: int,
    assignment_create: DepartmentAssignmentCreate,
    session: SessionDep,
    payload: dict = Depends(require_admin),
):
    """Assign an employee to a department. Requires Admin role."""
    service = DepartmentAssignmentService(session)
    try:
        assignment = await service.assign_user_to_department(
            session,
            user_id=assignment_create.user_id,
            department_id=assignment_create.department_id,
            is_primary=getattr(assignment_create, "is_primary", False),
        )
        return assignment
    except (ValidationError, DatabaseError):
        raise


@router.get(
    "/{employee_id}/assignments",
    response_model=List[DepartmentAssignmentResponse],
)
async def get_employee_assignments(
    employee_id: int,
    page: int = 1,
    per_page: int = 25,
    session: SessionDep,
    payload: dict = Depends(require_admin),
):
    """Get all assignments for an employee. Requires Admin role."""
    service = DepartmentAssignmentService(session)
    assignments, total = await service.list_assignments(
        session,
        page=page,
        per_page=per_page,
    )
    return assignments
