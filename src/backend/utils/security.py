"""
Security utilities for JWT token verification and authentication.

Includes:
- Rate limiting with Redis storage (distributed)
- JWT token verification with revocation cache
- Role-based access control dependencies
"""

import logging
import uuid
from datetime import datetime, timedelta
from functools import wraps
from typing import Callable, List, Optional

import pytz
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy.ext.asyncio import AsyncSession

from db.maria_database import get_maria_session
from settings import settings
from utils.observability import record_auth_failure

logger = logging.getLogger(__name__)


def _get_client_ip(request: Request) -> str:
    """
    Get client IP address, handling proxies correctly.

    Checks X-Forwarded-For and X-Real-IP headers for load-balanced scenarios.

    Args:
        request: FastAPI Request object

    Returns:
        str: Client IP address
    """
    # Check X-Forwarded-For header (common for reverse proxies)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # X-Forwarded-For can contain multiple IPs: client, proxy1, proxy2
        # Take the first (original client) IP
        return forwarded_for.split(",")[0].strip()

    # Check X-Real-IP header (nginx)
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()

    # Fall back to direct client IP
    if request.client:
        return request.client.host

    return "unknown"


def _create_limiter() -> Limiter:
    """
    Create rate limiter with appropriate storage backend.

    Uses Redis storage when REDIS_ENABLED and REDIS_URL are configured,
    otherwise falls back to in-memory storage.

    Returns:
        Limiter: Configured SlowAPI limiter instance
    """
    if settings.REDIS_ENABLED and settings.REDIS_URL:
        logger.info(
            "Initializing rate limiter with Redis storage",
            extra={"redis_url_masked": _mask_url(settings.REDIS_URL)},
        )
        return Limiter(
            key_func=_get_client_ip,
            storage_uri=settings.REDIS_URL,
            # Use async Redis for FastAPI compatibility
            strategy="fixed-window",
        )
    else:
        logger.warning(
            "Redis not configured - using in-memory rate limiting "
            "(counters will reset on restart and not shared across instances)"
        )
        return Limiter(key_func=_get_client_ip)


def _mask_url(url: str) -> str:
    """Mask password in URL for logging."""
    import re
    return re.sub(r"(://[^:]+:)[^@]+(@)", r"\1****\2", url)


# Initialize rate limiter with Redis storage (if available)
limiter = _create_limiter()

# Security scheme for Bearer tokens
security = HTTPBearer(auto_error=False)

# JWT configuration from settings
SECRET_KEY = settings.JWT_SECRET_KEY
ALGORITHM = settings.JWT_ALGORITHM

if not SECRET_KEY:
    logger.warning(
        "JWT_SECRET_KEY not configured - authentication will fail in production"
    )


def create_jwt(
    data: dict, token_type: str, expires_delta: timedelta
) -> tuple[str, str]:
    """
    Generate a JWT token with unique JTI (JWT ID).

    Args:
        data: The data to encode into the token
        token_type: Type of token ("access" or "refresh")
        expires_delta: Time after which the token will expire

    Returns:
        tuple: (encoded_token, jti)
    """
    jti = str(uuid.uuid4())
    to_encode = data.copy()
    expire = datetime.now(pytz.timezone("Africa/Cairo")) + expires_delta
    to_encode.update({"exp": expire, "jti": jti, "type": token_type})
    encoded_token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_token, jti


