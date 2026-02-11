"""Meal Types API endpoints."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from core.dependencies import SessionDep, CurrentUserDep, ActiveUserDep get_session
from utils.security import require_admin, require_authenticated
from api.schemas.meal_type_schemas import (
    MealTypeCreate,
    MealTypeResponse,
    MealTypeUpdate,
)
from api.services.meal_type_service import MealTypeService
from api.services.log_configuration_service import LogConfigurationService
from core.exceptions import NotFoundError
from utils.app_schemas import PaginatedResponse

router = APIRouter(prefix="/setting/meal-type-setup", tags=["setting-meal-type-setup"])


@router.get("", response_model=List[MealTypeResponse])
async def get_meal_types(
    active_only: bool = True,
    session: SessionDep,
    payload: dict = Depends(require_authenticated),
):
    """
    Get all meal types. Requires authentication.

    Args:
        active_only: If True, only return active meal types (default: True)
        session: Database session

    Returns:
        List of meal types
    """
    service = MealTypeService(session)

    if active_only:
        meal_types = await service.get_active_meal_types(session)
    else:
        meal_types, _ = await service.list_meal_types(session, page=1, per_page=100)

    return meal_types


@router.get("/paginated", response_model=PaginatedResponse[MealTypeResponse])
async def get_meal_types_paginated(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    active_only: Optional[bool] = Query(None),
    session: SessionDep,
    payload: dict = Depends(require_authenticated),
):
    """
    Get paginated meal types with filtering. Requires authentication.

    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        active_only: Filter by active status
        session: Database session

    Returns:
        Paginated list of meal types with total count
    """
    service = MealTypeService(session)
    page = (skip // limit) + 1

    meal_types, total = await service.list_meal_types(
        session,
        page=page,
        per_page=limit,
        active_only=active_only if active_only is not None else False,
    )

    # Calculate counts for active/inactive
    all_meal_types, _ = await service.list_meal_types(
        session, page=1, per_page=1000, active_only=False
    )
    active_count = sum(1 for mt in all_meal_types if mt.is_active and not mt.is_deleted)
    inactive_count = sum(
        1 for mt in all_meal_types if not mt.is_active and not mt.is_deleted
    )

    return PaginatedResponse(
        items=meal_types,
        total=total,
        skip=skip,
        limit=limit,
        active_count=active_count,
        inactive_count=inactive_count,
    )


@router.get("/{meal_type_id}", response_model=MealTypeResponse)
async def get_meal_type(
    meal_type_id: int,
    session: SessionDep,
    payload: dict = Depends(require_authenticated),
):
    """
    Get a meal type by ID. Requires authentication.

    Args:
        meal_type_id: ID of the meal type
        session: Database session

    Returns:
        Meal type details
    """
    service = MealTypeService(session)

    try:
        meal_type = await service.get_meal_type(session, meal_type_id)
        return meal_type
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Meal type with ID {meal_type_id} not found",
        )


@router.post("", response_model=MealTypeResponse, status_code=status.HTTP_201_CREATED)
async def create_meal_type(
    meal_type_data: MealTypeCreate,
    session: SessionDep,
    payload: dict = Depends(require_admin),
):
    """
    Create a new meal type. Requires Admin role.

    Args:
        meal_type_data: Meal type creation data
        session: Database session

    Returns:
        Created meal type
    """
    service = MealTypeService(session)
    log_service = LogConfigurationService(session)

    try:
        meal_type = await service.create_meal_type(
            session,
            name_en=meal_type_data.name_en,
            name_ar=meal_type_data.name_ar,
            priority=meal_type_data.priority,
            created_by_id=meal_type_data.created_by_id,
        )

        await session.commit()
        await session.refresh(meal_type)

        # Log successful creation
        await log_service.log_configuration(
            session=session,
            admin_id=payload.get("user_id"),
            entity_type="meal_type",
            entity_id=str(meal_type.id),
            action="create",
            is_successful=True,
            new_value={
                "name_en": meal_type.name_en,
                "name_ar": meal_type.name_ar,
                "priority": meal_type.priority,
            },
        )

        return meal_type
    except Exception as e:
        # Log failed creation
        await log_service.log_configuration(
            session=session,
            admin_id=payload.get("user_id"),
            entity_type="meal_type",
            entity_id=None,
            action="create",
            is_successful=False,
            result={"error": str(e)},
        )
        raise


@router.put("/{meal_type_id}", response_model=MealTypeResponse)
async def update_meal_type(
    meal_type_id: int,
    meal_type_data: MealTypeUpdate,
    session: SessionDep,
    payload: dict = Depends(require_admin),
):
    """
    Update a meal type. Requires Admin role.

    Args:
        meal_type_id: ID of the meal type to update
        meal_type_data: Updated meal type data
        session: Database session

    Returns:
        Updated meal type
    """
    service = MealTypeService(session)
    log_service = LogConfigurationService(session)

    try:
        # Get current state for old_value
        old_meal_type = await service.get_meal_type(session, meal_type_id)
        old_values = {
            "name_en": old_meal_type.name_en,
            "name_ar": old_meal_type.name_ar,
            "priority": old_meal_type.priority,
            "is_active": old_meal_type.is_active,
        }

        # Update meal type
        meal_type = await service.update_meal_type(
            session,
            meal_type_id,
            name_en=meal_type_data.name_en,
            name_ar=meal_type_data.name_ar,
            priority=meal_type_data.priority,
            is_active=meal_type_data.is_active,
            updated_by_id=meal_type_data.updated_by_id,
        )

        await session.commit()
        await session.refresh(meal_type)

        # Log successful update
        await log_service.log_configuration(
            session=session,
            admin_id=payload.get("user_id"),
            entity_type="meal_type",
            entity_id=str(meal_type_id),
            action="update",
            is_successful=True,
            old_value=old_values,
            new_value={
                "name_en": meal_type.name_en,
                "name_ar": meal_type.name_ar,
                "priority": meal_type.priority,
                "is_active": meal_type.is_active,
            },
        )

        return meal_type
    except NotFoundError as e:
        # Log failed update
        await log_service.log_configuration(
            session=session,
            admin_id=payload.get("user_id"),
            entity_type="meal_type",
            entity_id=str(meal_type_id),
            action="update",
            is_successful=False,
            result={"error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Meal type with ID {meal_type_id} not found",
        )


@router.delete("/{meal_type_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_meal_type(
    meal_type_id: int,
    session: SessionDep,
    payload: dict = Depends(require_admin),
):
    """
    Soft delete a meal type. Requires Admin role.

    Args:
        meal_type_id: ID of the meal type to delete
        session: Database session

    Returns:
        No content
    """
    service = MealTypeService(session)
    log_service = LogConfigurationService(session)

    try:
        # Get meal type info before deletion
        meal_type = await service.get_meal_type(session, meal_type_id)
        meal_type_info = {
            "name_en": meal_type.name_en,
            "name_ar": meal_type.name_ar,
            "priority": meal_type.priority,
        }

        # Delete meal type
        await service.delete_meal_type(session, meal_type_id)
        await session.commit()

        # Log successful deletion
        await log_service.log_configuration(
            session=session,
            admin_id=payload.get("user_id"),
            entity_type="meal_type",
            entity_id=str(meal_type_id),
            action="delete",
            is_successful=True,
            old_value=meal_type_info,
        )
    except NotFoundError as e:
        # Log failed deletion
        await log_service.log_configuration(
            session=session,
            admin_id=payload.get("user_id"),
            entity_type="meal_type",
            entity_id=str(meal_type_id),
            action="delete",
            is_successful=False,
            result={"error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Meal type with ID {meal_type_id} not found",
        )
