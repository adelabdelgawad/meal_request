"""
Login Endpoints - User authentication and token management.
"""

import logging
import traceback
from datetime import datetime
from uuid import UUID

import pytz
from fastapi import (
    APIRouter,
    Cookie,
    Depends,
    HTTPException,
    Request,
    Response,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_locale, get_session
from api.repositories.session_repository import SessionRepository
from api.repositories.user_repository import UserRepository
from api.schemas.auth_schemas import (
    LoginResponse,
    LogoutResponse,
    PageInfo,
    SessionResponse,
    SessionUserInfo,
    TokenRefreshResponse,
    UserInfo,
)
from core.redis import cache_get, cache_set
from api.services import PageService, RevokedTokenService, RoleService
from api.services.log_authentication_service import LogAuthenticationService
from core import sessions as session_helpers
from settings import settings
from utils.app_schemas import LoginRequest
from utils.custom_exceptions import AuthorizationError
from utils.login import Login
from utils.security import decode_jwt, limiter

logger = logging.getLogger(__name__)

# JWT configuration from settings
SECRET_KEY = settings.JWT_SECRET_KEY
ALGORITHM = settings.JWT_ALGORITHM
# Use settings for token lifetimes (configured via .env)
ACCESS_TOKEN_EXPIRE_MINUTES = settings.SESSION_ACCESS_TOKEN_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = settings.SESSION_REFRESH_LIFETIME_DAYS

# Validate required environment variables
if not SECRET_KEY:
    if settings.ENVIRONMENT == "local":
        # Generate a temporary secret for local development only
        import secrets

        SECRET_KEY = secrets.token_urlsafe(32)
        logger.warning(
            "WARNING: Using generated temporary SECRET_KEY for local development only. "
            "Set JWT_SECRET_KEY environment variable for production use."
        )
    else:
        raise RuntimeError(
            "JWT_SECRET_KEY environment variable is required for production. "
            "Use a secure secret store (Azure Key Vault, AWS Secrets Manager, etc.)"
        )

cairo_tz = pytz.timezone("Africa/Cairo")

router = APIRouter(prefix="/auth", tags=["auth"])

# Initialize services
page_service = PageService()
revoked_token_service = RevokedTokenService()
session_repository = SessionRepository()
user_repository = UserRepository()
role_service = RoleService()
log_auth_service = LogAuthenticationService()


@router.post("/login", response_model=LoginResponse)
@limiter.limit(settings.RATE_LIMIT_LOGIN)  # Brute force protection
async def login(
    request: Request,
    request_body: LoginRequest,
    response: Response,
    session: AsyncSession = Depends(get_session),
    locale: str = Depends(get_locale),
):
    """
    Handles the user login process. Authenticates the user and generates both access and refresh tokens.

    Authentication flow:
    1. Attempts domain (LDAP) authentication for all users
    2. If domain authentication fails, falls back to local authentication for admin users only
    3. Regular users must authenticate via domain

    Rate Limit: Configurable via RATE_LIMIT_LOGIN (default: 10/minute)
    This protects against brute force attacks.

    Args:
        request (LoginRequest): Contains the username and password.
        session (AsyncSession): The database session provided by FastAPI's dependency injection.

    Returns:
        Dict containing access token, refresh token, token type, account details, and optional pages information.

    Raises:
        HTTPException: Raised when authentication fails or when an internal server error occurs.
    """
    try:
        # Authenticate the user (domain-first, with local fallback for admin)
        account = Login(
            session=session,
            username=request_body.username,
            password=request_body.password,
        )
        await account.authenticate()

        if not account.is_authenticated:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
            )

        user_id = str(account.user.id)

        # Determine user scopes and roles from database
        # Super admin users automatically get "super_admin" scope
        if account.user.is_super_admin:
            scopes = ["super_admin"]
            roles = ["super_admin"]
            logger.info(
                f"User '{account.user.username}' identified as super admin"
            )
        else:
            # Fetch role names from database for regular users
            role_names = await role_service.get_user_role_names(
                session, user_id
            )
            scopes = role_names if role_names else []
            roles = role_names if role_names else []
            logger.info(
                f"User '{account.user.username}' has roles: {role_names}"
            )

        # Always include "user" scope for backward compatibility
        if "user" not in scopes:
            scopes.append("user")
            roles.append("user")
        username = request_body.username

        # Use user's preferred_locale from database if available, otherwise fallback to resolved locale
        user_locale = account.user.preferred_locale
        if user_locale and user_locale in settings.SUPPORTED_LOCALES:
            locale = user_locale
            logger.info(
                f"Using user's preferred locale from database: {locale}"
            )
        else:
            logger.info(
                f"User has no preferred locale, using resolved locale: {locale}"
            )

        # Stateful sessions (database-backed) - ALWAYS ENABLED
        # Create access token using session helpers
        access_token, access_jti = session_helpers.issue_access_token(
            user_id=user_id,
            username=username,
            scopes=scopes,
        )

        # Create refresh token and session (include scopes, roles, and locale for validation)
        refresh_token, refresh_jti, expires_at = (
            session_helpers.create_refresh_cookie_value(
                user_id=user_id,
                username=username,
                scopes=scopes,
                roles=roles,
                locale=locale,
            )
        )

        # Extract device information
        user_agent = session_helpers.parse_user_agent(request)
        ip_address = session_helpers.get_client_ip(request)
        accept_language = request.headers.get("accept-language")
        fingerprint = session_helpers.create_fingerprint_from_request(
            user_agent, ip_address, accept_language
        )

        # Create session in database with locale metadata
        new_session = await session_repository.create_session(
            session=session,
            user_id=user_id,
            refresh_token_id=refresh_jti,
            expires_at=expires_at,
            device_info=user_agent,
            ip_address=ip_address,
            fingerprint=fingerprint,
            locale=locale,
        )

        logger.info(
            f"Created new session with id={new_session.id}, refresh_token_id={new_session.refresh_token_id}"
        )

        # Log successful login
        await log_auth_service.log_authentication(
            session=session,
            user_id=user_id,
            action="login_success",
            is_successful=True,
            ip_address=ip_address,
            user_agent=user_agent,
            device_fingerprint=fingerprint,
            result={"username": username, "session_id": str(new_session.id)},
        )

        # Enforce concurrent session limit
        # If user has more sessions than allowed, revoke the oldest ones (excluding this new session)
        revoked_count = await session_repository.enforce_session_limit(
            session=session,
            user_id=user_id,
            max_sessions=settings.SESSION_MAX_CONCURRENT,
            exclude_session_id=new_session.id,  # Don't revoke the session we just created
        )
        if revoked_count > 0:
            logger.info(
                f"Revoked {revoked_count} old session(s) for user {username} "
                f"to enforce limit of {settings.SESSION_MAX_CONCURRENT}"
            )

        # Session will be auto-committed by get_maria_session() context manager
        # Set refresh token as HttpOnly cookie
        response.set_cookie(
            key=settings.SESSION_COOKIE_NAME,
            value=refresh_token,
            max_age=settings.SESSION_REFRESH_LIFETIME_DAYS * 24 * 60 * 60,
            httponly=True,
            secure=settings.SESSION_COOKIE_SECURE,
            samesite=settings.SESSION_COOKIE_SAMESITE,
        )

        # Set locale cookie (non-HttpOnly for client access)
        locale_max_age = settings.LOCALE_COOKIE_MAX_AGE_DAYS * 24 * 60 * 60
        response.set_cookie(
            key=settings.LOCALE_COOKIE_NAME,
            value=locale,
            max_age=locale_max_age,
            httponly=False,
            secure=settings.LOCALE_COOKIE_SECURE,
            samesite=settings.LOCALE_COOKIE_SAMESITE,
        )

        # Fetch page permissions and associated pages (if any)
        if account.user.is_super_admin:
            pages = await page_service.get_all_pages(session)
        else:
            pages = await page_service.get_pages_by_account(
                session, str(account.user.id)
            )
            logger.info(
                f"Retrieved user {account.user.username} permissions: {pages}"
            )

        # Localize page names and descriptions
        localized_pages = []
        if pages:
            for page in pages:
                localized_pages.append(
                    PageInfo(
                        id=page.id,
                        name=page.get_name(locale),
                        description=page.get_description(locale),
                        name_en=page.name_en,
                        name_ar=page.name_ar,
                        description_en=page.description_en,
                        description_ar=page.description_ar,
                        parent_id=page.parent_id,
                    )
                )

        # Return response with tokens using Pydantic model (auto-converts to camelCase)
        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # in seconds
            user=UserInfo(
                id=str(account.user.id),
                username=account.user.username,
                full_name=account.user.full_name,
                title=account.user.title,
                is_super_admin=account.user.is_super_admin,
                locale=locale,  # Include user's resolved locale
            ),
            pages=localized_pages,
        )
    except AuthorizationError as auth_error:
        logger.warning(
            f"Authorization Error during login for user {request_body.username}: {auth_error}"
        )
        # Log failed login
        await log_auth_service.log_authentication(
            session=session,
            user_id=None,
            action="login_failed",
            is_successful=False,
            ip_address=(request.client.host if request.client else None),
            user_agent=request.headers.get("user-agent"),
            result={
                "username": request_body.username,
                "reason": "Invalid credentials",
            },
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(auth_error),
        )

    except HTTPException as http_exc:
        # Log and re-raise HTTP-related exceptions
        logger.error(f"HTTP Exception during login: {http_exc.detail}")
        # Log failed login for 401 errors
        if http_exc.status_code == status.HTTP_401_UNAUTHORIZED:
            await log_auth_service.log_authentication(
                session=session,
                user_id=None,
                action="login_failed",
                is_successful=False,
                ip_address=(request.client.host if request.client else None),
                user_agent=request.headers.get("user-agent"),
                result={
                    "username": request_body.username,
                    "reason": http_exc.detail,
                },
            )
        raise http_exc

    except Exception as e:
        # Handle unexpected errors, log them, and raise a 500 error
        logger.error(
            f"Unexpected error during login for user {request_body.username}: {e}"
        )
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during login.",
        )


