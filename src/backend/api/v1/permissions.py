"""
Permission Management Endpoints - Manage user roles and permissions.
"""

import logging
import traceback
from typing import List, Optional

import pytz
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_session, parse_accept_language
from api.services import LogPermissionService, RoleService, UserService
from core.sessions import verify_refresh_token
from db.schemas import (
    LogPermissionCreate,
    Role,
    RolePermissionCreate,
    UserCreate,
)
from settings import settings
from utils.active_directory import LDAPAuthenticator
from utils.app_schemas import (
    DomainAccount,
    RolePermissionResponse,
    UpdateAccountPermissionRequest,
    UserCreateRequest,
    UserUpdateRequest,
)
from utils.ldap import get_user_attributes
from utils.security import require_admin

# Initialize logger and timezone
logger = logging.getLogger(__name__)
cairo_tz = pytz.timezone("Africa/Cairo")

# Define API router
router = APIRouter(prefix="/permissions", tags=["permissions"])
active_directory = LDAPAuthenticator()

# Initialize services
user_service = UserService()
role_service = RoleService()
log_permission_service = LogPermissionService()


@router.get("/", response_model=Optional[List[RolePermissionResponse]])
async def read_permissions_endpoint(
    session: AsyncSession = Depends(get_session),
    payload: dict = Depends(require_admin),
) -> Optional[List[RolePermissionResponse]]:
    """
    Retrieve all account permissions with associated usernames and role IDs.
    Requires Admin role.
    """
    try:
        accounts_with_permissions = (
            await role_service.get_all_role_permissions(session)
        )
        if accounts_with_permissions:
            return [
                RolePermissionResponse(username=username, role_ids=role_ids)
                for username, role_ids in accounts_with_permissions
            ]
        return None
    except HTTPException as http_exc:
        logger.error(
            f"HTTP Exception during permissions retrieval: {
                     http_exc.detail}"
        )
        raise http_exc
    except Exception as e:
        logger.error("Unexpected error during account permissions retrieval.")
        logger.error(f"Details: {e}")
        logger.debug(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving account permissions.",
        )


@router.get("/roles", response_model=Optional[List[Role]])
async def read_role_endpoint(
    request: Request,
    session: AsyncSession = Depends(get_session),
    payload: dict = Depends(require_admin),
) -> Optional[List[Role]]:
    """
    Retrieve all available roles in the system with bilingual support.
    Returns role names and descriptions in the requested locale.
    Requires Admin role.

    Locale resolution:
    1. JWT refresh token payload (authenticated users, zero DB queries)
    2. Accept-Language header
    3. Default locale
    """
    try:
        # Determine locale (zero DB queries!)
        locale = settings.DEFAULT_LOCALE

        # Priority 1: Try JWT payload (no DB query!)
        try:
            refresh_token = request.cookies.get(settings.SESSION_COOKIE_NAME)
            if refresh_token:
                payload = verify_refresh_token(refresh_token)
                if payload and "locale" in payload:
                    locale = payload["locale"]
        except Exception:
            pass

        # Priority 2: Accept-Language header
        if locale == settings.DEFAULT_LOCALE:
            accept_language = request.headers.get("accept-language")
            if accept_language:
                languages = parse_accept_language(accept_language)
                for lang_code, _ in languages:
                    if lang_code in settings.SUPPORTED_LOCALES:
                        locale = lang_code
                        break

        roles = await role_service.get_all_roles(session)
        if not roles:
            return None

        # Count users per role
        from sqlalchemy import func, select

        from db.models import RolePermission

        user_counts_query = select(
            RolePermission.role_id,
            func.count(RolePermission.user_id).label("count"),
        ).group_by(RolePermission.role_id)
        user_counts_result = await session.execute(user_counts_query)
        user_counts = {row.role_id: row.count for row in user_counts_result}

        # Convert to Pydantic models and add computed name/description fields
        result = []
        for role in roles:
            role_dict = Role.model_validate(role).model_dump()
            # Add computed fields based on locale
            role_dict["name"] = role.get_name(locale)
            role_dict["description"] = role.get_description(locale)
            # Add user count
            role_dict["total_users"] = user_counts.get(role.id, 0)
            result.append(Role(**role_dict))
        return result
    except HTTPException as http_exc:
        logger.error(
            f"HTTP Exception during role retrieval: {http_exc.detail}"
        )
        raise http_exc
    except Exception as e:
        logger.error("Unexpected error during role retrieval.")
        logger.error(f"Details: {e}")
        logger.debug(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving roles.",
        )


