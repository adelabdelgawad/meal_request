from sqlalchemy.ext.asyncio import AsyncSession

"""
Internal Token Service - Manages internal service token generation and verification.

Handles token issuance and validation for service-to-service communication.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Optional

from core.exceptions import ValidationError
from core.security import create_jwt, decode_jwt

logger = logging.getLogger(__name__)


class InternalTokenService:
    """Service for managing internal service tokens."""

    def __init__(self, token_expire_minutes: int = 60):
        """
        Initialize the internal token service.

        Args:
            token_expire_minutes: Token expiration time in minutes
        """
        self.token_expire_minutes = token_expire_minutes

    async def issue_token(
        self,
        service_name: str,
        user_id: Optional[str] = None,
        permissions: Optional[list] = None,
        metadata: Optional[Dict] = None,
    ) -> tuple[str, datetime]:
        """
        Issue an internal service token.

        Args:
            service_name: Name of the service requesting the token
            user_id: Optional user ID for the token
            permissions: Optional list of permissions
            metadata: Optional metadata to include in token

        Returns:
            Tuple of (token, expires_at datetime)

        Raises:
            ValidationError: If service_name is invalid
        """
        if not service_name or not isinstance(service_name, str):
            raise ValidationError("service_name must be a non-empty string")

        try:
            now = datetime.utcnow()
            expires_at = now + timedelta(minutes=self.token_expire_minutes)

            token_data = {
                "sub": service_name,
                "service": service_name,
                "type": "internal_service",
                "iat": now,
                "exp": expires_at,
                "user_id": user_id,
                "permissions": permissions or [],
                "metadata": metadata or {},
            }

            # Create JWT token
            access_token, _ = create_jwt(
                data=token_data,
                token_type="internal_service",
                expires_delta=timedelta(minutes=self.token_expire_minutes),
            )

            logger.info(f"Internal token issued for service: {service_name}")

            return access_token, expires_at

        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Failed to issue internal token for {service_name}: {e}")
            raise ValidationError(f"Failed to issue internal token: {str(e)}")

    async def verify_token(self, token: str) -> Dict:
        """
        Verify an internal service token.

        Args:
            token: Token to verify

        Returns:
            Dictionary with verification result:
            - valid: bool indicating token validity
            - claims: Token claims if valid, None otherwise
            - service_name: Service name from token if valid
            - expires_at: Token expiration time if valid
            - error: Error message if invalid

        Raises:
            ValidationError: If token format is invalid
        """
        if not token:
            raise ValidationError("Token is required")

        try:
            # Decode and verify the token
            payload = decode_jwt(token)

            # Check if it's an internal service token
            if payload.get("type") != "internal_service":
                return {
                    "valid": False,
                    "error": "Token is not an internal service token",
                    "claims": None,
                    "service_name": None,
                    "expires_at": None,
                }

            # Extract relevant information
            service_name = payload.get("service")
            expires_timestamp = payload.get("exp")
            expires_at = datetime.fromtimestamp(expires_timestamp).isoformat() if expires_timestamp else None

            logger.info(f"Internal token verified for service: {service_name}")

            return {
                "valid": True,
                "claims": payload,
                "service_name": service_name,
                "expires_at": expires_at,
                "error": None,
            }

        except ValidationError as e:
            logger.warning(f"Token verification failed: {str(e)}")
            error_msg = "Token expired" if "expired" in str(e).lower() else "Invalid token"
            return {
                "valid": False,
                "error": error_msg,
                "claims": None,
                "service_name": None,
                "expires_at": None,
            }
        except Exception as e:
            logger.error(f"Token verification error: {e}")
            return {
                "valid": False,
                "error": str(e),
                "claims": None,
                "service_name": None,
                "expires_at": None,
            }