@router.get("/session", response_model=SessionResponse)
async def validate_session(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """
    Validate the current user session and return user data.

    Extracts the access token from the Authorization header or cookies,
    validates it, and returns the current user's information.

    Locale is extracted from JWT refresh token (zero DB queries).

    Returns:
        Dict containing user information including id, username, roles, and pages

    Raises:
        HTTPException: If token is missing, invalid, expired, or revoked
    """
    # Determine locale from JWT refresh token (zero DB queries!)
    locale = settings.DEFAULT_LOCALE
    try:
        refresh_token = request.cookies.get(settings.SESSION_COOKIE_NAME)
        if refresh_token:
            refresh_payload = session_helpers.verify_refresh_token(
                refresh_token
            )
            if refresh_payload and "locale" in refresh_payload:
                locale = refresh_payload["locale"]
    except Exception:
        pass

    try:
        # Try to get token from Authorization header
        auth_header = request.headers.get("authorization")
        token = None

        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]

        # Fallback to cookies if no Authorization header
        if not token:
            token = request.cookies.get("access_token")

        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No authentication token provided",
            )

        # Decode and verify access token
        payload = decode_jwt(token)

        # Check token type
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )

        # Check if token is revoked
        jti = payload.get("jti")
        if jti:
            if await revoked_token_service.is_token_revoked(session, jti):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has been revoked",
                )

        # Extract user information from token
        user_id = payload.get("user_id")
        username = payload.get("sub")
        roles = payload.get("roles", [])
        scopes = payload.get("scopes", [])

        if not user_id or not username:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            )

        # Fetch user details from database including is_super_admin flag
        user_full_name = None
        user_title = None
        is_super_admin = False
        try:
            user_record = await user_repository.get_by_id(
                session, UUID(user_id)
            )
            if user_record:
                user_full_name = user_record.full_name
                user_title = user_record.title
                is_super_admin = user_record.is_super_admin
                logger.info(
                    f"[session] User {username} - is_super_admin from DB: {is_super_admin}"
                )
        except Exception as e:
            logger.warning(f"Could not fetch user details for {username}: {e}")

        # Get user's accessible pages with full bilingual information based on is_super_admin flag
        pages = []
        try:
            if is_super_admin:
                # Super admin sees all pages
                pages_result = await page_service.get_all_pages(session)
                logger.info(
                    f"[session] Super admin - fetched {len(pages_result) if pages_result else 0} pages"
                )
            else:
                # Regular user sees pages based on account ID
                pages_result = await page_service.get_pages_by_account(
                    session, user_id
                )
                logger.info(
                    f"[session] Regular user - fetched {len(pages_result) if pages_result else 0} pages"
                )

            if pages_result:
                # Return full page information with bilingual support using PageInfo model
                pages = [
                    PageInfo(
                        id=p.id,
                        name=p.get_name(locale),
                        description=p.get_description(locale),
                        name_en=p.name_en,
                        name_ar=p.name_ar,
                        description_en=p.description_en,
                        description_ar=p.description_ar,
                        parent_id=p.parent_id,
                    )
                    for p in pages_result
                ]
                logger.info(
                    f"[session] Prepared {len(pages)} page objects for response"
                )
        except Exception as e:
            logger.error(f"Could not fetch pages for user {username}: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            pages = []

        return SessionResponse(
            ok=True,
            user=SessionUserInfo(
                id=user_id,
                username=username,
                full_name=user_full_name,
                title=user_title,
                roles=roles,
                scopes=scopes,
                pages=pages,
                is_super_admin=is_super_admin,  # Use is_super_admin from database
                locale=locale,
            ),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating session: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
        )


@router.get("/validate", response_model=SessionResponse)
@limiter.limit("120/minute")  # Higher limit for SSR validation
async def validate_refresh_token(
    request: Request,
    refresh_cookie: str = Cookie(None, alias=settings.SESSION_COOKIE_NAME),
    session: AsyncSession = Depends(get_session),
):
    """
    Validate refresh token and return user info WITHOUT rotating the token.

    This endpoint is designed for SSR validation where multiple parallel requests
    may occur. Unlike /refresh, it does NOT rotate the refresh token.

    Locale is extracted from JWT refresh token (zero DB queries).

    Args:
        refresh_cookie: Refresh token from HttpOnly cookie
        session: Database session

    Returns:
        SessionResponse with user information including pages

    Raises:
        HTTPException: If refresh token is invalid or session doesn't exist
    """
    try:
        # Get token from cookie
        token = refresh_cookie
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No refresh token cookie found",
            )

        # Verify refresh token (just verify, don't rotate)
        payload = session_helpers.verify_refresh_token(token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )

        # Extract locale from JWT payload (zero DB queries!)
        locale = payload.get("locale", settings.DEFAULT_LOCALE)

        jti = payload.get("jti")
        user_id = payload.get("user_id")
        username = payload.get("sub")
        scopes = payload.get("scopes", ["user"])

        if not jti or not user_id or not username:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            )

        # Verify session exists and is not revoked
        db_session = await session_repository.get_by_refresh_id(session, jti)
        if not db_session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session not found",
            )

        if db_session.revoked:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session has been revoked",
            )

        # Check if session is expired
        now = datetime.utcnow()  # Use naive datetime to match database
        if db_session.expires_at < now:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session has expired",
            )

        # Try to get cached user data and pages (5-minute cache)
        cache_key = f"validation:user:{user_id}:{locale}"
        cached_data = await cache_get(cache_key)

        if cached_data:
            import json
            try:
                data = json.loads(cached_data)
                logger.debug(f"[validate] Using cached data for user {username}")

                # Return cached response
                return SessionResponse(
                    ok=True,
                    user=SessionUserInfo(
                        id=user_id,
                        username=username,
                        full_name=data.get("full_name"),
                        title=data.get("title"),
                        roles=payload.get("roles", []),
                        scopes=scopes,
                        pages=[PageInfo(**p) for p in data.get("pages", [])],
                        is_super_admin=data.get("is_super_admin", False),
                        locale=locale,
                    ),
                )
            except Exception as e:
                logger.warning(f"Failed to parse cached data for {username}: {e}")
                # Continue to fetch from database if cache parsing fails

        # Fetch user details from database including is_super_admin flag
        user_full_name = None
        user_title = None
        is_super_admin = False
        try:
            user_record = await user_repository.get_by_id(
                session, UUID(user_id)
            )
            if user_record:
                user_full_name = user_record.full_name
                user_title = user_record.title
                is_super_admin = user_record.is_super_admin
                logger.info(
                    f"[validate] User {username} - is_super_admin from DB: {is_super_admin}"
                )
            else:
                logger.warning(f"User record not found for user_id={user_id}")
        except Exception as e:
            logger.warning(f"Could not fetch user details for {username}: {e}")

        # Get user's accessible pages based on is_super_admin flag from database
        pages = []
        try:
            if is_super_admin:
                pages_result = await page_service.get_all_pages(session)
                logger.info(
                    f"[validate] Super admin - fetched {len(pages_result) if pages_result else 0} pages"
                )
            else:
                pages_result = await page_service.get_pages_by_account(
                    session, user_id
                )
                logger.info(
                    f"[validate] Regular user - fetched {len(pages_result) if pages_result else 0} pages"
                )

            if pages_result:
                pages = [
                    PageInfo(
                        id=p.id,
                        name=p.get_name(locale),
                        description=p.get_description(locale),
                        name_en=p.name_en,
                        name_ar=p.name_ar,
                        description_en=p.description_en,
                        description_ar=p.description_ar,
                        parent_id=p.parent_id,
                    )
                    for p in pages_result
                ]
                logger.info(
                    f"[validate] Prepared {len(pages)} page objects for response"
                )
        except Exception as e:
            logger.error(f"Could not fetch pages for user {username}: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            pages = []

        # Cache the user data and pages for 5 minutes (300 seconds)
        try:
            import json

            cache_data = {
                "full_name": user_full_name,
                "title": user_title,
                "is_super_admin": is_super_admin,
                "pages": [
                    {
                        "id": p.id,
                        "name": p.name,
                        "description": p.description,
                        "name_en": p.name_en,
                        "name_ar": p.name_ar,
                        "description_en": p.description_en,
                        "description_ar": p.description_ar,
                        "parent_id": p.parent_id,
                    }
                    for p in pages
                ],
            }

            await cache_set(cache_key, json.dumps(cache_data), ttl_seconds=300)
            logger.debug(f"[validate] Cached user data for {username} (TTL: 300s)")
        except Exception as e:
            logger.warning(f"Failed to cache user data for {username}: {e}")
            # Continue even if caching fails

        return SessionResponse(
            ok=True,
            user=SessionUserInfo(
                id=user_id,
                username=username,
                full_name=user_full_name,
                title=user_title,
                roles=payload.get("roles", []),
                scopes=scopes,
                pages=pages,
                is_super_admin=is_super_admin,  # Use is_super_admin from database
                locale=locale,
            ),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating refresh token: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
        )


@router.post("/refresh", response_model=TokenRefreshResponse)
@limiter.limit(
    "60/minute"
)  # Increased for SSR scenarios with multiple parallel requests
async def refresh_token(
    request: Request,
    response: Response,
    refresh_cookie: str = Cookie(None, alias=settings.SESSION_COOKIE_NAME),
    session: AsyncSession = Depends(get_session),
):
    """
    Refresh access token using stateful session (cookie-based).

    The refresh token is automatically extracted from the HttpOnly cookie.
    This endpoint rotates the refresh token and issues a new access token.

    Locale is preserved from JWT refresh token (zero DB queries).

    Args:
        refresh_cookie: Refresh token from HttpOnly cookie
        session: Database session

    Returns:
        Dict containing new access token

    Raises:
        HTTPException: If refresh token is invalid or expired
    """
    try:
        # Stateful session mode - get token from cookie
        token = refresh_cookie
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No refresh token cookie found",
            )

        # Verify refresh token
        payload = session_helpers.verify_refresh_token(token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )

        old_jti = payload.get("jti")
        user_id = payload.get("user_id")
        username = payload.get("sub")

        if not old_jti or not user_id or not username:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            )

        # Atomically rotate refresh token ID
        try:
            # Preserve locale from existing token payload (zero DB queries!)
            token_locale = payload.get("locale", settings.DEFAULT_LOCALE)

            new_refresh_token, new_jti, expires_at = (
                session_helpers.create_refresh_cookie_value(
                    user_id=user_id,
                    username=username,
                    scopes=payload.get("scopes", ["user"]),
                    roles=payload.get("roles", ["user"]),
                    locale=token_locale,
                )
            )

            # Update session with new refresh token ID and locale (with row lock)
            await session_repository.rotate_refresh_id(
                session=session,
                old_refresh_id=old_jti,
                new_refresh_id=new_jti,
                locale=token_locale,
            )

            # Issue new access token
            access_token, access_jti = session_helpers.issue_access_token(
                user_id=user_id,
                username=username,
                scopes=payload.get("scopes", ["user"]),
            )

            # Update cookie with new refresh token
            response.set_cookie(
                key=settings.SESSION_COOKIE_NAME,
                value=new_refresh_token,
                max_age=settings.SESSION_REFRESH_LIFETIME_DAYS * 24 * 60 * 60,
                httponly=True,
                secure=settings.SESSION_COOKIE_SECURE,
                samesite=settings.SESSION_COOKIE_SAMESITE,
            )

            # Locale cookie removed - locale now in JWT payload

            # Log successful token refresh
            await log_auth_service.log_authentication(
                session=session,
                user_id=user_id,
                action="token_refresh",
                is_successful=True,
                ip_address=request.client.host if request.client else None,
                result={"old_token_id": old_jti, "new_token_id": new_jti},
            )

            return TokenRefreshResponse(
                access_token=access_token,
                token_type="bearer",
                expires_in=settings.SESSION_ACCESS_TOKEN_MINUTES * 60,
            )

        except Exception as e:
            logger.error(f"Error rotating session: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Failed to rotate session",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error refreshing token: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )


