"""
Navigation Endpoints - Permission-aware, localized navigation tree API.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_maria_session as get_session
from api.deps import parse_accept_language
from api.schemas._base import CamelModel
from api.services.navigation_service import NavigationService
from core.sessions import verify_access_token, verify_refresh_token
from db.model import User
from core.config import settings
from utils.icon_validation import get_icon_allowlist, get_icon_allowlist_version
from utils.security import require_authenticated

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/navigation", tags=["navigation"])


class NavigationResponse(CamelModel):
    """Response model for navigation tree."""

    nodes: List[dict]
    locale: str
    nav_type: Optional[str]


class IconAllowlistResponse(CamelModel):
    """Response model for icon allowlist."""

    icons: List[str]
    version: str
    count: int


async def get_current_user_optional_for_nav(
    request: Request, session: AsyncSession = Depends(get_session)
) -> tuple[Optional[str], bool]:
    """
    Get current user ID and super_admin status if authenticated.

    Extracts user information from access token if present. This allows
    navigation to be permission-aware while still working for unauthenticated users.

    Args:
        request: FastAPI Request object
        session: Database session

    Returns:
        Tuple of (user_id, is_super_admin) or (None, False) if unauthenticated
    """
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
            return None, False

        # Decode and verify access token
        payload = verify_access_token(token)
        if not payload:
            return None, False

        user_id = payload.get("user_id")
        if not user_id:
            return None, False

        # Query database for user's super_admin status
        result = await session.execute(
            select(User.is_super_admin).where(User.id == user_id)
        )
        is_super_admin = result.scalar_one_or_none()

        if is_super_admin is None:
            # User not found in database
            return None, False

        return user_id, is_super_admin

    except Exception as e:
        # If anything fails, just return unauthenticated (don't block navigation)
        logger.debug(f"Failed to get user context for navigation: {e}")
        return None, False


@router.get("", response_model=NavigationResponse)
async def get_navigation(
    request: Request,
    nav_type: Optional[str] = Query(
        None, description="Filter by navigation type (e.g., 'primary', 'sidebar')"
    ),
    lang: Optional[str] = Query(None, description="Override locale (e.g., 'en', 'ar')"),
    session: AsyncSession = Depends(get_session),
    payload: dict = Depends(require_authenticated),
):
    """
    Get permission-filtered, localized navigation tree.

    Requires authentication - only authenticated users can access this endpoint.

    Returns a hierarchical navigation structure with:
    - Bilingual fields (name_en, name_ar, description_en, description_ar)
    - Resolved name/description based on locale
    - Icons (lucide-react identifiers)
    - Parent-child relationships
    - Permission filtering (only shows pages user can access)

    Locale Resolution:
        1. lang query parameter (for testing/override)
        2. JWT refresh token payload (authenticated users, zero DB queries)
        3. Accept-Language header
        4. Default locale (settings.locale.default_locale)

    Query Parameters:
        - nav_type: Filter by navigation type (optional)
        - lang: Override locale via query parameter (optional)

    Headers:
        - Accept-Language: Used for locale detection if no JWT or lang param
        - Authorization: Bearer token for authenticated requests (required)

    Authentication:
        - Requires valid JWT access token or session cookie
        - Token can be passed via Authorization: Bearer <token> header
        - Or via session cookie (refresh token)
    """
    try:
        # Determine locale (zero DB queries!)
        locale = settings.locale.default_locale

        # Priority 1: Query parameter override
        if lang and lang.lower() in settings.locale.supported_locales:
            locale = lang.lower()
            logger.debug(f"[get_navigation] Using locale from query param: {locale}")
        else:
            # Priority 2: Try JWT payload (no DB query!)
            try:
                refresh_token = request.cookies.get(settings.session.cookie_name)
                if refresh_token:
                    payload = verify_refresh_token(refresh_token)
                    if payload and "locale" in payload:
                        locale = payload["locale"]
                        logger.debug(
                            f"[get_navigation] Using locale from JWT: {locale}"
                        )
            except Exception as e:
                logger.debug(f"[get_navigation] Failed to get locale from JWT: {e}")

            # Priority 3: Accept-Language header
            if locale == settings.locale.default_locale:
                accept_language = request.headers.get("accept-language")
                if accept_language:
                    languages = parse_accept_language(accept_language)
                    for lang_code, _ in languages:
                        if lang_code in settings.locale.supported_locales:
                            locale = lang_code
                            logger.debug(
                                f"[get_navigation] Using locale from Accept-Language: {locale}"
                            )
                            break

        # Get user context (optional, for permission filtering)
        user_id, is_super_admin = await get_current_user_optional_for_nav(
            request, session
        )

        # Build navigation tree
        nav_service = NavigationService()
        tree = await nav_service.build_navigation_tree(
            session=session,
            locale=locale,
            nav_type=nav_type,
            user_id=user_id,
            is_super_admin=is_super_admin,
        )

        # Convert to dict format
        nodes = [node.to_dict() for node in tree]

        return NavigationResponse(
            nodes=nodes,
            locale=locale,
            nav_type=nav_type,
        )

    except Exception as e:
        logger.error(f"Error building navigation tree: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve navigation",
        )


@router.get("/icons", response_model=IconAllowlistResponse)
async def get_icon_list():
    """
    Get list of allowed lucide-react icon identifiers.

    Public endpoint - no authentication required.

    Returns the allowlist of valid icon names for use in page configuration.
    Frontend can use this to populate icon pickers.

    Returns:
        IconAllowlistResponse with list of icon names, version, and count
    """
    try:
        icons = sorted(list(get_icon_allowlist()))
        version = get_icon_allowlist_version()

        return IconAllowlistResponse(
            icons=icons,
            version=version,
            count=len(icons),
        )

    except Exception as e:
        logger.error(f"Error retrieving icon allowlist: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve icon allowlist",
        )