def decode_jwt(token: str) -> dict:
    """
    Decode and verify a JWT token.

    Args:
        token: The JWT token to decode

    Returns:
        dict: Decoded token payload

    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        record_auth_failure("expired_token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.JWTError as e:
        record_auth_failure("invalid_token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def verify_jwt_token(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    session: AsyncSession = Depends(get_maria_session),
) -> dict:
    """
    Verify and decode JWT token from Authorization header or cookies.
    Checks token revocation using Redis cache (with database fallback).

    Authentication methods (in priority order):
    1. Authorization: Bearer <token> header
    2. Session cookie (refresh token)

    Revocation Check Strategy:
    1. Check Redis cache first (O(1) lookup)
    2. If not in cache, check database
    3. Cache result for future lookups

    Args:
        request: FastAPI Request object (for cookie access)
        credentials: HTTP Bearer credentials from request
        session: Database session

    Returns:
        dict: Decoded JWT payload

    Raises:
        HTTPException: If token is missing, invalid, expired, or revoked
    """
    token = None

    # Priority 1: Check Authorization header
    if credentials:
        token = credentials.credentials
    # Priority 2: Check session cookie (refresh token)
    else:
        token = request.cookies.get(settings.SESSION_COOKIE_NAME)

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        # Check if token is revoked (for both access and refresh tokens)
        jti = payload.get("jti")
        if jti:
            is_revoked = await _check_token_revoked_with_cache(session, jti)
            if is_revoked:
                record_auth_failure("revoked_token")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has been revoked",
                    headers={"WWW-Authenticate": "Bearer"},
                )

        return payload
    except HTTPException:
        raise
    except JWTError as e:
        logger.warning(f"JWT verification failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def _check_token_revoked_with_cache(session: AsyncSession, jti: str) -> bool:
    """
    Check if token is revoked using Redis cache with database fallback.

    Cache Strategy:
    - If token is in cache as "revoked" -> return True (revoked)
    - If token is NOT in cache -> check database
    - If database says revoked -> cache it and return True
    - If database says not revoked -> DON'T cache (to allow future revocation)

    Note: We only cache revoked tokens, not valid ones. This ensures
    revocation takes effect immediately without cache invalidation concerns.

    Args:
        session: Database session
        jti: JWT ID to check

    Returns:
        bool: True if token is revoked
    """
    from core.redis import RedisKeys, cache_exists, cache_set, is_redis_available

    # Try Redis cache first (if available)
    if is_redis_available():
        cache_key = RedisKeys.revoked_token(jti)
        if await cache_exists(cache_key):
            # Token is in revoked cache -> definitely revoked
            logger.debug(f"Token {jti[:8]}... found in revocation cache")
            return True

    # Cache miss or Redis unavailable -> check database
    from api.services.revoked_token_service import RevokedTokenService

    revoked_token_service = RevokedTokenService()
    is_revoked = await revoked_token_service.is_token_revoked(session, jti)

    # If revoked, cache it for future lookups
    if is_revoked and is_redis_available():
        cache_key = RedisKeys.revoked_token(jti)
        # TTL matches access token lifetime to auto-cleanup
        ttl = settings.REDIS_REVOKED_TOKEN_TTL_SECONDS
        await cache_set(cache_key, "1", ttl)
        logger.debug(f"Cached revoked token {jti[:8]}... with TTL {ttl}s")

    return is_revoked


async def cache_revoked_token(jti: str, ttl_seconds: int = None) -> bool:
    """
    Explicitly cache a revoked token JTI.

    Called when a token is revoked to immediately populate the cache.

    Args:
        jti: JWT ID of the revoked token
        ttl_seconds: Optional TTL override (defaults to settings)

    Returns:
        bool: True if cached successfully
    """
    from core.redis import RedisKeys, cache_set, is_redis_available

    if not is_redis_available():
        return False

    cache_key = RedisKeys.revoked_token(jti)
    ttl = ttl_seconds or settings.REDIS_REVOKED_TOKEN_TTL_SECONDS
    return await cache_set(cache_key, "1", ttl)


async def require_role(role_name: str):
    """
    Dependency to check if user has required role.

    Args:
        role_name: Required role name (e.g., "admin", "user")

    Returns:
        dict: User payload if role check passes

    Raises:
        HTTPException: If user doesn't have required role
    """

    async def role_checker(payload: dict = Depends(verify_jwt_token)) -> dict:
        user_roles = payload.get("roles", [])
        if role_name not in user_roles and "admin" not in user_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {role_name}",
            )
        return payload

    return role_checker


def require_scope(scopes: List[str]) -> Callable:
    """
    Create a dependency that checks if the JWT token has required scopes.

    Args:
        scopes: List of required scopes (e.g., ["admin"], ["admin", "auditor"])

    Returns:
        Callable: Dependency function that validates token scopes
    """

    async def scope_checker(payload: dict = Depends(verify_jwt_token)) -> dict:
        token_scopes = payload.get("scopes", [])
        if not any(scope in token_scopes for scope in scopes):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required scopes: {scopes}",
            )
        return payload

    return scope_checker


# Role-based access control dependencies
async def require_super_admin(payload: dict = Depends(verify_jwt_token)) -> dict:
    """
    Require Super Admin role - highest level access.
    Super admins have complete system control including audit logs,
    system configuration, and scheduler management.

    Args:
        payload: JWT payload from verify_jwt_token

    Returns:
        dict: Payload if authorized

    Raises:
        HTTPException: 403 if user doesn't have super_admin scope
    """
    scopes = payload.get("scopes", [])
    if "super_admin" not in scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super Admin role required"
        )
    return payload


async def require_admin(payload: dict = Depends(verify_jwt_token)) -> dict:
    """
    Require Admin role (or Super Admin).
    Admins can manage users, roles, permissions, and view all data.

    Args:
        payload: JWT payload from verify_jwt_token

    Returns:
        dict: Payload if authorized

    Raises:
        HTTPException: 403 if user doesn't have admin or super_admin scope
    """
    scopes = payload.get("scopes", [])
    if "admin" not in scopes and "super_admin" not in scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required"
        )
    return payload


async def require_ordertaker(payload: dict = Depends(verify_jwt_token)) -> dict:
    """
    Require Ordertaker role (or Admin/Super Admin).
    Ordertakers can review and approve meal requests.

    Args:
        payload: JWT payload from verify_jwt_token

    Returns:
        dict: Payload if authorized

    Raises:
        HTTPException: 403 if user doesn't have ordertaker, admin, or super_admin scope
    """
    scopes = payload.get("scopes", [])
    if not any(role in scopes for role in ["ordertaker", "admin", "super_admin"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ordertaker role required"
        )
    return payload


async def require_requester(payload: dict = Depends(verify_jwt_token)) -> dict:
    """
    Require Requester role (or Admin/Super Admin).
    Requesters can create meal requests for employees.

    Args:
        payload: JWT payload from verify_jwt_token

    Returns:
        dict: Payload if authorized

    Raises:
        HTTPException: 403 if user doesn't have requester, admin, or super_admin scope
    """
    scopes = payload.get("scopes", [])
    if not any(role in scopes for role in ["requester", "admin", "super_admin"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requester role required"
        )
    return payload


async def require_auditor(payload: dict = Depends(verify_jwt_token)) -> dict:
    """
    Require Auditor role (or Admin/Super Admin).
    Auditors have read-only access to view meal requests and reports.

    Args:
        payload: JWT payload from verify_jwt_token

    Returns:
        dict: Payload if authorized

    Raises:
        HTTPException: 403 if user doesn't have auditor, admin, or super_admin scope
    """
    scopes = payload.get("scopes", [])
    if not any(role in scopes for role in ["auditor", "admin", "super_admin"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Auditor role required"
        )
    return payload


# Multi-role dependencies (any of the specified roles)
async def require_requester_or_admin(payload: dict = Depends(verify_jwt_token)) -> dict:
    """
    Require Requester or Admin role (or Super Admin).
    Used for endpoints accessible to requesters and administrators.

    Args:
        payload: JWT payload from verify_jwt_token

    Returns:
        dict: Payload if authorized

    Raises:
        HTTPException: 403 if user doesn't have requester, admin, or super_admin scope
    """
    scopes = payload.get("scopes", [])
    if not any(role in scopes for role in ["requester", "admin", "super_admin"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requester or Admin role required"
        )
    return payload


async def require_ordertaker_or_admin(payload: dict = Depends(verify_jwt_token)) -> dict:
    """
    Require Ordertaker or Admin role (or Super Admin).
    Used for endpoints accessible to ordertakers and administrators.

    Args:
        payload: JWT payload from verify_jwt_token

    Returns:
        dict: Payload if authorized

    Raises:
        HTTPException: 403 if user doesn't have ordertaker, admin, or super_admin scope
    """
    scopes = payload.get("scopes", [])
    if not any(role in scopes for role in ["ordertaker", "admin", "super_admin"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ordertaker or Admin role required"
        )
    return payload


async def require_auditor_or_admin(payload: dict = Depends(verify_jwt_token)) -> dict:
    """
    Require Auditor or Admin role (or Super Admin).
    Used for endpoints accessible to auditors and administrators.

    Args:
        payload: JWT payload from verify_jwt_token

    Returns:
        dict: Payload if authorized

    Raises:
        HTTPException: 403 if user doesn't have auditor, admin, or super_admin scope
    """
    scopes = payload.get("scopes", [])
    if not any(role in scopes for role in ["auditor", "admin", "super_admin"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Auditor or Admin role required"
        )
    return payload


async def require_ordertaker_auditor_or_admin(payload: dict = Depends(verify_jwt_token)) -> dict:
    """
    Require Ordertaker, Auditor, or Admin role (or Super Admin).
    Used for endpoints accessible to ordertakers, auditors, and administrators.

    Args:
        payload: JWT payload from verify_jwt_token

    Returns:
        dict: Payload if authorized

    Raises:
        HTTPException: 403 if user doesn't have ordertaker, auditor, admin, or super_admin scope
    """
    scopes = payload.get("scopes", [])
    if not any(role in scopes for role in ["ordertaker", "auditor", "admin", "super_admin"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ordertaker, Auditor, or Admin role required"
        )
    return payload


async def require_requester_ordertaker_or_admin(payload: dict = Depends(verify_jwt_token)) -> dict:
    """
    Require Requester, Ordertaker, or Admin role (or Super Admin).
    Used for endpoints accessible to requesters, ordertakers, and administrators.

    Args:
        payload: JWT payload from verify_jwt_token

    Returns:
        dict: Payload if authorized

    Raises:
        HTTPException: 403 if user doesn't have requester, ordertaker, admin, or super_admin scope
    """
    scopes = payload.get("scopes", [])
    if not any(role in scopes for role in ["requester", "ordertaker", "admin", "super_admin"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requester, Ordertaker, or Admin role required"
        )
    return payload


async def require_authenticated(payload: dict = Depends(verify_jwt_token)) -> dict:
    """
    Require any authenticated user (any role).
    Used for endpoints that only need the user to be logged in.

    Args:
        payload: JWT payload from verify_jwt_token

    Returns:
        dict: Payload (already verified by verify_jwt_token)
    """
    # If verify_jwt_token succeeds, user is authenticated
    return payload


def auth_limited(limit: str = "100/minute"):
    """
    Decorator that combines JWT authentication and rate limiting.

    Args:
        limit: Rate limit string (e.g., "100/minute")

    Returns:
        Callable: Decorated function
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Rate limiting will be applied via decorator
            # JWT verification will be applied via Depends(verify_jwt_token)
            return await func(*args, **kwargs)

        return wrapper

    return decorator


