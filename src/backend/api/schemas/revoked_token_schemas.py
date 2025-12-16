"""
RevokedToken Schemas - Pydantic DTOs for RevokedToken entity.
"""

from datetime import datetime
from uuid import UUID

from pydantic import ConfigDict, Field

from api.schemas._base import CamelModel
from api.schemas.user_schemas import UserResponse


class RevokedTokenBase(CamelModel):
    """Base revoked token schema."""

    user_id: UUID
    jti: str = Field(min_length=1, max_length=36)
    token_type: str = Field(min_length=1, max_length=20)

    model_config = ConfigDict(from_attributes=True)


class RevokedTokenCreate(RevokedTokenBase):
    """Schema for creating a revoked token record."""

    pass


class RevokedTokenResponse(RevokedTokenBase):
    """Schema for returning revoked token data."""

    id: int
    revoked_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LoginRequest(CamelModel):
    """Schema for login request."""

    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1)
    scope: str = Field(
        default="local",
        description="Authentication scope: 'domain' or 'local'",
    )


class TokenResponse(CamelModel):
    """Schema for token response after successful login."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Access token expiration in seconds")


class RefreshTokenRequest(CamelModel):
    """Schema for token refresh request."""

    refresh_token: str


class LoginResponse(CamelModel):
    """Full login response with user info and tokens."""

    user: "UserResponse"
    tokens: TokenResponse

    model_config = ConfigDict(from_attributes=True)


LoginResponse.model_rebuild()