@router.post("/logout", response_model=LogoutResponse)
@limiter.limit("30/minute")
async def logout(
    request: Request,
    response: Response,
    refresh_cookie: str = Cookie(None, alias=settings.SESSION_COOKIE_NAME),
    session: AsyncSession = Depends(get_session),
):
    """
    Logout and revoke session (cookie-based stateful sessions).

    Revokes the user session in the database and clears the refresh token cookie.

    Args:
        refresh_cookie: Refresh token from HttpOnly cookie
        session: Database session

    Returns:
        Dict with success message
    """
    try:
        # Stateful session mode - revoke session and clear cookie
        refresh_token = refresh_cookie
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No refresh token cookie found",
            )

        # Verify and decode refresh token
        payload = session_helpers.verify_refresh_token(refresh_token)
        if not payload:
            # Even if token is invalid, clear the cookie
            response.delete_cookie(key=settings.SESSION_COOKIE_NAME)
            return LogoutResponse(message="Logged out successfully", ok=True)

        jti = payload.get("jti")
        user_id = payload.get("user_id")

        if jti:
            # Revoke the session
            await session_repository.revoke_session(
                session=session, refresh_token_id=jti
            )

        # Log successful logout
        await log_auth_service.log_authentication(
            session=session,
            user_id=user_id,
            action="logout",
            is_successful=True,
            ip_address=request.client.host if request.client else None,
            result={"session_id": jti},
        )

        # Clear the refresh token cookie
        response.delete_cookie(
            key=settings.SESSION_COOKIE_NAME,
            httponly=True,
            secure=settings.SESSION_COOKIE_SECURE,
            samesite=settings.SESSION_COOKIE_SAMESITE,
        )

        return LogoutResponse(message="Logged out successfully", ok=True)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during logout: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error during logout",
        )
