"""
Settings Endpoints - User settings management including department assignments.
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, status
from core.dependencies import SessionDep
from sqlalchemy import select

from core.dependencies import SessionDep, CurrentUserDep, ActiveUserDep get_session
from api.schemas._base import CamelModel
from core.exceptions import NotFoundError, ValidationError
from db.model import DepartmentAssignment, User, Department
from utils.security import require_admin

router = APIRouter(prefix="/setting/settings", tags=["setting-settings"])


# Response Schemas
class UserDepartmentsResponse(CamelModel):
    """Response for user department assignments."""

    user_id: str
    department_ids: List[int]


class DepartmentForAssignment(CamelModel):
    """Department info with assignment status."""

    id: int
    name_en: str
    name_ar: str
    is_assigned: bool


class UserDepartmentsDetailResponse(CamelModel):
    """Detailed response for user department assignments."""

    user_id: str
    user_name: str | None
    assigned_department_ids: List[int]
    departments: List[DepartmentForAssignment]


class UserDepartmentsUpdateRequest(CamelModel):
    """Request to update user department assignments."""

    department_ids: List[int]


# Endpoints
@router.get(
    "/users/{user_id}/departments",
    response_model=UserDepartmentsResponse,
)
async def get_user_departments(
    user_id: UUID,
    session: SessionDep,
    payload: dict = Depends(require_admin),
):
    """
    Get department IDs assigned to a user.

    Users with no assignments can see all departments.
    Users with assignments can only see those specific departments.
    """
    # Get active department assignments for the user
    result = await session.execute(
        select(DepartmentAssignment.department_id)
        .where(DepartmentAssignment.user_id == str(user_id))
        .where(DepartmentAssignment.is_active)
    )
    department_ids = [row[0] for row in result.all()]

    return UserDepartmentsResponse(
        user_id=str(user_id),
        department_ids=department_ids,
    )


@router.get(
    "/users/{user_id}/departments/detail",
    response_model=UserDepartmentsDetailResponse,
)
async def get_user_departments_detail(
    user_id: UUID,
    session: SessionDep,
    payload: dict = Depends(require_admin),
):
    """
    Get detailed department assignment information for a user.

    Returns all departments with assignment status for the user.
    """
    # Get user info
    user_result = await session.execute(select(User).where(User.id == str(user_id)))
    user = user_result.scalar_one_or_none()
    if not user:
        raise NotFoundError(entity="User", identifier=str(user_id))

    # Get assigned department IDs
    assignments_result = await session.execute(
        select(DepartmentAssignment.department_id)
        .where(DepartmentAssignment.user_id == str(user_id))
        .where(DepartmentAssignment.is_active)
    )
    assigned_department_ids = [row[0] for row in assignments_result.all()]

    # Get all departments
    departments_result = await session.execute(select(Department))
    all_departments = departments_result.scalars().all()

    # Build department list with assignment status
    departments = [
        DepartmentForAssignment(
            id=dept.id,
            name_en=dept.name_en,
            name_ar=dept.name_ar,
            is_assigned=(dept.id in assigned_department_ids),
        )
        for dept in all_departments
    ]

    return UserDepartmentsDetailResponse(
        user_id=str(user_id),
        user_name=user.username,
        assigned_department_ids=assigned_department_ids,
        departments=departments,
    )


@router.put(
    "/users/{user_id}/departments",
    response_model=UserDepartmentsResponse,
)
async def update_user_departments(
    user_id: UUID,
    request: UserDepartmentsUpdateRequest,
    session: SessionDep,
    payload: dict = Depends(require_admin),
):
    """
    Update department assignments for a user.

    Replaces all existing manual assignments with the provided list.
    Preserves HRIS-synced assignments.
    """
    # Verify user exists
    user_result = await session.execute(select(User).where(User.id == str(user_id)))
    user = user_result.scalar_one_or_none()
    if not user:
        raise NotFoundError(entity="User", identifier=str(user_id))

    # Verify all departments exist
    if request.department_ids:
        dept_result = await session.execute(
            select(Department.id).where(Department.id.in_(request.department_ids))
        )
        existing_dept_ids = {row[0] for row in dept_result.all()}
        missing_dept_ids = set(request.department_ids) - existing_dept_ids
        if missing_dept_ids:
            raise ValidationError(f"Departments not found: {missing_dept_ids}")

    # Remove existing manual assignments (keep HRIS-synced ones)
    await session.execute(
        select(DepartmentAssignment)
        .where(DepartmentAssignment.user_id == str(user_id))
        .where(not DepartmentAssignment.is_synced_from_hris)
    )
    manual_assignments = (
        (
            await session.execute(
                select(DepartmentAssignment)
                .where(DepartmentAssignment.user_id == str(user_id))
                .where(not DepartmentAssignment.is_synced_from_hris)
            )
        )
        .scalars()
        .all()
    )

    for assignment in manual_assignments:
        await session.delete(assignment)

    # Create new assignments
    admin_user_id = payload.get("user_id")
    for dept_id in request.department_ids:
        new_assignment = DepartmentAssignment(
            user_id=str(user_id),
            department_id=dept_id,
            is_synced_from_hris=False,
            is_active=True,
            created_by_id=admin_user_id,
        )
        session.add(new_assignment)

    await session.flush()

    # Get all active department IDs (including HRIS-synced)
    result = await session.execute(
        select(DepartmentAssignment.department_id)
        .where(DepartmentAssignment.user_id == str(user_id))
        .where(DepartmentAssignment.is_active)
    )
    all_department_ids = [row[0] for row in result.all()]

    return UserDepartmentsResponse(
        user_id=str(user_id),
        department_ids=all_department_ids,
    )


@router.delete(
    "/users/{user_id}/departments",
    status_code=status.HTTP_200_OK,
)
async def clear_user_departments(
    user_id: UUID,
    session: SessionDep,
    payload: dict = Depends(require_admin),
):
    """
    Clear all manual department assignments for a user.

    User will see all departments after this.
    Preserves HRIS-synced assignments.
    """
    # Verify user exists
    user_result = await session.execute(select(User).where(User.id == str(user_id)))
    user = user_result.scalar_one_or_none()
    if not user:
        raise NotFoundError(entity="User", identifier=str(user_id))

    # Delete manual assignments
    manual_assignments = (
        (
            await session.execute(
                select(DepartmentAssignment)
                .where(DepartmentAssignment.user_id == str(user_id))
                .where(not DepartmentAssignment.is_synced_from_hris)
            )
        )
        .scalars()
        .all()
    )

    for assignment in manual_assignments:
        await session.delete(assignment)

    await session.flush()

    return {"ok": True}
