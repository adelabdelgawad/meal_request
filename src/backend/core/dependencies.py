"""
FastAPI dependencies for database sessions, authentication, and role-based access control.

Provides type-annotated dependency functions that can be used in route handlers:
- SessionDep: Async database session
- CurrentUserDep: Authenticated user with role information
- RoleChecker: Flexible permission checking
- Pre-made shortcuts: SuperAdminDep, ActiveUserDep, AdminDep, AdminOrSuperAdminDep
- In-memory user cache with 60s TTL
"""

import logging
import time
from typing import Annotated, Optional

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.exceptions import AuthenticationError, AuthorizationError
from db.database import get_application_session
from db.model import User

logger = logging.getLogger(__name__)

# Database session dependency
SessionDep = Annotated[AsyncSession, Depends(get_application_session)]

# Current user type annotation
CurrentUserDep = User

# In-memory user cache with 60s TTL
_user_cache: dict[str, tuple[User, float]] = {}
CACHE_TTL_SECONDS = 60


def get_cached_user(user_id: str) -> Optional[User]:
    """Get user from cache if valid, return None otherwise."""
    if user_id in _user_cache:
        user, cached_at = _user_cache[user_id]
        if time.time() - cached_at < CACHE_TTL_SECONDS:
            logger.debug(f"Cache hit for user {user_id}")
            return user
        else:
            del _user_cache[user_id]
    return None


def cache_user(user: User) -> None:
    """Cache user with current timestamp."""
    _user_cache[user.id] = (user, time.time())
    logger.debug(f"Cached user {user.id}")


def clear_user_cache(user_id: Optional[str] = None) -> None:
    """Clear cache for specific user or all users."""
    if user_id:
        _user_cache.pop(user_id, None)
        logger.debug(f"Cleared cache for user {user_id}")
    else:
        _user_cache.clear()
        logger.debug("Cleared all user cache")


