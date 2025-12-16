"""
User Schemas - Pydantic DTOs for User entity.

These schemas match the actual User model in db/models.py.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import ConfigDict, Field

from api.schemas._base import CamelModel
from api.schemas.role_schemas import SimpleRole
from core.user_source_enum import UserSourceMetadata


class UserBase(CamelModel):
    """Base user schema with common fields matching the User model."""

    username: str = Field(min_length=3, max_length=64)
    full_name: Optional[str] = Field(None, max_length=128)
    title: Optional[str] = Field(None, max_length=64)
    is_domain_user: bool = True  # Default True: all users are domain users except super admin
    is_super_admin: bool = False
    is_blocked: bool = False
    preferred_locale: Optional[str] = Field(None, max_length=2)

    model_config = ConfigDict(from_attributes=True)


class UserCreate(CamelModel):
    """Schema for creating a new user."""

    username: str = Field(min_length=3, max_length=64)
    email: Optional[str] = Field(None, max_length=128)
    password: Optional[str] = Field(
        None,
        description="Password required for local users (optional for domain users)",
    )
    full_name: Optional[str] = Field(None, max_length=128)
    title: Optional[str] = Field(None, max_length=64)
    is_domain_user: bool = True  # Default True: all users are domain users except super admin

    model_config = ConfigDict(from_attributes=True)


class UserUpdate(CamelModel):
    """Schema for updating a user."""

    full_name: Optional[str] = Field(None, max_length=128)
    title: Optional[str] = Field(None, max_length=64)
    preferred_locale: Optional[str] = Field(None, max_length=2)

    model_config = ConfigDict(from_attributes=True)


class UserRolesUpdate(CamelModel):
    """Schema for updating user roles."""

    role_ids: List[int] = Field(description="List of role IDs to assign to user")

    model_config = ConfigDict(from_attributes=True)


class UserStatusUpdate(CamelModel):
    """Schema for updating user active status."""

    is_active: bool = Field(description="Whether the user is active")

    model_config = ConfigDict(from_attributes=True)


class UserBlockUpdate(CamelModel):
    """Schema for updating user blocked status."""

    is_blocked: bool = Field(description="Whether the user is blocked")

    model_config = ConfigDict(from_attributes=True)


class UserBulkStatusUpdate(CamelModel):
    """Schema for bulk updating user active status."""

    user_ids: List[str] = Field(description="List of user IDs (UUIDs)")
    is_active: bool = Field(description="Whether the users should be active")

    model_config = ConfigDict(from_attributes=True)


class UserBulkStatusResponse(CamelModel):
    """Schema for bulk status update response."""

    updated_users: List["UserResponse"] = Field(description="List of updated users")
    updated_count: int = Field(description="Number of users updated")

    model_config = ConfigDict(from_attributes=True)


class UserResponse(CamelModel):
    """Schema for returning user data in API responses.

    Note: id is stored as CHAR(36) UUID string in the database.
    Includes all fields expected by frontend.
    Includes Strategy A fields: user_source, status_override, etc.
    """

    id: str
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    title: Optional[str] = None
    is_active: bool = True  # Default to true since User model doesn't have this
    is_blocked: bool = False
    is_domain_user: bool = True  # Default True: all users are domain users except super admin
    is_super_admin: bool = False
    role_id: Optional[int] = None
    roles: List[str] = Field(default_factory=list)  # Role names for display
    role_ids: List[int] = Field(default_factory=list)  # Role IDs for matching
    assigned_department_count: Optional[int] = Field(
        None,
        description="Number of departments assigned to user. 0/null = access to ALL departments"
    )

    # Strategy A: Source Tracking and Status Override Fields (Simplified to hris/manual)
    user_source: str = Field(
        default="hris",
        description="Source of user record: 'hris' or 'manual'"
    )
    user_source_metadata: Optional[UserSourceMetadata] = Field(
        None,
        description="Localized metadata for user source (name_en, name_ar, descriptions, icons)"
    )
    status_override: bool = Field(
        default=False,
        description="If true, is_active status is manually controlled (HRIS sync skips)"
    )
    override_reason: Optional[str] = Field(
        None,
        description="Admin-provided reason for status override"
    )
    override_set_by_id: Optional[str] = Field(
        None,
        description="User ID of admin who set the override"
    )
    override_set_at: Optional[datetime] = Field(
        None,
        description="Timestamp when override was enabled"
    )

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)


class UsersListResponse(CamelModel):
    """Schema for paginated users list response expected by frontend."""

    users: List[UserResponse]
    total: int
    active_count: int = 0
    inactive_count: int = 0
    role_options: List[SimpleRole] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class UserListResponse(CamelModel):
    """Schema for user list response (lightweight version)."""

    id: str
    username: str
    full_name: Optional[str] = None
    title: Optional[str] = None
    is_domain_user: bool = True  # Default True: all users are domain users except super admin
    is_super_admin: bool = False

    model_config = ConfigDict(from_attributes=True)


# Strategy A: User Source and Override Management Schemas

class UserMarkManualRequest(CamelModel):
    """Schema for marking a user as manual (non-HRIS)."""

    reason: str = Field(
        min_length=20,
        max_length=500,
        description="Reason for marking user as manual (min 20 characters)"
    )

    model_config = ConfigDict(from_attributes=True)


class UserStatusOverrideRequest(CamelModel):
    """Schema for enabling/disabling status override for a user."""

    status_override: bool = Field(
        description="Whether to enable (true) or disable (false) status override"
    )
    override_reason: Optional[str] = Field(
        None,
        min_length=20,
        max_length=500,
        description="Reason for override (required when enabling, min 20 characters)"
    )

    model_config = ConfigDict(from_attributes=True)


class UserStatusOverrideResponse(CamelModel):
    """Schema for status override operation response."""

    user: UserResponse = Field(description="Updated user object")
    message: str = Field(description="Success message")

    model_config = ConfigDict(from_attributes=True)
