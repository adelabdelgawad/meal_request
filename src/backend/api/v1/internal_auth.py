"""
Internal Auth Endpoints - Service-to-service authentication.

Provides token issuance and verification for internal service communication.
"""

import logging
import os
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status

from api.schemas import (
    InternalTokenCreate,
    InternalTokenResponse,
    InternalTokenVerifyRequest,
    InternalTokenVerifyResponse,
    ServiceConfigResponse,
    ServiceHealthResponse,
)
from api.services.internal_token_service import InternalTokenService
from core.exceptions import ValidationError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/internal", tags=["internal-auth"])

# Configuration
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY", "dev-internal-key-123")
INTERNAL_TOKEN_EXPIRE_MINUTES = int(os.getenv("INTERNAL_TOKEN_EXPIRE_MINUTES", "60"))


# Dependency to verify internal API key
async def verify_internal_api_key(
    x_internal_api_key: Optional[str] = Header(None),
):
    """Verify the internal API key for service authentication."""
    if not x_internal_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-Internal-API-Key header is required",
        )

    if x_internal_api_key != INTERNAL_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid internal API key",
        )

    return x_internal_api_key


@router.post("/token", response_model=InternalTokenResponse, status_code=status.HTTP_201_CREATED)
async def issue_internal_token(
    request: InternalTokenCreate,
    _: str = Depends(verify_internal_api_key),
):
    """
    Issue an internal service token.

    This endpoint is used by internal services to obtain tokens for
    authenticating with other services in the system.

    Args:
        request: Token issuance request containing service details
        service: Internal token service instance
        _: Verified internal API key

    Returns:
        InternalTokenResponse: Contains the issued token and metadata

    Raises:
        HTTPException: If the request is invalid or authentication fails
        ValidationError: If validation fails
    """
    service = InternalTokenService(INTERNAL_TOKEN_EXPIRE_MINUTES)
    try:
        access_token, expires_at = await service.issue_token(
            service_name=request.service_name,
            user_id=request.user_id,
            permissions=request.permissions,
            metadata=request.metadata,
        )

        return InternalTokenResponse(
            access_token=access_token,
            expires_in=INTERNAL_TOKEN_EXPIRE_MINUTES * 60,  # Convert to seconds
            service_name=request.service_name,
            issued_at=expires_at.isoformat(),
            expires_at=expires_at.isoformat(),
        )

    except ValidationError as e:
        logger.warning(f"Validation error during token issuance: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to issue internal token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to issue internal token",
        )



@router.post("/verify", response_model=InternalTokenVerifyResponse)
async def verify_internal_token(
    request: InternalTokenVerifyRequest,
    _: str = Depends(verify_internal_api_key),
):
    """
    Verify an internal service token.

    This endpoint is used by internal services to verify tokens
    received from other services in the system.

    Args:
        request: Token verification request containing the token to verify
        service: Internal token service instance
        _: Verified internal API key

    Returns:
        InternalTokenVerifyResponse: Contains verification result and token claims

    Raises:
        HTTPException: If the request is invalid or authentication fails
    """
    service = InternalTokenService(INTERNAL_TOKEN_EXPIRE_MINUTES)
    try:
        result = await service.verify_token(request.token)

        return InternalTokenVerifyResponse(
            valid=result["valid"],
            claims=result["claims"],
            error=result["error"],
            service_name=result["service_name"],
            expires_at=result["expires_at"],
        )

    except ValidationError as e:
        logger.warning(f"Validation error during token verification: {str(e)}")
        return InternalTokenVerifyResponse(
            valid=False,
            error=str(e),
            claims=None,
            service_name=None,
            expires_at=None,
        )
    except Exception as e:
        logger.error(f"Token verification error: {e}")
        return InternalTokenVerifyResponse(
            valid=False,
            error="Verification failed",
            claims=None,
            service_name=None,
            expires_at=None,
        )



@router.get("/health", response_model=ServiceHealthResponse)
async def auth_service_health(
    _: str = Depends(verify_internal_api_key),
):
    """
    Health check endpoint for the internal auth service.

    Args:
        _: Verified internal API key

    Returns:
        ServiceHealthResponse: Service health status and configuration
    """
    return ServiceHealthResponse(
        service="internal_auth",
        status="healthy",
        version="1.0.0",
        features={
            "token_issuance": True,
            "token_verification": True,
            "api_key_authentication": True,
        },
        configuration={
            "token_expiry_minutes": INTERNAL_TOKEN_EXPIRE_MINUTES,
            "algorithm": "HS256",
        },
    )



@router.get("/config", response_model=ServiceConfigResponse)
async def auth_service_config(
    _: str = Depends(verify_internal_api_key),
):
    """
    Get service configuration (non-sensitive).

    Args:
        _: Verified internal API key

    Returns:
        ServiceConfigResponse: Public configuration information
    """
    return ServiceConfigResponse(
        service_name="internal_auth",
        endpoints={
            "token_issuance": "/api/v1/internal/token",
            "token_verification": "/api/v1/internal/verify",
            "health_check": "/api/v1/internal/health",
            "configuration": "/api/v1/internal/config",
        },
        requirements={
            "headers": ["X-Internal-API-Key"],
            "authentication": "Bearer token in Authorization header",
        },
    )
