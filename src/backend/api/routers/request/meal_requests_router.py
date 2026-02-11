"""
Meal Request Endpoints - Meal request management and tracking.
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, status
from core.dependencies import SessionDep

from core.dependencies import SessionDep, CurrentUserDep, ActiveUserDep get_session
from db.hris_database import get_hris_session
from api.schemas import (
    MealTypeCreate,
    MealTypeResponse,
    MealTypeUpdate,
    MealRequestStatusCreate,
    MealRequestStatusResponse,
    MealRequestCreate,
    MealRequestResponse,
    MealRequestUpdate,
    MealRequestLineCreate,
    MealRequestLineResponse,
    MealRequestLineUpdate,
)
from api.services import (
    MealTypeService,
    MealRequestStatusService,
    MealRequestService,
)
from core.exceptions import (
    NotFoundError,
    ConflictError,
    ValidationError,
    DatabaseError,
)

router = APIRouter(prefix="/request/my-requests", tags=["request-my-requests"])


# Meal Type Endpoints
@router.post(
    "/types", response_model=MealTypeResponse, status_code=status.HTTP_201_CREATED
)
async def create_meal_type(
    meal_type_create: MealTypeCreate,
    session: SessionDep,
):
    """Create a new meal type."""
    service = MealTypeService(session)
    try:
        meal_type = await service.create_meal_type(
            session,
            name=meal_type_create.name,
            description=getattr(meal_type_create, "description", None),
        )
        return meal_type
    except (ConflictError, ValidationError, DatabaseError):
        raise


@router.get("/types/{type_id}", response_model=MealTypeResponse)
async def get_meal_type(
    type_id: int,
    session: SessionDep,
):
    """Get a meal type by ID."""
    service = MealTypeService(session)
    try:
        meal_type = await service.get_meal_type(session, type_id)
        return meal_type
    except NotFoundError:
        raise


@router.get("/types", response_model=List[MealTypeResponse])
async def list_meal_types(
    page: int = 1,
    per_page: int = 25,
    session: SessionDep,
):
    """List all meal types."""
    service = MealTypeService(session)
    meal_types, total = await service.list_meal_types(
        session, page=page, per_page=per_page
    )
    return meal_types


@router.put("/types/{type_id}", response_model=MealTypeResponse)
async def update_meal_type(
    type_id: int,
    meal_type_update: MealTypeUpdate,
    session: SessionDep,
):
    """Update a meal type."""
    service = MealTypeService(session)
    try:
        meal_type = await service.update_meal_type(
            session,
            type_id=type_id,
            name=meal_type_update.name,
            description=getattr(meal_type_update, "description", None),
        )
        return meal_type
    except (NotFoundError, ConflictError, DatabaseError):
        raise


@router.delete("/types/{type_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_meal_type(
    type_id: int,
    session: SessionDep,
):
    """Delete a meal type."""
    service = MealTypeService(session)
    try:
        await service.delete_meal_type(session, type_id)
    except NotFoundError:
        raise


# Meal Request Status Endpoints
@router.post(
    "/statuses",
    response_model=MealRequestStatusResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_meal_request_status(
    status_create: MealRequestStatusCreate,
    session: SessionDep,
):
    """Create a new meal request status."""
    service = MealRequestStatusService(session)
    try:
        status_obj = await service.create_meal_request_status(
            session,
            name=status_create.name,
            description=getattr(status_create, "description", None),
        )
        return status_obj
    except (ConflictError, ValidationError, DatabaseError):
        raise


@router.get("/statuses/{status_id}", response_model=MealRequestStatusResponse)
async def get_meal_request_status(
    status_id: int,
    session: SessionDep,
):
    """Get a meal request status by ID."""
    service = MealRequestStatusService(session)
    try:
        status_obj = await service.get_meal_request_status(session, status_id)
        return status_obj
    except NotFoundError:
        raise


@router.get("/statuses", response_model=List[MealRequestStatusResponse])
async def list_meal_request_statuses(
    page: int = 1,
    per_page: int = 25,
    session: SessionDep,
):
    """List all meal request statuses."""
    service = MealRequestStatusService(session)
    statuses, total = await service.list_meal_request_statuses(
        session, page=page, per_page=per_page
    )
    return statuses


# Meal Request Endpoints
@router.post(
    "", response_model=MealRequestResponse, status_code=status.HTTP_201_CREATED
)
async def create_meal_request(
    request_create: MealRequestCreate,
    session: SessionDep,
):
    """Create a new meal request."""
    service = MealRequestService(session)
    try:
        meal_request = await service.create_request(
            session,
            requester_id=request_create.requester_id,
            meal_type_id=request_create.meal_type_id,
            notes=getattr(request_create, "notes", None),
        )
        return meal_request
    except (NotFoundError, ValidationError, DatabaseError):
        raise


@router.get("/{request_id}", response_model=MealRequestResponse)
async def get_meal_request(
    request_id: int,
    session: SessionDep,
):
    """Get a meal request by ID."""
    service = MealRequestService(session)
    try:
        meal_request = await service.get_request(session, request_id)
        return meal_request
    except NotFoundError:
        raise


@router.get("", response_model=List[MealRequestResponse])
async def list_meal_requests(
    page: int = 1,
    per_page: int = 25,
    requester_id: Optional[UUID] = None,
    status_id: Optional[int] = None,
    meal_type_id: Optional[int] = None,
    session: SessionDep,
):
    """List meal requests with optional filtering."""
    service = MealRequestService(session)
    requests, total = await service.list_requests(
        session,
        page=page,
        per_page=per_page,
        requester_id=requester_id,
        status_id=status_id,
        meal_type_id=meal_type_id,
    )
    return requests


@router.put("/{request_id}", response_model=MealRequestResponse)
async def update_meal_request(
    request_id: int,
    request_update: MealRequestUpdate,
    session: SessionDep,
):
    """Update a meal request."""
    service = MealRequestService(session)
    try:
        # Update status if provided
        if hasattr(request_update, "status_id") and request_update.status_id:
            meal_request = await service.update_request_status(
                session,
                request_id=request_id,
                status_id=request_update.status_id,
            )
        return meal_request
    except (NotFoundError, ValidationError, DatabaseError):
        raise


@router.delete("/{request_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_meal_request(
    request_id: int,
    session: SessionDep,
):
    """Delete a meal request."""
    # Not implemented - requests shouldn't be deleted, only status changed


# Meal Request Line Endpoints
@router.post(
    "/{request_id}/lines",
    response_model=MealRequestLineResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_meal_request_line(
    request_id: int,
    line_create: MealRequestLineCreate,
    session: SessionDep,
    hris_session: AsyncSession = Depends(get_hris_session),
):
    """
    Add a line item to a meal request.

    This endpoint automatically fetches the employee's sign-in time from the HRIS
    TMS_Attendance table (SignTypeID = 1) to populate the attendance_time field.
    This enables real-time acceptance/rejection based on actual attendance.
    """
    service = MealRequestService(session)
    try:
        line = await service.add_line_to_request(
            session=session,
            request_id=request_id,
            employee_id=line_create.employee_id,
            # department_id is auto-populated from employee record
            attendance_time=getattr(line_create, "attendance_time", None),
            shift_hours=getattr(line_create, "shift_hours", None),
            notes=getattr(line_create, "notes", None),
            hris_session=hris_session,
        )
        return line
    except (NotFoundError, ValidationError, DatabaseError):
        raise


@router.get("/{request_id}/lines", response_model=List[MealRequestLineResponse])
async def get_meal_request_lines(
    request_id: int,
    session: SessionDep,
):
    """Get all lines for a meal request."""
    service = MealRequestService(session)
    try:
        lines = await service.get_request_lines(session, request_id)
        return lines
    except NotFoundError:
        raise


@router.put("/{request_id}/lines/{line_id}", response_model=MealRequestLineResponse)
async def update_meal_request_line(
    request_id: int,
    line_id: int,
    line_update: MealRequestLineUpdate,
    session: SessionDep,
):
    """Update a meal request line."""
    service = MealRequestService(session)
    try:
        line = await service.update_line(
            session,
            line_id=line_id,
            is_accepted=getattr(line_update, "is_accepted", None),
            notes=getattr(line_update, "notes", None),
        )
        return line
    except (NotFoundError, ValidationError, DatabaseError):
        raise


@router.delete("/{request_id}/lines/{line_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_meal_request_line(
    request_id: int,
    line_id: int,
    session: SessionDep,
):
    """Delete a meal request line."""
    service = MealRequestService(session)
    try:
        await service.delete_request_line(session, line_id)
    except NotFoundError:
        raise
