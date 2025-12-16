"""
Department Endpoints - Department management.
"""

from typing import List

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_session
from api.schemas import (
    DepartmentCreate,
    DepartmentResponse,
    DepartmentUpdate,
)
from api.services import DepartmentService
from utils.security import require_admin, require_authenticated
from core.exceptions import (
    NotFoundError,
    ConflictError,
    ValidationError,
    DatabaseError,
)

router = APIRouter(prefix="/departments", tags=["departments"])


@router.post("", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED)
async def create_department(
    department_create: DepartmentCreate,
    session: AsyncSession = Depends(get_session),
    payload: dict = Depends(require_admin),
):
    """Create a new department. Requires Admin role."""
    service = DepartmentService()
    try:
        department = await service.create_department(session,
            name=department_create.name,
            description=getattr(department_create, "description", None),
        )
        return department
    except (ConflictError, ValidationError, DatabaseError):
        raise


@router.get("/{department_id}", response_model=DepartmentResponse)
async def get_department(
    department_id: int,
    session: AsyncSession = Depends(get_session),
    payload: dict = Depends(require_authenticated),
):
    """Get a department by ID. Requires authentication."""
    service = DepartmentService()
    try:
        department = await service.get_department(session, department_id)
        return department
    except NotFoundError:
        raise



@router.get("", response_model=List[DepartmentResponse])
async def list_departments(
    page: int = 1,
    per_page: int = 25,
    session: AsyncSession = Depends(get_session),
    payload: dict = Depends(require_authenticated),
):
    """List all departments. Requires authentication."""
    service = DepartmentService()
    departments, total = await service.list_departments(session, page=page, per_page=per_page)
    return departments


@router.put("/{department_id}", response_model=DepartmentResponse)
async def update_department(
    department_id: int,
    department_update: DepartmentUpdate,
    session: AsyncSession = Depends(get_session),
    payload: dict = Depends(require_admin),
):
    """Update a department. Requires Admin role."""
    service = DepartmentService()
    try:
        department = await service.update_department(session,
            department_id=department_id,
            name=getattr(department_update, "name", None),
            description=getattr(department_update, "description", None),
        )
        return department
    except (NotFoundError, ConflictError, DatabaseError):
        raise



@router.delete("/{department_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_department(
    department_id: int,
    session: AsyncSession = Depends(get_session),
    payload: dict = Depends(require_admin),
):
    """Delete a department. Requires Admin role."""
    service = DepartmentService()
    try:
        await service.delete_department(session, department_id)
    except NotFoundError:
        raise