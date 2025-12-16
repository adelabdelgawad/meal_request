"""
Auth Endpoints - User authentication and authorization.
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_session
from utils.security import require_admin
from db.models import Role, User
from api.schemas import (
    RoleCreate,
    RolePageInfo,
    RolePagesResponse,
    RolePagesUpdate,
    RoleResponse,
    RoleStatusUpdate,
    RoleUpdate,
    RoleUserInfo,
    RoleUsersResponse,
    RoleUsersUpdate,
    SimpleRole,
    UserBlockUpdate,
    UserBulkStatusResponse,
    UserBulkStatusUpdate,
    UserCreate,
    UserResponse,
    UserRolesUpdate,
    UsersListResponse,
    UserStatusUpdate,
    UserUpdate,
)
from api.services import RoleService, UserService, LogUserService, LogRoleService
from core.exceptions import (
    ConflictError,
    DatabaseError,
    NotFoundError,
    ValidationError,
)

router = APIRouter(prefix="/auth", tags=["auth"])


# User Endpoints
@router.post(
    "/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def create_user(
    user_create: UserCreate,
    session: AsyncSession = Depends(get_session),
    payload: dict = Depends(require_admin),
):
    """Create a new user. Requires Admin role."""
    service = UserService()
    log_service = LogUserService()

    try:
        user = await service.create_user(
            session,
            username=user_create.username,
            email=user_create.email,
            password=user_create.password,
            full_name=user_create.full_name,
            title=user_create.title,
            is_domain_user=user_create.is_domain_user,
        )

        # Log successful user creation
        await log_service.log_user_action(
            session=session,
            admin_id=payload.get("user_id"),
            target_user_id=str(user.id),
            action="create",
            is_successful=True,
            result={
                "username": user.username,
                "email": user.email,
                "is_domain_user": user.is_domain_user,
            },
        )

        return user
    except (ConflictError, ValidationError, DatabaseError) as e:
        # Log failed user creation
        await log_service.log_user_action(
            session=session,
            admin_id=payload.get("user_id"),
            target_user_id=None,
            action="create",
            is_successful=False,
            result={
                "username": user_create.username,
                "error": str(e),
            },
        )
        raise


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    session: AsyncSession = Depends(get_session),
    payload: dict = Depends(require_admin),
):
    """Get a user by ID. Requires Admin role."""
    service = UserService()
    try:
        # Validate UUID format
        try:
            user_uuid = UUID(user_id)
        except ValueError:
            raise ValidationError(f"Invalid user ID format: {user_id}. Expected UUID format.")

        user = await service.get_user(session, user_uuid)
        return user
    except NotFoundError:
        raise


@router.get("/users", response_model=UsersListResponse)
async def list_users(
    limit: int = 10,
    skip: int = 0,
    is_active: str = None,
    username: str = None,
    role: str = None,
    session: AsyncSession = Depends(get_session),
    payload: dict = Depends(require_admin),
):
    """
    List all users with pagination and filtering. Requires Admin role.

    Frontend sends limit/skip, we convert to page/per_page for service.
    Returns wrapped response with users array, total count, and role options.

    Query Parameters:
        - limit: Number of items per page
        - skip: Number of items to skip
        - is_active: Filter by active status ("true"/"false")
        - username: Filter by username (partial match)
        - role: Filter by role ID
    """
    from db.models import RolePermission
    from typing import Optional

    # Convert limit/skip to page/per_page
    page = (skip // limit) + 1 if limit > 0 else 1
    per_page = limit

    # Parse is_active filter (string to bool or None)
    is_active_filter: Optional[bool] = None
    if is_active is not None:
        is_active_filter = is_active.lower() == "true"

    user_service = UserService()
    role_service = RoleService()

    # Fetch users with filters
    users, total = await user_service.list_users(
        session,
        page=page,
        per_page=per_page,
        is_active=is_active_filter,
        username=username,
        role_id=role,
    )

    # Fetch all roles for dropdown options and role name lookup
    roles, _ = await role_service.list_roles(session, page=1, per_page=100)
    roles_by_id = {role.id: role for role in roles}

    # Fetch role permissions to count users per role, filtered by is_active if specified
    from sqlalchemy import func
    role_counts_query = (
        select(RolePermission.role_id, func.count(RolePermission.user_id).label("count"))
        .join(User, User.id == RolePermission.user_id)
        .where(~User.is_super_admin)
    )
    # Apply is_active filter to role counts if filter is active
    if is_active_filter is not None:
        role_counts_query = role_counts_query.where(User.is_active == is_active_filter)
    role_counts_query = role_counts_query.group_by(RolePermission.role_id)
    role_counts_result = await session.execute(role_counts_query)
    role_user_counts = {row.role_id: row.count for row in role_counts_result}

    # Fetch role permissions for the users in this page (for user display)
    user_ids = [str(user.id) for user in users]
    role_permissions_query = select(RolePermission).where(
        RolePermission.user_id.in_(user_ids)
    )
    role_permissions_result = await session.execute(role_permissions_query)
    role_permissions = role_permissions_result.scalars().all()

    # Group role IDs by user ID (using set to ensure uniqueness)
    user_role_ids_sets: dict[str, set[str]] = {}
    for rp in role_permissions:
        if rp.user_id not in user_role_ids_sets:
            user_role_ids_sets[rp.user_id] = set()
        user_role_ids_sets[rp.user_id].add(rp.role_id)

    # Convert sets to lists for response
    user_role_ids: dict[str, list[str]] = {
        user_id: list(role_ids) for user_id, role_ids in user_role_ids_sets.items()
    }

    # Fetch department assignment counts for users on this page
    from db.models import DepartmentAssignment
    dept_assign_query = (
        select(
            DepartmentAssignment.user_id,
            func.count(DepartmentAssignment.department_id).label("dept_count")
        )
        .where(DepartmentAssignment.user_id.in_(user_ids))
        .where(DepartmentAssignment.is_active)
        .group_by(DepartmentAssignment.user_id)
    )
    dept_assign_result = await session.execute(dept_assign_query)
    user_dept_counts: dict[str, int] = {
        row.user_id: row.dept_count for row in dept_assign_result
    }

    # Convert users to response format with all required fields
    user_responses = []
    for user in users:
        user_id_str = str(user.id)
        # Get role names for this user
        user_roles = user_role_ids.get(user_id_str, [])
        role_names = [
            roles_by_id[rid].name_en or f"Role {rid}"
            for rid in user_roles
            if rid in roles_by_id
        ]

        user_responses.append(
            UserResponse(
                id=user_id_str,
                username=user.username,
                email=user.email,
                full_name=user.full_name,
                title=user.title,
                is_active=user.is_active,  # Use actual is_active from user model
                is_blocked=user.is_blocked,  # Use actual is_blocked from user model
                is_domain_user=user.is_domain_user,
                is_super_admin=user.is_super_admin,
                role_id=None,  # User model doesn't have role_id
                roles=role_names,
                role_ids=user_roles,  # Include role IDs for frontend matching
                assigned_department_count=user_dept_counts.get(user_id_str, 0),
                created_at=None,
                updated_at=None,
            )
        )

    # Convert roles to SimpleRole format with bilingual names and user counts
    role_options = [
        SimpleRole(
            id=role.id,
            name=role.name_en or f"Role {role.id}",
            name_en=role.name_en,
            name_ar=role.name_ar,
            total_users=role_user_counts.get(role.id, 0),
        )
        for role in roles
    ]

    # Calculate active/inactive counts from all users (not just current page), excluding super admins
    from sqlalchemy import func
    active_count_query = select(func.count(User.id)).where(
        User.is_active,
        ~User.is_super_admin
    )
    inactive_count_query = select(func.count(User.id)).where(
        ~User.is_active,
        ~User.is_super_admin
    )

    active_result = await session.execute(active_count_query)
    inactive_result = await session.execute(inactive_count_query)

    active_count = active_result.scalar() or 0
    inactive_count = inactive_result.scalar() or 0

    return UsersListResponse(
        users=user_responses,
        total=total,
        active_count=active_count,
        inactive_count=inactive_count,
        role_options=role_options,
    )


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_update: UserUpdate,
    session: AsyncSession = Depends(get_session),
    payload: dict = Depends(require_admin),
):
    """Update a user. Requires Admin role."""
    service = UserService()
    log_service = LogUserService()

    try:
        # Validate UUID format
        try:
            user_uuid = UUID(user_id)
        except ValueError:
            raise ValidationError(f"Invalid user ID format: {user_id}. Expected UUID format.")

        # Get current user state for old_value
        old_user = await service.get_user(session, user_uuid)
        old_values = {
            "full_name": old_user.full_name,
            "title": old_user.title,
        }

        # Update user
        user = await service.update_user(
            session,
            user_id=user_uuid,
            full_name=user_update.full_name,
            title=user_update.title,
        )

        # Log successful user update
        await log_service.log_user_action(
            session=session,
            admin_id=payload.get("user_id"),
            target_user_id=str(user_id),
            action="update_profile",
            is_successful=True,
            old_value=old_values,
            new_value={
                "full_name": user.full_name,
                "title": user.title,
            },
        )

        return user
    except (NotFoundError, ValidationError, DatabaseError) as e:
        # Log failed user update
        await log_service.log_user_action(
            session=session,
            admin_id=payload.get("user_id"),
            target_user_id=str(user_id),
            action="update_profile",
            is_successful=False,
            result={"error": str(e)},
        )
        raise


@router.put("/users/status", response_model=UserBulkStatusResponse)
async def bulk_update_user_status(
    bulk_update: UserBulkStatusUpdate,
    session: AsyncSession = Depends(get_session),
    payload: dict = Depends(require_admin),
):
    """Bulk update user active/inactive status. Requires Admin role."""
    service = UserService()
    log_service = LogUserService()

    try:
        user_uuids = [UUID(uid) for uid in bulk_update.user_ids]
        updated_users = await service.bulk_update_user_status(
            session, user_ids=user_uuids, is_active=bulk_update.is_active
        )

        # Build response with user details
        user_responses = []
        for user in updated_users:
            user_responses.append(
                UserResponse(
                    id=str(user.id),
                    username=user.username,
                    email=user.email,
                    full_name=user.full_name,
                    title=user.title,
                    is_active=user.is_active,
                    is_blocked=user.is_blocked,
                    is_domain_user=user.is_domain_user,
                    is_super_admin=user.is_super_admin,
                    role_id=None,
                    roles=[],
                    role_ids=[],
                    created_at=None,
                    updated_at=None,
                )
            )

        # Log bulk status update
        await log_service.log_user_action(
            session=session,
            admin_id=payload.get("user_id"),
            target_user_id=None,  # Bulk operation
            action="bulk_update_status",
            is_successful=True,
            result={
                "updated_count": len(updated_users),
                "is_active": bulk_update.is_active,
                "user_ids": bulk_update.user_ids,
            },
        )

        return UserBulkStatusResponse(
            updated_users=user_responses,
            updated_count=len(user_responses),
        )
    except (NotFoundError, ValidationError, DatabaseError) as e:
        # Log failed bulk update
        await log_service.log_user_action(
            session=session,
            admin_id=payload.get("user_id"),
            target_user_id=None,
            action="bulk_update_status",
            is_successful=False,
            result={"error": str(e), "user_ids": bulk_update.user_ids},
        )
        raise


@router.put("/users/{user_id}/status", response_model=UserResponse)
async def update_user_status(
    user_id: str,
    status_update: UserStatusUpdate,
    session: AsyncSession = Depends(get_session),
    payload: dict = Depends(require_admin),
):
    """Toggle user active/inactive status. Requires Admin role."""
    service = UserService()
    log_service = LogUserService()

    try:
        # Validate UUID format
        try:
            user_uuid = UUID(user_id)
        except ValueError:
            raise ValidationError(f"Invalid user ID format: {user_id}. Expected UUID format.")

        # Get current user state for old_value
        old_user = await service.get_user(session, user_uuid)
        old_status = old_user.is_active

        # Update user status
        user = await service.update_user_status(
            session, user_id=user_uuid, is_active=status_update.is_active
        )

        # Log successful status update
        await log_service.log_user_action(
            session=session,
            admin_id=payload.get("user_id"),
            target_user_id=str(user_id),
            action="update_status",
            is_successful=True,
            old_value={"is_active": old_status},
            new_value={"is_active": user.is_active},
        )

        return UserResponse(
            id=str(user.id),
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            title=user.title,
            is_active=user.is_active,
            is_blocked=user.is_blocked,
            is_domain_user=user.is_domain_user,
            is_super_admin=user.is_super_admin,
            role_id=None,
            roles=[],
            role_ids=[],
            created_at=None,
            updated_at=None,
        )
    except (NotFoundError, ValidationError, DatabaseError) as e:
        # Log failed status update
        await log_service.log_user_action(
            session=session,
            admin_id=payload.get("user_id"),
            target_user_id=str(user_id),
            action="update_status",
            is_successful=False,
            result={"error": str(e)},
        )
        raise


@router.patch("/users/{user_id}/block", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def toggle_user_block(
    user_id: str,
    block_update: UserBlockUpdate,
    session: AsyncSession = Depends(get_session),
    payload: dict = Depends(require_admin),
):
    """
    Block or unblock a user. Requires Admin role.

    Blocked users cannot authenticate, even with valid credentials.
    """
    from fastapi import HTTPException

    service = UserService()
    log_service = LogUserService()

    try:
        # Validate UUID format
        try:
            user_uuid = UUID(user_id)
        except ValueError:
            raise ValidationError(f"Invalid user ID format: {user_id}. Expected UUID format.")

        # Get user
        user = await service._repo.get_by_id(session, user_uuid)
        if not user:
            raise NotFoundError(entity="User", identifier=user_id)

        # Prevent self-blocking
        if str(user.id) == payload.get("user_id"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot block yourself"
            )

        # Store old value for audit
        old_blocked = user.is_blocked

        # Update is_blocked
        user.is_blocked = block_update.is_blocked
        await session.commit()
        await session.refresh(user)

        # Log block/unblock action
        action = "block_user" if block_update.is_blocked else "unblock_user"
        await log_service.log_user_action(
            session=session,
            admin_id=payload.get("user_id"),
            target_user_id=str(user.id),
            action=action,
            is_successful=True,
            old_value={"is_blocked": old_blocked},
            new_value={"is_blocked": user.is_blocked},
            result={
                "username": user.username,
                "full_name": user.full_name,
            }
        )

        # Fetch user's roles for response
        from db.models import RolePermission
        role_permissions_query = select(RolePermission).where(
            RolePermission.user_id == str(user.id)
        )
        role_permissions_result = await session.execute(role_permissions_query)
        role_permissions = role_permissions_result.scalars().all()
        role_ids = [rp.role_id for rp in role_permissions]

        # Get role names
        role_names = []
        for role_id in role_ids:
            try:
                role_query = select(Role).where(Role.id == role_id)
                role_result = await session.execute(role_query)
                role = role_result.scalar_one_or_none()
                if role:
                    role_names.append(role.name_en or f"Role {role_id}")
            except Exception:
                pass

        # Return updated user with roles populated
        return UserResponse(
            id=str(user.id),
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            title=user.title,
            is_active=user.is_active,
            is_domain_user=user.is_domain_user,
            is_super_admin=user.is_super_admin,
            role_id=None,
            roles=role_names,
            role_ids=role_ids,
            assigned_department_count=0,  # Not fetching department count for this endpoint
            created_at=None,
            updated_at=None,
        )
    except (NotFoundError, ValidationError, DatabaseError) as e:
        # Log failed block/unblock attempt
        await log_service.log_user_action(
            session=session,
            admin_id=payload.get("user_id"),
            target_user_id=str(user_id),
            action="block_user" if block_update.is_blocked else "unblock_user",
            is_successful=False,
            result={"error": str(e)},
        )
        raise


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_user(
    user_id: str,
    session: AsyncSession = Depends(get_session),
    payload: dict = Depends(require_admin),
):
    """Deactivate a user. Requires Admin role."""
    service = UserService()
    log_service = LogUserService()

    try:
        # Validate UUID format
        try:
            user_uuid = UUID(user_id)
        except ValueError:
            raise ValidationError(f"Invalid user ID format: {user_id}. Expected UUID format.")

        # Get user info before deletion
        user = await service.get_user(session, user_uuid)
        user_info = {
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
        }

        # Deactivate user
        await service.deactivate_user(session, user_uuid)

        # Log successful deletion
        await log_service.log_user_action(
            session=session,
            admin_id=payload.get("user_id"),
            target_user_id=str(user_id),
            action="delete",
            is_successful=True,
            result=user_info,
        )
    except NotFoundError as e:
        # Log failed deletion
        await log_service.log_user_action(
            session=session,
            admin_id=payload.get("user_id"),
            target_user_id=str(user_id),
            action="delete",
            is_successful=False,
            result={"error": str(e)},
        )
        raise


@router.put("/users/{user_id}/roles", response_model=UserResponse)
async def update_user_roles(
    user_id: str,
    roles_update: UserRolesUpdate,
    session: AsyncSession = Depends(get_session),
    payload: dict = Depends(require_admin),
):
    """Update user role assignments. Requires Admin role."""
    service = UserService()
    RoleService()

    log_service = LogUserService()

    try:
        # Validate UUID format
        try:
            user_uuid = UUID(user_id)
        except ValueError:
            raise ValidationError(f"Invalid user ID format: {user_id}. Expected UUID format.")

        # Get current roles for old_value
        from db.models import RolePermission
        current_roles_query = select(RolePermission).where(
            RolePermission.user_id == user_id
        )
        current_roles_result = await session.execute(current_roles_query)
        current_roles = current_roles_result.scalars().all()
        old_role_ids = [rp.role_id for rp in current_roles]

        # Update roles
        user = await service.update_user_roles(
            session,
            user_id=user_uuid,
            role_ids=roles_update.role_ids,
        )

        # Get role names for the response and logging
        role_names = []
        new_role_names = []
        for role_id in roles_update.role_ids:
            try:
                role_query = select(Role).where(Role.id == role_id)
                role_result = await session.execute(role_query)
                role = role_result.scalar_one_or_none()
                if role:
                    role_names.append(role.name_en or f"Role {role_id}")
                    new_role_names.append(role.name_en)
            except Exception:
                pass

        # Get old role names for logging
        old_role_names = []
        for role_id in old_role_ids:
            try:
                role_query = select(Role).where(Role.id == role_id)
                role_result = await session.execute(role_query)
                role = role_result.scalar_one_or_none()
                if role:
                    old_role_names.append(role.name_en)
            except Exception:
                pass

        # Log successful role assignment
        await log_service.log_user_action(
            session=session,
            admin_id=payload.get("user_id"),
            target_user_id=str(user_id),
            action="role_assignment",
            is_successful=True,
            old_value={"roles": old_role_names},
            new_value={"roles": new_role_names},
        )

        return UserResponse(
            id=str(user.id),
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            title=user.title,
            is_active=user.is_active,
            is_blocked=user.is_blocked,
            is_domain_user=user.is_domain_user,
            is_super_admin=user.is_super_admin,
            role_id=None,
            roles=role_names,
            role_ids=roles_update.role_ids,  # Include role IDs for frontend
            created_at=None,
            updated_at=None,
        )
    except (NotFoundError, ValidationError, DatabaseError) as e:
        # Log failed role assignment
        await log_service.log_user_action(
            session=session,
            admin_id=payload.get("user_id"),
            target_user_id=str(user_id),
            action="role_assignment",
            is_successful=False,
            result={"error": str(e)},
        )
        raise



# Role Endpoints
@router.post(
    "/roles", response_model=RoleResponse, status_code=status.HTTP_201_CREATED
)
async def create_role(
    role_create: RoleCreate,
    session: AsyncSession = Depends(get_session),
    payload: dict = Depends(require_admin),
):
    """Create a new role. Requires Admin role."""
    service = RoleService()
    log_service = LogRoleService()

    try:
        role = await service.create_role(
            session,
            name_en=role_create.name_en,
            name_ar=role_create.name_ar,
            description_en=role_create.description_en,
            description_ar=role_create.description_ar,
        )

        # Log successful role creation
        await log_service.log_role_action(
            session=session,
            admin_id=payload.get("user_id"),
            role_id=str(role.id),
            action="create_role",
            is_successful=True,
            new_value={
                "name_en": role.name_en,
                "name_ar": role.name_ar,
                "description_en": role.description_en,
                "description_ar": role.description_ar,
            },
        )

        return role
    except (ConflictError, ValidationError, DatabaseError) as e:
        # Log failed role creation
        await log_service.log_role_action(
            session=session,
            admin_id=payload.get("user_id"),
            role_id=None,
            action="create_role",
            is_successful=False,
            result={"error": str(e)},
        )
        raise


@router.get("/roles/{role_id}", response_model=RoleResponse)
async def get_role(
    role_id: str,
    session: AsyncSession = Depends(get_session),
    payload: dict = Depends(require_admin),
):
    """Get a role by ID. Requires Admin role."""
    service = RoleService()
    try:
        role = await service.get_role(session, role_id)
        return role
    except NotFoundError:
        raise


@router.get("/roles", response_model=List[RoleResponse])
async def list_roles(
    page: int = 1,
    per_page: int = 25,
    role_name: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
    payload: dict = Depends(require_admin),
):
    """List all roles with pagination and optional name filtering. Requires Admin role."""
    service = RoleService()
    roles, total = await service.list_roles(
        session,
        page=page,
        per_page=per_page,
        name_filter=role_name
    )
    return roles


@router.put("/roles/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: str,
    role_update: RoleUpdate,
    session: AsyncSession = Depends(get_session),
    payload: dict = Depends(require_admin),
):
    """Update a role. Requires Admin role."""
    service = RoleService()
    log_service = LogRoleService()

    try:
        # Get current role state for old_value
        old_role = await service.get_role(session, role_id)
        old_values = {
            "name_en": old_role.name_en,
            "name_ar": old_role.name_ar,
            "description_en": old_role.description_en,
            "description_ar": old_role.description_ar,
        }

        # Update role
        role = await service.update_role(
            session,
            role_id=role_id,
            name_en=role_update.name_en,
            name_ar=role_update.name_ar,
            description_en=role_update.description_en,
            description_ar=role_update.description_ar,
        )

        # Log successful role update
        await log_service.log_role_action(
            session=session,
            admin_id=payload.get("user_id"),
            role_id=str(role_id),
            action="update_role",
            is_successful=True,
            old_value=old_values,
            new_value={
                "name_en": role.name_en,
                "name_ar": role.name_ar,
                "description_en": role.description_en,
                "description_ar": role.description_ar,
            },
        )

        return role
    except (NotFoundError, ValidationError, DatabaseError) as e:
        # Log failed role update
        await log_service.log_role_action(
            session=session,
            admin_id=payload.get("user_id"),
            role_id=str(role_id),
            action="update_role",
            is_successful=False,
            result={"error": str(e)},
        )
        raise


@router.delete("/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    role_id: str,
    session: AsyncSession = Depends(get_session),
    payload: dict = Depends(require_admin),
):
    """Delete a role. Requires Admin role."""
    service = RoleService()
    log_service = LogRoleService()

    try:
        # Get role info before deletion
        role = await service.get_role(session, role_id)
        role_info = {
            "name_en": role.name_en,
            "name_ar": role.name_ar,
            "description_en": role.description_en,
            "description_ar": role.description_ar,
        }

        # Delete role
        await service.delete_role(session, role_id)

        # Log successful deletion
        await log_service.log_role_action(
            session=session,
            admin_id=payload.get("user_id"),
            role_id=str(role_id),
            action="delete_role",
            is_successful=True,
            old_value=role_info,
        )
    except NotFoundError as e:
        # Log failed deletion
        await log_service.log_role_action(
            session=session,
            admin_id=payload.get("user_id"),
            role_id=str(role_id),
            action="delete_role",
            is_successful=False,
            result={"error": str(e)},
        )
        raise


@router.put("/roles/{role_id}/status", response_model=RoleResponse)
async def update_role_status(
    role_id: str,
    status_update: RoleStatusUpdate,
    session: AsyncSession = Depends(get_session),
    payload: dict = Depends(require_admin),
):
    """Toggle role active/inactive status. Requires Admin role."""
    service = RoleService()
    log_service = LogRoleService()

    try:
        # Get current role state for old_value
        old_role = await service.get_role(session, role_id)
        old_status = old_role.is_active

        # Update role status
        role = await service.update_role_status(
            session, role_id=role_id, is_active=status_update.is_active
        )

        # Log successful status update
        await log_service.log_role_action(
            session=session,
            admin_id=payload.get("user_id"),
            role_id=str(role_id),
            action="update_status",
            is_successful=True,
            old_value={"is_active": old_status},
            new_value={"is_active": role.is_active},
        )

        return role
    except (NotFoundError, ValidationError, DatabaseError) as e:
        # Log failed status update
        await log_service.log_role_action(
            session=session,
            admin_id=payload.get("user_id"),
            role_id=str(role_id),
            action="update_status",
            is_successful=False,
            result={"error": str(e)},
        )
        raise


# Role Pages Endpoints
@router.get("/roles/{role_id}/pages", response_model=RolePagesResponse)
async def get_role_pages(
    role_id: str,
    include_inactive: bool = False,
    session: AsyncSession = Depends(get_session),
    payload: dict = Depends(require_admin),
):
    """Get all pages assigned to a role. Requires Admin role."""
    service = RoleService()
    try:
        pages = await service.get_role_pages(
            session, role_id=role_id, include_inactive=include_inactive
        )
        return RolePagesResponse(
            role_id=role_id,
            pages=[RolePageInfo(**page) for page in pages],
            total=len(pages),
        )
    except NotFoundError:
        raise


@router.put("/roles/{role_id}/pages", response_model=RolePagesResponse)
async def update_role_pages(
    role_id: str,
    pages_update: RolePagesUpdate,
    session: AsyncSession = Depends(get_session),
    payload: dict = Depends(require_admin),
):
    """Update pages assigned to a role (replaces all existing assignments). Requires Admin role."""
    service = RoleService()
    log_service = LogRoleService()
    created_by_id = "00000000-0000-0000-0000-000000000000"
    try:
        # Get current pages for old_value
        old_pages = await service.get_role_pages(session, role_id=role_id)
        old_page_ids = [p["id"] for p in old_pages]

        # Update pages
        pages = await service.update_role_pages(
            session,
            role_id=role_id,
            page_ids=pages_update.page_ids,
            created_by_id=created_by_id,
        )

        # Log successful page assignment update
        await log_service.log_role_action(
            session=session,
            admin_id=payload.get("user_id"),
            role_id=str(role_id),
            action="assign_pages",
            is_successful=True,
            old_value={"page_ids": old_page_ids},
            new_value={"page_ids": pages_update.page_ids},
        )

        return RolePagesResponse(
            role_id=role_id,
            pages=[RolePageInfo(**page) for page in pages],
            total=len(pages),
        )
    except NotFoundError as e:
        # Log failed page assignment
        await log_service.log_role_action(
            session=session,
            admin_id=payload.get("user_id"),
            role_id=str(role_id),
            action="assign_pages",
            is_successful=False,
            result={"error": str(e)},
        )
        raise


# Role Users Endpoints
@router.get("/roles/{role_id}/users", response_model=RoleUsersResponse)
async def get_role_users(
    role_id: str,
    include_inactive: bool = False,
    session: AsyncSession = Depends(get_session),
    payload: dict = Depends(require_admin),
):
    """Get all users assigned to a role. Requires Admin role."""
    service = RoleService()
    try:
        users = await service.get_role_users(
            session, role_id=role_id, include_inactive=include_inactive
        )
        return RoleUsersResponse(
            role_id=role_id,
            users=[RoleUserInfo(**user) for user in users],
            total=len(users),
        )
    except NotFoundError:
        raise


@router.put("/roles/{role_id}/users", response_model=RoleUsersResponse)
async def update_role_users(
    role_id: str,
    users_update: RoleUsersUpdate,
    session: AsyncSession = Depends(get_session),
    payload: dict = Depends(require_admin),
):
    """Update users assigned to a role (replaces all existing assignments). Requires Admin role."""
    service = RoleService()
    try:
        users = await service.update_role_users(
            session, role_id=role_id, user_ids=users_update.user_ids
        )
        return RoleUsersResponse(
            role_id=role_id,
            users=[RoleUserInfo(**user) for user in users],
            total=len(users),
        )
    except NotFoundError:
        raise
