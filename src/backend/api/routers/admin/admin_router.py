"""
Admin Endpoints - System configuration and management.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, Request, status
from core.dependencies import SessionDep

from core.dependencies import SessionDep, CurrentUserDep, ActiveUserDep get_session, parse_accept_language
from api.schemas import (
    PageCreate,
    PageResponse,
    PageUpdate,
    PagePermissionCreate,
    PagePermissionResponse,
    EmailCreate,
    EmailResponse,
    EmailRoleCreate,
    EmailRoleResponse,
    UserMarkManualRequest,
    UserResponse,
    UserStatusOverrideRequest,
    UserStatusOverrideResponse,
)
from core.user_source_enum import UserSourceMetadata, get_all_user_sources
from api.services import (
    PageService,
    PagePermissionService,
    EmailService,
    EmailRoleService,
)
from core.exceptions import (
    NotFoundError,
    ConflictError,
    ValidationError,
    DatabaseError,
)
from core.sessions import verify_refresh_token
from core.config import settings
from utils.security import require_super_admin

router = APIRouter(prefix="/admin", tags=["admin"])


def get_locale_from_request(request: Request) -> str:
    """
    Extract locale from JWT refresh token or Accept-Language header.

    Zero DB queries! Returns locale for bilingual page name/description resolution.

    Args:
        request: FastAPI Request object

    Returns:
        Locale code (e.g., 'en', 'ar')
    """
    locale = settings.locale.default_locale

        # Priority 1: Try JWT payload (no DB query!)
        try:
            refresh_token = request.cookies.get(settings.session.cookie_name)
            if refresh_token:
                payload = verify_refresh_token(refresh_token)
                if payload and "locale" in payload:
                    return payload["locale"]
        except Exception:
            pass
        # Priority 2: Accept-Language header
        accept_language = request.headers.get("accept-language")
        if accept_language:
            languages = parse_accept_language(accept_language)
            for lang_code, _ in languages:
                if lang_code in settings.locale.supported_locales:
                    return lang_code
        return locale


# Page Endpoints
@router.post("/pages", response_model=PageResponse, status_code=status.HTTP_201_CREATED)
async def create_page(
    request: Request,
    page_create: PageCreate,
    session: SessionDep,
    _: dict = Depends(require_super_admin),
):
    """Requires Super Admin role. Create a new page with bilingual support and navigation fields."""
    service = PageService(session)
    locale = get_locale_from_request(request)
    try:
        page = await service.create_page(
            session,
            name_en=page_create.name_en,
            name_ar=page_create.name_ar,
            description_en=page_create.description_en,
            description_ar=page_create.description_ar,
            path=page_create.path,
            icon=page_create.icon,
            nav_type=page_create.nav_type,
            order=page_create.order,
            is_menu_group=page_create.is_menu_group,
            show_in_nav=page_create.show_in_nav,
            open_in_new_tab=page_create.open_in_new_tab,
            parent_id=page_create.parent_id,
            key=page_create.key,
        )
        # Add computed fields for backward compatibility
        response = PageResponse.model_validate(page)
        response.name = page.get_name(locale)
        response.description = page.get_description(locale)
        return response
    except (ConflictError, ValidationError, DatabaseError):
        raise


@router.get("/pages/{page_id}", response_model=PageResponse)
async def get_page(
    request: Request,
    page_id: int,
    session: SessionDep,
    _: dict = Depends(require_super_admin),
):
    """Requires Super Admin role. Get a page by ID with locale-aware name/description."""
    service = PageService(session)
    locale = get_locale_from_request(request)
    try:
        page = await service.get_page(session, page_id)
        # Add computed fields for backward compatibility
        response = PageResponse.model_validate(page)
        response.name = page.get_name(locale)
        response.description = page.get_description(locale)
        return response
    except NotFoundError:
        raise


@router.get("/pages", response_model=List[PageResponse])
async def list_pages(
    request: Request,
    page: int = 1,
    per_page: int = 25,
    session: SessionDep,
    _: dict = Depends(require_super_admin),
):
    """Requires Super Admin role. List all pages with locale-aware names/descriptions."""
    service = PageService(session)
    locale = get_locale_from_request(request)
    pages, total = await service.list_pages(session, page=page, per_page=per_page)
    # Add computed fields for backward compatibility
    result = []
    for pg in pages:
        response = PageResponse.model_validate(pg)
        response.name = pg.get_name(locale)
        response.description = pg.get_description(locale)
        result.append(response)
    return result


@router.put("/pages/{page_id}", response_model=PageResponse)
async def update_page(
    request: Request,
    page_id: int,
    page_update: PageUpdate,
    session: SessionDep,
    _: dict = Depends(require_super_admin),
):
    """Requires Super Admin role. Update a page with bilingual support and navigation fields."""
    service = PageService(session)
    locale = get_locale_from_request(request)
    try:
        page = await service.update_page(
            session,
            page_id=page_id,
            name_en=page_update.name_en,
            name_ar=page_update.name_ar,
            description_en=page_update.description_en,
            description_ar=page_update.description_ar,
            path=page_update.path,
            icon=page_update.icon,
            nav_type=page_update.nav_type,
            order=page_update.order,
            is_menu_group=page_update.is_menu_group,
            show_in_nav=page_update.show_in_nav,
            open_in_new_tab=page_update.open_in_new_tab,
        )
        # Add computed fields for backward compatibility
        response = PageResponse.model_validate(page)
        response.name = page.get_name(locale)
        response.description = page.get_description(locale)
        return response
    except (NotFoundError, ConflictError, DatabaseError):
        raise


@router.delete("/pages/{page_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_page(
    page_id: int,
    session: SessionDep,
    _: dict = Depends(require_super_admin),
):
    """Requires Super Admin role. Delete a page."""
    service = PageService(session)
    try:
        await service.delete_page(session, page_id)
    except NotFoundError:
        raise


# Page Permission Endpoints
@router.post(
    "/permissions",
    response_model=PagePermissionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def grant_permission(
    perm_create: PagePermissionCreate,
    session: SessionDep,
    _: dict = Depends(require_super_admin),
):
    """Requires Super Admin role. Grant a page permission to a role."""
    service = PagePermissionService(session)
    try:
        permission = await service.grant_permission(
            session,
            role_id=perm_create.role_id,
            page_id=perm_create.page_id,
            created_by_id=perm_create.created_by_id,
        )
        return permission
    except (ValidationError, DatabaseError):
        raise


@router.get("/permissions/{permission_id}", response_model=PagePermissionResponse)
async def get_permission(
    permission_id: int,
    session: SessionDep,
    _: dict = Depends(require_super_admin),
):
    """Requires Super Admin role. Get a permission by ID."""
    service = PagePermissionService(session)
    try:
        permission = await service.get_permission(session, permission_id)
        return permission
    except NotFoundError:
        raise


@router.get("/permissions", response_model=List[PagePermissionResponse])
async def list_permissions(
    page: int = 1,
    per_page: int = 25,
    role_id: Optional[int] = None,
    page_id: Optional[int] = None,
    session: SessionDep,
    _: dict = Depends(require_super_admin),
):
    """Requires Super Admin role. List page permissions."""
    service = PagePermissionService(session)
    permissions, total = await service.list_permissions(
        session,
        page=page,
        per_page=per_page,
        role_id=role_id,
        page_id=page_id,
    )
    return permissions


@router.delete("/permissions/{permission_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_permission(
    permission_id: int,
    session: SessionDep,
    _: dict = Depends(require_super_admin),
):
    """Requires Super Admin role. Revoke a permission."""
    service = PagePermissionService(session)
    try:
        await service.revoke_permission(session, permission_id)
    except NotFoundError:
        raise


# Email Role Endpoints
@router.post(
    "/email-roles",
    response_model=EmailRoleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_email_role(
    role_create: EmailRoleCreate,
    session: SessionDep,
    _: dict = Depends(require_super_admin),
):
    """Requires Super Admin role. Create a new email role."""
    service = EmailRoleService(session)
    try:
        role = await service.create_email_role(session, name=role_create.name)
        return role
    except (ConflictError, ValidationError, DatabaseError):
        raise


@router.get("/email-roles/{role_id}", response_model=EmailRoleResponse)
async def get_email_role(
    role_id: int,
    session: SessionDep,
    _: dict = Depends(require_super_admin),
):
    """Requires Super Admin role. Get an email role by ID."""
    service = EmailRoleService(session)
    try:
        role = await service.get_email_role(session, role_id)
        return role
    except NotFoundError:
        raise


@router.get("/email-roles", response_model=List[EmailRoleResponse])
async def list_email_roles(
    page: int = 1,
    per_page: int = 25,
    session: SessionDep,
    _: dict = Depends(require_super_admin),
):
    """Requires Super Admin role. List email roles."""
    service = EmailRoleService(session)
    roles, total = await service.list_email_roles(session, page=page, per_page=per_page)
    return roles


# Email Endpoints
@router.post(
    "/emails", response_model=EmailResponse, status_code=status.HTTP_201_CREATED
)
async def add_email(
    email_create: EmailCreate,
    session: SessionDep,
    payload: dict = Depends(require_super_admin),
):
    """Add an email address. Requires Super Admin role."""
    service = EmailService(session)
    try:
        email = await service.add_email(
            session,
            address=email_create.address,
            role_id=email_create.role_id,
        )
        return email
    except (ConflictError, ValidationError, DatabaseError):
        raise


@router.get("/emails/{email_id}", response_model=EmailResponse)
async def get_email(
    email_id: int,
    session: SessionDep,
    payload: dict = Depends(require_super_admin),
):
    """Get an email by ID. Requires Super Admin role."""
    service = EmailService(session)
    try:
        email = await service.get_email(session, email_id)
        return email
    except NotFoundError:
        raise


@router.get("/emails", response_model=List[EmailResponse])
async def list_emails(
    page: int = 1,
    per_page: int = 25,
    role_id: Optional[int] = None,
    session: SessionDep,
    payload: dict = Depends(require_super_admin),
):
    """List emails. Requires Super Admin role."""
    service = EmailService(session)
    emails, total = await service.list_emails(
        session,
        page=page,
        per_page=per_page,
        role_id=role_id,
    )
    return emails


# Strategy A: User Source and Override Management Endpoints


@router.get("/user-sources", response_model=List[UserSourceMetadata])
async def get_user_sources():
    """
    Get available user source types with localized metadata.

    Returns all user source options with bilingual labels, descriptions,
    and UI hints (icons, colors). Frontend uses this for:
    - Rendering source badges with localized labels
    - Showing tooltips with descriptions
    - Applying consistent visual styles

    No authentication required (public metadata).

    Returns:
        List of UserSourceMetadata with en/ar labels and UI properties
    """
    return get_all_user_sources()


@router.post("/users/{user_id}/mark-manual", response_model=UserResponse)
async def mark_user_as_manual(
    user_id: str,
    request_data: UserMarkManualRequest,
    session: SessionDep,
    payload: dict = Depends(require_super_admin),
):
    """
    Mark a user as manual (non-HRIS).

    Strategy A: Changes user_source to 'manual' so HRIS sync will skip this user.
    Requires Super Admin role.

    Args:
        user_id: User UUID
        request_data: Reason for marking as manual (min 20 chars)

    Returns:
        Updated user object
    """
    from api.services.user_service import UserService
    from api.services.log_permission_service import LogPermissionService
    from db.model import User
    from sqlalchemy import select

    try:
        # Get the user
        stmt = select(User).where(User.id == user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            raise NotFoundError(entity="User", identifier=user_id)

        # Check if already manual
        if user.user_source == "manual":
            raise ConflictError(f"User '{user.username}' is already marked as manual")

        # Update user source to manual
        user.user_source = "manual"
        await session.flush()
        await session.refresh(user)

        # Log the action
        log_service = LogPermissionService(session)
        await log_service.log_permission(
            session=session,
            operation_type="user_marked_manual",
            user_id=user_id,
            admin_id=payload["user_id"],
            details={
                "reason": request_data.reason,
                "previous_source": user.user_source,
            },
        )

        await session.commit()

        return UserResponse.model_validate(user)

    except (NotFoundError, ConflictError):
        raise
    except Exception as e:
        await session.rollback()
        raise DatabaseError(f"Failed to mark user as manual: {str(e)}")


@router.post(
    "/users/{user_id}/override-status", response_model=UserStatusOverrideResponse
)
async def override_user_status(
    user_id: str,
    request_data: UserStatusOverrideRequest,
    session: SessionDep,
    payload: dict = Depends(require_super_admin),
):
    """
    Enable or disable status override for a user.

    Strategy A: When enabled, HRIS sync will not modify this user's is_active status.
    Requires Super Admin role.

    Args:
        user_id: User UUID
        request_data: Override settings (status_override + optional reason)

    Returns:
        Updated user object with success message
    """
    from api.services.log_permission_service import LogPermissionService
    from db.model import User
    from sqlalchemy import select
    from datetime import datetime, timezone

    try:
        # Get the user
        stmt = select(User).where(User.id == user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            raise NotFoundError(entity="User", identifier=user_id)

        # Validate override reason required when enabling
        if request_data.status_override and not request_data.override_reason:
            raise ValidationError(
                "override_reason is required when enabling status override"
            )

        # Only allow override for HRIS users
        if user.user_source != "hris":
            raise ValidationError(
                f"Status override is only supported for HRIS users (current source: {user.user_source})"
            )

        # Update override fields
        user.status_override = request_data.status_override

        if request_data.status_override:
            # Enabling override
            user.override_reason = request_data.override_reason
            user.override_set_by_id = payload["user_id"]
            user.override_set_at = datetime.now(timezone.utc)
            message = "Status override enabled. HRIS sync will not modify this user's active status."
        else:
            # Disabling override
            user.override_reason = None
            user.override_set_by_id = None
            user.override_set_at = None
            message = "Status override disabled. HRIS sync will now manage this user's active status."

        await session.flush()
        await session.refresh(user)

        # Log the action
        log_service = LogPermissionService(session)
        await log_service.log_permission(
            session=session,
            operation_type="user_status_override_changed",
            user_id=user_id,
            admin_id=payload["user_id"],
            details={
                "status_override": request_data.status_override,
                "override_reason": request_data.override_reason
                if request_data.status_override
                else None,
            },
        )

        await session.commit()

        return UserStatusOverrideResponse(
            user=UserResponse.model_validate(user), message=message
        )

    except (NotFoundError, ValidationError):
        raise
    except Exception as e:
        await session.rollback()
        raise DatabaseError(f"Failed to update status override: {str(e)}")
