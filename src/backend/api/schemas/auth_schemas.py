"""
Authentication Schemas - Login, token refresh, and session models.

Provides request/response models for user authentication endpoints.
All response models use CamelModel to ensure camelCase JSON output.
"""

from typing import List, Optional

from pydantic import Field, ConfigDict

from api.schemas._base import CamelModel


class UserInfo(CamelModel):
    """User information included in auth responses."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="User ID (UUID)")
    username: str = Field(..., description="Username")
    full_name: Optional[str] = Field(None, description="User's full name")
    title: Optional[str] = Field(None, description="User's job title")
    is_super_admin: bool = Field(..., description="Super admin flag")
    locale: str = Field(default="en", description="User's preferred locale")


class PageInfo(CamelModel):
    """Page information included in auth responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Page ID")
    name: str = Field(..., description="Localized page name")
    description: Optional[str] = Field(None, description="Localized page description")
    name_en: str = Field(..., description="English page name")
    name_ar: str = Field(..., description="Arabic page name")
    description_en: Optional[str] = Field(None, description="English description")
    description_ar: Optional[str] = Field(None, description="Arabic description")
    parent_id: Optional[int] = Field(None, description="Parent page ID for hierarchy")


class LoginResponse(CamelModel):
    """Response model for successful login.

    Note: Refresh token is stored in HttpOnly cookie (SESSION_COOKIE_NAME),
    not returned in response body for security.
    """

    model_config = ConfigDict(from_attributes=True)

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration in seconds")
    user: UserInfo = Field(..., description="User information")
    pages: List[PageInfo] = Field(default_factory=list, description="User's accessible pages")


class TokenRefreshResponse(CamelModel):
    """Response model for token refresh."""

    model_config = ConfigDict(from_attributes=True)

    access_token: str = Field(..., description="New JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration in seconds")


class SessionUserInfo(CamelModel):
    """User information returned from session validation."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="User ID (UUID)")
    username: str = Field(..., description="Username")
    full_name: Optional[str] = Field(None, description="User's full name")
    title: Optional[str] = Field(None, description="User's job title")
    roles: List[str] = Field(default_factory=list, description="User roles")
    scopes: List[str] = Field(default_factory=list, description="User scopes")
    pages: List[PageInfo] = Field(default_factory=list, description="User's accessible pages")
    is_super_admin: bool = Field(default=False, description="Super admin flag")
    locale: str = Field(default="en", description="User's preferred locale")


class SessionResponse(CamelModel):
    """Response model for session validation."""

    model_config = ConfigDict(from_attributes=True)

    ok: bool = Field(default=True, description="Success flag")
    user: SessionUserInfo = Field(..., description="User information with roles and scopes")


class LogoutResponse(CamelModel):
    """Response model for logout."""

    model_config = ConfigDict(from_attributes=True)

    message: str = Field(..., description="Logout confirmation message")
    ok: bool = Field(default=True, description="Success flag")