async def get_current_user(
    session: SessionDep,
    request: Request,
) -> User:
    """
    Get the currently authenticated user from JWT token in request.

    Extracts JWT from Authorization header, validates it, and fetches user from database.
    Uses in-memory cache with 60s TTL to reduce database queries.
    Raises AuthenticationError if token is invalid/expired/missing.
    Raises AuthorizationError if user not found/inactive/blocked.

    Args:
        session: Async database session
        request: FastAPI request object

    Returns:
        User: Authenticated user object

    Raises:
        AuthenticationError: Token validation failed
        AuthorizationError: User not found or not active
    """
    from jose import JWTError, jwt

    # Get Authorization header
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise AuthenticationError("Missing or invalid Authorization header")

    token = auth_header.split(" ")[1]

    # Decode JWT token
    try:
        payload = jwt.decode(
            token,
            settings.sec.jwt_secret_key,
            algorithms=[settings.sec.jwt_algorithm],
        )
        user_id: str = payload.get("sub")
        if not user_id:
            raise AuthenticationError("Invalid token payload")
    except JWTError as e:
        raise AuthenticationError(f"Token validation failed: {str(e)}")

    # Check if token is revoked
    from core.redis import is_token_revoked

    if is_token_revoked(token):
        raise AuthenticationError("Token has been revoked")

    # Try to get user from cache
    user = get_cached_user(user_id)
    if user:
        return user

    # Fetch user from database
    result = await session.execute(select(User).filter(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise AuthorizationError("User not found")

    if not user.is_active:
        raise AuthorizationError("User account is inactive")

    if user.is_blocked:
        raise AuthorizationError("User account is blocked")

    # Cache the user
    cache_user(user)

    return user


class RoleChecker:
    """
    Flexible role-based permission checker for FastAPI dependencies.

    Provides methods for checking various permission conditions:
    - Super admin status
    - Active user status
    - Specific role requirements
    - Any role from a list
    """

    def __init__(self, allowed_roles: Optional[list[str]] = None):
        """
        Initialize RoleChecker.

        Args:
            allowed_roles: List of role names that are allowed (e.g., ["admin", "super_admin"])
        """
        self.allowed_roles = allowed_roles or []

    async def require_super_admin(self, user: CurrentUserDep) -> User:
        """
        Require user to be a super admin.

        Args:
            user: Current authenticated user

        Returns:
            User: The super admin user

        Raises:
            AuthorizationError: User is not a super admin
        """
        if not user.is_super_admin:
            raise AuthorizationError("Super admin access required")
        return user

    async def require_active(self, user: CurrentUserDep) -> User:
        """
        Require user to be active.

        Args:
            user: Current authenticated user

        Returns:
            User: The active user

        Raises:
            AuthorizationError: User is not active
        """
        if not user.is_active:
            raise AuthorizationError("Active user required")
        return user

    async def require_roles(
        self,
        user: CurrentUserDep,
        allowed_roles: list[str],
        session: SessionDep,
    ) -> User:
        """
        Require user to have all specified roles (AND logic).

        Args:
            user: Current authenticated user
            allowed_roles: List of role names user must have all of
            session: Async database session

        Returns:
            User: User with required roles

        Raises:
            AuthorizationError: User does not have all required roles
        """
        from db.model import Role, RolePermission

        # Get user's role permissions
        result = await session.execute(
            select(Role)
            .join(RolePermission, Role.id == RolePermission.role_id)
            .where(RolePermission.user_id == user.id)
        )
        user_roles = {role.name_en for role in result.scalars().all()}

        # Check if user has ALL required roles
        missing_roles = set(allowed_roles) - user_roles
        if missing_roles:
            raise AuthorizationError(
                f"Missing required roles: {', '.join(missing_roles)}"
            )
        return user

    async def require_any(
        self,
        user: CurrentUserDep,
        allowed_roles: list[str],
        session: SessionDep,
    ) -> User:
        """
        Require user to have at least one of the specified roles (OR logic).

        Args:
            user: Current authenticated user
            allowed_roles: List of role names user must have at least one of
            session: Async database session

        Returns:
            User: User with at least one required role

        Raises:
            AuthorizationError: User does not have any of the required roles
        """
        from db.model import Role, RolePermission

        # Get user's role permissions
        result = await session.execute(
            select(Role)
            .join(RolePermission, Role.id == RolePermission.role_id)
            .where(RolePermission.user_id == user.id)
        )
        user_roles = {role.name_en for role in result.scalars().all()}

        # Check if user has ANY of the required roles
        if not set(allowed_roles) & user_roles:
            raise AuthorizationError(
                f"Missing required role. Must have one of: {', '.join(allowed_roles)}"
            )
        return user

    async def __call__(
        self,
        user: CurrentUserDep,
        session: SessionDep,
    ) -> User:
        """
        Callable version for use as a FastAPI dependency.

        Checks if user has at least one of the allowed_roles specified at init.

        Args:
            user: Current authenticated user
            session: Async database session

        Returns:
            User: User with required permissions

        Raises:
            AuthorizationError: User does not have any required role
        """
        if not self.allowed_roles:
            return user

        return await self.require_any(user, self.allowed_roles, session)


# Pre-made dependency shortcuts for common use cases


async def super_admin_dependency(session: SessionDep, request: Request) -> User:
    """
    Dependency that requires user to be a super admin.

    Usage:
        @router.get("/admin-only")
        async def admin_endpoint(user: Annotated[User, Depends(super_admin_dependency)]):
            ...
    """
    user = await get_current_user(session, request)
    checker = RoleChecker()
    return await checker.require_super_admin(user)


SuperAdminDep = Annotated[User, Depends(super_admin_dependency)]


async def active_user_dependency(session: SessionDep, request: Request) -> User:
    """
    Dependency that requires user to be active.

    Usage:
        @router.get("/user-only")
        async def user_endpoint(user: Annotated[User, Depends(active_user_dependency)]):
            ...
    """
    user = await get_current_user(session, request)
    checker = RoleChecker()
    return await checker.require_active(user)


ActiveUserDep = Annotated[User, Depends(active_user_dependency)]


async def admin_dependency(session: SessionDep, request: Request) -> User:
    """
    Dependency that requires user to have admin role.

    Usage:
        @router.get("/admin")
        async def admin_endpoint(user: Annotated[User, Depends(admin_dependency)]):
            ...
    """
    user = await get_current_user(session, request)
    checker = RoleChecker()
    return await checker.require_any(user, ["admin"], session)


AdminDep = Annotated[User, Depends(admin_dependency)]


async def admin_or_super_admin_dependency(
    session: SessionDep, request: Request
) -> User:
    """
    Dependency that requires user to have admin OR super admin role.

    Usage:
        @router.get("/admin-or-super")
        async def admin_endpoint(user: Annotated[User, Depends(admin_or_super_admin_dependency)]):
            ...
    """
    user = await get_current_user(session, request)
    checker = RoleChecker()
    return await checker.require_any(user, ["admin", "super_admin"], session)


AdminOrSuperAdminDep = Annotated[User, Depends(admin_or_super_admin_dependency)]
