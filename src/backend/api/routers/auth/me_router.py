"""
User Profile Endpoints (/me) - User-specific operations like locale preference.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import Field

from core.dependencies import SessionDep, CurrentUserDep, ActiveUserDep get_session
from api.repositories.user_repository import UserRepository
from api.schemas._base import CamelModel
from core.dependencies import SessionDep
from core.exceptions import DatabaseError, NotFoundError
from core.config import settings
from utils.security import require_authenticated

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/me", tags=["user-profile"])


class LocalePreferenceRequest(CamelModel):
    """Request body for setting user locale preference."""

    locale: str = Field(
        ..., description="Locale code (e.g., 'en', 'ar')", min_length=2, max_length=2
    )


class LocalePreferenceResponse(CamelModel):
    """Response for locale preference update."""

    message: str
    locale: str


class LocaleGetResponse(CamelModel):
    """Response for getting current locale."""

    locale: str


@router.get("/locale", response_model=LocaleGetResponse)
async def get_locale_preference(
    current_user: dict = Depends(require_authenticated),
) -> LocaleGetResponse:
    """
    Get user's current locale from JWT payload. Requires authentication.

    Returns locale from cached JWT (no DB query).
    Frontend can call this on initial load to sync localStorage with backend.

    Args:
        current_user: Current authenticated user from JWT

    Returns:
        LocaleGetResponse with current locale
    """
    locale = current_user.get("locale", settings.locale.default_locale)
    logger.info(f"[get_locale_preference] Returning locale from JWT: {locale}")

    return LocaleGetResponse(locale=locale)


@router.post("/locale", response_model=LocalePreferenceResponse)
async def set_locale_preference(
    request: LocalePreferenceRequest,
    response: Response,
    current_user: dict = Depends(require_authenticated),
    session: SessionDep,
):
    """
    Set user's preferred locale. Requires authentication.

    Updates:
    1. Database (User.preferred_locale) - source of truth
    2. Session metadata - for session tracking
    3. JWT refresh token - rotates token with new locale in payload

    No locale cookie is set - frontend uses localStorage.

    Args:
        request: Locale preference request body
        response: FastAPI Response object for setting refresh token cookie
        current_user: Current authenticated user from JWT
        session: Database session

    Returns:
        LocalePreferenceResponse with confirmation message

    Raises:
        HTTPException: If locale is invalid or update fails
    """
    from api.repositories.session_repository import SessionRepository
    from core import sessions as session_helpers

    try:
        locale = request.locale.lower()
        logger.info(
            f"[set_locale_preference] Received request to change locale to: {locale}"
        )

        # Validate locale
        if locale not in settings.locale.supported_locales:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid locale '{locale}'. Supported locales: {', '.join(settings.locale.supported_locales)}",
            )

        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User ID not found in token",
            )

        logger.info(f"[set_locale_preference] Updating locale for user_id: {user_id}")

        # 1. Update database (source of truth)
        user_repository_instance = UserRepository()
        await user_repository_instance.update_preferred_locale(
            session=session,
            user_id=user_id,
            locale=locale,
        )

        logger.info("[set_locale_preference] Updated preferred_locale in database")

        # 2. Create new refresh token with updated locale
        username = current_user.get("sub")
        scopes = current_user.get("scopes", ["user"])
        roles = current_user.get("roles", ["user"])

        new_refresh_token, new_jti, new_expires_at = (
            session_helpers.create_refresh_cookie_value(
                user_id=user_id,
                username=username,
                scopes=scopes,
                roles=roles,
                locale=locale,  # NEW locale in JWT payload
            )
        )

        logger.info(
            f"[set_locale_preference] Created new refresh token with locale: {locale}"
        )

        # 3. Rotate refresh token in session (also updates session_metadata.locale)
        session_repository = SessionRepository(session)
        old_jti = current_user.get("jti")

        await session_repository.rotate_refresh_id(
            session=session,
            old_refresh_id=old_jti,
            new_refresh_id=new_jti,
            locale=locale,
        )

        logger.info("[set_locale_preference] Rotated refresh token in session")
        # Session will be auto-committed by get_maria_session() context manager

        # 4. Set new refresh token cookie (with new locale in JWT)
        response.set_cookie(
            key=settings.session.cookie_name,
            value=new_refresh_token,
            max_age=settings.session.refresh_lifetime_days * 24 * 60 * 60,
            secure=settings.session.cookie_secure,
            samesite=settings.session.cookie_samesite,
            path="/",  # Available across entire site
        )

        logger.info(
            f"User {user_id} updated preferred locale to '{locale}' (JWT rotated, cookie set)"
        )

        return LocalePreferenceResponse(
            message=f"Locale preference updated to '{locale}'",
            locale=locale,
        )

    except NotFoundError as e:
        logger.warning(f"User not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except DatabaseError as e:
        logger.error(f"Database error updating locale: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error setting locale preference: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update locale preference",
        )
