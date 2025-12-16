"""
CORS allowlist service using centralized settings.

This service provides a unified interface for checking allowed CORS origins:
1. ALLOWED_ORIGINS from settings
2. Default origins based on environment (local vs production)
"""

import logging
from typing import List, Optional

from fastapi import Request

from settings import settings

logger = logging.getLogger(__name__)


class CORSAllowlistService:
    """Service for managing CORS allowed origins from environment variables."""

    # Default allowed origins for local development
    DEFAULT_LOCAL_ORIGINS = [
        "http://localhost:3000",
        "http://localhost:8080",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8080",
    ]

    # Default allowed origins for production
    DEFAULT_PROD_ORIGINS = []

    @staticmethod
    def get_allowed_origins_from_settings() -> List[str]:
        """
        Get allowed origins from settings.

        Returns:
            List of allowed origins
        """
        origins = settings.ALLOWED_ORIGINS or []
        return [origin.strip() for origin in origins if origin]

    @staticmethod
    def get_all_allowed_origins() -> List[str]:
        """
        Get all allowed origins with fallback priority:
        1. ALLOWED_ORIGINS from settings
        2. Default origins based on environment

        Returns:
            List of allowed origins
        """
        all_origins = set()

        # Priority 1: Settings
        settings_origins = CORSAllowlistService.get_allowed_origins_from_settings()
        all_origins.update(settings_origins)

        # Priority 2: Default origins (if no origins configured)
        if not all_origins:
            environment = settings.ENVIRONMENT.lower()
            if environment == "local":
                default_origins = CORSAllowlistService.DEFAULT_LOCAL_ORIGINS
            else:
                default_origins = CORSAllowlistService.DEFAULT_PROD_ORIGINS
            all_origins.update(default_origins)

        return list(all_origins)

    @staticmethod
    def is_origin_allowed(origin: str) -> bool:
        """
        Check if an origin is allowed.

        Args:
            origin: Origin to check

        Returns:
            True if origin is allowed, False otherwise
        """
        if not origin:
            return False

        # Check settings
        settings_origins = CORSAllowlistService.get_allowed_origins_from_settings()
        if origin in settings_origins:
            return True

        # Check default origins
        environment = settings.ENVIRONMENT.lower()
        if environment == "local":
            default_origins = CORSAllowlistService.DEFAULT_LOCAL_ORIGINS
        else:
            default_origins = CORSAllowlistService.DEFAULT_PROD_ORIGINS

        if origin in default_origins:
            return True

        return False

    @staticmethod
    async def get_request_origin(request: Request) -> Optional[str]:
        """
        Get the origin from a FastAPI request.

        Args:
            request: FastAPI request object

        Returns:
            Origin string or None
        """
        # Try to get origin from headers
        origin = request.headers.get("origin")
        if origin:
            return origin

        # Fallback to referer (less secure but sometimes necessary)
        referer = request.headers.get("referer")
        if referer:
            # Extract origin from referer
            try:
                from urllib.parse import urlparse

                parsed = urlparse(referer)
                return f"{parsed.scheme}://{parsed.netloc}"
            except Exception:
                pass

        return None

    @staticmethod
    def get_cors_config() -> dict:
        """
        Get CORS configuration dictionary for FastAPI.

        Returns:
            CORS configuration dictionary
        """
        allowed_origins = CORSAllowlistService.get_all_allowed_origins()

        config = {
            "allow_origins": allowed_origins,
            "allow_credentials": True,
            "allow_methods": [
                "GET",
                "POST",
                "PUT",
                "DELETE",
                "OPTIONS",
                "PATCH",
            ],
            "allow_headers": [
                "Authorization",
                "Content-Type",
                "X-Requested-With",
                "Accept",
                "Origin",
                "Access-Control-Request-Method",
                "Access-Control-Request-Headers",
            ],
            "expose_headers": [
                "X-Total-Count",
                "X-Request-ID",
                "X-Correlation-ID",
            ],
            "max_age": 86400,  # 24 hours
        }

        logger.info(
            "CORS configuration loaded",
            extra={
                "allowed_origins": allowed_origins,
                "origin_count": len(allowed_origins),
            },
        )

        return config


# Export main class
__all__ = [
    "CORSAllowlistService",
]
