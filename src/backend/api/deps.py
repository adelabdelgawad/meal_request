"""
Dependency Injection - Provides database session and locale to endpoints.

PATTERN: Single Session Per Request
- Endpoints explicitly depend on get_session() to establish database session
- Endpoints instantiate service classes directly (no dependency injection)
- Session is passed as method argument to service calls
- Services pass session as method argument to repository calls
- This guarantees exactly one database session per HTTP request
"""

import logging
from typing import AsyncGenerator, Optional

from fastapi import Cookie, Depends, Header, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.sessions import verify_access_token
from db.maria_database import get_maria_session
from db.models import User
from settings import settings

logger = logging.getLogger(__name__)


# Database Session Dependency
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get async database session for each request.

    This function is used with FastAPI's Depends() to automatically
    provide a database session to endpoints. The session is properly
    managed by the database layer.

    Endpoints should:
    1. Depend on this function to get a session
    2. Instantiate services directly (e.g., UserService())
    3. Pass session to service methods explicitly
    """
    async for session in get_maria_session():
        yield session


async def get_current_user_id_optional(
    request: Request,
    session: AsyncSession,
) -> Optional[str]:
    """
    Extract current user ID from access token or refresh token (if present).

    This is a helper for get_locale to access user preference without forcing auth.

    Args:
        request: FastAPI Request object
        session: Database session

    Returns:
        User ID if authenticated, None otherwise
    """
    try:
        from core.sessions import verify_refresh_token

        # Try to get token from Authorization header (access token)
        auth_header = request.headers.get("authorization")
        token = None

        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            # Decode and verify access token
            payload = verify_access_token(token)
            if payload:
                user_id = payload.get("user_id")
                if user_id:
                    return user_id

        # Fallback to access_token cookie if no Authorization header
        token = request.cookies.get("access_token")
        if token:
            payload = verify_access_token(token)
            if payload:
                user_id = payload.get("user_id")
                if user_id:
                    return user_id

        # Fallback to refresh token cookie (stateful sessions)
        refresh_token = request.cookies.get(settings.SESSION_COOKIE_NAME)
        if refresh_token:
            payload = verify_refresh_token(refresh_token)
            if payload:
                user_id = payload.get("user_id")
                if user_id:
                    return user_id

        return None
    except Exception:
        # If anything fails, just return None (unauthenticated)
        return None


def parse_accept_language(accept_language: str) -> list:
    """
    Parse Accept-Language header with RFC 2616 q-value support.

    Args:
        accept_language: Accept-Language header value

    Returns:
        List of (language, quality) tuples sorted by quality (highest first)

    Example:
        "ar-EG,ar;q=0.9,en;q=0.8" -> [('ar', 1.0), ('ar', 0.9), ('en', 0.8)]
    """
    languages = []

    for lang_entry in accept_language.split(','):
        lang_entry = lang_entry.strip()
        if not lang_entry:
            continue

        # Split language from q-value
        parts = lang_entry.split(';')
        lang_code = parts[0].strip()

        # Extract primary language code (e.g., 'ar' from 'ar-EG')
        primary_code = lang_code.split('-')[0].lower()

        # Parse q-value (default 1.0 if not specified)
        quality = 1.0
        if len(parts) > 1:
            for part in parts[1:]:
                part = part.strip()
                if part.startswith('q='):
                    try:
                        quality = float(part[2:])
                    except ValueError:
                        quality = 1.0
                    break

        languages.append((primary_code, quality))

    # Sort by quality (highest first)
    languages.sort(key=lambda x: x[1], reverse=True)
    return languages


async def get_locale(
    request: Request,
    lang: Optional[str] = Query(None, description="Override locale via query parameter"),
    locale_cookie: Optional[str] = Cookie(None, alias=settings.LOCALE_COOKIE_NAME),
    accept_language: Optional[str] = Header(None, alias="accept-language"),
    session: AsyncSession = Depends(get_session),
) -> str:
    """
    Extract locale with full precedence logic.

    Precedence (highest to lowest):
    1. lang query parameter
    2. locale cookie
    3. Authenticated user's preferred_locale
    4. Accept-Language header (with RFC q-value parsing)
    5. Application default (settings.DEFAULT_LOCALE)

    Args:
        request: FastAPI Request object
        session: Database session (optional, provided by dependency)
        lang: lang query parameter
        locale_cookie: Locale preference cookie
        accept_language: Accept-Language header value

    Returns:
        Locale code from settings.SUPPORTED_LOCALES (e.g., 'en', 'ar')
    """
    # Priority 1: Explicit lang query parameter
    if lang:
        locale = lang.lower()
        if locale in settings.SUPPORTED_LOCALES:
            return locale

    # Priority 2: locale cookie
    if locale_cookie:
        locale = locale_cookie.lower()
        if locale in settings.SUPPORTED_LOCALES:
            return locale

    # Priority 3: Authenticated user's preferred_locale
    if session:
        try:
            user_id = await get_current_user_id_optional(request, session)
            if user_id:
                result = await session.execute(
                    select(User.preferred_locale).where(User.id == user_id)
                )
                preferred_locale = result.scalar_one_or_none()
                logger.debug(f"[get_locale] user_id={user_id}, preferred_locale from DB={preferred_locale}")
                if preferred_locale and preferred_locale in settings.SUPPORTED_LOCALES:
                    return preferred_locale
        except Exception as e:
            # If user lookup fails, continue to next priority
            logger.debug(f"[get_locale] Failed to get user preferred_locale: {e}")
            pass

    # Priority 4: Accept-Language header with q-value parsing
    if accept_language:
        try:
            languages = parse_accept_language(accept_language)
            for lang_code, quality in languages:
                if lang_code in settings.SUPPORTED_LOCALES:
                    return lang_code
        except Exception:
            # If parsing fails, continue to default
            pass

    # Priority 5: Application default
    return settings.DEFAULT_LOCALE


# Client IP Helper
def get_client_ip(request: Request) -> Optional[str]:
    """
    Extract client IP from request, accounting for proxies.

    Args:
        request: FastAPI Request object

    Returns:
        Client IP address or None
    """
    # Check X-Forwarded-For header (proxy/load balancer)
    forwarded = request.headers.get('x-forwarded-for')
    if forwarded:
        return forwarded.split(',')[0].strip()

    # Check X-Real-IP header (Nginx)
    real_ip = request.headers.get('x-real-ip')
    if real_ip:
        return real_ip.strip()

    # Direct client
    if request.client:
        return request.client.host

    return None


# Current User Dependency
async def get_current_user(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Get current authenticated user from access token.

    This dependency extracts and verifies the access token,
    then returns the user payload as a dict.

    Args:
        request: FastAPI Request object
        session: Database session

    Returns:
        Dict with user info (user_id, sub, scopes, roles, etc.)

    Raises:
        HTTPException: If token is missing or invalid
    """
    from fastapi import HTTPException, status

    # Extract token from Authorization header
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header",
        )

    token = auth_header.replace("Bearer ", "")

    # Verify token and get payload
    payload = verify_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    # Check if user is blocked
    user_id = payload.get("user_id")
    if user_id:
        from api.repositories.user_repository import UserRepository
        from uuid import UUID

        user_repo = UserRepository()
        user = await user_repo.get_by_id(session, UUID(user_id))

        if user and user.is_blocked:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is blocked. Contact administrator.",
            )

    return payload


# Current User from Refresh Token (Session Cookie)
async def get_current_user_from_refresh(
    request: Request,
    refresh_token: Optional[str] = Cookie(None, alias=settings.SESSION_COOKIE_NAME),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Get current authenticated user from refresh token cookie.

    This dependency is used for endpoints that work with session cookies
    (stateful sessions) instead of access tokens.

    Args:
        request: FastAPI Request object
        refresh_token: Refresh token from HttpOnly cookie
        session: Database session

    Returns:
        Dict with user info (user_id, sub, scopes, roles, etc.)

    Raises:
        HTTPException: If refresh token is missing or invalid
    """
    from fastapi import HTTPException, status
    from core.sessions import verify_refresh_token

    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No session found",
        )

    # Verify refresh token and get payload
    payload = verify_refresh_token(refresh_token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
        )

    return payload
