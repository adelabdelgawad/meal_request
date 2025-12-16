"""
DomainUser Endpoints - CRUD operations for cached Active Directory users.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_session
from api.schemas import (
    DomainUserCreate,
    DomainUserListResponse,
    DomainUserResponse,
    DomainUserSyncResponse,
    DomainUserUpdate,
)
from api.services.domain_user_service import DomainUserService
from core.exceptions import ConflictError, DatabaseError, NotFoundError
from utils.security import limiter, require_admin

router = APIRouter(prefix="/domain-users", tags=["domain-users"])


@router.post("", response_model=DomainUserResponse, status_code=status.HTTP_201_CREATED)
async def create_domain_user(
    user_create: DomainUserCreate,
    session: AsyncSession = Depends(get_session),
    payload: dict = Depends(require_admin),
):
    """Create a new domain user entry. Requires Admin role."""
    service = DomainUserService()
    try:
        user = await service.create_domain_user(
            session,
            username=user_create.username,
            email=user_create.email,
            full_name=user_create.full_name,
            title=user_create.title,
            office=user_create.office,
            phone=user_create.phone,
            manager=user_create.manager,
        )
        return DomainUserResponse.model_validate(user)
    except (ConflictError, DatabaseError):
        raise


@router.get("/{user_id}", response_model=DomainUserResponse)
async def get_domain_user(
    user_id: int,
    session: AsyncSession = Depends(get_session),
    payload: dict = Depends(require_admin),
):
    """Get a domain user by ID. Requires Admin role."""
    service = DomainUserService()
    try:
        user = await service.get_domain_user(session, user_id)
        return DomainUserResponse.model_validate(user)
    except NotFoundError:
        raise


@router.get("/username/{username}", response_model=DomainUserResponse)
async def get_domain_user_by_username(
    username: str,
    session: AsyncSession = Depends(get_session),
    payload: dict = Depends(require_admin),
):
    """Get a domain user by username. Requires Admin role."""
    service = DomainUserService()
    try:
        user = await service.get_domain_user_by_username(session, username)
        return DomainUserResponse.model_validate(user)
    except NotFoundError:
        raise


@router.get("", response_model=DomainUserListResponse)
async def list_domain_users(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    q: Optional[str] = Query(None, description="Search by username or full name"),
    session: AsyncSession = Depends(get_session),
    payload: dict = Depends(require_admin),
):
    """
    List domain users with pagination and optional search.

    Query params:
    - page: Page number (1-indexed)
    - limit: Items per page (max 100)
    - q: Search term (matches username, full_name, or email)

    Requires Admin role.
    """
    service = DomainUserService()
    users, total = await service.list_domain_users(
        session,
        page=page,
        per_page=limit,
        search=q,
    )
    has_more = (page * limit) < total
    return DomainUserListResponse(
        items=[DomainUserResponse.model_validate(u) for u in users],
        total=total,
        page=page,
        limit=limit,
        has_more=has_more,
    )


@router.put("/{user_id}", response_model=DomainUserResponse)
async def update_domain_user(
    user_id: int,
    user_update: DomainUserUpdate,
    session: AsyncSession = Depends(get_session),
    payload: dict = Depends(require_admin),
):
    """Update a domain user's information. Requires Admin role."""
    service = DomainUserService()
    try:
        user = await service.update_domain_user(
            session,
            user_id=user_id,
            email=user_update.email,
            full_name=user_update.full_name,
            title=user_update.title,
            office=user_update.office,
            phone=user_update.phone,
            manager=user_update.manager,
        )
        return DomainUserResponse.model_validate(user)
    except (NotFoundError, DatabaseError):
        raise


@router.post("/upsert", response_model=DomainUserResponse)
async def upsert_domain_user(
    user_create: DomainUserCreate,
    session: AsyncSession = Depends(get_session),
    payload: dict = Depends(require_admin),
):
    """
    Create or update a domain user by username.

    Useful for syncing data from Active Directory.

    Requires Admin role.
    """
    service = DomainUserService()
    try:
        user = await service.upsert_domain_user(
            session,
            username=user_create.username,
            email=user_create.email,
            full_name=user_create.full_name,
            title=user_create.title,
            office=user_create.office,
            phone=user_create.phone,
            manager=user_create.manager,
        )
        return DomainUserResponse.model_validate(user)
    except DatabaseError:
        raise


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_domain_user(
    user_id: int,
    session: AsyncSession = Depends(get_session),
    payload: dict = Depends(require_admin),
):
    """Delete a domain user. Requires Admin role."""
    service = DomainUserService()
    try:
        await service.delete_domain_user(session, user_id)
    except NotFoundError:
        raise


@router.post("/bulk-upsert", response_model=List[DomainUserResponse])
async def bulk_upsert_domain_users(
    users_data: List[DomainUserCreate],
    session: AsyncSession = Depends(get_session),
    payload: dict = Depends(require_admin),
):
    """
    Bulk create or update domain users.

    Useful for batch syncing from Active Directory.

    Requires Admin role.
    """
    service = DomainUserService()
    try:
        # Convert Pydantic models to dicts
        data = [u.model_dump() for u in users_data]
        users = await service.bulk_upsert_domain_users(session, data)
        return [DomainUserResponse.model_validate(u) for u in users]
    except DatabaseError:
        raise


@router.post("/refresh", response_model=DomainUserSyncResponse)
@limiter.limit("1/30minutes")
async def refresh_domain_users(
    request: Request,
    session: AsyncSession = Depends(get_session),
    payload: dict = Depends(require_admin),
):
    """
    Refresh domain users from Active Directory.

    This endpoint:
    1. Fetches all enabled domain users from configured OUs (AD_ALLOWED_OUS)
    2. Deletes all existing records from domain_user table
    3. Inserts the fetched AD users into the database

    Rate limited to once every 30 minutes.

    Returns counts of deleted, created, and fetched records.

    Requires Admin role.
    """
    service = DomainUserService()
    try:
        result = await service.sync_from_active_directory(session)
        return DomainUserSyncResponse(
            deleted_count=result.deleted_count,
            created_count=result.created_count,
            ad_users_fetched=result.ad_users_fetched,
        )
    except DatabaseError:
        raise