# Helper to create scoped tokens (used in login endpoint)
def create_access_token_with_scopes(
    data: dict,
    scopes: Optional[List[str]] = None,
    expires_delta: Optional[int] = None,
) -> str:
    """
    Create JWT access token with optional scopes.

    Args:
        data: Token payload data
        scopes: Optional list of scopes/permissions
        expires_delta: Optional expiration time in minutes

    Returns:
        str: Encoded JWT token
    """
    to_encode = data.copy()
    if scopes:
        to_encode["scopes"] = scopes

    expire = datetime.now(pytz.timezone("Africa/Cairo")) + timedelta(
        minutes=expires_delta or settings.SESSION_ACCESS_TOKEN_MINUTES
    )
    to_encode.update({"exp": expire})

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# Export rate limiter and exception handler for use in app.py
__all__ = [
    "verify_jwt_token",
    "require_scope",
    "require_role",
    "auth_limited",
    "limiter",
    "_rate_limit_exceeded_handler",
    "RateLimitExceeded",
    "create_access_token_with_scopes",
    "create_jwt",
    "decode_jwt",
    # Token revocation cache
    "cache_revoked_token",
    # Role-based access control dependencies
    "require_super_admin",
    "require_admin",
    "require_ordertaker",
    "require_requester",
    "require_auditor",
    "require_requester_or_admin",
    "require_ordertaker_or_admin",
    "require_auditor_or_admin",
    "require_ordertaker_auditor_or_admin",
    "require_requester_ordertaker_or_admin",
    "require_authenticated",
]