@router.put("/remove-role", response_model=UserUpdateRequest)
async def remove_role_permission_endpoint(
    body: UpdateAccountPermissionRequest,
    session: AsyncSession = Depends(get_session),
    payload: dict = Depends(require_admin),
) -> UserUpdateRequest:
    """
    Remove specified roles from a user account.
    Requires Admin role.
    """
    try:
        logger.info(f"Removing roles for user: {body.username}")
        account = await user_service.get_account_by_username(
            session, body.username
        )
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        removed_roles = []
        for role_id in body.removed_roles:
            if await role_service.delete_role_permission(
                session, user_id=account.id, role_id=role_id
            ):
                await log_permission_service.create_permission_log(
                    session,
                    LogPermissionCreate(
                        user_id=str(account.id),
                        role_id=role_id,
                        admin_id=body.requester_id,
                        action="Remove",
                        result="Successfully removed",
                        is_successful=True,
                    ),
                )
                removed_roles.append(role_id)

        if not removed_roles:
            logger.warning(f"No roles removed for user: {body.username}")

        return UserUpdateRequest(role_ids=removed_roles)
    except HTTPException as http_exc:
        logger.error(
            f"HTTP Exception during role removal for {
                     body.username}: {http_exc.detail}"
        )
        raise http_exc
    except Exception as e:
        logger.error(f"Error during role removal for user: {body.username}")
        logger.error(f"Details: {e}")
        logger.debug(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error occurred while removing roles.",
        )


@router.put("/add-role", response_model=UserUpdateRequest)
async def add_role_permission_endpoint(
    body: UpdateAccountPermissionRequest,
    session: AsyncSession = Depends(get_session),
    payload: dict = Depends(require_admin),
) -> UserUpdateRequest:
    """
    Add specified roles to a user account.
    Requires Admin role.
    """
    try:
        logger.info(f"Adding roles for user: {body.username}")
        account = await user_service.get_account_by_username(
            session, body.username
        )
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        added_roles = []
        for role_id in body.added_roles or []:
            role_permission = RolePermissionCreate(
                user_id=account.id, role_id=role_id
            )
            if await role_service.create_role_permission(
                session, role_permission
            ):
                await log_permission_service.create_permission_log(
                    session,
                    LogPermissionCreate(
                        user_id=str(account.id),
                        role_id=role_id,
                        admin_id=body.requester_id,
                        action="Add",
                        result="Successfully Added",
                        is_successful=True,
                    ),
                )
                added_roles.append(role_id)

        if not added_roles:
            logger.warning(f"No roles added for user: {body.username}")

        return UserUpdateRequest(role_ids=added_roles)
    except HTTPException as http_exc:
        logger.error(
            f"HTTP Exception during role addition for {
                     body.username}: {http_exc.detail}"
        )
        raise http_exc
    except Exception as e:
        logger.error(f"Error during role addition for user: {body.username}")
        logger.error(f"Details: {e}")
        logger.debug(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error occurred while adding roles.",
        )


@router.post("/users", response_model=UserCreateRequest)
async def create_user_endpoint(
    request: UserCreateRequest,
    session: AsyncSession = Depends(get_session),
    payload: dict = Depends(require_admin),
) -> UserCreateRequest:
    """
    Create a new user account with specified roles.
    Fetches email and title from Active Directory if available.
    Requires Admin role.
    """
    try:
        logger.info(
            f"Creating user: {request.username} with roles {
                    request.role_ids}"
        )

        # Fetch user attributes from Active Directory
        ad_attributes = await get_user_attributes(request.username)

        # Build user data with AD attributes if available
        user_data = {"username": request.username}
        if ad_attributes:
            if ad_attributes.mail:
                user_data["email"] = ad_attributes.mail
            if ad_attributes.display_name:
                user_data["full_name"] = ad_attributes.display_name
            if ad_attributes.title:
                user_data["title"] = ad_attributes.title
            logger.info(
                f"Fetched AD attributes for {request.username}: email={ad_attributes.mail}, title={ad_attributes.title}"
            )
        else:
            logger.warning(
                f"Could not fetch AD attributes for {request.username}"
            )

        new_user = UserCreate(**user_data)
        account = await user_service.create_account(session, new_user)
        if not account:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="User creation failed.",
            )

        for role_id in request.role_ids:
            role_permission = RolePermissionCreate(
                user_id=account.id, role_id=role_id
            )
            await role_service.create_role_permission(session, role_permission)

        logger.info(
            f"User {request.username} created successfully with roles {
                    request.role_ids}"
        )
        return request
    except HTTPException as http_exc:
        logger.error(
            f"HTTP Exception during user creation for {
                     request.username}: {http_exc.detail}"
        )
        raise http_exc
    except Exception as e:
        logger.error(
            f"Unexpected error during user creation for {
                     request.username}."
        )
        logger.error(f"Details: {e}")
        logger.debug(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error occurred while creating the user.",
        )


@router.get("/domain-users", response_model=List[DomainAccount])
async def read_domain_accounts_endpoint(
    request: Request, payload: dict = Depends(require_admin)
) -> Optional[List[DomainAccount]]:
    """
    Retrieve all domain user accounts from Active Directory.
    Requires Admin role.
    """
    try:
        domain_accounts = active_directory.get_domain_accounts()
        if domain_accounts:
            logger.info(f"Found {len(domain_accounts)} domain accounts.")
            return domain_accounts
        return None
    except HTTPException as http_exc:
        logger.error(
            f"HTTP Exception during Domain Accounts retrieval: {
                     http_exc.detail}"
        )
        raise http_exc
    except Exception as e:
        logger.error("Unexpected error during Domain Accounts retrieval")
        logger.error(f"Details: {e}")
        logger.debug(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving Domain Accounts.",
        )
